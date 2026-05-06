import os
import re
import signal
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from ai_boss.core.cli_resolver import resolved_command, resolved_command_env
from ai_boss.core.runtime import cancel_requested, emit_runtime_log, runtime_hooks_enabled
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
            env = resolved_command_env(self.command)
            if runtime_hooks_enabled() and self.name == "codex":
                stdout, stderr, exit_code = self._run_streaming([*command, prompt], cwd, env)
            else:
                completed = subprocess.run(
                    [*command, prompt],
                    cwd=cwd,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout,
                    check=False,
                )
                stdout = completed.stdout
                stderr = completed.stderr
                exit_code = completed.returncode
                if runtime_hooks_enabled():
                    self._emit_captured_output(stdout, stderr)
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

    def _run_streaming(self, args: list[str], cwd: Path | None, env: dict[str, str]) -> tuple[str, str, int | None]:
        popen_kwargs = {}
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(
            args,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            **popen_kwargs,
        )
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        def read_stream(stream, target: list[str], source: str) -> None:
            if stream is None:
                return
            for line in iter(stream.readline, ""):
                target.append(line)
                emit_runtime_log(source, line.rstrip())
            stream.close()

        stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, stdout_parts, self.name), daemon=True)
        stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, stderr_parts, f"{self.name}:err"), daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        deadline = time.monotonic() + self.timeout

        while process.poll() is None:
            if cancel_requested():
                emit_runtime_log("sys", f"Отмена: останавливаю {self.name}.")
                self._terminate_process(process)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._terminate_process(process, force=True)
                    process.wait(timeout=5)
                stderr_parts.append("Выполнение отменено пользователем.\n")
                break
            if time.monotonic() > deadline:
                self._terminate_process(process, force=True)
                process.wait(timeout=5)
                raise subprocess.TimeoutExpired(cmd=args, timeout=self.timeout, output="".join(stdout_parts))
            time.sleep(0.1)

        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        return "".join(stdout_parts), "".join(stderr_parts), process.returncode

    def _emit_captured_output(self, stdout: str, stderr: str) -> None:
        for line in stdout.splitlines():
            emit_runtime_log(self.name, line)
        for line in stderr.splitlines():
            emit_runtime_log(f"{self.name}:err", line)

    def _terminate_process(self, process: subprocess.Popen, force: bool = False) -> None:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
                return
            except ProcessLookupError:
                return
            except OSError:
                pass
        if force:
            process.kill()
        else:
            process.terminate()


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
