INDEX_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI-Boss Super Brain</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f3f5f8;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --text: #141821;
      --muted: #667085;
      --line: #d8dee8;
      --accent: #0f766e;
      --accent-2: #2563eb;
      --warn: #b54708;
      --danger: #b42318;
      --ok: #027a48;
      --shadow: 0 8px 24px rgba(20, 24, 33, .08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }
    button, input, textarea, select { font: inherit; }
    button { cursor: pointer; }
    .app {
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      min-height: 100vh;
    }
    .sidebar {
      background: #e9eef5;
      border-right: 1px solid var(--line);
      padding: 18px;
      overflow: auto;
    }
    .brand {
      display: grid;
      gap: 4px;
      margin-bottom: 18px;
    }
    .brand h1 { margin: 0; font-size: 20px; }
    .brand span { color: var(--muted); font-size: 13px; }
    .main {
      min-width: 0;
      display: grid;
      grid-template-rows: auto 1fr;
      min-height: 100vh;
    }
    .topbar {
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      padding: 16px 22px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: center;
    }
    .topbar h2 { margin: 0; font-size: 18px; }
    .topbar p { margin: 4px 0 0; color: var(--muted); }
    .content {
      padding: 18px 22px;
      display: grid;
      grid-template-columns: minmax(360px, 1.1fr) minmax(320px, .9fr);
      gap: 18px;
      align-items: start;
      overflow: auto;
    }
    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
    }
    .panel-head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .panel-head h3 { margin: 0; font-size: 15px; }
    .panel-body { padding: 16px; }
    .grid { display: grid; gap: 12px; }
    .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .kv {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-soft);
      padding: 10px;
      display: grid;
      gap: 4px;
      overflow-wrap: anywhere;
    }
    .kv strong { color: var(--muted); font-size: 12px; }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 12px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--muted);
    }
    .pill.ok { color: var(--ok); border-color: #abefc6; background: #ecfdf3; }
    .pill.warn { color: var(--warn); border-color: #fedf89; background: #fffaeb; }
    .pill.bad { color: var(--danger); border-color: #fecdca; background: #fef3f2; }
    label { display: grid; gap: 6px; color: var(--muted); font-size: 12px; }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      padding: 10px 11px;
    }
    textarea {
      min-height: 150px;
      resize: vertical;
      line-height: 1.45;
    }
    .btn {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      background: #fff;
      color: var(--text);
    }
    .btn.primary {
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
      font-weight: 650;
    }
    .btn.blue {
      border-color: var(--accent-2);
      background: var(--accent-2);
      color: #fff;
      font-weight: 650;
    }
    .btn:disabled { opacity: .55; cursor: wait; }
    .task-list { display: grid; gap: 8px; }
    .task {
      width: 100%;
      text-align: left;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 10px;
    }
    .task:hover { border-color: var(--accent); }
    .task strong { display: block; font-size: 13px; overflow-wrap: anywhere; }
    .task span { color: var(--muted); font-size: 12px; }
    .messages {
      display: grid;
      gap: 10px;
      max-height: 420px;
      overflow: auto;
    }
    .msg {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-soft);
      padding: 12px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .msg.error { color: var(--danger); border-color: #fecdca; background: #fef3f2; }
    .msg.user { border-color: #bfdbfe; background: #eff6ff; }
    pre {
      margin: 0;
      white-space: pre-wrap;
      overflow: auto;
      max-height: 520px;
      background: #111827;
      color: #e5e7eb;
      padding: 12px;
      border-radius: 8px;
      font-size: 13px;
    }
    .worker-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    @media (max-width: 1060px) {
      .app { grid-template-columns: 1fr; }
      .sidebar { border-right: 0; border-bottom: 1px solid var(--line); }
      .content { grid-template-columns: 1fr; }
      .worker-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <h1>AI-Boss</h1>
        <span>Super Brain local dashboard</span>
      </div>
      <section class="panel">
        <div class="panel-head"><h3>Система</h3><button class="btn" id="refreshAll" type="button">Обновить</button></div>
        <div class="panel-body grid" id="statusBox"></div>
      </section>
      <div style="height:12px"></div>
      <section class="panel">
        <div class="panel-head"><h3>Проекты</h3></div>
        <div class="panel-body grid">
          <div id="projectsBox" class="grid"></div>
          <label>Название <input id="projectName" placeholder="my-app"></label>
          <label>Путь <input id="projectAddPath" placeholder="/path/to/project"></label>
          <button class="btn" id="addProject" type="button">Добавить профиль</button>
        </div>
      </section>
    </aside>
    <main class="main">
      <header class="topbar">
        <div>
          <h2>Рабочая область</h2>
          <p>Один локальный UI для планирования, запуска, ревью и истории задач.</p>
        </div>
        <span class="pill ok">local-only</span>
      </header>
      <section class="content">
        <div class="grid">
          <section class="panel">
            <div class="panel-head">
              <h3>Новая задача</h3>
              <button class="btn" id="preflightBtn" type="button">Preflight</button>
            </div>
            <div class="panel-body grid">
              <div class="row">
                <label style="flex: 0 0 150px">Режим
                  <select id="mode">
                    <option value="do">auto</option>
                    <option value="ask">ask</option>
                    <option value="plan">plan</option>
                    <option value="review">review</option>
                    <option value="run">run</option>
                  </select>
                </label>
                <label style="flex: 1 1 260px">Project path
                  <input id="projectPath" placeholder="/path/to/project">
                </label>
              </div>
              <label>Запрос
                <textarea id="taskText" placeholder="Например: Добавь страницу настроек пользователя"></textarea>
              </label>
              <div class="row">
                <button class="btn primary" id="sendBtn" type="button">Запустить</button>
                <button class="btn blue" id="reviewBtn" type="button">Review diff</button>
              </div>
            </div>
          </section>
          <section class="panel">
            <div class="panel-head"><h3>Журнал</h3><button class="btn" id="clearLog" type="button">Очистить</button></div>
            <div class="panel-body"><div id="messages" class="messages"></div></div>
          </section>
        </div>
        <div class="grid">
          <section class="panel">
            <div class="panel-head"><h3>Preflight</h3><span id="preflightState" class="pill">не проверено</span></div>
            <div class="panel-body grid" id="preflightBox"></div>
          </section>
          <section class="panel">
            <div class="panel-head"><h3>Workers</h3></div>
            <div class="panel-body"><div id="workersBox" class="worker-grid"></div></div>
          </section>
          <section class="panel">
            <div class="panel-head"><h3>История</h3><button class="btn" id="refreshTasks" type="button">Обновить</button></div>
            <div class="panel-body"><div id="tasksBox" class="task-list"></div></div>
          </section>
        </div>
      </section>
    </main>
  </div>
  <script>
    const $ = (id) => document.getElementById(id);
    const state = {status: null, tasks: [], projects: []};

    function el(tag, cls, text) {
      const node = document.createElement(tag);
      if (cls) node.className = cls;
      if (text !== undefined) node.textContent = text;
      return node;
    }
    function kv(label, value) {
      const box = el('div', 'kv');
      box.appendChild(el('strong', '', label));
      box.appendChild(el('span', '', value || ''));
      return box;
    }
    function pill(ok, text) {
      return `<span class="pill ${ok ? 'ok' : 'bad'}">${text}</span>`;
    }
    async function getJson(url) {
      const response = await fetch(url);
      return response.json();
    }
    async function postJson(url, payload) {
      const response = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      return response.json();
    }
    function log(text, kind='') {
      const box = el('div', `msg ${kind}`, text);
      $('messages').appendChild(box);
      $('messages').scrollTop = $('messages').scrollHeight;
    }
    function logJson(data) {
      const box = el('div', 'msg');
      const pre = el('pre');
      pre.textContent = JSON.stringify(data, null, 2);
      box.appendChild(pre);
      $('messages').appendChild(box);
      $('messages').scrollTop = $('messages').scrollHeight;
    }
    function currentPayload() {
      return {text: $('taskText').value.trim(), project_path: $('projectPath').value.trim() || null};
    }
    async function loadStatus() {
      const data = await getJson('/api/status');
      state.status = data;
      $('statusBox').innerHTML = '';
      $('statusBox').appendChild(kv('Vault', `${data.vault.path} (${data.vault.exists ? 'есть' : 'нет'})`));
      $('statusBox').appendChild(kv('Текущая папка', data.project.current_path));
      $('statusBox').appendChild(kv('Git', data.project.current_is_git_repo ? (data.project.current_git_status || 'чисто') : 'не git repo'));
      $('projectPath').placeholder = data.project.current_path;
      $('workersBox').innerHTML = '';
      Object.entries(data.workers).forEach(([name, worker]) => {
        const box = el('div', 'kv');
        box.appendChild(el('strong', '', name));
        box.insertAdjacentHTML('beforeend', `${pill(worker.cli_found, worker.cli_found ? 'CLI найден' : 'CLI не найден')} ${pill(worker.enabled, worker.status)}`);
        if (name === 'codex') box.appendChild(el('span', '', `subagents: ${worker.allow_subagents ? 'auto' : 'off'}`));
        $('workersBox').appendChild(box);
      });
    }
    async function loadProjects() {
      const data = await getJson('/api/projects');
      state.projects = data.projects || [];
      $('projectsBox').innerHTML = '';
      if (!state.projects.length) {
        $('projectsBox').appendChild(kv('Профили', 'Пока не добавлены'));
        return;
      }
      state.projects.forEach(project => {
        const button = el('button', 'task');
        button.type = 'button';
        button.innerHTML = `<strong>${project.name}${project.default ? ' · default' : ''}</strong><span>${project.path}</span>`;
        button.addEventListener('click', () => { $('projectPath').value = project.path; runPreflight(); });
        $('projectsBox').appendChild(button);
      });
    }
    async function loadTasks() {
      const data = await getJson('/api/tasks?limit=25');
      state.tasks = data.tasks || [];
      $('tasksBox').innerHTML = '';
      if (!state.tasks.length) {
        $('tasksBox').appendChild(kv('История', 'Задач пока нет'));
        return;
      }
      state.tasks.forEach(task => {
        const button = el('button', 'task');
        button.type = 'button';
        button.innerHTML = `<strong>${task.id}</strong><span>${task.status || ''} · ${task.project || ''}</span>`;
        button.addEventListener('click', async () => {
          const detail = await getJson(`/api/task/${encodeURIComponent(task.id)}`);
          if (detail.ok) log(`${detail.path || detail.task?.path}\\n\\n${detail.markdown || detail.task?.content}`, '');
          else log(detail.error || 'Задача не найдена', 'error');
        });
        $('tasksBox').appendChild(button);
      });
    }
    async function runPreflight() {
      const data = await postJson('/api/preflight', {project_path: $('projectPath').value.trim() || null});
      $('preflightState').className = `pill ${data.ok ? 'ok' : 'warn'}`;
      $('preflightState').textContent = data.ok ? 'готово' : 'проверь';
      $('preflightBox').innerHTML = '';
      (data.checks || []).forEach(check => {
        const box = kv(check.name, check.detail);
        box.insertAdjacentHTML('beforeend', pill(check.ok, check.ok ? 'ok' : 'attention'));
        $('preflightBox').appendChild(box);
      });
      return data;
    }
    async function send(mode) {
      const payload = currentPayload();
      if (mode !== 'review' && !payload.text) {
        log('Введите запрос.', 'error');
        return;
      }
      if (mode === 'review' && !payload.text) payload.text = 'Проверь текущие изменения';
      $('sendBtn').disabled = true;
      log(`${mode}: ${payload.text}`, 'user');
      try {
        const data = await postJson(`/api/${mode}`, payload);
        if (!data.ok) log(data.error || 'Ошибка выполнения', 'error');
        else logJson(data);
        await Promise.all([loadStatus(), loadTasks()]);
      } catch (error) {
        log(String(error), 'error');
      } finally {
        $('sendBtn').disabled = false;
      }
    }
    $('sendBtn').addEventListener('click', () => send($('mode').value));
    $('reviewBtn').addEventListener('click', () => send('review'));
    $('preflightBtn').addEventListener('click', runPreflight);
    $('refreshAll').addEventListener('click', () => Promise.all([loadStatus(), loadProjects(), loadTasks(), runPreflight()]));
    $('refreshTasks').addEventListener('click', loadTasks);
    $('clearLog').addEventListener('click', () => $('messages').innerHTML = '');
    $('addProject').addEventListener('click', async () => {
      const name = $('projectName').value.trim();
      const path = $('projectAddPath').value.trim();
      if (!name || !path) { log('Заполните название и путь проекта.', 'error'); return; }
      const data = await postJson('/api/projects', {name, path});
      if (!data.ok) log(data.error || 'Не удалось добавить проект', 'error');
      await loadProjects();
    });
    Promise.all([loadStatus(), loadProjects(), loadTasks()]).then(runPreflight);
  </script>
</body>
</html>
"""

