from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ai_boss.core.errors import ConfigError
from ai_boss.models.worker import WorkerSettings


DEFAULT_VAULT_PATH = Path("~/AI-Boss-Vault").expanduser()
SYSTEM_DIR = "99_System"
CONFIG_FILE = "config.yaml"


class SystemConfig(BaseModel):
    name: str = "AI-Boss Super Brain"
    language: str = "ru"
    vault_path: Path = DEFAULT_VAULT_PATH
    default_project_path: Path | None = None


class SafetyConfig(BaseModel):
    require_git_repo: bool = True
    block_if_dirty_tree: bool = True
    create_branch_per_task: bool = True
    allow_parallel_writes: bool = False
    max_fix_loops: int = 2


class VerificationConfig(BaseModel):
    default_commands: list[str] = Field(default_factory=lambda: ["git status --short", "git diff --stat"])


class AIBossConfig(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    workers: dict[str, WorkerSettings]
    routing: dict[str, str] = Field(default_factory=dict)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)


def _expand_paths(data: dict[str, Any]) -> dict[str, Any]:
    system = data.setdefault("system", {})
    for key in ("vault_path", "default_project_path"):
        value = system.get(key)
        if value:
            system[key] = Path(value).expanduser()
    return data


def default_config_path() -> Path:
    return Path(__file__).with_name("default_config.yaml")


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError as exc:
        raise ConfigError(f"Файл конфигурации не найден: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Не удалось прочитать YAML: {path}") from exc


def load_default_config() -> AIBossConfig:
    return AIBossConfig.model_validate(_expand_paths(load_yaml(default_config_path())))


def config_path_for_vault(vault_path: Path | None = None) -> Path:
    vault = (vault_path or DEFAULT_VAULT_PATH).expanduser()
    return vault / SYSTEM_DIR / CONFIG_FILE


def load_config(vault_path: Path | None = None) -> AIBossConfig:
    path = config_path_for_vault(vault_path)
    if not path.exists():
        return load_default_config()
    return AIBossConfig.model_validate(_expand_paths(load_yaml(path)))

