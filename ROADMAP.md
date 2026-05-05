# Roadmap

Ближайший фокус AI-Boss v2: сделать local-only workflow устойчивее, прозрачнее и проще для ежедневной работы без расширения trust boundary.

## Done In Current v2 Line

- Persistent queue: web-задачи сохраняются в Vault и восстанавливаются после перезапуска.
- Cancel/retry: web UI умеет отменять и повторять запуски.
- Settings UI: ключевые safety и worker-настройки редактируются через local-only интерфейс.
- Live logs: worker stdout/stderr попадает в web live log во время выполнения.
- Task detail: задача показывает plan, execution log, review и final report из Vault.

## Near Term

- Security hardening: усилить local-only ограничения, обработку секретов, защиту от опасных git-операций и документацию по safe deployment.
- Packaging: подготовить предсказуемую установку и релизный процесс для локального использования.
- Очередь как daemon/service: отделить выполнение задач от жизненного цикла вкладки браузера и web-процесса.

## Later

- Более богатая диагностика worker CLI и preflight-проверок.
- Улучшенные project profiles для повторяющихся рабочих деревьев.
- Экспорт release/report артефактов без привязки к web UI.
