from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from ai_boss.config.loader import AIBossConfig, load_config
from ai_boss.core.errors import AIBossError
from ai_boss.core.git_guard import GitGuard
from ai_boss.core.orchestrator import Orchestrator
from ai_boss.memory.obsidian_vault import ObsidianVault
from ai_boss.memory.state_store import WorkerStateStore


def create_app(config: AIBossConfig | None = None) -> MiniWebApp:
    return MiniWebApp(config=config)


class MiniWebApp:
    def __init__(self, config: AIBossConfig | None = None) -> None:
        self.config = config

    def test_client(self) -> "MiniTestClient":
        return MiniTestClient(self)

    def handle(self, method: str, path: str, payload: dict[str, Any] | None = None) -> "MiniResponse":
        parsed = urlparse(path)
        try:
            if method == "GET":
                return self._handle_get(parsed.path)
            if method == "POST":
                return self._handle_post(parsed.path, payload or {})
            return json_response({"ok": False, "error": "Метод не поддерживается."}, 405)
        except AIBossError as exc:
            return json_response({"ok": False, "error": str(exc)}, 400)

    def _config(self) -> AIBossConfig:
        return self.config or load_config()

    def _handle_get(self, path: str) -> "MiniResponse":
        if path == "/api/status":
            return json_response(status_payload(self._config()))
        if path == "/api/tasks":
            vault = ObsidianVault(self._config().system.vault_path)
            tasks = [_json_safe_task(task) for task in vault.list_tasks()]
            return json_response({"ok": True, "tasks": tasks})
        if path.startswith("/api/task/"):
            task_id = unquote(path.removeprefix("/api/task/"))
            vault = ObsidianVault(self._config().system.vault_path)
            task_path = vault.find_task(task_id)
            if not task_path:
                return json_response({"ok": False, "error": "Задача не найдена."}, 404)
            return json_response(
                {
                    "ok": True,
                    "task": {
                        "id": task_id,
                        "path": str(task_path),
                        "content": task_path.read_text(encoding="utf-8"),
                    },
                }
            )
        return json_response({"ok": False, "error": "Маршрут не найден."}, 404)

    def _handle_post(self, path: str, payload: dict[str, Any]) -> "MiniResponse":
        orchestrator = Orchestrator(self._config())
        project_path = _payload_project_path(payload)
        if path == "/api/ask":
            result = orchestrator.ask(_required_payload_text(payload, "question", "text"))
            return json_response(_flat_result(result))
        if path == "/api/plan":
            result = orchestrator.plan(_required_payload_text(payload, "task", "text"), project_path)
            return json_response(_flat_result(result))
        if path == "/api/review":
            task = _required_payload_text(payload, "task", "text")
            result = orchestrator.review(user_task=task, project_path=project_path)
            return json_response(_flat_result(result))
        if path == "/api/run":
            result = orchestrator.run(_required_payload_text(payload, "task", "text"), project_path)
            return json_response(_flat_result(result))
        return json_response({"ok": False, "error": "Маршрут не найден."}, 404)


class MiniTestClient:
    def __init__(self, app: MiniWebApp) -> None:
        self.app = app

    def get(self, path: str) -> "MiniResponse":
        return self.app.handle("GET", path)

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: str | bytes | None = None,
        content_type: str | None = None,
    ) -> "MiniResponse":
        payload = json
        if payload is None and data:
            raw = data.decode("utf-8") if isinstance(data, bytes) else data
            payload = json_module_loads(raw)
        return self.app.handle("POST", path, payload or {})


@dataclass
class MiniResponse:
    status_code: int
    payload: dict[str, Any]

    def get_json(self) -> dict[str, Any]:
        return self.payload

    def get_data(self, as_text: bool = False) -> str | bytes:
        body = json.dumps(self.payload, ensure_ascii=False)
        return body if as_text else body.encode("utf-8")


def json_response(payload: dict[str, Any], status_code: int = 200) -> MiniResponse:
    return MiniResponse(status_code=status_code, payload=payload)


def status_payload(config: AIBossConfig) -> dict[str, Any]:
    vault = ObsidianVault(config.system.vault_path)
    workers = {}
    states = WorkerStateStore(vault.path).load()
    for name, settings in config.workers.items():
        state = states.get(name)
        workers[name] = {
            "command": settings.command,
            "cli_found": shutil.which(settings.command[0]) is not None,
            "status": state.status.value if state else "unknown",
            "enabled": settings.enabled,
            "allow_subagents": settings.allow_subagents,
            "subagent_policy": settings.subagent_policy,
        }
    current_dir = Path.cwd().resolve()
    current_guard = GitGuard(current_dir)
    return {
        "ok": True,
        "vault": {"path": str(vault.path), "exists": vault.exists()},
        "project": {
            "current_path": str(current_dir),
            "current_is_git_repo": current_guard.is_git_repo(),
            "current_git_status": current_guard.status_short() if current_guard.is_git_repo() else None,
            "default_project_path": str(config.system.default_project_path) if config.system.default_project_path else None,
        },
        "workers": workers,
        "safety": config.safety.model_dump(mode="json"),
    }


def _required_payload_text(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    joined = " или ".join(keys)
    raise AIBossError(f"Не заполнено обязательное поле: {joined}.")


def _payload_project_path(payload: dict[str, Any]) -> Path | None:
    value = payload.get("project_path")
    if not value:
        return None
    return Path(str(value)).expanduser().resolve()


def _flat_result(result: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "task_id": result.task_id,
        "answer": result.answer,
        "worker": result.worker,
        "warning": result.warning,
        "files": {key: str(path) for key, path in result.files.items()},
    }


def _json_safe_task(task: dict[str, Any]) -> dict[str, Any]:
    return {key: str(value) if isinstance(value, Path) else value for key, value in task.items()}


def json_module_loads(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}

