from ai_boss.models.task import TaskType
from ai_boss.models.worker import WorkerState, WorkerStatus


DEFAULT_ROUTES = {
    TaskType.SIMPLE_QUESTION: "gemini",
    TaskType.PLANNING: "gemini",
    TaskType.ARCHITECTURE: "claude",
    TaskType.CODE_CHANGE: "codex",
    TaskType.BUGFIX: "codex",
    TaskType.REFACTOR: "codex",
    TaskType.REVIEW: "claude",
    TaskType.DOCUMENTATION: "gemini",
    TaskType.TEST_GENERATION: "codex",
    TaskType.DEPLOYMENT_HELP: "gemini",
}

FALLBACKS = {
    "claude": "gemini",
}

UNAVAILABLE = {WorkerStatus.LIMITED, WorkerStatus.FAILED, WorkerStatus.DISABLED, WorkerStatus.COOLDOWN}


class Router:
    def __init__(self, states: dict[str, WorkerState] | None = None) -> None:
        self.states = states or {}

    def route(self, task_type: TaskType) -> str:
        worker = DEFAULT_ROUTES[task_type]
        if task_type == TaskType.SIMPLE_QUESTION:
            return "gemini"
        return self._with_fallback(worker)

    def _with_fallback(self, worker: str) -> str:
        state = self.states.get(worker)
        if state and state.status in UNAVAILABLE:
            return FALLBACKS.get(worker, worker)
        return worker

