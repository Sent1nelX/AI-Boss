# Changelog

## Unreleased

- Добавлена persistent web-очередь в `99_System/web-jobs.json`.
- Добавлены cancel/retry для web-запусков и live logs из worker stdout/stderr.
- Добавлены Settings UI и settings API для безопасного изменения whitelist-полей `config.yaml`.
- Детализация задач в web UI теперь показывает task markdown и связанные Vault-артефакты: plan, execution, review, final report.
- Security hardening для local-only режима и безопасной работы с git-проектами.
- Packaging и release polish для более предсказуемой установки.

## 0.2.0

- Добавлен улучшенный local-only web dashboard.
- Добавлены проектные профили в `99_System/projects.yaml`.
- Добавлен `ai-boss preflight` и web endpoint `/api/preflight`.
- Добавлены CLI-команды `project-add`, `project-list`, `project-remove`.
- Web UI получил preflight-панель, project profiles, worker cards и более удобную рабочую область.
- Добавлены тесты для project store, preflight и новых web endpoints.

## 0.1.0

Первый публичный v2-срез AI-Boss Super Brain:

- интерактивный CLI shell `ai-boss`;
- local-only web UI `ai-boss web`;
- Obsidian Vault вместо базы данных;
- маршрутизация Gemini/Codex/Claude;
- Codex-only write-agent;
- GitGuard для git-проектов;
- bounded fix-loop после ревью;
- история задач и артефактов;
- pytest-покрытие без реальных вызовов AI CLI.
