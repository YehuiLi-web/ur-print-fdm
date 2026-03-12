from __future__ import annotations

import copy
from typing import Any


DEFAULT_ACTIVE_ROBOT_TARGET_ID = "virtual"

DEFAULT_ROBOT_TARGETS: dict[str, dict[str, Any]] = {
    "virtual": {
        "label": "虚拟机械臂 (URSim)",
        "ip_addresses": ["192.168.1.106"],
        "default_ip": "192.168.1.106",
        "sftp": {
            "port": 22,
            "username": "ur",
            "password": "easybot",
            "remote_dir": "/home/ur/ursim-current/programs",
        },
        "dashboard": {
            "loader_urp_path": "/home/ur/ursim-current/programs/loader.urp",
            "remote_loader_name": "remote_loader.script",
        },
    },
    "real": {
        "label": "真实机械臂",
        "ip_addresses": ["192.168.137.120", "192.168.137.100"],
        "default_ip": "192.168.137.120",
        "sftp": {
            "port": 22,
            "username": "root",
            "password": "easybot",
            "remote_dir": "/programs",
        },
        "dashboard": {
            "loader_urp_path": "/programs/loader.urp",
            "remote_loader_name": "remote_loader.script",
        },
    },
}


def robot_target_defaults() -> dict[str, Any]:
    return {
        "active_id": DEFAULT_ACTIVE_ROBOT_TARGET_ID,
        "items": copy.deepcopy(DEFAULT_ROBOT_TARGETS),
    }


def _ensure_dict(base: dict[str, Any], key: str) -> dict[str, Any]:
    value = base.get(key)
    if not isinstance(value, dict):
        value = {}
        base[key] = value
    return value


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> None:
    for key, value in update.items():
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)


def _normalize_ip_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif value:
        raw_items = [value]
    else:
        raw_items = []

    result: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = str(item or "").strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _normalize_target_item(target_id: str, item: dict[str, Any]) -> None:
    merged = copy.deepcopy(DEFAULT_ROBOT_TARGETS.get(target_id, {}))
    _deep_merge(merged, item)
    item.clear()
    item.update(merged)

    item["ip_addresses"] = _normalize_ip_list(item.get("ip_addresses", []))

    default_ip = str(item.get("default_ip", "") or "").strip()
    if not default_ip and item["ip_addresses"]:
        default_ip = item["ip_addresses"][0]
    item["default_ip"] = default_ip

    item["label"] = str(item.get("label", target_id) or target_id).strip() or target_id


def _infer_active_target_id(robot: dict[str, Any]) -> str:
    sftp = robot.get("sftp", {})
    dashboard = robot.get("dashboard", {})

    username = str(sftp.get("username", "") or "").strip().lower() if isinstance(sftp, dict) else ""
    remote_dir = str(sftp.get("remote_dir", "") or "").strip() if isinstance(sftp, dict) else ""
    loader_urp_path = (
        str(dashboard.get("loader_urp_path", "") or "").strip() if isinstance(dashboard, dict) else ""
    )

    if username == "root":
        return "real"
    if remote_dir.rstrip("/") == "/programs":
        return "real"
    if loader_urp_path.startswith("/programs/"):
        return "real"
    return DEFAULT_ACTIVE_ROBOT_TARGET_ID


def _ensure_robot_target_container(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], bool]:
    robot = _ensure_dict(config, "robot")

    existing_targets = robot.get("targets")
    had_target_items = False
    if isinstance(existing_targets, dict):
        existing_items = existing_targets.get("items")
        had_target_items = isinstance(existing_items, dict) and bool(existing_items)

    targets = _ensure_dict(robot, "targets")
    items = _ensure_dict(targets, "items")

    for target_id in DEFAULT_ROBOT_TARGETS:
        item = items.get(target_id)
        if not isinstance(item, dict):
            item = {}
            items[target_id] = item
        _normalize_target_item(target_id, item)

    active_id = str(targets.get("active_id", "") or "").strip()
    if active_id not in items:
        active_id = _infer_active_target_id(robot)
    if active_id not in items:
        active_id = DEFAULT_ACTIVE_ROBOT_TARGET_ID
    targets["active_id"] = active_id

    return robot, targets, items, had_target_items


