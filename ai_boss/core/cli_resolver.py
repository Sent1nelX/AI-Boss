from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from functools import lru_cache


@lru_cache(maxsize=64)
def resolve_cli_executable(command: str) -> str | None:
    """Resolve CLI tools visible either in this process PATH or an interactive shell."""
    if not command:
        return None

    direct = shutil.which(command)
    if direct:
        return direct

    if os.path.sep in command:
        return None

    for shell in ("/bin/bash", "/usr/bin/bash", "/bin/zsh", "/usr/bin/zsh"):
        resolved = _resolve_with_shell(shell, command)
        if resolved:
            return resolved
    return None


def cli_exists(command: str) -> bool:
    return resolve_cli_executable(command) is not None


def resolved_command(command: list[str]) -> list[str]:
    if not command:
        return command
    executable = resolve_cli_executable(command[0])
    if not executable:
        return command
    return [executable, *command[1:]]


def _resolve_with_shell(shell: str, command: str) -> str | None:
    if not os.path.exists(shell):
        return None
    try:
        completed = subprocess.run(
            [shell, "-ic", f"command -v -- {shlex.quote(command)}"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    for line in completed.stdout.splitlines():
        candidate = line.strip()
        if candidate and os.path.isabs(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None
