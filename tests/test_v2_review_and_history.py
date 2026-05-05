from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import ai_boss.cli.app as cli_app
from ai_boss.config.loader import load_default_config
from ai_boss.core import orchestrator as orchestrator_module
from ai_boss.core.orchestrator import Orchestrator
from ai_boss.memory.obsidian_vault import ObsidianVault
from ai_boss.models.review import parse_review_approval
from ai_boss.models.worker import WorkerResult


class FakeGitGuard:
    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path

    def ensure_git_repo(self) -> None:
        return None

    def is_git_repo(self) -> bool:
        return True

    def is_dirty(self) -> bool:
        return False

    def status_short(self) -> str:
        return ""

    def create_branch(self, task_id: str) -> str:
        return f"ai-boss/{task_id}"

    def diff(self) -> str:
        return "diff --git a/app.py b/app.py\n+fixed\n"

    def diff_stat(self) -> str:
        return "app.py | 1 +"


def worker_result(worker_name: str, stdout: str, success: bool = True) -> WorkerResult:
    now = datetime.now()
    return WorkerResult(
        worker_name=worker_name,
        success=success,
        stdout=stdout,
        stderr="",
        exit_code=0 if success else 1,
        started_at=now,
        finished_at=now,
        duration_seconds=0.01,
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# Решение\napproved: true\n", True),
        ("# Решение\napproved: false\n", False),
        ("# Решение\n  APPROVED: TRUE  \n\n# Итог\nok", True),
        ("# Решение\napproved: maybe\n", None),
        ("# Решение\nРевью принято, явного поля нет.\n", None),
    ],
)
def test_parse_review_approval_from_markdown_text(text: str, expected: bool | None) -> None:
    assert parse_review_approval(text) is expected


def test_run_does_not_start_fix_loop_when_review_is_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config = load_default_config()
    config.system.vault_path = tmp_path / "vault"
    config.safety.block_if_dirty_tree = False
    config.safety.create_branch_per_task = False
    calls: list[tuple[str, str]] = []

    def fake_worker(self: Orchestrator, name: str) -> Any:
        class Worker:
            def run(self, prompt: str, cwd: Path | None = None) -> WorkerResult:
                calls.append((name, prompt))
                if name == "gemini" and "planner.md" in prompt:
                    return worker_result(name, "PLAN")
                if name == "codex":
                    return worker_result(name, "CODEX PASS")
                if "reviewer.md" in prompt:
                    return worker_result(name, "# Решение\napproved: true\n")
                return worker_result(name, "FINAL REPORT")

        return Worker()

    monkeypatch.setattr(orchestrator_module, "GitGuard", FakeGitGuard)
    monkeypatch.setattr(Orchestrator, "_render_prompt", lambda self, template_name, **values: f"{template_name}: {values}")
    monkeypatch.setattr(Orchestrator, "_worker", fake_worker)

    Orchestrator(config).run("Добавь проверку", project)

    assert [name for name, _ in calls].count("codex") == 1
    assert sum("reviewer.md" in prompt for _, prompt in calls) == 1


def test_run_starts_bounded_fix_loop_when_review_is_not_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config = load_default_config()
    config.system.vault_path = tmp_path / "vault"
    config.safety.block_if_dirty_tree = False
    config.safety.create_branch_per_task = False
    config.safety.max_fix_loops = 2
    calls: list[tuple[str, str]] = []

    def fake_worker(self: Orchestrator, name: str) -> Any:
        class Worker:
            def run(self, prompt: str, cwd: Path | None = None) -> WorkerResult:
                calls.append((name, prompt))
                if name == "gemini" and "planner.md" in prompt:
                    return worker_result(name, "PLAN")
                if name == "codex":
                    return worker_result(name, f"CODEX PASS {self_codex_calls()}")
                if "reviewer.md" in prompt:
                    return worker_result(name, "# Решение\napproved: false\n\n# Что исправить\nStill broken")
                return worker_result(name, "FINAL REPORT")

        def self_codex_calls() -> int:
            return [call_name for call_name, _ in calls].count("codex")

        return Worker()

    monkeypatch.setattr(orchestrator_module, "GitGuard", FakeGitGuard)
    monkeypatch.setattr(Orchestrator, "_render_prompt", lambda self, template_name, **values: f"{template_name}: {values}")
    monkeypatch.setattr(Orchestrator, "_worker", fake_worker)

    result = Orchestrator(config).run("Исправь баг", project)

    assert [name for name, _ in calls].count("codex") == 1 + config.safety.max_fix_loops
    assert sum("reviewer.md" in prompt for _, prompt in calls) == 1 + config.safety.max_fix_loops
    assert sorted(key for key in result.files if key.startswith("execution_fix_")) == ["execution_fix_1", "execution_fix_2"]
    assert sorted(key for key in result.files if key.startswith("review_fix_")) == ["review_fix_1", "review_fix_2"]


def test_task_history_helpers_list_tasks_newest_first(tmp_path: Path) -> None:
    vault = ObsidianVault(tmp_path / "vault")
    vault.create()
    first = vault.create_task("20260505-120000-first", "Первая задача", tmp_path)
    second = vault.create_task("20260505-121000-second", "Вторая задача", tmp_path)
    vault.update_task_frontmatter(first, status="finished", planner="gemini", coder="codex", reviewer="claude")
    vault.update_task_frontmatter(second, status="reviewed", planner="gemini", coder="codex", reviewer="gemini")

    tasks = vault.list_tasks(limit=2)  # type: ignore[attr-defined]

    assert [task["id"] for task in tasks] == ["20260505-121000-second", "20260505-120000-first"]
    assert tasks[0]["status"] == "reviewed"
    assert tasks[0]["path"] == second


def test_interactive_history_commands_print_task_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_default_config()
    config.system.vault_path = tmp_path / "vault"
    config.system.default_project_path = None
    vault = ObsidianVault(config.system.vault_path)
    vault.create()
    vault.create_task("20260505-120000-first", "Первая задача", tmp_path)

    monkeypatch.setattr(cli_app, "load_config", lambda vault_path=None: config)
    monkeypatch.setattr("ai_boss.cli.app.GitGuard.is_git_repo", lambda self: False)
    monkeypatch.setattr("ai_boss.cli.app.shutil.which", lambda command: None)
    monkeypatch.setattr(cli_app, "_dispatch_auto", lambda text, project_path: pytest.fail(f"Unknown command: {text}"))

    result = CliRunner().invoke(cli_app.app, [], input="/history\n/tasks\n/exit\n")

    assert result.exit_code == 0
    assert result.output.count("Последние задачи: 1") == 2
    assert "20260505-120000-fir" in result.output
    assert "created" in result.output
