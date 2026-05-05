from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class WorkerStatus(StrEnum):
    AVAILABLE = "available"
    UNKNOWN = "unknown"
    LIMITED = "limited"
    FAILED = "failed"
    DISABLED = "disabled"
    COOLDOWN = "cooldown"


class WorkerState(BaseModel):
    status: WorkerStatus = WorkerStatus.UNKNOWN
    last_check: str | None = None
    last_error: str | None = None
    cooldown_until: str | None = None
    available_after: str | None = None
    total_runs_today: int = 0
    last_token_usage: str | None = None
    note: str | None = None
    fallback: str | None = None


class WorkerSettings(BaseModel):
    enabled: bool = True
    command: list[str]
    roles: list[str] = Field(default_factory=list)
    cost_level: str = "low"
    avoid_for_small_tasks: bool = False
    fallback_to: str | None = None
    allow_subagents: bool = True
    subagent_policy: str = "auto"


class WorkerResult(BaseModel):
    worker_name: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    detected_limit: bool = False
    available_after: str | None = None
