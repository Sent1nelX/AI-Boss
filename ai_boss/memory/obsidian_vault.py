from datetime import datetime
from pathlib import Path
from uuid import uuid4

import yaml

from ai_boss.config.loader import default_config_path


VAULT_DIRS = [
    "00_Inbox",
    "01_Tasks",
    "02_Plans",
    "03_Execution",
    "04_Reviews",
    "05_Final-Reports",
    "06_Project-Knowledge",
    "07_Decisions",
    "08_Errors",
    "99_System",
]


DEFAULT_WORKERS = {
    "gemini": {"status": "unknown", "last_check": None, "last_error": None, "cooldown_until": None, "total_runs_today": 0},
    "codex": {
        "status": "unknown",
        "last_check": None,
        "last_error": None,
        "cooldown_until": None,
        "total_runs_today": 0,
        "last_token_usage": None,
        "note": "Не использовать для мелких вопросов",
    },
    "claude": {"status": "unknown", "last_check": None, "last_error": None, "available_after": None, "fallback": "gemini"},
}


DEFAULT_ROUTING = {
    "simple_question": "gemini",
    "planning": "gemini",
    "architecture": "claude",
    "code_change": "codex",
    "bugfix": "codex",
    "refactor": "codex",
    "review": "claude",
    "documentation": "gemini",
    "test_generation": "codex",
    "deployment_help": "gemini",
}


class ObsidianVault:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()

    def create(self) -> list[Path]:
        created: list[Path] = []
        self.path.mkdir(parents=True, exist_ok=True)
        for directory in VAULT_DIRS:
            target = self.path / directory
            if not target.exists():
                target.mkdir(parents=True)
                created.append(target)
        self._write_if_missing(self.system_path("config.yaml"), default_config_path().read_text(encoding="utf-8"))
        self._write_yaml_if_missing(self.system_path("workers.yaml"), DEFAULT_WORKERS)
        self._write_yaml_if_missing(self.system_path("routing-rules.yaml"), DEFAULT_ROUTING)
        return created

    def exists(self) -> bool:
        return self.path.exists()

    def system_path(self, filename: str) -> Path:
        return self.path / "99_System" / filename

    def task_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{timestamp}-{uuid4().hex[:6]}"

    def write_inbox(self, question: str, answer: str, worker: str) -> Path:
        file_path = self.path / "00_Inbox" / f"{self.task_id()}-ask.md"
        content = f"---\ntype: ask\nworker: {worker}\ncreated_at: {datetime.now().isoformat()}\n---\n\n# Вопрос\n\n{question}\n\n# Ответ\n\n{answer}\n"
        self._write(file_path, content)
        return file_path

    def create_task(self, task_id: str, user_task: str, project_path: Path | None = None) -> Path:
        project_name = project_path.name if project_path else None
        now = datetime.now().isoformat()
        frontmatter = {
            "id": task_id,
            "status": "created",
            "project": project_name,
            "project_path": str(project_path) if project_path else None,
            "branch": None,
            "created_at": now,
            "updated_at": now,
            "planner": None,
            "coder": None,
            "reviewer": None,
            "risk_level": "unknown",
        }
        body = (
            f"{self._frontmatter(frontmatter)}\n# Задача\n\n{user_task}\n\n# Контекст\n\nПока не заполнено.\n\n"
            "# План\n\nПока не заполнено.\n\n# Выполнение\n\nПока не заполнено.\n\n# Ревью\n\nПока не заполнено.\n\n# Итог\n\nПока не заполнено.\n"
        )
        path = self.path / "01_Tasks" / f"{task_id}.md"
        self._write(path, body)
        return path

    def update_task_frontmatter(self, task_path: Path, **updates: object) -> None:
        text = task_path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            return
        _, raw_frontmatter, rest = text.split("---", 2)
        data = yaml.safe_load(raw_frontmatter) or {}
        data.update(updates)
        data["updated_at"] = datetime.now().isoformat()
        task_path.write_text(f"{self._frontmatter(data)}{rest.lstrip()}", encoding="utf-8")

    def list_tasks(self, limit: int = 20) -> list[dict[str, object]]:
        tasks_dir = self.path / "01_Tasks"
        if not tasks_dir.exists():
            return []
        records: list[dict[str, object]] = []
        for task_path in sorted(tasks_dir.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True):
            frontmatter = self._read_frontmatter(task_path)
            if not frontmatter:
                continue
            frontmatter["path"] = task_path
            records.append(frontmatter)
            if len(records) >= limit:
                break
        return records

    def find_task(self, task_id: str) -> Path | None:
        exact = self.path / "01_Tasks" / f"{task_id}.md"
        if exact.exists():
            return exact
        matches = sorted((self.path / "01_Tasks").glob(f"{task_id}*.md"))
        return matches[0] if matches else None

    def write_plan(self, task_id: str, content: str, worker: str) -> Path:
        return self._write_artifact("02_Plans", task_id, "plan", content, worker)

    def write_execution(self, task_id: str, content: str, worker: str, phase: str = "execution") -> Path:
        return self._write_artifact("03_Execution", task_id, phase, content, worker)

    def write_review(self, task_id: str, content: str, worker: str, phase: str = "review") -> Path:
        return self._write_artifact("04_Reviews", task_id, phase, content, worker)

    def write_final_report(self, task_id: str, content: str) -> Path:
        return self._write_artifact("05_Final-Reports", task_id, "final-report", content, "ai-boss")

    def write_error(self, title: str, content: str, worker: str | None = None) -> Path:
        task_id = self.task_id()
        safe_title = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in title.lower())[:60]
        path = self.path / "08_Errors" / f"{task_id}-{safe_title}.md"
        frontmatter = {"type": "error", "worker": worker, "created_at": datetime.now().isoformat()}
        self._write(path, f"{self._frontmatter(frontmatter)}\n# Ошибка\n\n{title}\n\n# Детали\n\n{content}\n")
        return path

    def _write_artifact(self, directory: str, task_id: str, kind: str, content: str, worker: str) -> Path:
        path = self.path / directory / f"{task_id}-{kind}.md"
        frontmatter = {"task_id": task_id, "type": kind, "worker": worker, "created_at": datetime.now().isoformat()}
        self._write(path, f"{self._frontmatter(frontmatter)}\n{content.rstrip()}\n")
        return path

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _write_if_missing(self, path: Path, content: str) -> None:
        if not path.exists():
            self._write(path, content)

    def _write_yaml_if_missing(self, path: Path, data: dict[str, object]) -> None:
        if not path.exists():
            self._write(path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False))

    def _frontmatter(self, data: dict[str, object]) -> str:
        return f"---\n{yaml.safe_dump(data, allow_unicode=True, sort_keys=False)}---\n"

    def _read_frontmatter(self, path: Path) -> dict[str, object]:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            return {}
        try:
            _, raw_frontmatter, _ = text.split("---", 2)
        except ValueError:
            return {}
        return yaml.safe_load(raw_frontmatter) or {}
