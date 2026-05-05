from pathlib import Path

import pytest
import yaml

from ai_boss.config.writer import config_yaml_path, patch_config_data, read_config_data, write_config_update
from ai_boss.core.errors import ConfigError


def test_config_yaml_path_points_to_vault_system_config(tmp_path: Path) -> None:
    assert config_yaml_path(tmp_path) == tmp_path / "99_System" / "config.yaml"


def test_read_config_data_uses_default_when_vault_config_missing(tmp_path: Path) -> None:
    data = read_config_data(tmp_path)

    assert data["system"]["name"] == "AI-Boss Super Brain"
    assert data["workers"]["codex"]["command"] == ["codex", "exec"]


def test_patch_config_data_allows_only_settings_whitelist() -> None:
    current = {
        "system": {"name": "AI-Boss", "default_project_path": None},
        "safety": {"require_git_repo": True, "max_fix_loops": 2},
        "workers": {"codex": {"command": ["codex", "exec"], "roles": ["coder"]}},
        "routing": {"code_changes": "codex"},
    }

    patched = patch_config_data(
        current,
        {
            "system": {"default_project_path": "~/project", "vault_path": "/tmp/secret-vault"},
            "safety": {"require_git_repo": False, "max_fix_loops": 4, "api_token": "secret"},
            "workers": {
                "codex": {
                    "command": ["codex", "exec", "--fast"],
                    "enabled": False,
                    "allow_subagents": False,
                    "subagent_policy": "never",
                    "roles": ["owner"],
                    "password": "secret",
                }
            },
            "routing": {"code_changes": "gemini"},
            "api_key": "secret",
        },
    )

    assert patched["system"] == {"name": "AI-Boss", "default_project_path": "~/project"}
    assert patched["safety"] == {"require_git_repo": False, "max_fix_loops": 4}
    assert patched["workers"]["codex"] == {
        "command": ["codex", "exec", "--fast"],
        "roles": ["coder"],
        "enabled": False,
        "allow_subagents": False,
        "subagent_policy": "never",
    }
    assert patched["routing"] == {"code_changes": "codex"}
    assert "api_key" not in patched


def test_write_config_update_validates_and_writes_filtered_yaml(tmp_path: Path) -> None:
    config_path = config_yaml_path(tmp_path)
    config = write_config_update(
        tmp_path,
        {
            "system.default_project_path": tmp_path / "project",
            "safety": {"allow_parallel_writes": True, "block_if_dirty_tree": False},
            "workers": {"codex": {"command": ("codex", "exec", "--sandbox"), "enabled": False, "token": "secret"}},
        },
    )

    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config.system.default_project_path == tmp_path / "project"
    assert config.safety.allow_parallel_writes is True
    assert config.workers["codex"].command == ["codex", "exec", "--sandbox"]
    assert saved["system"]["default_project_path"] == str(tmp_path / "project")
    assert saved["safety"]["block_if_dirty_tree"] is False
    assert saved["workers"]["codex"]["enabled"] is False
    assert "token" not in saved["workers"]["codex"]


def test_write_config_update_does_not_write_invalid_result(tmp_path: Path) -> None:
    config_path = config_yaml_path(tmp_path)
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
workers:
  codex:
    command: ["codex", "exec"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="Некорректная конфигурация"):
        write_config_update(tmp_path, {"workers": {"codex": {"command": "codex exec"}}})

    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved["workers"]["codex"]["command"] == ["codex", "exec"]
