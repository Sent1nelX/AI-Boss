from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class TaskType(StrEnum):
    SIMPLE_QUESTION = "simple_question"
    PLANNING = "planning"
    CODE_CHANGE = "code_change"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    REVIEW = "review"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    TEST_GENERATION = "test_generation"
    DEPLOYMENT_HELP = "deployment_help"


class TaskRecord(BaseModel):
    id: str
    user_task: str
    status: str = "created"
    project: str | None = None
    project_path: Path | None = None
    branch: str | None = None
    created_at: datetime
    updated_at: datetime
    planner: str | None = None
    coder: str | None = None
    reviewer: str | None = None
    risk_level: str = "unknown"

