import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from ai_boss.config.loader import load_config
from ai_boss.core.errors import AIBossError
from ai_boss.core.git_guard import GitGuard
from ai_boss.core.orchestrator import Orchestrator
from ai_boss.core.preflight import build_preflight
from ai_boss.core.task_classifier import TaskClassifier
from ai_boss.memory.obsidian_vault import ObsidianVault
from ai_boss.memory.project_store import ProjectStore
from ai_boss.memory.state_store import WorkerStateStore
from ai_boss.models.task import TaskType
from ai_boss.web.server import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT, serve_web


app = typer.Typer(
    help="AI-Boss Super Brain: локальный оркестратор AI CLI-инструментов.",
    invoke_without_command=True,
    no_args_is_help=False,
)
console = Console()


@app.callback()
def main(ctx: typer.Context) -> None:
    """Запустить интерактивный режим, если команда не указана."""
    if ctx.invoked_subcommand is None:
        interactive()


def interactive() -> None:
    """Интерактивная сессия AI-Boss."""
    config = load_config()
    project_path = _infer_initial_project(config)
    console.print("[bold green]AI-Boss Super Brain[/bold green]")
    console.print("Пишите задачу обычным текстом. Служебные команды: /help, /status, /preflight, /tasks, /project, /exit.")
    if project_path:
        console.print(f"[dim]Проект сессии: {project_path}[/dim]")
    else:
        console.print("[yellow]Проект не выбран.[/yellow] Для изменения кода перейдите в git-папку или введите `/project /path/to/project`.")

    while True:
        try:
            text = input("ai-boss> ").strip()
        except EOFError:
            console.print()
            return
        except KeyboardInterrupt:
            console.print("\nВыход.")
            return

        if not text:
            continue
        if text in {"/exit", "/quit", "exit", "quit", "q"}:
            console.print("Готово, сессия закрыта.")
            return
        if text == "/help":
            _print_interactive_help()
            continue
        if text == "/status":
            _print_status(config)
            continue
        if text == "/preflight":
            _print_preflight(config, project_path)
            continue
        if text in {"/tasks", "/history"}:
            _print_tasks(config)
            continue
        if text == "/projects":
            _print_projects(config)
            continue
        if text.startswith("/show "):
            _print_task(config, text.removeprefix("/show ").strip())
            continue
        if text == "/project":
            console.print(f"Проект сессии: {project_path or 'не выбран'}")
            continue
        if text.startswith("/project "):
            candidate = Path(text.removeprefix("/project ").strip()).expanduser().resolve()
            if not candidate.exists():
                console.print(f"[red]Путь не существует:[/red] {candidate}")
                continue
            project_path = candidate
            console.print(f"[green]Проект сессии:[/green] {project_path}")
            continue
        if text == "/clear-project":
            project_path = None
            console.print("Проект сессии сброшен.")
            continue

        _run_interactive_with_errors(lambda text=text, project_path=project_path: _dispatch_auto(text, project_path))


@app.command()
def init(vault_path: Path | None = typer.Option(None, "--vault-path", help="Путь к Obsidian Vault.")) -> None:
    """Создать Obsidian Vault и системные файлы."""
    config = load_config(vault_path)
    if vault_path:
        config.system.vault_path = vault_path.expanduser()
    orchestrator = Orchestrator(config)
    created = orchestrator.init_vault()
    console.print("[bold green]AI-Boss Vault готов.[/bold green]")
    console.print(f"Vault: {config.system.vault_path.expanduser()}")
    if created:
        console.print("Созданы папки:")
        for path in created:
            console.print(f"  - {path}")
    else:
        console.print("Все папки уже существовали.")


@app.command()
def status(vault_path: Path | None = typer.Option(None, "--vault-path", help="Путь к Obsidian Vault.")) -> None:
    """Показать локальный статус без запросов к AI CLI."""
    config = load_config(vault_path)
    if vault_path:
        config.system.vault_path = vault_path.expanduser()
    _print_status(config)


@app.command()
def tasks(limit: int = typer.Option(20, "--limit", "-n", help="Сколько последних задач показать.")) -> None:
    """Показать последние задачи из Obsidian Vault."""
    _print_tasks(load_config(), limit=limit)


@app.command()
def show(task_id: str) -> None:
    """Показать markdown-файл задачи по id или префиксу id."""
    _print_task(load_config(), task_id)


@app.command()
def preflight(project_path: Path | None = typer.Option(None, "--project-path", "-p", help="Путь к git-проекту.")) -> None:
    """Проверить готовность Vault, CLI workers и проекта перед run/review."""
    _print_preflight(load_config(), project_path)


@app.command("project-list")
def project_list() -> None:
    """Показать сохранённые проектные профили."""
    _print_projects(load_config())


