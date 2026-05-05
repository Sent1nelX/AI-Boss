from ai_boss.core.router import Router
from ai_boss.core.task_classifier import TaskClassifier
from ai_boss.models.task import TaskType
from ai_boss.models.worker import WorkerState, WorkerStatus


def test_task_classifier_matches_keywords_in_priority_order() -> None:
    classifier = TaskClassifier()

    assert classifier.classify("Объясни, что такое git rebase") == TaskType.SIMPLE_QUESTION
    assert classifier.classify("Составь план миграции") == TaskType.PLANNING
    assert classifier.classify("Архитектура нового сервиса") == TaskType.ARCHITECTURE
    assert classifier.classify("Почини ошибку авторизации") == TaskType.BUGFIX
    assert classifier.classify("Сделай review изменений") == TaskType.REVIEW
    assert classifier.classify("Добавь pytest для роутера") == TaskType.TEST_GENERATION
    assert classifier.classify("Помоги настроить nginx на сервер") == TaskType.DEPLOYMENT_HELP
    assert classifier.classify("Нужен refactor модуля") == TaskType.REFACTOR
    assert classifier.classify("Обнови README документация") == TaskType.DOCUMENTATION
    assert classifier.classify("Реализуй новый endpoint") == TaskType.CODE_CHANGE


def test_task_classifier_defaults_to_simple_question() -> None:
    assert TaskClassifier().classify("Как дела у системы?") == TaskType.SIMPLE_QUESTION


def test_router_uses_default_routes_for_available_workers() -> None:
    router = Router(
        {
            "codex": WorkerState(status=WorkerStatus.AVAILABLE),
            "claude": WorkerState(status=WorkerStatus.AVAILABLE),
        }
    )

    assert router.route(TaskType.CODE_CHANGE) == "codex"
    assert router.route(TaskType.BUGFIX) == "codex"
    assert router.route(TaskType.REVIEW) == "claude"
    assert router.route(TaskType.ARCHITECTURE) == "claude"
    assert router.route(TaskType.PLANNING) == "gemini"


def test_router_falls_back_from_unavailable_claude_to_gemini() -> None:
    for status in (WorkerStatus.LIMITED, WorkerStatus.FAILED, WorkerStatus.DISABLED, WorkerStatus.COOLDOWN):
        router = Router({"claude": WorkerState(status=status)})

        assert router.route(TaskType.REVIEW) == "gemini"


def test_router_keeps_codex_route_when_unavailable_because_no_fallback_is_defined() -> None:
    router = Router({"codex": WorkerState(status=WorkerStatus.LIMITED)})

    assert router.route(TaskType.CODE_CHANGE) == "codex"


def test_router_always_sends_simple_questions_to_gemini() -> None:
    router = Router({"gemini": WorkerState(status=WorkerStatus.DISABLED)})

    assert router.route(TaskType.SIMPLE_QUESTION) == "gemini"
