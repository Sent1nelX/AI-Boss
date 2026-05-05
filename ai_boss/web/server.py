from __future__ import annotations

import json
import shutil
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from ai_boss.config.loader import AIBossConfig, load_config
from ai_boss.core.errors import AIBossError
from ai_boss.core.git_guard import GitGuard
from ai_boss.core.orchestrator import Orchestrator
from ai_boss.core.preflight import build_preflight
from ai_boss.core.task_classifier import TaskClassifier
from ai_boss.memory.obsidian_vault import ObsidianVault
from ai_boss.memory.project_store import ProjectStore
from ai_boss.memory.state_store import WorkerStateStore
from ai_boss.models.task import TaskType
from ai_boss.web.ui import INDEX_HTML as DASHBOARD_HTML


DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8000


def serve_web(host: str = DEFAULT_WEB_HOST, port: int = DEFAULT_WEB_PORT, open_browser: bool = True) -> None:
    try:
        server = create_server(host, port)
    except OSError:
        if port != DEFAULT_WEB_PORT:
            raise
        server = create_server(host, 0)
    url = f"http://{host}:{server.server_port}"
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    print(f"AI-Boss Web запущен: {url}")
    print("Остановить: Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAI-Boss Web остановлен.")
    finally:
        server.server_close()


def create_server(host: str = DEFAULT_WEB_HOST, port: int = DEFAULT_WEB_PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), AIBossRequestHandler)