@app.command("project-add")
def project_add(
    name: str,
    path: Path = typer.Argument(..., help="Путь к проекту."),
    default: bool = typer.Option(False, "--default", help="Сделать проект профилем по умолчанию."),
) -> None:
    """Добавить проектный профиль в Vault."""
    config = load_config()
    ProjectStore(config.system.vault_path).add_project(name, path, make_default=default)
    console.print(f"[green]Проект добавлен:[/green] {name} -> {path.expanduser().resolve()}")


@app.command("project-remove")
def project_remove(name: str) -> None:
    """Удалить проектный профиль из Vault."""
    removed = ProjectStore(load_config().system.vault_path).remove_project(name)
    if removed:
        console.print(f"[green]Проект удалён:[/green] {name}")
    else:
        console.print(f"[yellow]Проект не найден:[/yellow] {name}")


@app.command()
def web(
    host: str = typer.Option(DEFAULT_WEB_HOST, "--host", help="Адрес локального web-интерфейса."),
    port: int = typer.Option(DEFAULT_WEB_PORT, "--port", help="Порт локального web-интерфейса."),
    open_browser: bool = typer.Option(True, "--open-browser/--no-open-browser", help="Открыть браузер после запуска."),
) -> None:
    """Запустить локальный web-интерфейс."""
    serve_web(host=host, port=port, open_browser=open_browser)


@app.command()
def ask(question: str) -> None:
    """Задать простой вопрос через Gemini."""
    _run_with_errors(lambda: _print_answer(Orchestrator(load_config()).ask(question)))


@app.command("do")
def do_auto(
    text: str,
    project_path: Path | None = typer.Option(None, "--project-path", "-p", help="Путь к git-проекту, если задачу нужно выполнять в коде."),
) -> None:
    """Автоматически выбрать режим: вопрос, план, ревью или выполнение."""
    _run_with_errors(lambda: _dispatch_auto(text, project_path))


@app.command()
def plan(task: str, project_path: Path | None = typer.Option(None, "--project-path", help="Путь к проекту.")) -> None:
    """Создать план через Gemini и сохранить его в Vault."""
    def action() -> None:
        result = Orchestrator(load_config()).plan(task, project_path)
        _print_files("План создан.", result.files)

    _run_with_errors(action)


@app.command()
def review(project_path: Path | None = typer.Option(None, "--project-path", help="Путь к git-проекту.")) -> None:
    """Проверить текущий git diff через Claude или Gemini fallback."""
    def action() -> None:
        result = Orchestrator(load_config()).review(project_path=project_path)
        if result.warning:
            console.print(f"[yellow]{result.warning}[/yellow]")
            return
        _print_files(f"Ревью сохранено. Reviewer: {result.worker}", result.files)

    _run_with_errors(action)


@app.command()
def run(task: str, project_path: Path | None = typer.Option(None, "--project-path", help="Путь к git-проекту.")) -> None:
    """Запланировать, выполнить через Codex, отревьюить и сохранить отчёт."""
    def action() -> None:
        result = Orchestrator(load_config()).run(task, project_path)
        if result.warning:
            console.print(f"[yellow]{result.warning}[/yellow]")
        _print_files("Задача завершена без auto-commit/push.", result.files)

    _run_with_errors(action)


def _print_answer(result) -> None:
    console.print(result.answer or "")
    _print_files("Сохранено в Obsidian.", result.files)


def _print_files(title: str, files: dict[str, Path]) -> None:
    console.print(f"[bold green]{title}[/bold green]")
    for name, path in files.items():
        console.print(f"{name}: {path}")


def _dispatch_auto(text: str, project_path: Path | None) -> None:
    config = load_config()
    orchestrator = Orchestrator(config)
    task_type = TaskClassifier().classify(text)
    console.print(f"[dim]AI-Boss классифицировал задачу как: {task_type.value}[/dim]")

    if task_type == TaskType.SIMPLE_QUESTION:
        _print_answer(orchestrator.ask(text))
        return

    if task_type == TaskType.REVIEW:
        result = orchestrator.review(user_task=text, project_path=project_path)
        if result.warning:
            console.print(f"[yellow]{result.warning}[/yellow]")
            return
        _print_files(f"Ревью сохранено. Reviewer: {result.worker}", result.files)
        return

    if task_type in {TaskType.CODE_CHANGE, TaskType.BUGFIX, TaskType.REFACTOR, TaskType.TEST_GENERATION}:
        result = orchestrator.run(text, project_path)
        if result.warning:
            console.print(f"[yellow]{result.warning}[/yellow]")
        _print_files("Задача выполнена в автопилоте без auto-commit/push.", result.files)
        return

    result = orchestrator.plan(text, project_path)
    _print_files("Создан план в автопилоте.", result.files)