def get_robot_target_items(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ensure_robot_target_config(config)
    robot = _ensure_dict(config, "robot")
    targets = _ensure_dict(robot, "targets")
    items = _ensure_dict(targets, "items")
    return items


def get_active_robot_target_id(config: dict[str, Any]) -> str:
    ensure_robot_target_config(config)
    robot = _ensure_dict(config, "robot")
    targets = _ensure_dict(robot, "targets")
    active_id = str(targets.get("active_id", DEFAULT_ACTIVE_ROBOT_TARGET_ID) or "").strip()
    items = _ensure_dict(targets, "items")
    if active_id not in items:
        active_id = DEFAULT_ACTIVE_ROBOT_TARGET_ID if DEFAULT_ACTIVE_ROBOT_TARGET_ID in items else next(iter(items), "")
        targets["active_id"] = active_id
    return active_id


def sync_runtime_robot_config_to_active_target(config: dict[str, Any]) -> None:
    robot, targets, items, _had_target_items = _ensure_robot_target_container(config)
    active_id = str(targets.get("active_id", DEFAULT_ACTIVE_ROBOT_TARGET_ID) or "").strip()
    if active_id not in items:
        return

    target = items[active_id]

    target["ip_addresses"] = _normalize_ip_list(robot.get("ip_addresses", target.get("ip_addresses", [])))

    default_ip = str(robot.get("default_ip", target.get("default_ip", "")) or "").strip()
    if not default_ip and target["ip_addresses"]:
        default_ip = target["ip_addresses"][0]
    target["default_ip"] = default_ip

    sftp = robot.get("sftp", {})
    if isinstance(sftp, dict):
        merged_sftp = copy.deepcopy(target.get("sftp", {}))
        _deep_merge(merged_sftp, sftp)
        target["sftp"] = merged_sftp

    dashboard = robot.get("dashboard", {})
    if isinstance(dashboard, dict):
        merged_dashboard = copy.deepcopy(target.get("dashboard", {}))
        _deep_merge(merged_dashboard, dashboard)
        target["dashboard"] = merged_dashboard

    _normalize_target_item(active_id, target)


def sync_active_robot_target_to_runtime_config(config: dict[str, Any]) -> None:
    robot, targets, items, _had_target_items = _ensure_robot_target_container(config)
    active_id = str(targets.get("active_id", DEFAULT_ACTIVE_ROBOT_TARGET_ID) or "").strip()
    if active_id not in items:
        return

    target = items[active_id]

    robot["ip_addresses"] = copy.deepcopy(target.get("ip_addresses", []))
    robot["default_ip"] = copy.deepcopy(target.get("default_ip", ""))
    robot["sftp"] = copy.deepcopy(target.get("sftp", {}))
    robot["dashboard"] = copy.deepcopy(target.get("dashboard", {}))


def set_active_robot_target(
    config: dict[str, Any],
    target_id: str,
    *,
    persist_runtime: bool = True,
) -> bool:
    _robot, targets, items, _had_target_items = _ensure_robot_target_container(config)
    if target_id not in items:
        return False

    if persist_runtime:
        sync_runtime_robot_config_to_active_target(config)

    targets["active_id"] = target_id
    sync_active_robot_target_to_runtime_config(config)
    return True


def ensure_robot_target_config(config: dict[str, Any], *, sync_runtime_from_active: bool = True) -> None:
    _robot, _targets, _items, had_target_items = _ensure_robot_target_container(config)
    if not had_target_items:
        sync_runtime_robot_config_to_active_target(config)
    if sync_runtime_from_active:
        sync_active_robot_target_to_runtime_config(config)
