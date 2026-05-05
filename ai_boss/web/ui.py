INDEX_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI-Boss Super Brain</title>
  <style>
    :root {
      --bg: #f4f5f3;
      --surface: #fbfbf9;
      --surface-2: #f0f1ee;
      --ink: #16181a;
      --ink-2: #2c3033;
      --muted: #6b7177;
      --muted-2: #8d9298;
      --line: #d9dad6;
      --line-2: #e6e7e3;
      --line-strong: #b8bab4;
      --ok: #317957;
      --ok-bg: #edf7f1;
      --warn: #9a6a18;
      --warn-bg: #fff7df;
      --bad: #a34a35;
      --bad-bg: #fff0ed;
      --info: #4a668f;
      --info-bg: #eef4fb;
      --accent: #316f7a;
      --w-gemini: #5c75ad;
      --w-codex: #a65d47;
      --w-claude: #9b7b22;
      --r-1: 3px;
      --r-2: 6px;
      --r-3: 10px;
      --f-sans: ui-sans-serif, -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
      --f-mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; min-height: 100%; }
    body {
      background: var(--bg);
      color: var(--ink);
      font-family: var(--f-sans);
      font-size: 13px;
      line-height: 1.45;
      letter-spacing: 0;
      -webkit-font-smoothing: antialiased;
    }
    button, input, textarea, select { font: inherit; color: inherit; }
    button { cursor: pointer; border: 0; background: none; }
    .mono { font-family: var(--f-mono); }
    .app {
      display: grid;
      grid-template-columns: 232px minmax(0, 1fr);
      min-height: 100vh;
      background: var(--surface);
    }
    .sidebar {
      border-right: 1px solid var(--line);
      background: var(--surface);
      padding: 14px 12px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      min-width: 0;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 9px;
      padding: 4px 6px 8px;
      border-bottom: 1px solid var(--line-2);
    }
    .brand-mark {
      width: 22px;
      height: 22px;
      border-radius: 5px;
      background: var(--ink);
      color: var(--bg);
      display: grid;
      place-items: center;
      font-family: var(--f-mono);
      font-size: 11px;
      font-weight: 700;
    }
    .brand-name { font-size: 13px; font-weight: 650; }
    .brand-tag {
      margin-left: auto;
      font-family: var(--f-mono);
      color: var(--muted);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: .06em;
    }
    .nav { display: flex; flex-direction: column; gap: 1px; }
    .nav-group {
      font-family: var(--f-mono);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--muted-2);
      padding: 8px 8px 4px;
    }
    .nav button {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 6px 8px;
      border-radius: 5px;
      color: var(--ink-2);
      text-align: left;
    }
    .nav button:hover { background: var(--surface-2); }
    .nav button.active { background: var(--ink); color: var(--bg); }
    .nav .ico { width: 14px; text-align: center; font-family: var(--f-mono); opacity: .72; }
    .nav .ct { margin-left: auto; font-family: var(--f-mono); font-size: 10px; color: var(--muted); }
    .nav button.active .ct { color: rgba(255,255,255,.72); }
    .side-foot {
      margin-top: auto;
      display: grid;
      gap: 6px;
      padding-top: 10px;
      border-top: 1px solid var(--line-2);
    }
    .side-foot .row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: var(--f-mono);
      font-size: 10.5px;
      color: var(--muted);
      min-width: 0;
    }
    .side-foot b { color: var(--ink-2); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .main { display: grid; grid-template-rows: auto 1fr; min-width: 0; }
    .topbar {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: center;
      padding: 10px 16px;
      background: var(--surface);
      border-bottom: 1px solid var(--line);
    }
    .crumbs {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      font-family: var(--f-mono);
      color: var(--muted);
      font-size: 11.5px;
    }
    .crumbs b { color: var(--ink); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .branch {
      padding: 2px 6px;
      background: var(--surface-2);
      border: 1px solid var(--line-2);
      border-radius: 3px;
      color: var(--ink-2);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 360px;
    }
    .top-actions { display: flex; align-items: center; gap: 6px; }
    .workspace {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(340px, 1fr);
      gap: 14px;
      padding: 14px 16px 24px;
      align-items: start;
      overflow: auto;
      background: var(--bg);
    }
    .col { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
    .panel {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: var(--r-2);
      overflow: hidden;
      min-width: 0;
      box-shadow: 0 4px 14px -12px rgba(20,24,33,.24);
    }
    .p-head {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border-bottom: 1px solid var(--line-2);
      background: var(--surface);
    }
    .p-head h3 { margin: 0; font-size: 12.5px; font-weight: 650; }
    .h-meta {
      font-family: var(--f-mono);
      font-size: 10.5px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .06em;
    }
    .right { margin-left: auto; display: flex; align-items: center; gap: 6px; }
    .p-body { padding: 12px; }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 5px 10px;
      border: 1px solid var(--line);
      border-radius: var(--r-1);
      background: #fff;
      color: var(--ink-2);
      font-size: 12px;
      white-space: nowrap;
    }
    .btn:hover { background: var(--surface-2); border-color: var(--line-strong); }
    .btn.primary { background: var(--ink); color: var(--bg); border-color: var(--ink); }
    .btn.primary:hover { background: #000; }
    .btn.danger { color: var(--bad); border-color: #e6c8c2; }
    .btn.danger:hover { background: var(--bad-bg); }
    .btn.sm { padding: 3px 7px; font-size: 11.5px; }
    .btn[disabled] { opacity: .5; cursor: wait; }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      min-height: 20px;
      padding: 2px 7px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--muted);
      font-family: var(--f-mono);
      font-size: 10.5px;
      white-space: nowrap;
    }
    .pill.ok { color: var(--ok); border-color: #bcd5be; background: var(--ok-bg); }
    .pill.warn { color: var(--warn); border-color: #dac494; background: var(--warn-bg); }
    .pill.bad { color: var(--bad); border-color: #dcb6ac; background: var(--bad-bg); }
    .pill.info { color: var(--info); border-color: #b9c6d8; background: var(--info-bg); }
    .led { width: 6px; height: 6px; border-radius: 50%; background: currentColor; display: inline-block; }
    .field { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
    .lbl {
      font-family: var(--f-mono);
      font-size: 10.5px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .06em;
    }
    .input, .select, .textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: var(--r-1);
      background: #fff;
      padding: 7px 9px;
      font-size: 12.5px;
    }
    .input:focus, .select:focus, .textarea:focus {
      outline: 0;
      border-color: var(--ink);
      box-shadow: 0 0 0 3px rgba(20,24,33,.07);
    }
    .textarea { min-height: 134px; resize: vertical; line-height: 1.5; }
    .composer { display: grid; gap: 10px; }
    .mode-tabs {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      border: 1px solid var(--line);
      border-radius: var(--r-1);
      overflow: hidden;
      background: var(--surface-2);
    }
    .mode-tabs button {
      padding: 6px 8px;
      color: var(--muted);
      border-right: 1px solid var(--line);
      text-transform: lowercase;
      font-size: 12px;
    }
    .mode-tabs button:last-child { border-right: 0; }
    .mode-tabs button.on { background: #fff; color: var(--ink); }
    .field-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: end; }
    .check-list { display: grid; gap: 6px; }
    .check {
      display: grid;
      grid-template-columns: 18px minmax(0, 1fr) auto;
      align-items: center;
      gap: 8px;
      padding: 7px 8px;
      border: 1px solid var(--line-2);
      border-radius: var(--r-1);
      background: var(--surface);
    }
    .glyph {
      width: 18px;
      height: 18px;
      display: grid;
      place-items: center;
      border-radius: 4px;
      background: var(--surface-2);
      color: var(--muted);
      font-family: var(--f-mono);
      font-size: 11px;
    }
    .check.ok .glyph { background: var(--ok-bg); color: var(--ok); }
    .check.bad .glyph { background: var(--bad-bg); color: var(--bad); }
    .check .name { font-family: var(--f-mono); font-size: 11px; color: var(--ink-2); }
    .check .detail { font-family: var(--f-mono); font-size: 10.5px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .worker-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
    .worker {
      border: 1px solid var(--line);
      border-radius: var(--r-1);
      background: var(--surface);
      padding: 10px;
      display: grid;
      gap: 6px;
      border-top-width: 3px;
    }
    .worker.gemini { border-top-color: var(--w-gemini); }
    .worker.codex { border-top-color: var(--w-codex); }
    .worker.claude { border-top-color: var(--w-claude); }
    .worker .role { font-family: var(--f-mono); font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
    .worker .name { font-weight: 650; }
    .worker .meta { font-family: var(--f-mono); font-size: 10.5px; color: var(--muted); display: flex; gap: 8px; flex-wrap: wrap; }
    .live-log { background: #161718; color: #cfd0cb; font-family: var(--f-mono); min-height: 244px; max-height: 420px; overflow: auto; }
    .ll { display: grid; grid-template-columns: 56px 62px minmax(0, 1fr); gap: 8px; padding: 3px 10px; border-bottom: 1px solid #222426; font-size: 11.5px; }
    .ll .t { color: #6b7177; }
    .ll .src { color: #9ba1a8; text-transform: uppercase; font-size: 10.5px; letter-spacing: .04em; }
    .ll.gem .src { color: #9ab2d9; }
    .ll.cdx .src { color: #d99a87; }
    .ll.cld .src { color: #cbb47a; }
    .ll.err .body { color: #e89d92; }
    .ll.ok .body { color: #a8c9aa; }
    .timeline { display: flex; align-items: center; gap: 10px; overflow: auto; padding-bottom: 2px; }
    .step { display: flex; align-items: center; gap: 5px; font-family: var(--f-mono); font-size: 10.5px; color: var(--muted); white-space: nowrap; }
    .num {
      display: inline-flex;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: var(--surface-2);
      color: var(--muted);
      align-items: center;
      justify-content: center;
      font-size: 10px;
    }
    .step.done .num { background: var(--ok-bg); color: var(--ok); }
    .step.curr .num { background: var(--ink); color: var(--bg); }
    .task-list, .project-list { display: grid; gap: 6px; }
    .task-row, .project-row {
      display: grid;
      gap: 2px;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: var(--r-1);
      background: #fff;
      padding: 8px 9px;
      text-align: left;
    }
    .task-row:hover, .project-row:hover { border-color: var(--line-strong); background: var(--surface); }
    .task-row .id, .project-row .path { font-family: var(--f-mono); font-size: 10.5px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .task-row .title, .project-row .name { font-size: 12.5px; color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .meta-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .meta-cell { border: 1px solid var(--line-2); border-radius: var(--r-1); padding: 8px; background: var(--surface); }
    .meta-cell .k { font-family: var(--f-mono); font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
    .meta-cell .v { font-size: 12.5px; color: var(--ink-2); overflow-wrap: anywhere; }
    .markdown {
      max-height: 360px;
      overflow: auto;
      padding: 10px;
      border: 1px solid var(--line-2);
      border-radius: var(--r-1);
      background: var(--surface);
      white-space: pre-wrap;
      font-family: var(--f-mono);
      font-size: 11.5px;
    }
    .empty { padding: 18px; text-align: center; color: var(--muted); background: var(--surface); border: 1px dashed var(--line); border-radius: var(--r-1); }
    @media (max-width: 1180px) {
      .app { grid-template-columns: 1fr; }
      .sidebar { border-right: 0; border-bottom: 1px solid var(--line); }
      .workspace { grid-template-columns: 1fr; }
    }
    @media (max-width: 760px) {
      .topbar { grid-template-columns: 1fr; }
      .worker-grid, .meta-grid, .field-row { grid-template-columns: 1fr; }
      .mode-tabs { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">AI</div>
        <div class="brand-name">AI-Boss</div>
        <div class="brand-tag">local</div>
      </div>
      <nav class="nav">
        <div class="nav-group">Работа</div>
        <button class="active" data-scroll="composer"><span class="ico">⌘</span>Новая задача<span class="ct">auto</span></button>
        <button data-scroll="activeTask"><span class="ico">◉</span>Активная задача<span class="ct" id="activeTaskCount">0</span></button>
        <button data-scroll="history"><span class="ico">T</span>История<span class="ct" id="taskCount">0</span></button>
        <div class="nav-group">Контекст</div>
        <button data-scroll="preflight"><span class="ico">✓</span>Preflight<span class="ct" id="preflightTiny">?</span></button>
        <button data-scroll="projects"><span class="ico">P</span>Проекты<span class="ct" id="projectCount">0</span></button>
        <button data-scroll="workers"><span class="ico">W</span>Workers<span class="ct">3</span></button>
      </nav>
      <div class="side-foot">
        <div class="row"><span>vault</span><b id="vaultPath">...</b></div>
        <div class="row"><span>git</span><b id="gitState">...</b></div>
        <div class="row"><span>mode</span><b>local-only</b></div>
      </div>
    </aside>
    <main class="main">
      <header class="topbar">
        <div class="crumbs">
          <b>workspace</b>
          <span>/</span>
          <span class="branch" id="currentProject">...</span>
          <span class="pill" id="gitPill"><span class="led"></span>git</span>
        </div>
        <div class="top-actions">
          <button class="btn sm" id="refreshAll" type="button">Обновить</button>
          <button class="btn sm" id="preflightTop" type="button">Preflight</button>
        </div>
      </header>
      <section class="workspace">
        <div class="col">
          <section class="panel" id="composer">
            <div class="p-head">
              <h3>Command composer</h3>
              <span class="h-meta">Gemini → Codex → Review</span>
              <div class="right"><span class="pill info">Codex-only write</span></div>
            </div>
            <div class="p-body">
              <div class="composer">
                <div class="mode-tabs" id="modeTabs">
                  <button class="on" data-mode="do">auto</button>
                  <button data-mode="ask">ask</button>
                  <button data-mode="plan">plan</button>
                  <button data-mode="review">review</button>
                  <button data-mode="run">run</button>
                </div>
                <div class="field-row">
                  <label class="field">
                    <span class="lbl">project path</span>
                    <input class="input mono" id="projectPath" placeholder="/path/to/project">
                  </label>
                  <button class="btn" id="useCurrent" type="button">Текущая папка</button>
                </div>
                <label class="field">
                  <span class="lbl">запрос</span>
                  <textarea class="textarea" id="taskText" placeholder="Например: Добавь retry в PaymentService.charge и покрой тестами"></textarea>
                </label>
                <div class="field-row">
                  <div class="timeline">
                    <span class="step done"><span class="num">1</span>plan</span>
                    <span class="step curr"><span class="num">2</span>codex</span>
                    <span class="step"><span class="num">3</span>review</span>
                    <span class="step"><span class="num">4</span>fix-loop</span>
                    <span class="step"><span class="num">5</span>report</span>
                  </div>
                  <div class="right">
                    <button class="btn" id="reviewBtn" type="button">Review diff</button>
                    <button class="btn primary" id="sendBtn" type="button">Запустить</button>
                  </div>
                </div>
              </div>
            </div>
          </section>
          <section class="panel" id="activeTask">
            <div class="p-head">
              <h3>Active task</h3>
              <span class="h-meta" id="activeTaskMeta">нет активного запуска</span>
              <div class="right"><button class="btn sm danger" id="clearLog" type="button">Очистить</button></div>
            </div>
            <div class="live-log" id="liveLog"></div>
          </section>
          <section class="panel" id="taskDetails">
            <div class="p-head"><h3>Детали задачи</h3><span class="h-meta" id="taskDetailsMeta">выберите задачу</span></div>
            <div class="p-body">
              <div id="taskMeta" class="meta-grid"></div>
              <div style="height:8px"></div>
              <div id="taskMarkdown" class="markdown">Задача пока не выбрана.</div>
            </div>
          </section>
        </div>
        <div class="col">
          <section class="panel" id="preflight">
            <div class="p-head">
              <h3>Preflight</h3>
              <span class="h-meta">перед run/review</span>
              <div class="right"><span class="pill" id="preflightState">не проверено</span></div>
            </div>
            <div class="p-body"><div class="check-list" id="preflightBox"></div></div>
          </section>
          <section class="panel" id="workers">
            <div class="p-head"><h3>Workers</h3><span class="h-meta">CLI и лимиты</span></div>
            <div class="p-body"><div class="worker-grid" id="workersBox"></div></div>
          </section>
          <section class="panel" id="projects">
            <div class="p-head"><h3>Проекты</h3><span class="h-meta">profiles.yaml</span></div>
            <div class="p-body">
              <div class="project-list" id="projectsBox"></div>
              <div style="height:10px"></div>
              <div class="field-row">
                <label class="field"><span class="lbl">name</span><input class="input" id="projectName" placeholder="orders-api"></label>
                <label class="field"><span class="lbl">path</span><input class="input mono" id="projectAddPath" placeholder="/path/to/project"></label>
              </div>
              <div style="height:8px"></div>
              <button class="btn" id="addProject" type="button">+ Добавить профиль</button>
            </div>
          </section>
          <section class="panel" id="history">
            <div class="p-head">
              <h3>История</h3>
              <span class="h-meta">Obsidian Vault</span>
              <div class="right"><button class="btn sm" id="refreshTasks" type="button">Обновить</button></div>
            </div>
            <div class="p-body"><div class="task-list" id="tasksBox"></div></div>
          </section>
        </div>
      </section>
    </main>
  </div>
  <script>
    const $ = (id) => document.getElementById(id);
    const state = { mode: 'do', status: null, tasks: [], projects: [], activeTask: null };
    const lifecycle = ['created', 'planned', 'awaiting_approval', 'running', 'reviewed', 'fixing', 'finished'];

    function node(tag, cls, text) {
      const el = document.createElement(tag);
      if (cls) el.className = cls;
      if (text !== undefined) el.textContent = text;
      return el;
    }
    function statusClass(ok) { return ok ? 'ok' : 'bad'; }
    function statusPill(ok, text) { return `<span class="pill ${statusClass(ok)}"><span class="led"></span>${text}</span>`; }
    function softStatusClass(value) {
      if (['finished', 'available', 'approved', 'clean', 'ok', true].includes(value)) return 'ok';
      if (['failed', 'limited', 'disabled', 'blocked', false].includes(value)) return 'bad';
      return 'warn';
    }
    function addLog(source, text, kind = '') {
      const row = node('div', `ll ${source} ${kind}`);
      const now = new Date().toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
      row.appendChild(node('span', 't', now));
      row.appendChild(node('span', 'src', source));
      row.appendChild(node('span', 'body', text));
      $('liveLog').appendChild(row);
      $('liveLog').scrollTop = $('liveLog').scrollHeight;
    }
    function addJsonLog(source, data) { addLog(source, JSON.stringify(data, null, 2)); }
    async function getJson(url) { const res = await fetch(url); return res.json(); }
    async function postJson(url, payload) {
      const res = await fetch(url, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      return res.json();
    }
    function payload() {
      return { text: $('taskText').value.trim(), project_path: $('projectPath').value.trim() || null };
    }
    function renderStatus(data) {
      state.status = data;
      $('vaultPath').textContent = data.vault.path;
      $('currentProject').textContent = $('projectPath').value || data.project.current_path;
      $('projectPath').placeholder = data.project.current_path;
      const gitClean = data.project.current_is_git_repo && !data.project.current_git_status;
      $('gitPill').className = `pill ${data.project.current_is_git_repo ? (gitClean ? 'ok' : 'warn') : 'bad'}`;
      $('gitPill').innerHTML = `<span class="led"></span>${data.project.current_is_git_repo ? (gitClean ? 'git clean' : 'dirty tree') : 'not git'}`;
      $('gitState').textContent = data.project.current_is_git_repo ? (gitClean ? 'clean' : 'dirty') : 'not git';
      $('workersBox').innerHTML = '';
      Object.entries(data.workers).forEach(([name, worker]) => {
        const card = node('div', `worker ${name}`);
        card.appendChild(node('div', 'role', name === 'codex' ? 'write-agent' : 'read/review'));
        card.appendChild(node('div', 'name', name));
        const meta = node('div', 'meta');
        meta.innerHTML = `${statusPill(worker.cli_found, worker.cli_found ? 'CLI найден' : 'CLI нет')} <span>${worker.status}</span>`;
        card.appendChild(meta);
        if (name === 'codex') card.appendChild(node('div', 'meta', `subagents: ${worker.allow_subagents ? worker.subagent_policy : 'off'}`));
        $('workersBox').appendChild(card);
      });
    }
    function renderPreflight(data) {
      const ok = Boolean(data.ok);
      $('preflightState').className = `pill ${ok ? 'ok' : 'warn'}`;
      $('preflightState').innerHTML = `<span class="led"></span>${ok ? 'готово' : 'проверь'}`;
      $('preflightTiny').textContent = ok ? 'ok' : '!';
      $('preflightBox').innerHTML = '';
      (data.checks || []).forEach(check => {
        const row = node('div', `check ${check.ok ? 'ok' : 'bad'}`);
        row.appendChild(node('span', 'glyph', check.ok ? '✓' : '!'));
        const mid = node('span');
        mid.appendChild(node('div', 'name', check.name));
        mid.appendChild(node('div', 'detail', check.detail || ''));
        row.appendChild(mid);
        const p = node('span', `pill ${check.ok ? 'ok' : 'bad'}`, check.ok ? 'ok' : 'attention');
        row.appendChild(p);
        $('preflightBox').appendChild(row);
      });
    }
    function renderProjects(data) {
      state.projects = data.projects || [];
      $('projectCount').textContent = state.projects.length;
      $('projectsBox').innerHTML = '';
      if (!state.projects.length) {
        $('projectsBox').appendChild(node('div', 'empty', 'Проектные профили пока не добавлены.'));
        return;
      }
      state.projects.forEach(project => {
        const btn = node('button', 'project-row');
        btn.type = 'button';
        btn.innerHTML = `<span class="name">${project.name} ${project.default ? '<span class="pill ok">default</span>' : ''}</span><span class="path">${project.path}</span>`;
        btn.addEventListener('click', () => {
          $('projectPath').value = project.path;
          $('currentProject').textContent = project.path;
          runPreflight();
        });
        $('projectsBox').appendChild(btn);
      });
    }
    function renderTasks(data) {
      state.tasks = data.tasks || [];
      $('taskCount').textContent = state.tasks.length;
      $('tasksBox').innerHTML = '';
      if (!state.tasks.length) {
        $('tasksBox').appendChild(node('div', 'empty', 'История пуста. Запустите первую задачу.'));
        return;
      }
      state.tasks.forEach(task => {
        const btn = node('button', 'task-row');
        btn.type = 'button';
        const status = task.status || 'created';
        btn.innerHTML = `<span class="id">${task.id}</span><span class="title">${status} · ${task.project || 'без проекта'}</span><span class="id">${task.created_at || ''}</span>`;
        btn.addEventListener('click', () => openTask(task.id));
        $('tasksBox').appendChild(btn);
      });
    }
    function renderTaskDetail(taskId, content, path) {
      $('taskDetailsMeta').textContent = taskId;
      $('taskMeta').innerHTML = '';
      [['id', taskId], ['path', path || ''], ['source', 'Obsidian Vault'], ['format', 'markdown']].forEach(([k, v]) => {
        const cell = node('div', 'meta-cell');
        cell.appendChild(node('div', 'k', k));
        cell.appendChild(node('div', 'v mono', v));
        $('taskMeta').appendChild(cell);
      });
      $('taskMarkdown').textContent = content || '';
    }
    async function loadStatus() { renderStatus(await getJson('/api/status')); }
    async function loadProjects() { renderProjects(await getJson('/api/projects')); }
    async function loadTasks() { renderTasks(await getJson('/api/tasks?limit=30')); }
    async function runPreflight() { const data = await postJson('/api/preflight', {project_path: $('projectPath').value.trim() || null}); renderPreflight(data); return data; }
    async function openTask(id) {
      const data = await getJson(`/api/task/${encodeURIComponent(id)}`);
      if (!data.ok) { addLog('err', data.error || 'Задача не найдена', 'err'); return; }
      renderTaskDetail(id, data.markdown || data.task?.content, data.path || data.task?.path);
    }
    async function send(mode) {
      const body = payload();
      if (mode !== 'review' && !body.text) { addLog('err', 'Введите запрос.', 'err'); return; }
      if (mode === 'review' && !body.text) body.text = 'Проверь текущие изменения';
      $('sendBtn').disabled = true;
      state.activeTask = body.text;
      $('activeTaskMeta').textContent = mode;
      $('activeTaskCount').textContent = '1';
      addLog('sys', `${mode}: ${body.text}`);
      if (['run', 'do'].includes(mode)) addLog('gem', 'planner/reporter будет выбран автоматически');
      if (mode === 'run') addLog('cdx', 'Codex остаётся единственным write-agent');
      try {
        const data = await postJson(`/api/${mode}`, body);
        if (!data.ok) {
          addLog('err', data.error || 'Ошибка выполнения', 'err');
        } else {
          addLog('sys', `готово · worker=${data.result?.worker || data.worker || 'n/a'}`, 'ok');
          addJsonLog('sys', data);
          await Promise.all([loadStatus(), loadTasks(), runPreflight()]);
        }
      } catch (error) {
        addLog('err', String(error), 'err');
      } finally {
        $('sendBtn').disabled = false;
        $('activeTaskCount').textContent = '0';
      }
    }
    document.querySelectorAll('#modeTabs button').forEach(button => {
      button.addEventListener('click', () => {
        document.querySelectorAll('#modeTabs button').forEach(b => b.classList.remove('on'));
        button.classList.add('on');
        state.mode = button.dataset.mode;
      });
    });
    document.querySelectorAll('.nav button[data-scroll]').forEach(button => {
      button.addEventListener('click', () => {
        document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
        button.classList.add('active');
        const target = document.getElementById(button.dataset.scroll);
        if (target) target.scrollIntoView({behavior: 'smooth', block: 'start'});
      });
    });
    $('sendBtn').addEventListener('click', () => send(state.mode));
    $('reviewBtn').addEventListener('click', () => send('review'));
    $('preflightTop').addEventListener('click', runPreflight);
    $('useCurrent').addEventListener('click', () => { if (state.status) $('projectPath').value = state.status.project.current_path; runPreflight(); });
    $('refreshAll').addEventListener('click', () => refreshAll());
    $('refreshTasks').addEventListener('click', loadTasks);
    $('clearLog').addEventListener('click', () => $('liveLog').innerHTML = '');
    $('addProject').addEventListener('click', async () => {
      const name = $('projectName').value.trim();
      const path = $('projectAddPath').value.trim();
      if (!name || !path) { addLog('err', 'Заполните название и путь проекта.', 'err'); return; }
      const data = await postJson('/api/projects', {name, path});
      if (!data.ok) addLog('err', data.error || 'Не удалось добавить проект', 'err');
      await loadProjects();
    });
    async function refreshAll() {
      await Promise.all([loadStatus(), loadProjects(), loadTasks()]);
      await runPreflight();
    }
    addLog('sys', 'AI-Boss dashboard готов. Выберите проект, проверьте preflight и запустите задачу.');
    refreshAll();
    setInterval(() => { loadStatus(); }, 4000);
    setInterval(() => { loadTasks(); }, 10000);
  </script>
</body>
</html>
"""
