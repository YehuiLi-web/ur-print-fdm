from __future__ import annotations

from dataclasses import dataclass
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from ur_print_fdm.paths import logs_dir
from ur_print_fdm.shared.logging_context import ContextFilter, get_session_id, new_session_id, set_session_id

_FILE_HANDLER_NAME = "ur_print_fdm_file"


@dataclass(frozen=True)
class LoggingSetupResult:
    session_id: str
    log_dir: Path
    base_log_path: Path


def _level_from_name(name: str, *, default: int = logging.INFO) -> int:
    if not name:
        return default
    level = getattr(logging, str(name).upper(), None)
    return int(level) if isinstance(level, int) else default


def _resolve_log_dir(config_manager, *, override: Path | None = None) -> Path:
    if override is not None:
        override.mkdir(parents=True, exist_ok=True)
        return override

    cfg = config_manager.get("logging.dir", "")
    if cfg and isinstance(cfg, str):
        p = Path(cfg).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    return logs_dir()


def setup_file_logging(config_manager, *, override_log_dir: Path | None = None, reconfigure: bool = True) -> LoggingSetupResult:
    """
    Configure persisted file logging for the whole application.

    This is intended to be called once at startup (before creating the UI).
    """

    session_id = get_session_id()
    if session_id == "-":
        session_id = new_session_id()
        set_session_id(session_id)

    log_dir = _resolve_log_dir(config_manager, override=override_log_dir)
    base_log_path = log_dir / "ur_print_fdm.log"

    level_name = config_manager.get("logging.level", "INFO")
    retention_days = int(config_manager.get("logging.retention_days", 14) or 14)
    retention_days = max(1, min(retention_days, 365))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    if reconfigure:
        for h in list(root.handlers):
            if getattr(h, "name", None) == _FILE_HANDLER_NAME:
                root.removeHandler(h)
                try:
                    h.close()
                except Exception:
                    pass

    handler = TimedRotatingFileHandler(
        filename=str(base_log_path),
        when="midnight",
        interval=1,
        backupCount=retention_days,
        encoding="utf-8",
        utc=False,
    )
    handler.name = _FILE_HANDLER_NAME
    handler.suffix = "%Y-%m-%d"
    handler.setLevel(_level_from_name(str(level_name), default=logging.INFO))
    handler.addFilter(ContextFilter())

    fmt = (
        "%(asctime)s.%(msecs)03d | %(levelname)s | sid=%(session_id)s tid=%(trace_id)s | "
        "%(name)s | %(threadName)s | %(message)s (%(filename)s:%(lineno)d)"
    )
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S"))

    root.addHandler(handler)
    return LoggingSetupResult(session_id=session_id, log_dir=log_dir, base_log_path=base_log_path)
