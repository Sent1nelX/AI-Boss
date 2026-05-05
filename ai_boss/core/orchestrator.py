from pathlib import Path

from ai_boss.config.loader import AIBossConfig
from ai_boss.core.errors import GitGuardError, WorkerUnavailableError
from ai_boss.core.git_guard import GitGuard
from ai_boss.core.router import Router
from ai_boss.memory.obsidian_vault import ObsidianVault
from ai_boss.memory.state_store import WorkerStateStore
from ai_boss.memory.task_files import read_prompt_template
from ai_boss.models.result import OrchestrationResult
from ai_boss.models.review import parse_review_approval
from ai_boss.models.task import TaskType
from ai_boss.workers.base import BaseWorker
from ai_boss.workers.claude_worker import ClaudeWorker
from ai_boss.workers.codex_worker import CodexWorker
from ai_boss.workers.gemini_worker import GeminiWorker


class Orchestrator:
    def __init__(self, config: AIBossConfig) -> None:
        self.config = config
        self.vault = ObsidianVault(config.system.vault_path)
        self.state_store = WorkerStateStore(self.vault.path)

    def init_vault(self) -> list[Path]:
        return self.vault.create()

    def ask(self, question: str) -> OrchestrationResult:
        worker = self._worker("gemini")
        result = worker.run(question)
        if not result.success:
            raise WorkerUnavailableError("Gemini недоступен для простого вопроса. Подробности сохранены в 08_Errors.")
        inbox_path = self.vault.write_inbox(question, result.stdout, "gemini")
        return OrchestrationResult(answer=result.stdout, worker="gemini", files={"inbox": inbox_path})

    def plan(self, user_task: str, project_path: Path | None = None) -> OrchestrationResult:
        project = self._resolve_optional_project(project_path)
        task_id = self.vault.task_id()
        task_path = self.vault.create_task(task_id, user_task, project)
        prompt = self._render_prompt(
            "planner.md",
            user_task=user_task,
            project_context=self._project_context(project),
        )
        worker = self._worker("gemini")
        result = worker.run(prompt, cwd=project)
        if not result.success:
            raise WorkerUnavailableError("Gemini недоступен для планирования. Подробности сохранены в 08_Errors.")
        plan_path = self.vault.write_plan(task_id, result.stdout, "gemini")
        self.vault.update_task_frontmatter(task_path, status="planned", planner="gemini")
        return OrchestrationResult(task_id=task_id, worker="gemini", files={"task": task_path, "plan": plan_path})

    def review(self, user_task: str = "Ревью текущих изменений", project_path: Path | None = None) -> OrchestrationResult:
        project = self._resolve_project(project_path)
        guard = GitGuard(project)
        guard.ensure_git_repo()
        diff = guard.diff()
        if not diff.strip():
            return OrchestrationResult(warning="В git diff нет изменений для ревью.")
        task_id = self.vault.task_id()
        task_path = self.vault.create_task(task_id, user_task, project)
        reviewer_name = Router(self.state_store.load()).route(TaskType.REVIEW)
        prompt = self._render_prompt("reviewer.md", user_task=user_task, planner_output="План не передан.", git_diff=diff)
        result = self._worker(reviewer_name).run(prompt, cwd=project)
        if not result.success and reviewer_name == "claude":
            reviewer_name = "gemini"
            result = self._worker("gemini").run(prompt, cwd=project)
        if not result.success:
            raise WorkerUnavailableError("Reviewer недоступен. Подробности сохранены в 08_Errors.")
        review_path = self.vault.write_review(task_id, result.stdout, reviewer_name)
        self.vault.update_task_frontmatter(task_path, status="reviewed", reviewer=reviewer_name)
        return OrchestrationResult(task_id=task_id, worker=reviewer_name, files={"task": task_path, "review": review_path})

    def run(self, user_task: str, project_path: Path | None = None) -> OrchestrationResult:
        project = self._resolve_project(project_path)
        guard = GitGuard(project)
        guard.ensure_git_repo()
        if self.config.safety.block_if_dirty_tree and guard.is_dirty():
            raise GitGuardError("Рабочее дерево не чистое. Сначала закоммитьте или уберите текущие изменения.")

        task_id = self.vault.task_id()
        task_path = self.vault.create_task(task_id, user_task, project)

        plan_prompt = self._render_prompt("planner.md", user_task=user_task, project_context=self._project_context(project))
        plan_result = self._worker("gemini").run(plan_prompt, cwd=project)
        if not plan_result.success:
            raise WorkerUnavailableError("Gemini недоступен для создания плана. Подробности сохранены в 08_Errors.")
        plan_path = self.vault.write_plan(task_id, plan_result.stdout, "gemini")
        self.vault.update_task_frontmatter(task_path, status="planned", planner="gemini")

        branch = None
        if self.config.safety.create_branch_per_task:
            branch = guard.create_branch(task_id)
            self.vault.update_task_frontmatter(task_path, branch=branch)

        coder_prompt = self._render_prompt(
            "coder.md",
            user_task=user_task,
            planner_output=plan_result.stdout,
            subagent_policy=self._codex_subagent_policy(),
        )
        codex_result = self._worker("codex").run(coder_prompt, cwd=project)
        execution_body = _worker_report(codex_result)
        execution_path = self.vault.write_execution(task_id, execution_body, "codex")
        self.vault.update_task_frontmatter(task_path, status="executed", coder="codex")
        if not codex_result.success:
            raise WorkerUnavailableError("Codex не смог выполнить задачу. Вывод сохранён в 03_Execution и 08_Errors.")

        diff = guard.diff()
        diff_stat = guard.diff_stat()
        warning = None
        if not diff.strip():
            warning = "Codex завершился без изменений в git diff."

        reviewer_name, review_text = self._review_diff(user_task, plan_result.stdout, diff, project)
        review_path = self.vault.write_review(task_id, review_text, reviewer_name)
        review_approved = parse_review_approval(review_text)
        self.vault.update_task_frontmatter(task_path, status="reviewed", reviewer=reviewer_name, review_approved=review_approved)

        fix_loops_done = 0
        while review_approved is False and fix_loops_done < self.config.safety.max_fix_loops:
            fix_loops_done += 1
            self.vault.update_task_frontmatter(task_path, status=f"fixing_{fix_loops_done}", fix_loops_done=fix_loops_done)
            fix_prompt = self._render_fix_prompt(
                user_task=user_task,
                plan_output=plan_result.stdout,
                review_output=review_text,
                git_diff=diff,
                iteration=fix_loops_done,
            )
            fix_result = self._worker("codex").run(fix_prompt, cwd=project)
            execution_fix_path = self.vault.write_execution(task_id, _worker_report(fix_result), "codex", phase=f"execution-fix-{fix_loops_done}")
            files_key = f"execution_fix_{fix_loops_done}"
            if not fix_result.success:
                self.vault.update_task_frontmatter(task_path, status="fix_failed", fix_loops_done=fix_loops_done)
                raise WorkerUnavailableError(f"Codex не смог выполнить fix-loop #{fix_loops_done}. Вывод сохранён в {execution_fix_path}.")

            diff = guard.diff()
            diff_stat = guard.diff_stat()
            reviewer_name, review_text = self._review_diff(user_task, plan_result.stdout, diff, project)
            review_fix_path = self.vault.write_review(task_id, review_text, reviewer_name, phase=f"review-fix-{fix_loops_done}")
            review_approved = parse_review_approval(review_text)
            self.vault.update_task_frontmatter(
                task_path,
                status="reviewed",
                reviewer=reviewer_name,
                review_approved=review_approved,
                fix_loops_done=fix_loops_done,
            )

        final_report = self._build_final_report(user_task, plan_result.stdout, codex_result.stdout, review_text, diff_stat, warning, project)
        final_path = self.vault.write_final_report(task_id, final_report)
        final_status = "finished" if review_approved is not False else "finished_with_review_findings"
        self.vault.update_task_frontmatter(task_path, status=final_status, fix_loops_done=fix_loops_done, review_approved=review_approved)

        files = {"task": task_path, "plan": plan_path, "execution": execution_path, "review": review_path, "final_report": final_path}
        for index in range(1, fix_loops_done + 1):
            execution_candidate = self.vault.path / "03_Execution" / f"{task_id}-execution-fix-{index}.md"
            review_candidate = self.vault.path / "04_Reviews" / f"{task_id}-review-fix-{index}.md"
            if execution_candidate.exists():
                files[f"execution_fix_{index}"] = execution_candidate
            if review_candidate.exists():
                files[f"review_fix_{index}"] = review_candidate

        return OrchestrationResult(
            task_id=task_id,
            worker="codex",
            warning=warning,
            files=files,
        )

    def _worker(self, name: str) -> BaseWorker:
        settings = self.config.workers.get(name)
        if not settings or not settings.enabled:
            raise WorkerUnavailableError(f"AI-агент отключён или не настроен: {name}")
        if name == "gemini":
            return GeminiWorker(settings.command, self.vault)
        if name == "codex":
            return CodexWorker(settings.command, self.vault)
        if name == "claude":
            return ClaudeWorker(settings.command, self.vault)
        raise WorkerUnavailableError(f"Неизвестный AI-агент: {name}")

    def _render_prompt(self, template_name: str, **values: str) -> str:
        return read_prompt_template(Path(__file__).parents[1] / "prompts" / template_name, **values)

    def _resolve_project(self, project_path: Path | None) -> Path:
        project = self._resolve_optional_project(project_path)
        if project is None:
            raise GitGuardError("Не найден git-проект: перейдите в папку проекта или передайте --project-path.")
        return project.expanduser().resolve()

    def _resolve_optional_project(self, project_path: Path | None) -> Path | None:
        if project_path is not None:
            return project_path.expanduser().resolve()

        current_dir = Path.cwd().resolve()
        if GitGuard(current_dir).is_git_repo():
            return current_dir

        if self.config.system.default_project_path is not None:
            return self.config.system.default_project_path.expanduser().resolve()

        return None

    def _project_context(self, project_path: Path | None) -> str:
        if not project_path:
            return "Проект не указан."
        guard = GitGuard(project_path)
        if not guard.is_git_repo():
            return f"Путь указан, но git-репозиторий не найден: {project_path}"
        return f"Путь проекта: {project_path}\nGit status --short:\n{guard.status_short() or 'чисто'}"

    def _review_diff(self, user_task: str, plan_output: str, git_diff: str, project_path: Path) -> tuple[str, str]:
        reviewer_name = Router(self.state_store.load()).route(TaskType.REVIEW)
        review_prompt = self._render_prompt("reviewer.md", user_task=user_task, planner_output=plan_output, git_diff=git_diff)
        review_result = self._worker(reviewer_name).run(review_prompt, cwd=project_path)
        if not review_result.success and reviewer_name == "claude":
            reviewer_name = "gemini"
            review_result = self._worker("gemini").run(review_prompt, cwd=project_path)
        review_text = review_result.stdout if review_result.success else _worker_report(review_result)
        return reviewer_name, review_text

    def _render_fix_prompt(self, user_task: str, plan_output: str, review_output: str, git_diff: str, iteration: int) -> str:
        fix_task = (
            f"{user_task}\n\n"
            f"Fix-loop #{iteration}: исправь только замечания reviewer-а ниже. "
            "Не делай unrelated-изменения и не переписывай уже рабочую реализацию без необходимости.\n\n"
            f"# Ревью\n{review_output}\n\n# Текущий git diff\n```diff\n{git_diff}\n```"
        )
        return self._render_prompt(
            "coder.md",
            user_task=fix_task,
            planner_output=plan_output,
            subagent_policy=self._codex_subagent_policy(),
        )

    def _final_report(
        self,
        user_task: str,
        plan_output: str,
        coder_output: str,
        review_output: str,
        diff_stat: str,
        warning: str | None,
    ) -> str:
        warning_text = f"\n# Предупреждение\n\n{warning}\n" if warning else ""
        return (
            "# Финальный отчёт\n\n"
            f"# Задача пользователя\n\n{user_task}\n\n"
            f"# План\n\n{plan_output.strip()}\n\n"
            f"# Выполнение\n\n{coder_output.strip() or 'Codex не вернул stdout.'}\n\n"
            f"# Ревью\n\n{review_output.strip()}\n\n"
            f"# Git diff --stat\n\n```text\n{diff_stat.strip() or 'Нет изменений'}\n```\n"
            f"{warning_text}"
        )

    def _build_final_report(
        self,
        user_task: str,
        plan_output: str,
        coder_output: str,
        review_output: str,
        diff_stat: str,
        warning: str | None,
        project_path: Path,
    ) -> str:
        prompt = self._render_prompt(
            "reporter.md",
            user_task=user_task,
            planner_output=plan_output,
            coder_output=coder_output or "Codex не вернул stdout.",
            review_output=review_output,
            diff_stat=diff_stat or "Нет изменений",
            warning=warning or "Нет.",
        )
        try:
            result = self._worker("gemini").run(prompt, cwd=project_path)
        except WorkerUnavailableError:
            result = None
        if result and result.success and result.stdout.strip():
            return result.stdout
        local_report = self._final_report(user_task, plan_output, coder_output, review_output, diff_stat, warning)
        return f"{local_report}\n# Примечание\n\nReporter Agent недоступен, поэтому отчёт сформирован локально.\n"

    def _codex_subagent_policy(self) -> str:
        settings = self.config.workers.get("codex")
        if not settings or not settings.allow_subagents:
            return "Субагенты отключены. Выполняй задачу самостоятельно."
        if settings.subagent_policy == "auto":
            return (
                "Режим auto: для крупных или многокомпонентных задач можешь использовать доступных субагентов. "
                "Для маленьких задач работай сам без делегирования."
            )
        return f"Режим: {settings.subagent_policy}."


def _worker_report(result) -> str:
    return (
        "# Вывод агента\n\n"
        f"- Агент: {result.worker_name}\n"
        f"- Успех: {result.success}\n"
        f"- Код выхода: {result.exit_code}\n"
        f"- Длительность: {result.duration_seconds:.2f} сек.\n"
        f"- Обнаружен лимит: {result.detected_limit}\n\n"
        "## stdout\n\n"
        f"```text\n{result.stdout.strip()}\n```\n\n"
        "## stderr\n\n"
        f"```text\n{result.stderr.strip()}\n```\n"
    )
