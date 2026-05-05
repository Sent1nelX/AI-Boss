from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import ai_boss.cli.app as cli_app
from ai_boss.config.loader import load_default_config
from ai_boss.models.result import OrchestrationResult


class FakeOrchestrator:
    calls: list[tuple[str, dict[str, Any]]] = []

    def __init__(self, config) -> None:
        self.config = config

    @classmethod
    def reset(cls) -> None:
        cls.calls = []

    def ask(self, question: str) -> OrchestrationResult:
        self.calls.append(("ask", {"question": question}))
        return OrchestrationResult(answer=f"answer: {question}", worker="gemini", files={"inbox": Path("/vault/inbox.md")})

    def plan(self, user_task: str, project_path: Path | None = None) -> OrchestrationResult:
        self.calls.append(("plan", {"task": user_task, "project_path": project_path}))
        return OrchestrationResult(task_id="task-plan", worker="gemini", files={"task": Path("/vault/task.md"), "plan": Path("/vault/plan.md")})

    def review(self, user_task: str = "Ревью текущих изменений", project_path: Path | None = None) -> OrchestrationResult:
        self.calls.append(("review", {"task": user_task, "project_path": project_path}))
        return OrchestrationResult(task_id="task-review", worker="claude", files={"task": Path("/vault/task.md"), "review": Path("/vault/review.md")})

    def run(self, user_task: str, project_path: Path | None = None) -> OrchestrationResult:
        self.calls.append(("run", {"task": user_task, "project_path": project_path}))
        return OrchestrationResult(task_id="task-run", worker="codex", warning="local warning", files={"final_report": Path("/vault/final.md")})


