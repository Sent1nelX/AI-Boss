from pathlib import Path

import pytest

from ai_boss.config import loader
from ai_boss.config.loader import (
    CONFIG_FILE,
    SYSTEM_DIR,
    config_path_for_vault,
    load_config,
    load_default_config,
    load_yaml,
)
from ai_boss.core.errors import ConfigError


def test_load_default_config_expands_paths() -> None:
    config = load_default_config()

    assert config.system.name == "AI-Boss Super Brain"
    assert config.system.vault_path == Path("~/AI-Boss-Vault").expanduser()
    assert config.workers["codex"].command == ["codex", "exec"]
    assert config.workers["claude"].fallback_to == "gemini"


def test_config_path_for_vault_points_to_system_config(tmp_path: Path) -> None:
    assert config_path_for_vault(tmp_path) == tmp_path / SYSTEM_DIR / CONFIG_FILE


def test_load_config_uses_vault_config_and_expands_user_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    config_path = tmp_path / SYSTEM_DIR / CONFIG_FILE
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
system:
  vault_path: ~/brain
  default_project_path: ~/project
workers:
  gemini:
    command: ["gemini", "-p"]
""",
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.system.vault_path == fake_home / "brain"
    assert config.system.default_project_path == fake_home / "project"
    assert config.workers["gemini"].enabled is True


def test_load_config_accepts_codex_subagent_settings(tmp_path: Path) -> None:
    config_path = tmp_path / SYSTEM_DIR / CONFIG_FILE
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
workers:
  codex:
    command: ["codex", "exec"]
    allow_subagents: true
    subagent_policy: auto
""",
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.workers["codex"].allow_subagents is True
    assert config.workers["codex"].subagent_policy == "auto"


def test_load_config_falls_back_to_default_when_vault_config_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    default_path = tmp_path / "default.yaml"
    default_path.write_text(
        """
workers:
  gemini:
    command: ["mock-gemini"]
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(loader, "default_config_path", lambda: default_path)

    config = load_config(tmp_path)

    assert config.workers["gemini"].command == ["mock-gemini"]


def test_load_yaml_wraps_missing_file_and_yaml_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Файл конфигурации не найден"):
        load_yaml(tmp_path / "missing.yaml")

    broken_yaml = tmp_path / "broken.yaml"
    broken_yaml.write_text("workers: [", encoding="utf-8")

    with pytest.raises(ConfigError, match="Не удалось прочитать YAML"):
        load_yaml(broken_yaml)
