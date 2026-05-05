from pathlib import Path

from typer.testing import CliRunner

import ai_boss.cli.app as cli_app
from ai_boss.config.loader import load_default_config
from ai_boss.core.preflight import build_preflight
from ai_boss.memory.obsidian_vault import ObsidianVault
from ai_boss.memory.project_store import ProjectStore


def test_project_store_add_list_remove_and_default(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "vault")
    project_path = tmp_path / "project"
    project_path.mkdir()

    store.add_project("demo", project_path, make_default=True)

    projects = store.list_projects()
    assert projects == [{"name": "demo", "path": str(project_path.resolve()), "default": True}]
    assert store.default_project_path() == project_path.resolve()
    assert store.find_path("demo") == project_path.resolve()
    assert store.remove_project("demo") is True
    assert store.list_projects() == []


def test_vault_init_creates_projects_yaml(tmp_path: Path) -> None:
    vault = ObsidianVault(tmp_path / "vault")

    vault.create()

    assert vault.system_path("projects.yaml").exists()


def test_preflight_reports_missing_project_without_crashing(tmp_path: Path, monkeypatch) -> None:
    config = load_default_config()
    config.system.vault_path = tmp_path / "vault"
    monkeypatch.setattr("ai_boss.core.preflight.which", lambda command: None)
    monkeypatch.setattr("ai_boss.core.preflight.GitGuard.is_git_repo", lambda self: False)

    result = build_preflight(config)

    assert result["ok"] is False
    assert any(check["name"] == "project_selected" for check in result["checks"])


def test_cli_project_commands_use_vault_store(tmp_path: Path, monkeypatch) -> None:
    config = load_default_config()
    config.system.vault_path = tmp_path / "vault"
    project_path = tmp_path / "project"
    project_path.mkdir()
    monkeypatch.setattr(cli_app, "load_config", lambda vault_path=None: config)
    runner = CliRunner()

    add = runner.invoke(cli_app.app, ["project-add", "demo", str(project_path), "--default"])
    listing = runner.invoke(cli_app.app, ["project-list"])

    assert add.exit_code == 0
    assert listing.exit_code == 0
    assert "demo" in listing.output
    assert ProjectStore(config.system.vault_path).find_path("demo") == project_path.resolve()
