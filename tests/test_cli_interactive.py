from pathlib import Path

from typer.testing import CliRunner

from ai_boss.cli import app as cli_app
from ai_boss.config.loader import load_default_config


def test_cli_without_command_starts_interactive_mode_and_handles_service_commands(
    tmp_path: Path, monkeypatch
) -> None:
    config = load_default_config()
    config.system.vault_path = tmp_path / "vault"
    config.system.default_project_path = None

    monkeypatch.setattr(cli_app, "load_config", lambda vault_path=None: config)
    monkeypatch.setattr("ai_boss.cli.app.GitGuard.is_git_repo", lambda self: False)
    monkeypatch.setattr("ai_boss.cli.app.resolve_cli_executable", lambda command: None)

    result = CliRunner().invoke(
        cli_app.app,
        [],
        input="/help\n/status\n/project\n/clear-project\n/exit\n",
    )

    assert result.exit_code == 0
    assert "AI-Boss Super Brain" in result.output
    assert "Служебные команды" in result.output
    assert "AI-Boss status" in result.output
    assert "Проект сессии: не выбран" in result.output
    assert "Проект сессии сброшен." in result.output
    assert "Готово, сессия закрыта." in result.output
