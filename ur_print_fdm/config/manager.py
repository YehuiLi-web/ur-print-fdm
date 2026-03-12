from __future__ import annotations

import copy
import json
import threading
from pathlib import Path
from typing import Any, Optional, Union

from ur_print_fdm.config.defaults import DEFAULTS
from ur_print_fdm.config.robot_targets import (
    ensure_robot_target_config,
    sync_active_robot_target_to_runtime_config,
    sync_runtime_robot_config_to_active_target,
)
from ur_print_fdm.paths import ensure_app_data_dir


def default_config_path() -> Path:
    return ensure_app_data_dir() / "config.json"


def _has_explicit_robot_targets(data: dict[str, Any]) -> bool:
    robot = data.get("robot")
    if not isinstance(robot, dict):
        return False
    targets = robot.get("targets")
    return isinstance(targets, dict) and bool(targets)


class ConfigManager:
    """
    Thread-safe configuration manager with dot-notation access and JSON persistence.
    Keeps compatibility with legacy callers via load_config/save_config naming.
    """

    def __init__(
        self,
        config_file: Optional[Union[str, Path]] = None,
        *,
        config_path: Optional[Union[str, Path]] = None,
        defaults: Optional[dict] = None,
    ):
        self._lock = threading.RLock()
        if config_path is not None and config_file is not None:
            raise TypeError("Pass only one of config_file or config_path")
        effective_path = config_path if config_path is not None else config_file
        self.config_file = Path(effective_path) if effective_path else default_config_path()
        self.default_config: dict[str, Any] = copy.deepcopy(defaults) if defaults else copy.deepcopy(DEFAULTS)
        self.config: dict[str, Any] = copy.deepcopy(self.default_config)
        self.load_config()

    def load_config(self) -> dict[str, Any]:
        if not self.config_file.exists():
            self.config = copy.deepcopy(self.default_config)
            ensure_robot_target_config(self.config)
            return self.config

        with self._lock:
            try:
                loaded = json.loads(self.config_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.config = copy.deepcopy(self.default_config)
                return self.config

            self.config = copy.deepcopy(self.default_config)
            loaded_data = loaded if isinstance(loaded, dict) else {}
            self._recursive_update(self.config, loaded_data)
            if not _has_explicit_robot_targets(loaded_data):
                robot = self.config.get("robot")
                if isinstance(robot, dict):
                    robot.pop("targets", None)
            ensure_robot_target_config(self.config)
            return self.config

    def save_config(self) -> bool:
        with self._lock:
            try:
                ensure_robot_target_config(self.config, sync_runtime_from_active=False)
                sync_runtime_robot_config_to_active_target(self.config)
                sync_active_robot_target_to_runtime_config(self.config)
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                payload = json.dumps(self.config, indent=2, ensure_ascii=False)

                # Atomic-ish write: use a deterministic temp file in the same directory, then replace.
                #
                # Using `NamedTemporaryFile` can hang on some restricted filesystems/sandboxes where file
                # creation is blocked. A fixed temp path fails fast with PermissionError when not writable.
                tmp_path = self.config_file.parent / f".{self.config_file.name}.tmp"
                tmp_path.write_text(payload, encoding="utf-8")
                tmp_path.replace(self.config_file)
                return True
            except OSError:
                return False

    def save(self) -> bool:
        return self.save_config()

    def snapshot(self) -> dict[str, Any]:
        """Return a deep-copied snapshot of the current config dict."""
        with self._lock:
            snap = copy.deepcopy(self.config)
        ensure_robot_target_config(snap, sync_runtime_from_active=False)
        sync_runtime_robot_config_to_active_target(snap)
        sync_active_robot_target_to_runtime_config(snap)
        return snap

    def apply_dict(self, data: dict[str, Any]) -> None:
        """
        Replace current config with `defaults + data` (deep-merged).

        This is useful for Preferences dialogs that edit a working copy and then
        apply changes in one shot.
        """
        with self._lock:
            self.config = copy.deepcopy(self.default_config)
            payload = data if isinstance(data, dict) else {}
            self._recursive_update(self.config, payload)
            if not _has_explicit_robot_targets(payload):
                robot = self.config.get("robot")
                if isinstance(robot, dict):
                    robot.pop("targets", None)
            ensure_robot_target_config(self.config, sync_runtime_from_active=False)
            sync_runtime_robot_config_to_active_target(self.config)
            sync_active_robot_target_to_runtime_config(self.config)

    def get(self, key_path: str, default: Any = None) -> Any:
        with self._lock:
            keys = key_path.split(".")
            current: Any = self.config
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
            return current

    def set(self, key_path: str, value: Any) -> None:
        with self._lock:
            keys = key_path.split(".")
            current: dict[str, Any] = self.config
            for key in keys[:-1]:
                if key not in current or not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = copy.deepcopy(value)

    def _merge_config(self, new_data: dict[str, Any]) -> None:
        with self._lock:
            self._recursive_update(self.config, new_data)

    @staticmethod
    def _recursive_update(base: dict[str, Any], update: dict[str, Any]) -> None:
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigManager._recursive_update(base[key], value)
            else:
                base[key] = copy.deepcopy(value)


config_manager = ConfigManager()
