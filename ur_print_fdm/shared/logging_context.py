from __future__ import annotations

import contextlib
import contextvars
import uuid
import logging

_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("ur_print_fdm_trace_id", default="-")
_session_id: str | None = None


def new_session_id() -> str:
    # Short but unique enough for log correlation in a single workstation.
    return uuid.uuid4().hex[:12]


def set_session_id(session_id: str) -> None:
    global _session_id
    _session_id = str(session_id)


def get_session_id() -> str:
    return _session_id or "-"


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]


def set_trace_id(trace_id: str | None) -> contextvars.Token[str]:
    return _trace_id_var.set(str(trace_id) if trace_id else "-")


def get_trace_id() -> str:
    return _trace_id_var.get()


def reset_trace_id(token: contextvars.Token[str]) -> None:
    _trace_id_var.reset(token)


@contextlib.contextmanager
def trace_context(trace_id: str | None):
    token = set_trace_id(trace_id)
    try:
        yield
    finally:
        reset_trace_id(token)


class ContextFilter(logging.Filter):
    """
    Inject session/trace context fields onto every LogRecord.

    This allows formatters to use %(session_id)s and %(trace_id)s safely.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = get_session_id()
        record.trace_id = get_trace_id()
        return True

