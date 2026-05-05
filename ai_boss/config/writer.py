from __future__ import annotations

import copy
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import ValidationError

from ai_boss.config.loader import AIBossConfig, config_path_for_vault, default_config_path, load_yaml
from ai_boss.core.errors import ConfigError


SYSTEM_FIELDS = {"default_project_path"}
SAFETY_FIELDS = {
    "require_git_repo",
    "block_if_dirty_tree",
    "create_branch_per_task",
    "allow_parallel_writes",
    "max_fix_loops",
}
WORKER_FIELDS = {"command", "enabled", "allow_subagents", "subagent_policy"}


def config_yaml_path(vault_path: Path | None = None) -> Path:
    return config_path_for_vault(vault_path)


def read_config_data(vault_path: Path | None = None) -> dict[str, Any]:
    path = config_yaml_path(vault_path)
    if path.exists():
        return load_yaml(path)
    return load_yaml(default_config_path())


def patch_config_data(current: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    patched = copy.deepcopy(dict(current))
    for path, value in _iter_payload_paths(payload):
        if len(path) == 2 and path[0] == "system" and path[1] in SYSTEM_FIELDS:
            _section(patched, "system")[path[1]] = _yaml_value(value)
        elif len(path) == 2 and path[0] == "safety" and path[1] in SAFETY_FIELDS:
            _section(patched, "safety")[path[1]] = _yaml_value(value)
        elif len(path) == 3 and path[0] == "workers" and path[2] in WORKER_FIELDS:
            workers = _section(patched, "workers")
            worker = workers.setdefault(path[1], {})
            if isinstance(worker, dict):
                worker[path[2]] = _yaml_value(value)
    return patched


def validate_config_data(data: Mapping[str, Any]) -> AIBossConfig:
    try:
        return AIBossConfig.model_validate(_expand_paths_for_validation(copy.deepcopy(dict(data))))
    except ValidationError as exc:
        raise ConfigError("Некорректная конфигурация config.yaml") from exc


def write_config_update(vault_path: Path | None, payload: Mapping[str, Any]) -> AIBossConfig:
    path = config_yaml_path(vault_path)
    current = read_config_data(vault_path)
    patched = patch_config_data(current, payload)
    config = validate_config_data(patched)
    _atomic_write_yaml(path, patched)
    return config


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    section = data.setdefault(name, {})
    if not isinstance(section, dict):
        section = {}
        data[name] = section
    return section


def _iter_payload_paths(payload: Mapping[str, Any]) -> list[tuple[tuple[str, ...], Any]]:
    paths: list[tuple[tuple[str, ...], Any]] = []
    for key, value in payload.items():
        key_path = tuple(str(key).split("."))
        if isinstance(value, Mapping):
            for child_path, child_value in _iter_payload_paths(value):
                paths.append((key_path + child_path, child_value))
        else:
            paths.append((key_path, value))
    return paths


def _yaml_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return [_yaml_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _yaml_value(item) for key, item in value.items()}
    return value


def _expand_paths_for_validation(data: dict[str, Any]) -> dict[str, Any]:
    system = data.setdefault("system", {})
    if isinstance(system, dict):
        for key in ("vault_path", "default_project_path"):
            value = system.get(key)
            if value:
                system[key] = Path(value).expanduser()
    return data


def _atomic_write_yaml(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.safe_dump(dict(data), allow_unicode=True, sort_keys=False)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        temp_path.replace(path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
