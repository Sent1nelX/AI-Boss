from pathlib import Path

from pydantic import BaseModel, Field


class OrchestrationResult(BaseModel):
    task_id: str | None = None
    answer: str | None = None
    files: dict[str, Path] = Field(default_factory=dict)
    worker: str | None = None
    warning: str | None = None

