import logging

from ur_print_fdm.config.defaults import DEFAULTS
from ur_print_fdm.config.manager import ConfigManager
from ur_print_fdm.ui.services.qt_log_handler import install_qt_log_handler


class _EmitterStub:
    def __init__(self):
        self.emitted: list[tuple[str, str]] = []

        class _Signal:
            def __init__(self, outer):
                self._outer = outer

            def emit(self, ui_level: str, message: str) -> None:
                self._outer.emitted.append((ui_level, message))

        self.message = _Signal(self)


def test_install_qt_log_handler_updates_policy(tmp_path):
    cm = ConfigManager(config_path=tmp_path / "config.json", defaults=DEFAULTS)
    emitter = _EmitterStub()

    root = logging.getLogger()
    try:
        cm.set("logging.ui_level", "INFO")
        cm.set("logging.ui_show_third_party", False)
        handler = install_qt_log_handler(cm, emitter)  # type: ignore[arg-type]

        record = logging.LogRecord(
            name="third.party",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        handler.emit(record)
        assert emitter.emitted == []

        cm.set("logging.ui_show_third_party", True)
        handler2 = install_qt_log_handler(cm, emitter)  # type: ignore[arg-type]
        assert handler2 is handler

        handler.emit(record)
        assert emitter.emitted, "Expected third-party log to be forwarded after policy update"
    finally:
        for h in list(root.handlers):
            if getattr(h, "name", None) == "ur_print_fdm_ui":
                root.removeHandler(h)
                h.close()
