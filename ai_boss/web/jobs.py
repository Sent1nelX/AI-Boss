from __future__ import annotations

import threading
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ai_boss.config.loader import load_config
from ai_boss.core.orchestrator import Orchestrator
from ai_boss.core.runtime import runtime_context
from ai_boss.core.task_classifier import TaskClassifier
from ai_boss.models.result import OrchestrationResult
from ai_boss.models.task import TaskType


@dataclass
class Job:
    id: str
    mode: str
    text: str
    project_path: str | None
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    logs: list[dict[str, str]] = field(default_factory=list)
    result: dict[str, object] | None = None
    error: str | None = None
    retry_of: str | None = None

    def add_log(self, source: str, message: str) -> None:
        self.logs.append({"time": datetime.now().isoformat(), "source": source, "message": message})

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "mode": self.mode,
            "text": self.text,
            "project_path": self.project_path,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "logs": self.logs,
            "result": self.result,
            "error": self.error,
            "retry_of": self.retry_of,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Job":
        logs = data.get("logs")
        return cls(
            id=str(data.get("id") or uuid4().hex[:12]),
            mode=str(data.get("mode") or "do"),
            text=str(data.get("text") or ""),
            project_path=str(data["project_path"]) if data.get("project_path") else None,
            status=str(data.get("status") or "queued"),
            created_at=str(data.get("created_at") or datetime.now().isoformat()),
            started_at=str(data["started_at"]) if data.get("started_at") else None,
            finished_at=str(data["finished_at"]) if data.get("finished_at") else None,
            logs=logs if isinstance(logs, list) else [],
            result=data.get("result") if isinstance(data.get("result"), dict) else None,
            error=str(data["error"]) if data.get("error") else None,
            retry_of=str(data["retry_of"]) if data.get("retry_of") else None,
        )