class JsonClient:
    def __init__(self, client: Any, mode: str) -> None:
        self.client = client
        self.mode = mode

    def get(self, path: str) -> tuple[int, dict[str, Any]]:
        response = self.client.get(path)
        return _json_response(response, self.mode)

    def post(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if self.mode == "flask":
            response = self.client.post(path, json=payload)
        elif self.mode == "starlette":
            response = self.client.post(path, json=payload)
        else:
            response = self.client.post(path, data=json.dumps(payload), content_type="application/json")
        return _json_response(response, self.mode)


def _json_response(response: Any, mode: str) -> tuple[int, dict[str, Any]]:
    status_code = getattr(response, "status_code", None) or getattr(response, "status", None)
    if mode == "flask":
        body = response.get_json()
    elif mode == "starlette":
        body = response.json()
    else:
        body = json.loads(response.get_data(as_text=True))
    assert isinstance(body, dict)
    return int(status_code), body


def _client_for(app: Any) -> JsonClient:
    if hasattr(app, "test_client"):
        return JsonClient(app.test_client(), "flask")

    if hasattr(app, "routes") or hasattr(app, "router"):
        try:
            from starlette.testclient import TestClient
        except ImportError as exc:  # pragma: no cover - documents the expected test dependency.
            pytest.fail(f"ASGI app returned, but starlette TestClient is unavailable: {exc}")
        return JsonClient(TestClient(app), "starlette")

    if callable(app):
        try:
            from werkzeug.test import Client
            from werkzeug.wrappers import Response
        except ImportError as exc:  # pragma: no cover - documents the expected test dependency.
            pytest.fail(f"WSGI app returned, but werkzeug test client is unavailable: {exc}")
        return JsonClient(Client(app, Response), "wsgi")

    pytest.fail("create_app() must return a testable Flask, ASGI, or WSGI app")


@pytest.fixture()
def web_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> JsonClient:
    config = load_default_config()
    config.system.vault_path = tmp_path / "vault"
    config.system.default_project_path = tmp_path / "project"
    config.system.default_project_path.mkdir()
    config.system.vault_path.mkdir()
    FakeOrchestrator.reset()

    try:
        web_app = importlib.import_module("ai_boss.web.app")
    except ModuleNotFoundError as exc:
        raise AssertionError("Expected web implementation module ai_boss.web.app with create_app(config=None)") from exc
    monkeypatch.setattr(web_app, "load_config", lambda vault_path=None: config, raising=False)
    monkeypatch.setattr(web_app, "Orchestrator", FakeOrchestrator, raising=False)
    monkeypatch.setattr("ai_boss.core.orchestrator.Orchestrator", FakeOrchestrator)
    monkeypatch.setattr("ai_boss.cli.app.load_config", lambda vault_path=None: config)

    assert hasattr(web_app, "create_app"), "ai_boss.web.app must expose create_app(config=None)"
    try:
        app = web_app.create_app(config=config)
    except TypeError:
        app = web_app.create_app()
    return _client_for(app)


def test_status_endpoint_reports_local_state_without_orchestrator_call(web_client: JsonClient) -> None:
    status_code, body = web_client.get("/api/status")

    assert status_code == 200
    assert body["ok"] is True
    assert "vault" in body
    assert "workers" in body
    assert FakeOrchestrator.calls == []


def test_tasks_and_single_task_endpoints_return_vault_history(web_client: JsonClient, tmp_path: Path) -> None:
    from ai_boss.memory.obsidian_vault import ObsidianVault

    vault = ObsidianVault(tmp_path / "vault")
    vault.create()
    task_path = vault.create_task("20260505-120000-web", "Показать web историю", tmp_path)
    vault.update_task_frontmatter(task_path, status="planned", planner="gemini")

    status_code, body = web_client.get("/api/tasks")

    assert status_code == 200
    assert body["tasks"][0]["id"] == "20260505-120000-web"
    assert body["tasks"][0]["status"] == "planned"

    status_code, body = web_client.get("/api/task/20260505-120000-web")

    assert status_code == 200
    assert body["task"]["id"] == "20260505-120000-web"
    assert "Показать web историю" in body["task"]["content"]


def test_projects_and_preflight_endpoints_are_available(web_client: JsonClient, tmp_path: Path) -> None:
    project = tmp_path / "project"

    status_code, body = web_client.post("/api/projects", {"name": "demo", "path": str(project), "default": True})

    assert status_code == 200
    assert body["projects"][0]["name"] == "demo"

    status_code, body = web_client.post("/api/preflight", {"project_path": str(project)})

    assert status_code == 200
    assert "checks" in body


@pytest.mark.parametrize(
    ("path", "payload", "expected_call", "expected_worker"),
    [
        ("/api/ask", {"question": "Что такое git diff?"}, "ask", "gemini"),
        ("/api/plan", {"task": "Составь план", "project_path": "/tmp/project"}, "plan", "gemini"),
        ("/api/review", {"task": "Проверь diff", "project_path": "/tmp/project"}, "review", "claude"),
        ("/api/run", {"task": "Добавь тесты", "project_path": "/tmp/project"}, "run", "codex"),
    ],
)
def test_action_endpoints_delegate_to_orchestrator_without_external_workers(
    web_client: JsonClient,
    path: str,
    payload: dict[str, str],
    expected_call: str,
    expected_worker: str,
) -> None:
    status_code, body = web_client.post(path, payload)

    assert status_code == 200
    assert body["worker"] == expected_worker
    assert body["files"]
    assert FakeOrchestrator.calls[-1][0] == expected_call


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/ask", {}),
        ("/api/plan", {}),
        ("/api/review", {"project_path": "/tmp/project"}),
        ("/api/run", {"project_path": "/tmp/project"}),
    ],
)
def test_action_endpoints_validate_required_json_fields(
    web_client: JsonClient,
    path: str,
    payload: dict[str, str],
) -> None:
    status_code, body = web_client.post(path, payload)

    assert status_code == 400
    assert body["ok"] is False
    assert body["error"]


def test_cli_web_command_is_registered() -> None:
    result = CliRunner().invoke(cli_app.app, ["web", "--help"])

    assert result.exit_code == 0
    assert "web" in result.output.lower()
    assert "--host" in result.output
    assert "--port" in result.output
