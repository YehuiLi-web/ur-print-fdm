#!/usr/bin/env python
"""
命令行测试工具：复现主窗口中的两套运行/暂停逻辑
1) 生产模式：SFTP 上传 + Dashboard load/play/pause/stop（loader.urp）
2) 直连模式：RTDEControl sendCustomScript（对应当前 direct 模式）

用于定位 rtde_control 被替换后的行为与 stop 流程问题。
"""

from __future__ import annotations

import os
import socket
import sys
import time

from ur_print_fdm.config import config_manager
from ur_print_fdm.core.dashboard_driver import SimpleDashboardDriver
from ur_print_fdm.core.driver import URDriver
from ur_print_fdm.shared.net import is_valid_ip


IP_DEFAULT = "192.168.145.128"
SCRIPT_DEFAULT = r"D:\onedrive\桌面\Project\URscript\fiber.script"


def _print(msg: str) -> None:
    print(msg, flush=True)


def send_secondary_script(ip: str, script: str, *, port: int = 30002, timeout: float = 1.0) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        s.sendall(script.encode("utf-8"))
        return True
    except Exception as e:
        _print(f"[30002] send failed: {e}")
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def load_script_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def sftp_upload_dual(ip: str, local_path: str) -> bool:
    try:
        import paramiko  # type: ignore
    except Exception:
        _print("paramiko not installed; cannot SFTP upload.")
        return False

    remote_dir = str(
        config_manager.get("robot.sftp.remote_dir", "/home/ur/ursim-current/programs") or ""
    ).rstrip("/")
    remote_loader_name = str(
        config_manager.get("robot.dashboard.remote_loader_name", "remote_loader.script") or "remote_loader.script"
    )
    username = str(config_manager.get("robot.sftp.username", "ur") or "ur")
    password = str(config_manager.get("robot.sftp.password", "easybot") or "easybot")
    port = int(config_manager.get("robot.sftp.port", 22) or 22)

    remote_original = f"{remote_dir}/{os.path.basename(local_path)}"
    remote_loader = f"{remote_dir}/{remote_loader_name}"

    _print(f"[SFTP] {local_path} -> {remote_original}")
    _print(f"[SFTP] {local_path} -> {remote_loader} (loader)")

    try:
        transport = paramiko.Transport((ip, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.put(local_path, remote_original)
        sftp.put(local_path, remote_loader)
        sftp.close()
        transport.close()
        return True
    except Exception as e:
        _print(f"[SFTP] upload failed: {e}")
        return False


def main() -> int:
    ip = IP_DEFAULT
    if not is_valid_ip(ip):
        _print(f"IP 地址无效: {ip}")
        return 1

    driver = URDriver()
    db = SimpleDashboardDriver()
    db.set_ip(ip)

    loader_urp_path = str(
        config_manager.get("robot.dashboard.loader_urp_path", "/home/ur/ursim-current/programs/loader.urp")
        or "/home/ur/ursim-current/programs/loader.urp"
    )

    mode = "production"
    last_script_path: str | None = SCRIPT_DEFAULT

    def show_status() -> None:
        _print(f"当前模式: {mode}")
        _print(f"驱动连接: {driver.is_connected()}  只读: {driver.is_read_only()}")
        try:
            rc = driver.rc
            rr = driver.rr
            dbi = driver.db
            _print(f"rc: {'是' if rc else '否'}  rr: {'是' if rr else '否'}  db: {'是' if dbi else '否'}")
        except Exception:
            pass
        _print(f"当前加载程序: {driver.get_loaded_program() or '-'}")
        _print(f"Dashboard programState: {db.program_state()}")
        _print(f"Dashboard running: {db.running()}")

    def menu() -> None:
        _print("")
        _print("=== 运行模式测试 ===")
        _print("1) 切换模式（production / direct）")
        _print("2) 连接驱动")
        _print("3) 断开驱动")
        _print("4) 设置脚本路径（用于发送/上传）")
        _print("5) 生产模式：SFTP 双份上传")
        _print("6) 生产模式：Dashboard 加载 loader.urp")
        _print("7) 生产模式：Dashboard play")
        _print("8) 生产模式：Dashboard pause")
        _print("9) 生产模式：Dashboard stop")
        _print("10) 直连模式：RTDEControl 发送脚本（sendCustomScript）")
        _print("11) 直连模式：30002 发送脚本")
        _print("12) 停止（driver.stop，模拟工具栏）")
        _print("13) 重连 RTDEControl（driver.reconnect_control_interface）")
        _print("14) stopJ 探测（若 rtde_control 被替换可能失败）")
        _print("15) 查看状态")
        _print("q) 退出")

    while True:
        menu()
        choice = input("Select: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            break

        if choice == "1":
            mode_in = input("模式 [production/direct]: ").strip().lower()
            if mode_in in ("production", "direct"):
                mode = mode_in
            else:
                _print("模式无效。")
            continue

        if choice == "2":
            ok = driver.connect(ip)
            _print(f"连接结果: {ok}")
            continue

        if choice == "3":
            driver.disconnect()
            _print("已断开")
            continue

        if choice == "4":
            p = input(f"脚本路径 [{last_script_path or ''}]: ").strip()
            if p:
                last_script_path = p
            _print(f"脚本: {last_script_path}")
            continue

        if choice == "5":
            if not last_script_path:
                _print("请先设置脚本路径。")
                continue
            if not os.path.isfile(last_script_path):
                _print("脚本文件不存在。")
                continue
            _print("开始上传...")
            _print("上传成功" if sftp_upload_dual(ip, last_script_path) else "上传失败")
            continue

        if choice == "6":
            resp = db.load_program(loader_urp_path)
            _print(f"load: {resp}")
            continue

        if choice == "7":
            resp = db.play()
            _print(f"play: {resp}")
            continue

        if choice == "8":
            resp = db.pause()
            _print(f"pause: {resp}")
            continue

        if choice == "9":
            resp = db.stop()
            _print(f"stop: {resp}")
            continue

        if choice == "10":
            if not last_script_path:
                _print("请先设置脚本路径。")
                continue
            if not os.path.isfile(last_script_path):
                _print("脚本文件不存在。")
                continue
            script_text = load_script_text(last_script_path)
            ok = driver.send_script(script_text)
            _print(f"sendCustomScript: {ok}")
            continue

        if choice == "11":
            if not last_script_path:
                _print("请先设置脚本路径。")
                continue
            if not os.path.isfile(last_script_path):
                _print("脚本文件不存在。")
                continue
            script_text = load_script_text(last_script_path)
            ok = send_secondary_script(ip, script_text)
            _print(f"30002 发送: {ok}")
            continue

        if choice == "12":
            ok = driver.stop()
            _print(f"driver.stop: {ok}")
            continue

        if choice == "13":
            ok = driver.reconnect_control_interface()
            _print(f"重连控制接口: {ok}")
            continue

        if choice == "14":
            try:
                ok = driver.stop_j(1.0)
                _print(f"stopJ 探测: {ok}")
            except Exception as e:
                _print(f"stopJ 探测异常: {e}")
            continue

        if choice == "15":
            show_status()
            continue

        _print("未知选项。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
