from pathlib import Path

from ai_boss.config.loader import AIBossConfig
from ai_boss.core.cli_resolver import resolve_cli_executable
from ai_boss.core.git_guard import GitGuard
from ai_boss.memory.project_store import ProjectStore
from ai_boss.memory.state_store import WorkerStateStore


def build_preflight(config: AIBossConfig, project_path: Path | None = None) -> dict[str, object]:
    project = _resolve_project_for_preflight(config, project_path)
    checks: list[dict[str, object]] = []
    checks.append({"name": "vault_exists", "ok": config.system.vault_path.expanduser().exists(), "detail": str(config.system.vault_path)})

    for worker_name, settings in config.workers.items():
        cli_path = resolve_cli_executable(settings.command[0])
        checks.append(
            {
                "name": f"cli_{worker_name}",
                "ok": cli_path is not None,
                "detail": f"{' '.join(settings.command)} -> {cli_path}" if cli_path else " ".join(settings.command),
            }
        )

    states = WorkerStateStore(config.system.vault_path).load()
    for worker_name, state in states.items():
        checks.append(
            {
                "name": f"worker_{worker_name}",
                "ok": state.status.value not in {"disabled", "failed", "limited", "cooldown"},
                "detail": state.status.value,
            }
        )

    if project is None:
        checks.append({"name": "project_selected", "ok": False, "detail": "Проект не выбран."})
        return {"ok": False, "project_path": None, "checks": checks}

    guard = GitGuard(project)
    project_exists = project.exists()
    is_git_repo = guard.is_git_repo() if project_exists else False
    checks.append({"name": "project_exists", "ok": project_exists, "detail": str(project)})
    checks.append({"name": "git_repo", "ok": is_git_repo, "detail": str(project)})
    status_short = guard.status_short() if is_git_repo else ""
    dirty = bool(status_short.strip())
    checks.append(
        {
            "name": "dirty_tree",
            "ok": not dirty or not config.safety.block_if_dirty_tree,
            "detail": status_short or "clean",
        }
    )
    checks.append({"name": "parallel_writes", "ok": not config.safety.allow_parallel_writes, "detail": "disabled"})
    return {"ok": all(bool(check["ok"]) for check in checks), "project_path": str(project), "checks": checks}


def _resolve_project_for_preflight(config: AIBossConfig, project_path: Path | None) -> Path | None:
    if project_path is not None:
        return project_path.expanduser().resolve()
    current_dir = Path.cwd().resolve()
    if GitGuard(current_dir).is_git_repo():
        return current_dir
    default_profile = ProjectStore(config.system.vault_path).default_project_path()
    if default_profile is not None:
        return default_profile.expanduser().resolve()
    if config.system.default_project_path is not None:
        return config.system.default_project_path.expanduser().resolve()
    return None
