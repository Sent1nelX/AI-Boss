from pathlib import Path

from ai_boss.core.command_runner import run_command
from ai_boss.core.errors import GitGuardError


class GitGuard:
    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path.expanduser().resolve()

    def ensure_path_exists(self) -> None:
        if not self.project_path.exists():
            raise GitGuardError(f"Путь проекта не существует: {self.project_path}")

    def is_git_repo(self) -> bool:
        if not self.project_path.exists():
            return False
        result = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=self.project_path, timeout=10)
        return result.exit_code == 0 and result.stdout.strip() == "true"

    def ensure_git_repo(self) -> None:
        self.ensure_path_exists()
        if not self.is_git_repo():
            raise GitGuardError(f"Путь не является git-репозиторием: {self.project_path}")

    def status_short(self) -> str:
        self.ensure_git_repo()
        return run_command(["git", "status", "--short"], cwd=self.project_path, timeout=20).stdout

    def is_dirty(self) -> bool:
        return bool(self.status_short().strip())

    def create_branch(self, task_id: str) -> str:
        self.ensure_git_repo()
        branch = f"ai-boss/{task_id}"
        result = run_command(["git", "switch", "-c", branch], cwd=self.project_path, timeout=30)
        if result.exit_code != 0:
            raise GitGuardError(f"Не удалось создать ветку {branch}: {result.stderr.strip()}")
        return branch

    def diff(self) -> str:
        self.ensure_git_repo()
        return run_command(["git", "diff"], cwd=self.project_path, timeout=60).stdout

    def diff_stat(self) -> str:
        self.ensure_git_repo()
        return run_command(["git", "diff", "--stat"], cwd=self.project_path, timeout=60).stdout

