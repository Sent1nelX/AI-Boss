# Contributing to AI-Boss Super Brain

Спасибо за интерес к проекту. AI-Boss — локальный orchestrator для AI CLI-инструментов, поэтому главный приоритет проекта: безопасность git-проектов пользователя.

## Как начать

```bash
git clone git@github.com:Sent1nelX/AI-Boss.git
cd AI-Boss
uv sync --extra dev
uv run pytest
```

Запуск CLI из рабочей копии:

```bash
uv run ai-boss --help
uv run ai-boss
uv run ai-boss web --no-open-browser
```

## Правила разработки

- Не добавляйте автокоммит, autopush, autodeploy или автоматический merge.
- Codex остаётся единственным write-agent.
- Gemini и Claude не должны менять файлы проекта.
- Web UI должен использовать тот же `Orchestrator`, `GitGuard` и Obsidian Vault, что CLI.
- Тесты не должны реально вызывать `gemini`, `codex` или `claude`.
- Любая новая write-операция должна проходить через git-safety проверки.
- Не храните секреты в конфиге, fixtures, docs или тестах.

## Pull request checklist

- [ ] Добавлены или обновлены тесты.
- [ ] `uv run pytest` проходит локально.
- [ ] README/документация обновлены, если изменился пользовательский сценарий.
- [ ] Нет auto-commit/push/deploy поведения.
- [ ] Нет новых внешних сервисов без обсуждения.

