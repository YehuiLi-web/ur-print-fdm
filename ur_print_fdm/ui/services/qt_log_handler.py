from __future__ import annotations

import logging
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal

from ur_print_fdm.shared.logging_context import ContextFilter

class QtLogEmitter(QObject):
    message = pyqtSignal(str, str)  # (ui_level, message)


@dataclass(frozen=True)
class UiLogPolicy:
    min_level: int
    show_third_party: bool


def _level_from_name(name: str, *, default: int = logging.INFO) -> int:
    if not name:
        return default
    level = getattr(logging, str(name).upper(), None)
    return int(level) if isinstance(level, int) else default


class QtLogHandler(logging.Handler):
    """
    Forward Python logging records to a Qt signal, safe across threads.
    """

    def __init__(self, emitter: QtLogEmitter, policy: UiLogPolicy):
        super().__init__(level=logging.DEBUG)
        self._emitter = emitter
        self._policy = policy

    def update_policy(self, policy: UiLogPolicy) -> None:
        self._policy = policy

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.levelno < self._policy.min_level:
                return

            if not self._policy.show_third_party and not record.name.startswith("ur_print_fdm"):
                return

            trace_id = getattr(record, "trace_id", "-")
            ui_level = getattr(record, "ui_level", None) or record.levelname
            ui_level = str(ui_level).upper()
            if ui_level == "WARNING":
                ui_level = "WARN"

            msg = record.getMessage()
            if trace_id and trace_id != "-":
                msg = f"[{trace_id}] {msg}"

            self._emitter.message.emit(ui_level, msg)
        except Exception:
            self.handleError(record)


def install_qt_log_handler(config_manager, emitter: QtLogEmitter) -> QtLogHandler:
    """
    Install a single UI log handler on the root logger (idempotent).
    """

    min_level = _level_from_name(config_manager.get("logging.ui_level", "INFO"), default=logging.INFO)
    show_third_party = bool(config_manager.get("logging.ui_show_third_party", False))

    policy = UiLogPolicy(min_level=min_level, show_third_party=show_third_party)
    handler = QtLogHandler(emitter, policy=policy)
    handler.name = "ur_print_fdm_ui"
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    for h in root.handlers:
        if getattr(h, "name", None) == handler.name:
            if isinstance(h, QtLogHandler):
                h.update_policy(policy)
            return h  # type: ignore[return-value]

    root.addHandler(handler)
    return handler
