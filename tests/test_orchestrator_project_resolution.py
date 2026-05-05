from pathlib import Path

import pytest

from ai_boss.config.loader import load_default_config
from ai_boss.core.errors import GitGuardError
from ai_boss.core.orchestrator import Orchestrator


def test_resolve_project_prefers_explicit_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    current = tmp_path / "current"
    explicit = tmp_path / "explicit"
    current.mkdir()
    explicit.mkdir()
    monkeypatch.chdir(current)
    monkeypatch.setattr("ai_boss.core.orchestrator.GitGuard.is_git_repo", lambda self: True)

    orchestrator = Orchestrator(load_default_config())

    assert orchestrator._resolve_project(explicit) == explicit.resolve()


def test_resolve_project_uses_current_git_directory_before_config_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = tmp_path / "current"
    default = tmp_path / "default"
    current.mkdir()
    default.mkdir()
    monkeypatch.chdir(current)

    config = load_default_config()
    config.system.default_project_path = default
    monkeypatch.setattr(
        "ai_boss.core.orchestrator.GitGuard.is_git_repo",
        lambda self: self.project_path == current.resolve(),
    )

    orchestrator = Orchestrator(config)

    assert orchestrator._resolve_project(None) == current.resolve()


def test_resolve_project_uses_config_default_when_current_directory_is_not_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = tmp_path / "current"
    default = tmp_path / "default"
    current.mkdir()
    default.mkdir()
    monkeypatch.chdir(current)
    monkeypatch.setattr("ai_boss.core.orchestrator.GitGuard.is_git_repo", lambda self: False)

    config = load_default_config()
    config.system.default_project_path = default
    orchestrator = Orchestrator(config)

    assert orchestrator._resolve_project(None) == default.resolve()


def test_resolve_project_raises_when_no_project_can_be_inferred(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("ai_boss.core.orchestrator.GitGuard.is_git_repo", lambda self: False)

    orchestrator = Orchestrator(load_default_config())

    with pytest.raises(GitGuardError, match="Не найден git-проект"):
        orchestrator._resolve_project(None)