def _print_status(config) -> None:
    vault = ObsidianVault(config.system.vault_path)
    table = Table(title="AI-Boss status")
    table.add_column("Проверка")
    table.add_column("Значение")
    table.add_row("Vault", str(vault.path))
    table.add_row("Vault существует", "да" if vault.exists() else "нет")
    table.add_row("Текущая папка", str(Path.cwd()))
    table.add_row("Проект из config.yaml", str(config.system.default_project_path))

    current_guard = GitGuard(Path.cwd())
    if current_guard.is_git_repo():
        short = current_guard.status_short().strip()
        table.add_row("Git-статус текущей папки", "dirty tree" if short else "чисто")
    else:
        table.add_row("Git-статус текущей папки", "не git repo")

    if config.system.default_project_path:
        guard = GitGuard(config.system.default_project_path)
        git_status = "git repo" if guard.is_git_repo() else "не git repo"
        if guard.is_git_repo():
            short = guard.status_short().strip()
            git_status += ", dirty tree" if short else ", чисто"
        table.add_row("Git-статус проекта", git_status)

    for name, settings in config.workers.items():
        found = shutil.which(settings.command[0]) is not None
        table.add_row(f"CLI {name}", "найден" if found else "не найден")
        if name == "codex":
            subagents = "включены" if settings.allow_subagents else "отключены"
            table.add_row("Codex subagents", f"{subagents}, политика: {settings.subagent_policy}")

    states = WorkerStateStore(vault.path).load()
    for name, state in states.items():
        table.add_row(f"Состояние {name}", state.status.value)
    console.print(table)
    if not vault.exists():
        console.print("[yellow]Предупреждение:[/yellow] выполните `ai-boss init`.")


def _print_preflight(config, project_path: Path | None = None) -> None:
    data = build_preflight(config, project_path)
    title = "Preflight: готово" if data["ok"] else "Preflight: есть предупреждения"
    table = Table(title=title)
    table.add_column("Проверка")
    table.add_column("OK")
    table.add_column("Детали")
    for check in data["checks"]:
        table.add_row(str(check["name"]), "да" if check["ok"] else "нет", str(check["detail"]))
    console.print(table)


def _print_projects(config) -> None:
    projects = ProjectStore(config.system.vault_path).list_projects()
    if not projects:
        console.print("Проектные профили пока не добавлены.")
        return
    table = Table(title=f"Проекты: {len(projects)}")
    table.add_column("Название")
    table.add_column("Путь")
    table.add_column("По умолчанию")
    for project in projects:
        table.add_row(str(project.get("name", "")), str(project.get("path", "")), "да" if project.get("default") else "")
    console.print(table)


def _print_tasks(config, limit: int = 20) -> None:
    vault = ObsidianVault(config.system.vault_path)
    tasks = vault.list_tasks(limit=limit)
    if not tasks:
        console.print("Задач пока нет.")
        return
    table = Table(title=f"Последние задачи: {len(tasks)}")
    table.add_column("ID")
    table.add_column("Статус")
    table.add_column("Проект")
    table.add_column("Создано")
    for task in tasks:
        table.add_row(
            str(task.get("id", "")),
            str(task.get("status", "")),
            str(task.get("project", "") or ""),
            str(task.get("created_at", "")),
        )
    console.print(table)


def _print_task(config, task_id: str) -> None:
    if not task_id:
        console.print("[red]Укажите id задачи: /show TASK_ID[/red]")
        return
    vault = ObsidianVault(config.system.vault_path)
    task_path = vault.find_task(task_id)
    if not task_path:
        console.print(f"[red]Задача не найдена:[/red] {task_id}")
        return
    console.print(f"[dim]{task_path}[/dim]")
    console.print(Markdown(task_path.read_text(encoding="utf-8")))


def _print_interactive_help() -> None:
    console.print(
        """
[bold]Как пользоваться[/bold]

Пишите обычным текстом:
  Что такое git diff?
  Хочу систему импорта студентов из DOCX
  Проверь текущие изменения
  Добавь страницу настроек пользователя

Служебные команды:
  /status              показать состояние Vault, CLI и текущей папки
  /preflight           проверить готовность перед run/review
  /tasks               показать последние задачи
  /show TASK_ID        показать markdown-файл задачи
  /projects            показать проектные профили
  /project             показать проект текущей сессии
  /project /path       выбрать проект для этой сессии
  /clear-project       сбросить проект сессии
  /exit                выйти
""".strip()
    )


def _infer_initial_project(config) -> Path | None:
    current_dir = Path.cwd().resolve()
    if GitGuard(current_dir).is_git_repo():
        return current_dir
    if config.system.default_project_path:
        return config.system.default_project_path.expanduser().resolve()
    return None


def _run_with_errors(action) -> None:
    try:
        action()
    except AIBossError as exc:
        console.print(f"[bold red]Ошибка:[/bold red] {exc}")
        raise typer.Exit(1) from exc


def _run_interactive_with_errors(action) -> None:
    try:
        action()
    except AIBossError as exc:
        console.print(f"[bold red]Ошибка:[/bold red] {exc}")
