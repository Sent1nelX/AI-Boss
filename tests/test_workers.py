import subprocess
from pathlib import Path
from types import SimpleNamespace

from ai_boss.core.runtime import runtime_context
from ai_boss.memory.obsidian_vault import ObsidianVault
from ai_boss.memory.state_store import WorkerStateStore
from ai_boss.models.worker import WorkerStatus
from ai_boss.workers.base import BaseWorker, detect_limit, extract_available_after
from ai_boss.workers.claude_worker import ClaudeWorker
from ai_boss.workers.codex_worker import CodexWorker
from ai_boss.workers.gemini_worker import GeminiWorker


def test_detect_limit_recognizes_supported_messages() -> None:
    assert detect_limit("You've hit your limit. Resets tomorrow.") is True
    assert detect_limit("HTTP 429 Too Many Requests") is True
    assert detect_limit("Превышен лимит запросов") is True
    assert detect_limit("all good") is False


def test_extract_available_after_supports_resets_and_available_after() -> None:
    assert extract_available_after("Rate limit. Resets in 2 hours\nTry later") == "in 2 hours"
    assert extract_available_after("available_after: 2026-05-06T10:00:00") == "2026-05-06T10:00:00"
    assert extract_available_after("available_after=tomorrow morning") == "tomorrow morning"
    assert extract_available_after("no retry info") is None


def test_worker_run_success_uses_mocked_subprocess_and_updates_state(
    tmp_path: Path, monkeypatch
) -> None:
    vault = ObsidianVault(tmp_path / "vault")
    vault.create()

    def fake_run(args, cwd=None, env=None, text=False, capture_output=False, timeout=None, check=True):
        assert args == ["mock-ai", "--prompt", "hello"]
        assert cwd == tmp_path
        assert env == {"PATH": "/mock/bin"}
        assert text is True
        assert capture_output is True
        assert timeout == 7
        assert check is False
        return SimpleNamespace(stdout="answer", stderr="", returncode=0)

    monkeypatch.setattr("ai_boss.workers.base.resolved_command", lambda command: command)
    monkeypatch.setattr("ai_boss.workers.base.resolved_command_env", lambda command: {"PATH": "/mock/bin"})
    monkeypatch.setattr(subprocess, "run", fake_run)

    worker = BaseWorker(["mock-ai", "--prompt"], vault, timeout=7)
    result = worker.run("hello", cwd=tmp_path)
    state = WorkerStateStore(vault.path).load()["base"]

    assert result.success is True
    assert result.stdout == "answer"
    assert result.exit_code == 0
    assert result.detected_limit is False
    assert state.status == WorkerStatus.AVAILABLE
    assert state.total_runs_today == 1


def test_non_codex_worker_uses_captured_run_with_runtime_logs(
    tmp_path: Path, monkeypatch
) -> None:
    vault = ObsidianVault(tmp_path / "vault")
    vault.create()
    logs: list[tuple[str, str]] = []

    def fake_run(args, cwd=None, env=None, text=False, capture_output=False, timeout=None, check=True):
        assert args == ["gemini", "-p", "hello"]
        assert env == {"PATH": "/mock/bin"}
        assert text is True
        assert capture_output is True
        assert timeout == 7
        assert check is False
        return SimpleNamespace(stdout="answer line\nsecond line\n", stderr="warning\n", returncode=0)

    def fake_popen(*args, **kwargs):
        raise AssertionError("Gemini should not use streaming Popen")

    monkeypatch.setattr("ai_boss.workers.base.resolved_command", lambda command: command)
    monkeypatch.setattr("ai_boss.workers.base.resolved_command_env", lambda command: {"PATH": "/mock/bin"})
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    worker = GeminiWorker(["gemini", "-p"], vault, timeout=7)
    with runtime_context(log_sink=lambda source, message: logs.append((source, message))):
        result = worker.run("hello")

    assert result.success is True
    assert ("gemini", "answer line") in logs
    assert ("gemini", "second line") in logs
    assert ("gemini:err", "warning") in logs


def test_worker_run_records_limit_and_writes_error_without_real_cli(
    tmp_path: Path, monkeypatch
) -> None:
    vault = ObsidianVault(tmp_path / "vault")
    vault.create()
    monkeypatch.setattr(vault, "task_id", lambda: "20260505-120000-abcdef")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="",
            stderr="Rate limit. Resets in 2 hours\n",
            returncode=0,
        ),
    )

    worker = CodexWorker(["codex"], vault, timeout=1)
    result = worker.run("prompt")
    state = WorkerStateStore(vault.path).load()["codex"]
    errors = list((vault.path / "08_Errors").glob("*.md"))

    assert result.success is False
    assert result.detected_limit is True
    assert result.available_after == "in 2 hours"
    assert state.status == WorkerStatus.LIMITED
    assert state.cooldown_until == "in 2 hours"
    assert len(errors) == 1
    assert "Ошибка worker codex" in errors[0].read_text(encoding="utf-8")


def test_worker_run_handles_missing_command_and_timeout(tmp_path: Path, monkeypatch) -> None:
    vault = ObsidianVault(tmp_path / "vault")
    vault.create()

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()))
    missing = GeminiWorker(["missing-gemini"], vault).run("prompt")

    assert missing.success is False
    assert missing.exit_code is None
    assert "Команда не найдена: missing-gemini" in missing.stderr

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(cmd=["claude"], timeout=3)),
    )
    timeout = ClaudeWorker(["claude"], vault, timeout=3).run("prompt")

    assert timeout.success is False
    assert timeout.exit_code is None
    assert "Таймаут выполнения после 3 секунд" in timeout.stderr


def test_concrete_worker_names() -> None:
    assert GeminiWorker.name == "gemini"
    assert CodexWorker.name == "codex"
    assert ClaudeWorker.name == "claude"
