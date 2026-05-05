from pathlib import Path

import yaml

from ai_boss.memory.obsidian_vault import DEFAULT_ROUTING, DEFAULT_WORKERS, VAULT_DIRS, ObsidianVault


def test_create_builds_vault_directories_and_system_files(tmp_path: Path) -> None:
    vault = ObsidianVault(tmp_path / "vault")

    created = vault.create()

    assert created == [vault.path / directory for directory in VAULT_DIRS]
    assert all((vault.path / directory).is_dir() for directory in VAULT_DIRS)
    assert vault.system_path("config.yaml").exists()
    assert yaml.safe_load(vault.system_path("workers.yaml").read_text(encoding="utf-8")) == DEFAULT_WORKERS
    assert yaml.safe_load(vault.system_path("routing-rules.yaml").read_text(encoding="utf-8")) == DEFAULT_ROUTING


def test_create_does_not_overwrite_existing_system_files(tmp_path: Path) -> None:
    vault = ObsidianVault(tmp_path / "vault")
    existing = vault.system_path("workers.yaml")
    existing.parent.mkdir(parents=True)
    existing.write_text("custom: true\n", encoding="utf-8")

    vault.create()

    assert existing.read_text(encoding="utf-8") == "custom: true\n"


def test_create_task_and_update_frontmatter(tmp_path: Path) -> None:
    vault = ObsidianVault(tmp_path / "vault")
    project_path = tmp_path / "project"

    task_path = vault.create_task("task-1", "Сделай важное", project_path)
    vault.update_task_frontmatter(task_path, status="planned", planner="gemini")

    text = task_path.read_text(encoding="utf-8")
    _, raw_frontmatter, body = text.split("---", 2)
    frontmatter = yaml.safe_load(raw_frontmatter)

    assert frontmatter["id"] == "task-1"
    assert frontmatter["status"] == "planned"
    assert frontmatter["project"] == "project"
    assert frontmatter["project_path"] == str(project_path)
    assert frontmatter["planner"] == "gemini"
    assert "# Задача\n\nСделай важное" in body


def test_writes_inbox_artifacts_and_errors(tmp_path: Path, monkeypatch) -> None:
    vault = ObsidianVault(tmp_path / "vault")
    monkeypatch.setattr(vault, "task_id", lambda: "20260505-120000-abcdef")

    inbox = vault.write_inbox("Что такое pytest?", "Фреймворк тестов", "gemini")
    plan = vault.write_plan("task-1", "План\n", "gemini")
    execution = vault.write_execution("task-1", "Готово", "codex")
    review = vault.write_review("task-1", "Ок", "claude")
    final_report = vault.write_final_report("task-1", "Финал")
    error = vault.write_error("Bad title!*", "Details", "codex")

    assert inbox.name == "20260505-120000-abcdef-ask.md"
    assert "worker: gemini" in inbox.read_text(encoding="utf-8")
    assert plan == vault.path / "02_Plans" / "task-1-plan.md"
    assert execution == vault.path / "03_Execution" / "task-1-execution.md"
    assert review == vault.path / "04_Reviews" / "task-1-review.md"
    assert final_report == vault.path / "05_Final-Reports" / "task-1-final-report.md"
    assert error.name == "20260505-120000-abcdef-bad-title--.md"
    assert "worker: codex" in error.read_text(encoding="utf-8")
