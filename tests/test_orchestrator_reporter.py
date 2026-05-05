from datetime import datetime
from pathlib import Path

import pytest

from ai_boss.config.loader import load_default_config
from ai_boss.core import orchestrator as orchestrator_module
from ai_boss.core.orchestrator import Orchestrator
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
        return "diff --git a/file.py b/file.py"

    def diff_stat(self) -> str:
        return "file.py | 1 +"


class FakeWorker:
    def __init__(self, name: str, calls: list[tuple[str, str, Path | None]]) -> None:
        self.name = name
        self.calls = calls

    def run(self, prompt: str, cwd: Path | None = None) -> WorkerResult:
        self.calls.append((self.name, prompt, cwd))
        stdout = "REPORTER FINAL" if self.name == "gemini" and "reporter.md" in prompt else f"{self.name} output"
        now = datetime.now()
        return WorkerResult(
            worker_name=self.name,
            success=True,
            stdout=stdout,
            stderr="",
            exit_code=0,
            started_at=now,
            finished_at=now,
            duration_seconds=0.01,
        )


def test_run_can_delegate_final_report_to_reporter_prompt_and_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config = load_default_config()
    config.system.vault_path = tmp_path / "vault"
    config.safety.create_branch_per_task = False

    rendered_templates: list[str] = []
    rendered_values: dict[str, dict[str, str]] = {}
    worker_calls: list[tuple[str, str, Path | None]] = []

    def fake_render_prompt(self, template_name: str, **values: str) -> str:
        rendered_templates.append(template_name)
        rendered_values[template_name] = values
        return f"{template_name}: {values}"

    monkeypatch.setattr(orchestrator_module, "GitGuard", FakeGitGuard)
    monkeypatch.setattr(Orchestrator, "_render_prompt", fake_render_prompt)
    monkeypatch.setattr(Orchestrator, "_worker", lambda self, name: FakeWorker(name, worker_calls))

    result = Orchestrator(config).run("Сделай изменение", project)

    final_report = result.files["final_report"].read_text(encoding="utf-8")
    assert "reporter.md" in rendered_templates
    assert "subagent_policy" in rendered_values["coder.md"]
    assert "Режим auto" in rendered_values["coder.md"]["subagent_policy"]
    assert any(worker_name == "gemini" and "reporter.md" in prompt for worker_name, prompt, _ in worker_calls)
    assert "REPORTER FINAL" in final_report
