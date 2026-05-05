from ai_boss.models.task import TaskType


KEYWORDS: list[tuple[TaskType, tuple[str, ...]]] = [
    (TaskType.SIMPLE_QUESTION, ("объясни", "что значит", "почему ошибка", "что такое", "расскажи")),
    (TaskType.PLANNING, ("план", "распланируй", "спроектируй", "планирование")),
    (TaskType.ARCHITECTURE, ("архитектура", "архитектор", "структура системы")),
    (TaskType.BUGFIX, ("баг", "ошибка", "сломалось", "почини", "исправь")),
    (TaskType.REVIEW, ("ревью", "проверь diff", "проверь изменения", "review")),
    (TaskType.TEST_GENERATION, ("тест", "pytest", "unit test", "unit-test")),
    (TaskType.DEPLOYMENT_HELP, ("деплой", "сервер", "nginx", "systemd")),
    (TaskType.REFACTOR, ("рефактор", "refactor", "перепиши")),
    (TaskType.DOCUMENTATION, ("документация", "readme", "docs", "документируй")),
    (TaskType.CODE_CHANGE, ("реализуй", "добавь", "сделай", "измени", "создай")),
]


class TaskClassifier:
    def classify(self, text: str) -> TaskType:
        normalized = text.lower()
        for task_type, keywords in KEYWORDS:
            if any(keyword in normalized for keyword in keywords):
                return task_type
        return TaskType.SIMPLE_QUESTION

