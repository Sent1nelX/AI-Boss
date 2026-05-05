class AIBossError(Exception):
    """Базовая ошибка AI-Boss."""


class ConfigError(AIBossError):
    """Ошибка чтения или проверки конфигурации."""


class GitGuardError(AIBossError):
    """Ошибка проверки git-проекта."""


class WorkerUnavailableError(AIBossError):
    """Нужный AI-агент недоступен."""