class AIBossRequestHandler(BaseHTTPRequestHandler):
    server_version = "AIBossWeb/0.2"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(DASHBOARD_HTML)
            return
        if parsed.path == "/api/status":
            self._send_json(api_status())
            return
        if parsed.path == "/api/tasks":
            limit = _int_query_param(parsed.query, "limit", 20)
            self._send_json(api_tasks(limit=limit))
            return
        if parsed.path == "/api/projects":
            self._send_json(api_projects())
            return
        if parsed.path == "/api/preflight":
            self._send_json(api_preflight({}))
            return
        if parsed.path.startswith("/api/task/"):
            task_id = unquote(parsed.path.removeprefix("/api/task/"))
            self._send_json(api_task(task_id))
            return
        self._send_json({"ok": False, "error": "Маршрут не найден."}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self._read_json()
        try:
            if parsed.path == "/api/ask":
                self._send_json(api_ask(payload))
                return
            if parsed.path == "/api/plan":
                self._send_json(api_plan(payload))
                return
            if parsed.path == "/api/review":
                self._send_json(api_review(payload))
                return
            if parsed.path == "/api/run":
                self._send_json(api_run(payload))
                return
            if parsed.path == "/api/do":
                self._send_json(api_do(payload))
                return
            if parsed.path == "/api/projects":
                self._send_json(api_project_add(payload))
                return
            if parsed.path == "/api/preflight":
                self._send_json(api_preflight(payload))
                return
            self._send_json({"ok": False, "error": "Маршрут не найден."}, HTTPStatus.NOT_FOUND)
        except AIBossError as exc:
            self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw_body = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def api_status(config: AIBossConfig | None = None) -> dict[str, Any]:
    config = config or load_config()
    vault = ObsidianVault(config.system.vault_path)
    current_dir = Path.cwd().resolve()
    current_guard = GitGuard(current_dir)
    workers = {}
    states = WorkerStateStore(vault.path).load()
    for name, settings in config.workers.items():
        state = states.get(name)
        workers[name] = {
            "command": settings.command,
            "cli_found": shutil.which(settings.command[0]) is not None,
            "status": state.status.value if state else "unknown",
            "enabled": settings.enabled,
            "allow_subagents": settings.allow_subagents,
            "subagent_policy": settings.subagent_policy,
        }
    return {
        "ok": True,
        "vault": {"path": str(vault.path), "exists": vault.exists()},
        "project": {
            "current_path": str(current_dir),
            "current_is_git_repo": current_guard.is_git_repo(),
            "current_git_status": _git_status(current_guard),
            "default_project_path": str(config.system.default_project_path) if config.system.default_project_path else None,
        },
        "safety": config.safety.model_dump(mode="json"),
        "workers": workers,
    }


def api_tasks(limit: int = 20, config: AIBossConfig | None = None) -> dict[str, Any]:
    config = config or load_config()
    tasks = ObsidianVault(config.system.vault_path).list_tasks(limit=limit)
    return {"ok": True, "tasks": [_json_safe_task(task) for task in tasks]}


def api_projects(config: AIBossConfig | None = None) -> dict[str, Any]:
    config = config or load_config()
    return {"ok": True, "projects": ProjectStore(config.system.vault_path).list_projects()}


def api_project_add(payload: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    name = _required_field(payload, "name")
    path = _required_field(payload, "path")
    ProjectStore(config.system.vault_path).add_project(name, Path(path), make_default=bool(payload.get("default")))
    return api_projects(config)


def api_preflight(payload: dict[str, Any], config: AIBossConfig | None = None) -> dict[str, Any]:
    config = config or load_config()
    return build_preflight(config, _payload_project_path(payload))


def api_task(task_id: str, config: AIBossConfig | None = None) -> dict[str, Any]:
    config = config or load_config()
    vault = ObsidianVault(config.system.vault_path)
    task_path = vault.find_task(task_id)
    if not task_path:
        return {"ok": False, "error": "Задача не найдена."}
    return {"ok": True, "path": str(task_path), "markdown": task_path.read_text(encoding="utf-8")}


def api_ask(payload: dict[str, Any]) -> dict[str, Any]:
    text = _required_text(payload)
    result = Orchestrator(load_config()).ask(text)
    return {"ok": True, "mode": "ask", "result": _result_to_json(result)}


def api_plan(payload: dict[str, Any]) -> dict[str, Any]:
    text = _required_text(payload)
    project_path = _payload_project_path(payload)
    result = Orchestrator(load_config()).plan(text, project_path)
    return {"ok": True, "mode": "plan", "result": _result_to_json(result)}


def api_review(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text") or "Ревью текущих изменений")
    project_path = _payload_project_path(payload)
    result = Orchestrator(load_config()).review(user_task=text, project_path=project_path)
    return {"ok": True, "mode": "review", "result": _result_to_json(result)}


def api_run(payload: dict[str, Any]) -> dict[str, Any]:
    text = _required_text(payload)
    project_path = _payload_project_path(payload)
    result = Orchestrator(load_config()).run(text, project_path)
    return {"ok": True, "mode": "run", "result": _result_to_json(result)}


def api_do(payload: dict[str, Any]) -> dict[str, Any]:
    text = _required_text(payload)
    project_path = _payload_project_path(payload)
    task_type = TaskClassifier().classify(text)
    if task_type == TaskType.SIMPLE_QUESTION:
        response = api_ask(payload)
        response["classified_as"] = task_type.value
        return response
    if task_type == TaskType.REVIEW:
        response = api_review({"text": text, "project_path": str(project_path) if project_path else None})
        response["classified_as"] = task_type.value
        return response
    if task_type in {TaskType.CODE_CHANGE, TaskType.BUGFIX, TaskType.REFACTOR, TaskType.TEST_GENERATION}:
        response = api_run(payload)
        response["classified_as"] = task_type.value
        return response
    response = api_plan(payload)
    response["classified_as"] = task_type.value
    return response


def _payload_project_path(payload: dict[str, Any]) -> Path | None:
    value = payload.get("project_path")
    if not value:
        return None
    return Path(str(value)).expanduser().resolve()


def _required_text(payload: dict[str, Any]) -> str:
    text = str(payload.get("text") or "").strip()
    if not text:
        raise AIBossError("Пустой запрос.")
    return text


def _required_field(payload: dict[str, Any], field_name: str) -> str:
    value = str(payload.get(field_name) or "").strip()
    if not value:
        raise AIBossError(f"Не заполнено обязательное поле: {field_name}.")
    return value


def _result_to_json(result: Any) -> dict[str, Any]:
    data = result.model_dump(mode="python")
    data["files"] = {key: str(path) for key, path in result.files.items()}
    return data


def _json_safe_task(task: dict[str, Any]) -> dict[str, Any]:
    return {key: str(value) if isinstance(value, Path) else value for key, value in task.items()}


def _git_status(guard: GitGuard) -> str | None:
    if not guard.is_git_repo():
        return None
    return guard.status_short()


def _int_query_param(query: str, name: str, default: int) -> int:
    values = parse_qs(query).get(name)
    if not values:
        return default
    try:
        return int(values[0])
    except ValueError:
        return default


INDEX_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI-Boss Super Brain</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #16181d;
      --muted: #626b7a;
      --line: #d9dee7;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --danger: #b42318;
      --code: #111827;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    button, input, textarea, select { font: inherit; }
    .layout {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      min-height: 100vh;
    }
    aside {
      border-right: 1px solid var(--line);
      background: #eef2f6;
      padding: 18px;
      overflow: auto;
    }
    main {
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-height: 100vh;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      padding: 16px 22px;
    }
    h1, h2, h3 { margin: 0; }
    h1 { font-size: 20px; }
    h2 { font-size: 15px; margin-bottom: 10px; }
    .muted { color: var(--muted); }
    .section { margin-bottom: 18px; }
    .status-grid {
      display: grid;
      gap: 8px;
    }
    .kv {
      display: grid;
      gap: 2px;
      padding: 9px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      overflow-wrap: anywhere;
    }
    .kv strong { font-size: 12px; color: var(--muted); }
    .task-list {
      display: grid;
      gap: 8px;
    }
    .task {
      width: 100%;
      text-align: left;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 10px;
      cursor: pointer;
    }
    .task:hover { border-color: var(--accent); }
    .messages {
      padding: 20px 22px;
      overflow: auto;
      display: grid;
      align-content: start;
      gap: 12px;
    }
    .msg {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 13px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .msg.user { border-color: #9bb8d3; }
    .msg.error { border-color: #f3b6ae; color: var(--danger); }
    .msg.result { border-color: #9ed3ca; }
    form {
      border-top: 1px solid var(--line);
      background: var(--panel);
      padding: 14px 22px;
      display: grid;
      grid-template-columns: 150px minmax(0, 1fr) 190px 112px;
      gap: 10px;
      align-items: end;
    }
    label { display: grid; gap: 6px; font-size: 12px; color: var(--muted); }
    select, input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      padding: 10px;
    }
    textarea {
      min-height: 48px;
      max-height: 170px;
      resize: vertical;
    }
    button.primary {
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: white;
      padding: 11px 14px;
      cursor: pointer;
      font-weight: 650;
    }
    button.primary:hover { background: var(--accent-dark); }
    button.primary:disabled { opacity: .55; cursor: wait; }
    pre {
      margin: 0;
      padding: 12px;
      border-radius: 8px;
      background: var(--code);
      color: #e5e7eb;
      overflow: auto;
      white-space: pre-wrap;
    }
    .toolbar {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    .small-btn {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      padding: 8px 10px;
      cursor: pointer;
    }
    @media (max-width: 860px) {
      .layout { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); max-height: 45vh; }
      form { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="layout">
    <aside>
      <section class="section">
        <h2>Состояние</h2>
        <div id="status" class="status-grid"></div>
        <div class="toolbar">
          <button class="small-btn" id="refreshStatus" type="button">Обновить</button>
          <button class="small-btn" id="refreshTasks" type="button">Задачи</button>
        </div>
      </section>
      <section class="section">
        <h2>История задач</h2>
        <div id="tasks" class="task-list"></div>
      </section>
    </aside>
    <main>
      <header>
        <h1>AI-Boss Super Brain</h1>
        <div class="muted">Локальный web UI поверх того же Orchestrator, GitGuard и Obsidian Vault.</div>
      </header>
      <section id="messages" class="messages"></section>
      <form id="requestForm">
        <label>Режим
          <select id="mode">
            <option value="do">auto</option>
            <option value="ask">ask</option>
            <option value="plan">plan</option>
            <option value="review">review</option>
            <option value="run">run</option>
          </select>
        </label>
        <label>Запрос
          <textarea id="text" placeholder="Например: Добавь страницу настроек пользователя"></textarea>
        </label>
        <label>Project path
          <input id="projectPath" placeholder="/path/to/project">
        </label>
        <button id="submit" class="primary" type="submit">Отправить</button>
      </form>
    </main>
  </div>
  <script>
    const statusEl = document.querySelector('#status');
    const tasksEl = document.querySelector('#tasks');
    const messagesEl = document.querySelector('#messages');
    const form = document.querySelector('#requestForm');
    const submitBtn = document.querySelector('#submit');

    function addMessage(text, kind = '') {
      const el = document.createElement('div');
      el.className = `msg ${kind}`;
      el.textContent = text;
      messagesEl.appendChild(el);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function addJsonMessage(data, kind = 'result') {
      const el = document.createElement('div');
      el.className = `msg ${kind}`;
      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify(data, null, 2);
      el.appendChild(pre);
      messagesEl.appendChild(el);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function getJson(url) {
      const response = await fetch(url);
      return await response.json();
    }

    async function postJson(url, payload) {
      const response = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      return await response.json();
    }

    function kv(label, value) {
      const el = document.createElement('div');
      el.className = 'kv';
      el.innerHTML = `<strong></strong><span></span>`;
      el.querySelector('strong').textContent = label;
      el.querySelector('span').textContent = value ?? '';
      return el;
    }

    async function loadStatus() {
      const data = await getJson('/api/status');
      statusEl.innerHTML = '';
      statusEl.appendChild(kv('Vault', `${data.vault.path} (${data.vault.exists ? 'есть' : 'нет'})`));
      statusEl.appendChild(kv('Текущая папка', data.project.current_path));
      statusEl.appendChild(kv('Git', data.project.current_is_git_repo ? (data.project.current_git_status || 'чисто') : 'не git repo'));
      statusEl.appendChild(kv('Codex subagents', `${data.workers.codex?.allow_subagents ? 'включены' : 'отключены'}, ${data.workers.codex?.subagent_policy || 'n/a'}`));
      statusEl.appendChild(kv('Workers', Object.entries(data.workers).map(([k,v]) => `${k}: ${v.cli_found ? 'found' : 'missing'} / ${v.status}`).join('\\n')));
      document.querySelector('#projectPath').placeholder = data.project.current_path;
    }

    async function loadTasks() {
      const data = await getJson('/api/tasks?limit=20');
      tasksEl.innerHTML = '';
      if (!data.tasks.length) {
        tasksEl.appendChild(kv('История', 'Задач пока нет.'));
        return;
      }
      data.tasks.forEach(task => {
        const button = document.createElement('button');
        button.className = 'task';
        button.type = 'button';
        button.textContent = `${task.id}\\n${task.status || ''} ${task.project || ''}`;
        button.addEventListener('click', () => openTask(task.id));
        tasksEl.appendChild(button);
      });
    }

    async function openTask(id) {
      const data = await getJson(`/api/task/${encodeURIComponent(id)}`);
      if (!data.ok) {
        addMessage(data.error || 'Задача не найдена.', 'error');
        return;
      }
      addMessage(`${data.path}\\n\\n${data.markdown}`, 'result');
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const mode = document.querySelector('#mode').value;
      const text = document.querySelector('#text').value.trim();
      const projectPath = document.querySelector('#projectPath').value.trim();
      if (!text && mode !== 'review') {
        addMessage('Введите запрос.', 'error');
        return;
      }
      const payload = {text, project_path: projectPath || null};
      addMessage(`${mode}: ${text || 'Ревью текущих изменений'}`, 'user');
      submitBtn.disabled = true;
      try {
        const data = await postJson(`/api/${mode}`, payload);
        if (!data.ok) {
          addMessage(data.error || 'Ошибка выполнения.', 'error');
        } else {
          addJsonMessage(data);
          await loadTasks();
          await loadStatus();
        }
      } catch (error) {
        addMessage(String(error), 'error');
      } finally {
        submitBtn.disabled = false;
      }
    });

    document.querySelector('#refreshStatus').addEventListener('click', loadStatus);
    document.querySelector('#refreshTasks').addEventListener('click', loadTasks);
    loadStatus();
    loadTasks();
  </script>
</body>
</html>
"""
