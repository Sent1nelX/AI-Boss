from datetime import datetime, timedelta
from pathlib import Path

import yaml

from ai_boss.memory.obsidian_vault import DEFAULT_WORKERS
from ai_boss.models.worker import WorkerResult, WorkerState, WorkerStatus


class WorkerStateStore:
    def __init__(self, vault_path: Path) -> None:
        self.path = vault_path.expanduser() / "99_System" / "workers.yaml"

    def load(self) -> dict[str, WorkerState]:
        if not self.path.exists():
            return {name: WorkerState.model_validate(data) for name, data in DEFAULT_WORKERS.items()}
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        return {name: WorkerState.model_validate(value or {}) for name, value in data.items()}

    def save(self, states: dict[str, WorkerState]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: state.model_dump(mode="json") for name, state in states.items()}
        self.path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def get_status(self, name: str) -> WorkerStatus:
        return self.load().get(name, WorkerState()).status

    def update_from_result(self, result: WorkerResult) -> None:
        states = self.load()
        state = states.get(result.worker_name, WorkerState())
        state.last_check = datetime.now().isoformat()
        state.total_runs_today += 1
        state.last_error = result.stderr.strip() or None
        state.available_after = result.available_after
        if result.detected_limit:
            state.status = WorkerStatus.LIMITED
            state.cooldown_until = result.available_after or (datetime.now() + timedelta(minutes=30)).isoformat()
        elif result.success:
            state.status = WorkerStatus.AVAILABLE
            state.cooldown_until = None
        else:
            state.status = WorkerStatus.FAILED
        states[result.worker_name] = state
        self.save(states)

