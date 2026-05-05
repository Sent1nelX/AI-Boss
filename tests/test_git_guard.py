from pathlib import Path

import pytest

from ai_boss.core.command_runner import CommandOutput
from ai_boss.core.errors import GitGuardError
from ai_boss.core.git_guard import GitGuard


def test_ensure_path_exists_raises_for_missing_path(tmp_path: Path) -> None:
    guard = GitGuard(tmp_path / "missing")

    with pytest.raises(GitGuardError, match="Путь проекта не существует"):
        guard.ensure_path_exists()


def test_is_git_repo_false_when_path_missing(tmp_path: Path) -> None:
    assert GitGuard(tmp_path / "missing").is_git_repo() is False


def test_git_guard_delegates_git_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_run_command(args: list[str], cwd: Path | None = None, timeout: int = 120) -> CommandOutput:
        calls.append((args, cwd, timeout))
        if args == ["git", "rev-parse", "--is-inside-work-tree"]:
            return CommandOutput(stdout="true\n", stderr="", exit_code=0)
        if args == ["git", "status", "--short"]:
            return CommandOutput(stdout=" M ai_boss/core/router.py\n", stderr="", exit_code=0)
        if args == ["git", "diff"]:
            return CommandOutput(stdout="diff --git ...\n", stderr="", exit_code=0)
        if args == ["git", "diff", "--stat"]:
            return CommandOutput(stdout=" router.py | 2 +-\n", stderr="", exit_code=0)
        raise AssertionError(f"Unexpected git command: {args}")

    monkeypatch.setattr("ai_boss.core.git_guard.run_command", fake_run_command)
    guard = GitGuard(tmp_path)

    assert guard.is_git_repo() is True
    assert guard.status_short() == " M ai_boss/core/router.py\n"
    assert guard.is_dirty() is True
    assert guard.diff() == "diff --git ...\n"
    assert guard.diff_stat() == " router.py | 2 +-\n"
    assert calls[0] == (["git", "rev-parse", "--is-inside-work-tree"], tmp_path.resolve(), 10)


def test_ensure_git_repo_raises_when_rev_parse_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ai_boss.core.git_guard.run_command",
        lambda *args, **kwargs: CommandOutput(stdout="false\n", stderr="", exit_code=1),
    )

    with pytest.raises(GitGuardError, match="Путь не является git-репозиторием"):
        GitGuard(tmp_path).ensure_git_repo()


def test_create_branch_returns_branch_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str], cwd: Path | None = None, timeout: int = 120) -> CommandOutput:
        if args == ["git", "rev-parse", "--is-inside-work-tree"]:
            return CommandOutput(stdout="true\n", stderr="", exit_code=0)
        if args == ["git", "switch", "-c", "ai-boss/task-1"]:
            return CommandOutput(stdout="", stderr="", exit_code=0)
        raise AssertionError(f"Unexpected git command: {args}")

    monkeypatch.setattr("ai_boss.core.git_guard.run_command", fake_run_command)

    assert GitGuard(tmp_path).create_branch("task-1") == "ai-boss/task-1"


def test_create_branch_raises_on_switch_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str], cwd: Path | None = None, timeout: int = 120) -> CommandOutput:
        if args == ["git", "rev-parse", "--is-inside-work-tree"]:
            return CommandOutput(stdout="true\n", stderr="", exit_code=0)
        if args == ["git", "switch", "-c", "ai-boss/task-1"]:
            return CommandOutput(stdout="", stderr="branch exists\n", exit_code=128)
        raise AssertionError(f"Unexpected git command: {args}")

    monkeypatch.setattr("ai_boss.core.git_guard.run_command", fake_run_command)

    with pytest.raises(GitGuardError, match="Не удалось создать ветку ai-boss/task-1"):
        GitGuard(tmp_path).create_branch("task-1")
