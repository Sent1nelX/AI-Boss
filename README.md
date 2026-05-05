# AI-Boss Super Brain

[![CI](https://github.com/Sent1nelX/AI-Boss/actions/workflows/ci.yml/badge.svg)](https://github.com/Sent1nelX/AI-Boss/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](pyproject.toml)

AI-Boss Super Brain — локальный Python-оркестратор для работы с несколькими AI CLI-инструментами из одного места. В v2 им можно пользоваться через интерактивный CLI или локальный web-интерфейс.

Репозиторий: <https://github.com/Sent1nelX/AI-Boss>

После установки он работает как обычный интерактивный shell: заходите в папку проекта, запускаете `ai-boss` и дальше пишете задачи внутри сессии.

```bash
cd /path/to/project
ai-boss
```

Или запускаете локальный web UI:

```bash
cd /path/to/project
ai-boss web
```

Откройте адрес, который напечатает команда. По умолчанию web-интерфейс доступен только локально: `http://127.0.0.1:8000`.

Внутри:

```text
ai-boss> Что такое git diff?
ai-boss> Добавь README-раздел про локальный запуск
ai-boss> Проверь текущие изменения
```

## Зачем это нужно

У разных AI-инструментов разные сильные стороны и разная цена ошибки. AI-Boss делает не round-robin, а простую диспетчеризацию:

- Gemini используется для простых вопросов, планирования, fallback-ревью и отчётов.
- Codex используется только для задач, где реально нужно менять код.
- Claude используется для глубокого ревью и архитектурной критики, если он доступен.

Codex намеренно не используется для простых вопросов: он может тратить дорогие лимиты на мелочи и работает как write-agent. В v2 только Codex может менять файлы проекта. Gemini и Claude читают, планируют, ревьюят и помогают формировать отчёты.

Субагенты разрешены только внутри Codex и только по политике `subagent_policy: auto`. AI-Boss не запускает внешних write-agent параллельно с Codex. Если Codex CLI умеет делегировать работу, он может использовать субагентов для независимого исследования, проверки или изолированных частей задачи, но ответственность за запись в проект остаётся у Codex.

## Безопасность v2

AI-Boss исходит из того, что проект может содержать рабочие изменения пользователя или другого агента. Поэтому базовые правила такие:

- не откатывать и не переписывать чужие изменения без прямого запроса;
- не менять unrelated-файлы;
- не хранить секреты в конфиге, промптах, отчётах или истории задач;
- не делать auto-commit, auto-push, deploy или merge;
- останавливать опасные операции, если включены проверки `safety`;
- держать единственным write-agent именно Codex;
- разрешать субагентов только внутри Codex policy `auto`.

Проверки из `config.yaml` помогают удерживать границы: требовать git-репозиторий, блокировать запуск при dirty tree, создавать ветку на задачу и запрещать параллельные записи.

Web UI в v2 не является отдельным серверным продуктом с собственной логикой выполнения. Это local-only интерфейс поверх тех же компонентов:

- `Orchestrator` выбирает маршрут и запускает ask/plan/review/run;
- `GitGuard` проверяет git-репозиторий, dirty tree, diff и рабочие ветки;
- Obsidian Vault хранит задачи, планы, execution logs, ревью и финальные отчёты.
- web-очередь держит активные запуски в памяти процесса, чтобы длинные операции не блокировали интерфейс.

В v2 у web-интерфейса пока нет auth, пользователей, ролей, CSRF-защиты для публичного размещения и multi-tenant режима. Запускайте его только на localhost, не публикуйте через reverse proxy, tunnel или bind на внешний интерфейс. Если нужен доступ с другого устройства, считайте это отдельной задачей безопасности.

## Почему Obsidian вместо базы данных

В v2 по-прежнему нет SQLite, Redis и внешних API. Память хранится в Obsidian Vault как Markdown/YAML:

```text
~/AI-Boss-Vault/
  00_Inbox/
  01_Tasks/
  02_Plans/
  03_Execution/
  04_Reviews/
  05_Final-Reports/
  06_Project-Knowledge/
  07_Decisions/
  08_Errors/
  99_System/
```

Это удобно читать глазами, версионировать и переносить без миграций.

## История задач

Каждая существенная операция сохраняется в Vault как цепочка Markdown-файлов:

- `01_Tasks` — исходная задача пользователя и метаданные;
- `02_Plans` — план Planner Agent;
- `03_Execution` — вывод Codex;
- `04_Reviews` — ревью Claude или Gemini fallback;
- `05_Final-Reports` — итоговый отчёт Reporter Agent;
- `08_Errors` — ошибки запуска, лимиты и fallback-сценарии.

Эта история нужна не для автопамяти, которая сама меняет проект, а для прозрачности: можно открыть задачу, увидеть план, diff, ревью, исправления и финальный статус. AI-Boss не использует историю как основание для скрытых записей в проект.

## Установка

Требуется Python 3.12+.

### Из GitHub

```bash
git clone git@github.com:Sent1nelX/AI-Boss.git
cd AI-Boss
uv sync --extra dev
uv run ai-boss --help
```

Самый удобный локальный вариант через `uv`:

```bash
cd /home/srv-home-ubuntu-2/ai-boss
uv tool install --editable .
```

После этого команда доступна как обычный CLI:

```bash
ai-boss --help
ai-boss init
ai-boss
ai-boss web
```

Если shell не видит `ai-boss`, добавьте каталог инструментов uv в `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Вариант для разработки внутри виртуального окружения:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

AI-Boss не хранит ключи. Установите и настройте CLI-инструменты отдельно:

```bash
gemini
codex
claude
```

Команда `ai-boss status` проверяет их наличие через `shutil.which` и не отправляет реальные запросы.

## Инициализация Vault

```bash
ai-boss init
```

По умолчанию будет создан `~/AI-Boss-Vault`. В системной папке появятся:

- `99_System/config.yaml`
- `99_System/workers.yaml`
- `99_System/routing-rules.yaml`

Можно указать другой путь:

```bash
ai-boss init --vault-path ~/My-AI-Boss-Vault
```

## Настройка config.yaml

Главный файл:

```text
~/AI-Boss-Vault/99_System/config.yaml
```

Важные параметры:

```yaml
system:
  vault_path: ~/AI-Boss-Vault
  default_project_path: null

safety:
  require_git_repo: true
  block_if_dirty_tree: true
  create_branch_per_task: true
  allow_parallel_writes: false

workers:
  gemini:
    command: ["gemini", "-p"]
  codex:
    command: ["codex", "exec"]
    allow_subagents: true
    subagent_policy: auto
  claude:
    command: ["claude", "-p"]
```

## Команды

### Интерактивный shell

Главный режим работы:

```bash
cd /path/to/project
ai-boss
```

AI-Boss откроет интерактивный shell:

```text
ai-boss>
```

Пишите обычным текстом. Shell сохраняет контекст выбранного проекта, позволяет менять проект служебными командами и отправляет каждую задачу в нужный маршрут:

```text
Что такое git diff?
Хочу систему импорта студентов из DOCX
Проверь текущие изменения
Добавь страницу настроек пользователя
```

Если сессия запущена внутри git-проекта, AI-Boss считает текущую папку проектом. Путь указывать не нужно.

Служебные команды внутри чата:

```text
/help
/status
/tasks
/history
/show TASK_ID
/project
/project /path/to/project
/clear-project
/exit
```

Если данные или проект лежат в другом месте, выберите проект внутри сессии:

```text
ai-boss> /project ~/Desktop/some-project
ai-boss> Проверь текущие изменения
```

Интерактивный shell удобен для серии связанных действий: сначала задать вопрос, затем попросить план, затем запустить изменение или ревью текущего diff. История выполнения всё равно пишется в Vault, поэтому после выхода из shell задача не теряется.

Историю можно смотреть прямо из shell:

```text
ai-boss> /tasks
ai-boss> /show 20260505-120000
```

Или одной командой:

```bash
ai-boss tasks
ai-boss show 20260505-120000
```

### Локальный web-интерфейс

Web UI запускается отдельной командой:

```bash
cd /path/to/project
ai-boss web
```

Откройте локальный адрес из вывода команды. Ожидаемый адрес по умолчанию:

```text
http://127.0.0.1:8000
```

Web-интерфейс предназначен для работы на той же машине, где лежит проект и настроены `gemini`, `codex`, `claude` CLI. Он не требует отдельной базы данных и не создаёт отдельную память: все действия пишутся в тот же Obsidian Vault, что и CLI.

Доступные действия в web UI:

- задать простой вопрос через маршрут `ask`;
- создать план через `plan`;
- запустить изменение через полный pipeline `run`: Planner → Codex → Reviewer → bounded fix-loop → Reporter;
- проверить текущий `git diff` через `review`;
- посмотреть статус Vault, проекта, CLI-инструментов и worker state;
- выполнить preflight перед `run` или `review`;
- отправить длинную операцию в web-очередь и следить за live log;
- добавлять и выбирать проектные профили;
- выбрать или увидеть текущий project path;
- открыть список последних задач;
- посмотреть карточку задачи и связанные Markdown-артефакты из Vault.

Правила безопасности такие же, как в CLI: Codex остаётся единственным write-agent, GitGuard применяет настройки из `config.yaml`, AI-Boss не делает auto-commit, auto-push, deploy или merge. Web UI только вызывает те же операции Orchestrator и показывает их результат.

Важно: в v2 web UI пока без авторизации и рассчитан только на `127.0.0.1`. Не запускайте его как публичный сервис.

### Самый простой режим

Для разового запуска без входа в чат используйте:

```bash
ai-boss do "ваш запрос"
```

AI-Boss сам классифицирует задачу:

- вопрос → Gemini;
- планирование, архитектура, документация, деплой-помощь → Gemini;
- ревью diff → Claude или Gemini fallback;
- изменение кода, багфикс, рефакторинг, тесты → Gemini планирует, Codex меняет код, Claude/Gemini ревьюит.

Примеры:

```bash
ai-boss do "Что такое git diff?"
ai-boss do "Хочу систему импорта студентов из DOCX"
cd /path/to/project
ai-boss do "Проверь текущие изменения"
ai-boss do "Добавь страницу настроек пользователя"
```

Если вы находитесь внутри git-проекта, AI-Boss работает с текущей папкой. `--project-path` нужен только когда проект лежит в другом месте:

```bash
ai-boss do "Проверь текущие изменения" --project-path ~/Desktop/some-project
```

### ai-boss init

Создаёт Obsidian Vault, папки и системные YAML-файлы. Существующие файлы не перетираются.

### ai-boss status

Показывает путь к Vault, состояние проекта из конфига, наличие CLI-команд и статусы агентов из `workers.yaml`. Реальные AI-запросы не выполняются.

### ai-boss preflight

```bash
ai-boss preflight
ai-boss preflight --project-path /path/to/project
```

Проверяет готовность перед `run` или `review`: Vault, наличие CLI, worker state, git-репозиторий, dirty tree и запрет параллельных записей.

### Проектные профили

```bash
ai-boss project-add my-app ~/Projects/my-app --default
ai-boss project-list
ai-boss project-remove my-app
```

Профили сохраняются в:

```text
~/AI-Boss-Vault/99_System/projects.yaml
```

Они нужны, чтобы быстро выбирать рабочий проект в CLI/web UI и не вводить длинные пути руками.

### ai-boss web

```bash
ai-boss web
```

Запускает local-only web UI для текущей машины. Откройте `http://127.0.0.1:8000` или адрес, который напечатала команда. Интерфейс использует тот же `Orchestrator`, `GitGuard`, Obsidian Vault и worker-настройки, что CLI-команды.

В v2 web UI пока без auth и не предназначен для публикации в сеть.

### ai-boss ask

```bash
ai-boss ask "Объясни, что такое git diff"
```

Всегда использует Gemini, сохраняет вопрос и ответ в `00_Inbox`.

### ai-boss plan

```bash
ai-boss plan "Распланируй импорт студентов из DOCX"
```

Создаёт задачу в `01_Tasks`, отправляет planner prompt в Gemini и сохраняет план в `02_Plans`.

### ai-boss review

```bash
ai-boss review --project-path /path/to/project
```

Проверяет текущий `git diff`. Если Claude доступен, ревью делает Claude. Если Claude в лимите или упал, используется Gemini.

### ai-boss run

```bash
ai-boss run "Добавь страницу настроек пользователя" --project-path /path/to/project
```

Пайплайн v2:

1. Проверить путь и git-репозиторий.
2. Остановиться при dirty tree, если это запрещено в конфиге.
3. Создать задачу в Obsidian.
4. Получить план от Gemini.
5. Создать ветку `ai-boss/<task_id>`, если включено.
6. Передать задачу Codex как единственному write-agent.
7. Сохранить вывод Codex в `03_Execution`.
8. Получить `git diff`.
9. Отправить diff на ревью Claude или Gemini fallback.
10. Если ревью не approved, запустить ограниченный fix-loop.
11. Сформировать финальный отчёт через Gemini Reporter.
12. Если Reporter недоступен, сохранить локальный финальный отчёт.

### Bounded fix-loop после ревью

В v2 AI-Boss может выполнить ограниченный цикл исправлений после ревью:

1. Reviewer возвращает `approved: false` и список конкретных проблем.
2. AI-Boss передаёт Codex только эти замечания и исходную задачу.
3. Codex исправляет замечания в рамках уже затронутой области.
4. AI-Boss снова получает diff и отправляет его на ревью.
5. Цикл останавливается после approval, достижения лимита попыток или появления блокера.

Fix-loop не является бесконечной автодоработкой. Он не должен расширять задачу, менять unrelated-файлы, выполнять destructive-команды или превращать reviewer в write-agent. Если замечания требуют продуктового решения, миграции с риском потери данных или доступа к секретам, AI-Boss сохраняет это как остаточный риск в финальном отчёте.

AI-Boss не делает auto-commit, auto-push, deploy или merge.

## Ограничения v2

Во второй версии web-интерфейс есть только как локальный UI поверх ядра AI-Boss. В нём пока нет auth, пользовательских ролей, публичного server mode, фонового daemon-режима и persistent-очереди между перезапусками. Также нет Telegram-бота, SQLite, Redis, Docker, GitHub API и сложного RAG. Цель v2 — крепкое локальное ядро с прозрачной историей задач, интерактивным shell, local-only web UI, безопасным Codex-only write path, in-memory web-очередью и ограниченным fix-loop после ревью.

## Contributing

Проект открыт для issues и pull requests. Перед PR проверьте:

```bash
uv run pytest
```

Главные правила разработки описаны в [CONTRIBUTING.md](CONTRIBUTING.md):

- не добавлять auto-commit, auto-push, deploy или merge;
- не вызывать реальные AI CLI в тестах;
- держать Codex единственным write-agent;
- не хранить секреты и персональные данные в репозитории.

## Security

Если нашли уязвимость, не публикуйте exploit в issue. Используйте GitHub Security Advisory или следуйте инструкции в [SECURITY.md](SECURITY.md).

## License

MIT. См. [LICENSE](LICENSE).
