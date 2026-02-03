from __future__ import annotations

from pathlib import Path


def app_data_dir() -> Path:
    """
    User-writable app data directory.

    Using the home directory keeps behavior consistent across platforms without
    adding OS-specific dependencies.
    """

    return Path.home() / ".ur_print_fdm"


def ensure_app_data_dir() -> Path:
    path = app_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def editor_session_path() -> Path:
    return ensure_app_data_dir() / "editor_session.json"


def logs_dir() -> Path:
    """
    Directory for persisted log files.

    Defaults to a user-writable location under the app data directory.
    """

    path = ensure_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
