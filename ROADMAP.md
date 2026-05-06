# Roadmap

AI-Boss is focused on a reliable local workflow for developers: clear task history, conservative git safety, predictable worker routing and a dashboard that stays useful without becoming a hosted service.

## Done

- Persistent queue: web-задачи сохраняются в Vault и восстанавливаются после перезапуска.
- Cancel/retry: web UI умеет отменять и повторять запуски.
- Settings UI: ключевые safety и worker-настройки редактируются через local-only интерфейс.
- Live logs: worker stdout/stderr попадает в web live log во время выполнения.
- Task detail: задача показывает plan, execution log, review и final report из Vault.

## Near Term

- Security hardening: усилить local-only ограничения, обработку секретов и защиту от опасных git-операций.
- Packaging: подготовить предсказуемую установку, релизный процесс и версионирование.
- Очередь как daemon/service: отделить выполнение задач от жизненного цикла вкладки браузера и web-процесса.

## Later

- Более богатая диагностика worker CLI и preflight-проверок.
- Улучшенные project profiles для повторяющихся рабочих деревьев.
- Экспорт release/report артефактов без привязки к web UI.
- Интеграции с GitHub/issue trackers после укрепления локального ядра.
