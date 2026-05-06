# AI-Boss Super Brain

[![CI](https://github.com/Sent1nelX/AI-Boss/actions/workflows/ci.yml/badge.svg)](https://github.com/Sent1nelX/AI-Boss/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](pyproject.toml)

AI-Boss Super Brain is a local orchestrator for AI command-line tools. It gives one CLI and one local web dashboard for working with Gemini, Codex and Claude while keeping task history in a portable Obsidian-style Vault.

The project is designed for developers who want a practical local assistant, not a hosted SaaS service. AI-Boss runs on your machine, uses your existing AI CLIs, and treats your git working tree as something that must be protected.

## Features

- Interactive `ai-boss` shell for asking questions and sending tasks in plain language.
- Local dashboard with task queue, live logs, preflight checks, project profiles and settings.
- Automatic routing: Gemini for questions/plans/reports, Codex for code changes, Claude for review when available.
- Codex-only write path: Gemini and Claude are used for reading, planning and reviewing, not editing files.
- Persistent task history in `~/AI-Boss-Vault` as Markdown/YAML files.
- Git safety checks for repository presence, dirty trees, branches and review loops.
- Persistent web queue stored in the Vault with cancel/retry support.
- Works with CLIs installed through regular `PATH`, `nvm`, shell profile setup, or absolute paths.

## Requirements

- Python 3.12 or newer.
- [`uv`](https://docs.astral.sh/uv/) for the recommended install and development workflow.
- At least one configured AI CLI. For the full workflow install and authenticate:

```bash
gemini
codex
claude
```

AI-Boss does not store API keys. Authentication stays inside the external CLI tools.

## Installation

Clone the repository:

```bash
git clone git@github.com:Sent1nelX/AI-Boss.git
cd AI-Boss
```

Install as a local editable CLI tool:

```bash
uv tool install --editable .
```

If your shell cannot find `ai-boss`, add uv's tool directory to `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

For development instead of tool installation:

```bash
uv sync --extra dev
uv run ai-boss --help
```

## Quick Start

Create the local Vault:

```bash
ai-boss init
```

Open a project and start the interactive shell:

```bash
cd /path/to/your/git-project
ai-boss
```

Then type tasks naturally:

```text
ai-boss> Что такое git diff?
ai-boss> Проверь текущие изменения
ai-boss> Добавь retry для PaymentService.charge и покрой тестами
```

Start the local dashboard:

```bash
cd /path/to/your/git-project
ai-boss web
```

Open the printed URL. By default it is local-only:

```text
http://127.0.0.1:8000
```

For one-off commands without entering the shell:

```bash
ai-boss do "Проверь текущие изменения"
ai-boss ask "Объясни git rebase простыми словами"
ai-boss run "Добавь страницу настроек пользователя"
```

## How It Works

AI-Boss uses a conservative routing model:

| Task type | Default tool |
| --- | --- |
| Simple questions | Gemini |
| Planning and reports | Gemini |
| Code changes, bugfixes, refactors, tests | Codex |
| Diff review and architecture critique | Claude, with Gemini fallback |

A full `run` task follows this flow:

1. Resolve the project path.
2. Check git safety rules.
3. Create a task record in the Vault.
4. Ask Gemini for a plan.
5. Create a task branch if configured.
6. Ask Codex to implement the change.
7. Save Codex output and current diff.
8. Ask Claude or Gemini to review the diff.
9. Run a bounded fix loop if review findings require it.
10. Save the final report.

AI-Boss never performs automatic commit, push, merge or deploy.

## CLI Reference

```bash
ai-boss --help
```

Common commands:

| Command | Purpose |
| --- | --- |
| `ai-boss` | Start the interactive shell. |
| `ai-boss web` | Start the local dashboard. |
| `ai-boss init` | Create the Vault and default config files. |
| `ai-boss status` | Show local Vault, git and worker status without calling AI CLIs. |
| `ai-boss preflight` | Check readiness before `run` or `review`. |
| `ai-boss do "..."` | Auto-route a request. |
| `ai-boss ask "..."` | Ask Gemini and save the answer. |
| `ai-boss plan "..."` | Create a task and plan. |
| `ai-boss review` | Review the current git diff. |
| `ai-boss run "..."` | Plan, implement, review and report. |
| `ai-boss tasks` | Show recent Vault tasks. |
| `ai-boss show TASK_ID` | Show a task markdown file. |

Inside the interactive shell:

```text
/help
/status
/preflight
/tasks
/history
/show TASK_ID
/project
/project /path/to/project
/clear-project
/exit
```

If you start AI-Boss inside a git repository, that directory is used as the current project. Pass `--project-path` or use `/project` only when the target project is somewhere else.

## Web Dashboard

The dashboard is a local control panel over the same core used by the CLI. It includes:

- command composer for `auto`, `ask`, `plan`, `review` and `run`;
- persistent queue with live logs, cancel and retry;
- preflight and ready checks;
- worker status cards with resolved executable paths;
- project profiles;
- safe settings editor for selected `config.yaml` fields;
- task details with plan, execution log, review and final report artifacts.

The dashboard is intended for localhost use. Do not expose it through a public bind, reverse proxy or tunnel without adding separate authentication and network controls.

## Vault Layout

By default AI-Boss stores its state in `~/AI-Boss-Vault`:

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
    config.yaml
    projects.yaml
    routing-rules.yaml
    web-jobs.json
    workers.yaml
```

The Vault is intentionally plain Markdown/YAML. You can inspect it in a text editor, sync it, back it up, or open it in Obsidian.

## Configuration

Main config file:

```text
~/AI-Boss-Vault/99_System/config.yaml
```

Important fields:

```yaml
system:
  vault_path: ~/AI-Boss-Vault
  default_project_path: null

safety:
  require_git_repo: true
  block_if_dirty_tree: true
  create_branch_per_task: true
  allow_parallel_writes: false
  max_fix_loops: 2

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

Project profiles:

```bash
ai-boss project-add my-app ~/Projects/my-app --default
ai-boss project-list
ai-boss project-remove my-app
```

Profiles are stored in `~/AI-Boss-Vault/99_System/projects.yaml` and are available in both CLI and web UI.

## Safety Model

AI-Boss assumes your working tree may contain valuable human work. The project therefore follows these rules:

- Codex is the only worker allowed to edit project files.
- Gemini and Claude are used for questions, plans, reviews and reports.
- Dirty working trees can block write tasks when configured.
- Task branches can be created automatically.
- Review fix loops are bounded by `max_fix_loops`.
- No auto-commit, auto-push, auto-merge or auto-deploy.
- Secrets should not be stored in prompts, config files, logs, tests or reports.

Codex subagents are controlled by the Codex worker configuration. AI-Boss does not start independent external write agents in parallel.

## Troubleshooting

Check local status without spending AI tokens:

```bash
ai-boss status
ai-boss preflight
```

If a CLI is installed through `nvm` or shell profile setup, AI-Boss tries to resolve it through an interactive shell and then adjusts the subprocess `PATH` so shebangs such as `#!/usr/bin/env node` can find their runtime.

If the web UI shows an old worker status, run a small command to refresh the worker state:

```bash
ai-boss ask "Ответь одним словом: ok"
```

If a write task is blocked because the tree is dirty, commit, stash or remove unrelated changes first, or adjust `safety.block_if_dirty_tree` deliberately.

## Development

```bash
git clone git@github.com:Sent1nelX/AI-Boss.git
cd AI-Boss
uv sync --extra dev
uv run pytest
uv run ai-boss --help
```

Useful checks:

```bash
uv run pytest
uv build
```

Project documents:

- [Changelog](CHANGELOG.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

## License

MIT. See [LICENSE](LICENSE).
