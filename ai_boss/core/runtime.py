from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar


LogSink = Callable[[str, str], None]

_log_sink: ContextVar[LogSink | None] = ContextVar("ai_boss_log_sink", default=None)
_cancel_event: ContextVar[threading.Event | None] = ContextVar("ai_boss_cancel_event", default=None)


@contextmanager
def runtime_context(log_sink: LogSink | None = None, cancel_event: threading.Event | None = None) -> Iterator[None]:
    log_token = _log_sink.set(log_sink)
    cancel_token = _cancel_event.set(cancel_event)
    try:
        yield
    finally:
        _log_sink.reset(log_token)
        _cancel_event.reset(cancel_token)


def emit_runtime_log(source: str, message: str) -> None:
    sink = _log_sink.get()
    if sink is not None and message:
        sink(source, message)


def cancel_requested() -> bool:
    event = _cancel_event.get()
    return bool(event and event.is_set())


def runtime_hooks_enabled() -> bool:
    return _log_sink.get() is not None or _cancel_event.get() is not None