class JobQueue:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._queue: deque[str] = deque()
        self._cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._loaded_path: Path | None = None

    def submit(self, mode: str, text: str, project_path: Path | None = None) -> Job:
        normalized_mode = mode if mode in {"do", "ask", "plan", "review", "run"} else "do"
        job = Job(id=uuid4().hex[:12], mode=normalized_mode, text=text, project_path=str(project_path) if project_path else None)
        job.add_log("sys", "Задача добавлена в очередь.")
        with self._lock:
            self._ensure_loaded_locked()
            self._jobs[job.id] = job
            self._queue.append(job.id)
            self._save_locked()
            self._ensure_worker_locked()
        return job

    def retry(self, job_id: str) -> Job | None:
        with self._lock:
            self._ensure_loaded_locked()
            original = self._jobs.get(job_id)
            if not original:
                return None
            job = Job(id=uuid4().hex[:12], mode=original.mode, text=original.text, project_path=original.project_path, retry_of=original.id)
            job.add_log("sys", f"Повторный запуск задачи {original.id}.")
            self._jobs[job.id] = job
            self._queue.append(job.id)
            self._save_locked()
            self._ensure_worker_locked()
            return job

    def cancel(self, job_id: str) -> Job | None:
        with self._lock:
            self._ensure_loaded_locked()
            job = self._jobs.get(job_id)
            if not job:
                return None
            if job.status == "queued":
                self._queue = deque(item for item in self._queue if item != job_id)
                job.status = "cancelled"
                job.finished_at = datetime.now().isoformat()
                job.error = "Отменено пользователем до запуска."
                job.add_log("sys", "Задача отменена до запуска.")
                self._save_locked()
                return job
            if job.status == "running":
                job.status = "cancelling"
                job.add_log("sys", "Запрошена отмена активного процесса.")
                self._cancel_events.setdefault(job_id, threading.Event()).set()
                self._save_locked()
                return job
            return job

    def list_jobs(self, limit: int = 20) -> list[dict[str, object]]:
        with self._lock:
            self._ensure_loaded_locked()
            jobs = sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
            return [job.to_dict() for job in jobs[:limit]]

    def get_job(self, job_id: str) -> dict[str, object] | None:
        with self._lock:
            self._ensure_loaded_locked()
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None

    def reset(self) -> None:
        with self._lock:
            self._loaded_path = _jobs_path()
            self._jobs = {}
            self._queue = deque()
            self._cancel_events = {}
            self._save_locked()

    def _ensure_worker_locked(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._work_loop, name="ai-boss-web-job-worker", daemon=True)
        self._worker.start()

    def _work_loop(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    self._save_locked()
                    return
                job_id = self._queue.popleft()
                job = self._jobs[job_id]
                if job.status != "queued":
                    continue
                job.status = "running"
                job.started_at = datetime.now().isoformat()
                job.add_log("sys", "Выполнение начато.")
                cancel_event = self._cancel_events.setdefault(job_id, threading.Event())
                self._save_locked()
            self._run_job(job)

    def _run_job(self, job: Job) -> None:
        try:
            config = load_config()
            orchestrator = Orchestrator(config)
            project_path = Path(job.project_path).expanduser().resolve() if job.project_path else None
            cancel_event = self._cancel_events.setdefault(job.id, threading.Event())
            with runtime_context(log_sink=job.add_log, cancel_event=cancel_event):
                result = self._dispatch(orchestrator, job, project_path)
            with self._lock:
                if cancel_event.is_set():
                    job.status = "cancelled"
                    job.error = "Отменено пользователем."
                else:
                    job.status = "succeeded"
                    job.result = _result_to_json(result)
                job.finished_at = datetime.now().isoformat()
                job.add_log("sys", "Выполнение завершено.")
                self._cancel_events.pop(job.id, None)
                self._save_locked()
        except Exception as exc:
            with self._lock:
                cancel_event = self._cancel_events.get(job.id)
                job.status = "cancelled" if cancel_event and cancel_event.is_set() else "failed"
                job.finished_at = datetime.now().isoformat()
                job.error = "Отменено пользователем." if job.status == "cancelled" else str(exc)
                job.add_log("err", job.error)
                self._cancel_events.pop(job.id, None)
                self._save_locked()

    def _dispatch(self, orchestrator: Orchestrator, job: Job, project_path: Path | None) -> OrchestrationResult:
        if job.mode == "ask":
            job.add_log("gem", "Gemini отвечает на вопрос.")
            return orchestrator.ask(job.text)
        if job.mode == "plan":
            job.add_log("gem", "Planner Agent готовит план.")
            return orchestrator.plan(job.text, project_path)
        if job.mode == "review":
            job.add_log("cld", "Reviewer проверяет git diff.")
            return orchestrator.review(user_task=job.text or "Ревью текущих изменений", project_path=project_path)
        if job.mode == "run":
            job.add_log("cdx", "Codex получил write-задачу.")
            return orchestrator.run(job.text, project_path)

        task_type = TaskClassifier().classify(job.text)
        job.add_log("sys", f"Автоклассификация: {task_type.value}.")
        if task_type == TaskType.SIMPLE_QUESTION:
            job.add_log("gem", "Маршрут: ask.")
            return orchestrator.ask(job.text)
        if task_type == TaskType.REVIEW:
            job.add_log("cld", "Маршрут: review.")
            return orchestrator.review(user_task=job.text, project_path=project_path)
        if task_type in {TaskType.CODE_CHANGE, TaskType.BUGFIX, TaskType.REFACTOR, TaskType.TEST_GENERATION}:
            job.add_log("cdx", "Маршрут: run.")
            return orchestrator.run(job.text, project_path)
        job.add_log("gem", "Маршрут: plan.")
        return orchestrator.plan(job.text, project_path)

    def _ensure_loaded_locked(self) -> None:
        path = _jobs_path()
        if self._loaded_path == path:
            return
        self._loaded_path = path
        self._jobs = {}
        self._queue = deque()
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        jobs = raw.get("jobs") if isinstance(raw, dict) else None
        if not isinstance(jobs, list):
            return
        changed = False
        for item in jobs:
            if not isinstance(item, dict):
                continue
            job = Job.from_dict(item)
            if job.status in {"running", "cancelling"}:
                job.status = "failed"
                job.finished_at = datetime.now().isoformat()
                job.error = "AI-Boss web был перезапущен во время выполнения."
                job.add_log("sys", "Задача помечена failed после перезапуска web-процесса.")
                changed = True
            if job.status == "queued":
                self._queue.append(job.id)
            self._jobs[job.id] = job
        if changed:
            self._save_locked()
        if self._queue:
            self._ensure_worker_locked()

    def _save_locked(self) -> None:
        path = self._loaded_path or _jobs_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "jobs": [job.to_dict() for job in sorted(self._jobs.values(), key=lambda item: item.created_at)],
        }
        temp_path = path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        temp_path.replace(path)


def _result_to_json(result: OrchestrationResult) -> dict[str, object]:
    return {
        "task_id": result.task_id,
        "answer": result.answer,
        "worker": result.worker,
        "warning": result.warning,
        "files": {key: str(path) for key, path in result.files.items()},
    }


def _jobs_path() -> Path:
    return load_config().system.vault_path.expanduser() / "99_System" / "web-jobs.json"


job_queue = JobQueue()
