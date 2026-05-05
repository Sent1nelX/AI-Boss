from pathlib import Path

import yaml


class ProjectStore:
    def __init__(self, vault_path: Path) -> None:
        self.path = vault_path.expanduser() / "99_System" / "projects.yaml"

    def list_projects(self) -> list[dict[str, str | bool]]:
        data = self._load()
        projects = data.get("projects", [])
        return projects if isinstance(projects, list) else []

    def add_project(self, name: str, path: Path, make_default: bool = False) -> None:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Название проекта не может быть пустым.")
        resolved_path = str(path.expanduser().resolve())
        projects = [project for project in self.list_projects() if project.get("name") != normalized_name]
        if make_default:
            for project in projects:
                project["default"] = False
        projects.append({"name": normalized_name, "path": resolved_path, "default": make_default})
        self._save({"projects": sorted(projects, key=lambda project: str(project.get("name", "")).lower())})

    def remove_project(self, name: str) -> bool:
        projects = self.list_projects()
        filtered = [project for project in projects if project.get("name") != name]
        self._save({"projects": filtered})
        return len(filtered) != len(projects)

    def default_project_path(self) -> Path | None:
        for project in self.list_projects():
            if project.get("default") and project.get("path"):
                return Path(str(project["path"])).expanduser()
        return None

    def find_path(self, name: str) -> Path | None:
        for project in self.list_projects():
            if project.get("name") == name and project.get("path"):
                return Path(str(project["path"])).expanduser()
        return None

    def _load(self) -> dict[str, object]:
        if not self.path.exists():
            return {"projects": []}
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {"projects": []}

    def _save(self, data: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

