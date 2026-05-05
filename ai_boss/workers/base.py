import re
import subprocess
from datetime import datetime
from pathlib import Path

from ai_boss.core.cli_resolver import resolved_command
from ai_boss.memory.obsidian_vault import ObsidianVault
from ai_boss.memory.state_store import WorkerStateStore
from ai_boss.models.worker import WorkerResult


LIMIT_PATTERNS = (
    "you've hit your limit",
    "rate limit",
    "quota exceeded",
    "too many requests",
    "лимит",
    "429",
)


class BaseWorker:
    name = "base"

    def __init__(self, command: list[str], vault: ObsidianVault, timeout: int = 600) -> None:
        self.command = command
        self.vault = vault
        self.timeout = timeout
        self.state_store = WorkerStateStore(vault.path)

    def run(self, prompt: str, cwd: Path | None = None) -> WorkerResult:
        started = datetime.now()
        stdout = ""
        stderr = ""
        exit_code: int | None = None
        try:
            command = resolved_command(self.command)
            completed = subprocess.run(
                [*command, prompt],
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = completed.returncode
        except FileNotFoundError as exc:
            stderr = f"Команда не найдена: {self.command[0]}"
            exit_code = None
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = f"Таймаут выполнения после {self.timeout} секунд"
            exit_code = None
        finished = datetime.now()
        combined = f"{stdout}\n{stderr}"
        detected_limit = detect_limit(combined)
        result = WorkerResult(
            worker_name=self.name,
            success=exit_code == 0 and not detected_limit,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            started_at=started,
            finished_at=finished,
            duration_seconds=(finished - started).total_seconds(),
            detected_limit=detected_limit,
            available_after=extract_available_after(combined),
        )
        self.state_store.update_from_result(result)
        if not result.success:
            self.vault.write_error(f"Ошибка worker {self.name}", combined.strip() or "Нет вывода", self.name)
        return result


def detect_limit(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in LIMIT_PATTERNS)


def extract_available_after(text: str) -> str | None:
    match = re.search(r"resets?\s+(.+?)(?:\n|$)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"available_after[:=]\s*(.+?)(?:\n|$)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None
