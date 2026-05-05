from __future__ import annotations

import subprocess
from types import SimpleNamespace

from ai_boss.core import cli_resolver


def test_resolve_cli_executable_uses_regular_path(monkeypatch) -> None:
    cli_resolver.resolve_cli_executable.cache_clear()
    monkeypatch.setattr(cli_resolver.shutil, "which", lambda command: "/usr/bin/gemini")

    assert cli_resolver.resolve_cli_executable("gemini") == "/usr/bin/gemini"


def test_resolve_cli_executable_falls_back_to_interactive_shell(monkeypatch) -> None:
    cli_resolver.resolve_cli_executable.cache_clear()
    monkeypatch.setattr(cli_resolver.shutil, "which", lambda command: None)
    monkeypatch.setattr(cli_resolver.os.path, "exists", lambda path: path == "/bin/bash")
    monkeypatch.setattr(cli_resolver.os.path, "isabs", lambda path: path.startswith("/"))
    monkeypatch.setattr(cli_resolver.os, "access", lambda path, mode: path == "/home/user/.nvm/bin/gemini")

    def fake_run(args, **kwargs):
        assert args[:2] == ["/bin/bash", "-ic"]
        return SimpleNamespace(returncode=0, stdout="/home/user/.nvm/bin/gemini\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert cli_resolver.resolve_cli_executable("gemini") == "/home/user/.nvm/bin/gemini"


def test_resolved_command_replaces_only_executable(monkeypatch) -> None:
    cli_resolver.resolve_cli_executable.cache_clear()
    monkeypatch.setattr(cli_resolver, "resolve_cli_executable", lambda command: "/opt/bin/gemini")

    assert cli_resolver.resolved_command(["gemini", "-p"]) == ["/opt/bin/gemini", "-p"]
