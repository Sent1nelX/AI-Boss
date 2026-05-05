import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandOutput:
    stdout: str
    stderr: str
    exit_code: int


def run_command(args: list[str], cwd: Path | None = None, timeout: int = 120) -> CommandOutput:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return CommandOutput(stdout=completed.stdout, stderr=completed.stderr, exit_code=completed.returncode)

