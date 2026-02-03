import logging

from ur_print_fdm.config.defaults import DEFAULTS
from ur_print_fdm.config.manager import ConfigManager
from ur_print_fdm.shared.logging_context import trace_context
from ur_print_fdm.shared.logging_setup import setup_file_logging


def test_setup_file_logging_writes_session_and_trace_ids(tmp_path):
    cm = ConfigManager(config_path=tmp_path / "config.json", defaults=DEFAULTS)
    cm.set("logging.level", "INFO")

    setup = setup_file_logging(cm, override_log_dir=tmp_path, reconfigure=True)
    try:
        with trace_context("trace_test"):
            logging.getLogger("ur_print_fdm.tests").info("hello")

        # Flush to disk
        root = logging.getLogger()
        for h in root.handlers:
            if getattr(h, "baseFilename", None):
                h.flush()

        text = (tmp_path / "ur_print_fdm.log").read_text(encoding="utf-8", errors="replace")
        assert f"sid={setup.session_id}" in text
        assert "tid=trace_test" in text
        assert "hello" in text
    finally:
        # Keep global logging clean for other tests.
        root = logging.getLogger()
        for h in list(root.handlers):
            if getattr(h, "name", None) == "ur_print_fdm_file":
                root.removeHandler(h)
                h.close()


def test_setup_file_logging_reconfigure_preserves_session_id(tmp_path):
    cm = ConfigManager(config_path=tmp_path / "config.json", defaults=DEFAULTS)

    root = logging.getLogger()
    try:
        first = setup_file_logging(cm, override_log_dir=tmp_path, reconfigure=True)
        second = setup_file_logging(cm, override_log_dir=tmp_path, reconfigure=True)
        assert second.session_id == first.session_id
    finally:
        for h in list(root.handlers):
            if getattr(h, "name", None) == "ur_print_fdm_file":
                root.removeHandler(h)
                h.close()
