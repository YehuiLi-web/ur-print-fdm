"""
测试直连模式：纯 30002 端口发送脚本 + 停止

完全不使用 RTDEControlInterface.sendCustomScript()，
只使用 30002 端口发送脚本，避免阻塞问题。
"""

import socket
import time
from typing import Optional

# 尝试导入 ur_rtde 用于状态监控（可选）
try:
    from rtde_receive import RTDEReceiveInterface
    HAS_RTDE = True
except ImportError:
    HAS_RTDE = False
    print("警告: ur_rtde 未安装，无法监控机器人状态")


class Direct30002Controller:
    """纯 30002 端口控制器"""

    SCRIPT_PORT = 30002

    def __init__(self, ip: str):
        self.ip = ip
        self.rr: Optional[RTDEReceiveInterface] = None

    def connect_monitor(self) -> bool:
        """连接状态监控接口（可选）"""
        if not HAS_RTDE:
            print("跳过状态监控（ur_rtde 未安装）")
            return False
        try:
            print(f"连接状态监控接口 {self.ip}...")
            self.rr = RTDEReceiveInterface(self.ip)
            if self.rr.isConnected():
                print("状态监控接口连接成功")
                return True
            else:
                print("状态监控接口连接失败")
                return False
        except Exception as e:
            print(f"状态监控接口连接异常: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.rr:
            try:
                self.rr.disconnect()
            except:
                pass
            self.rr = None

    def send_script(self, script: str, timeout: float = 2.0) -> bool:
        """通过 30002 端口发送脚本（非阻塞，立即返回）"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((self.ip, self.SCRIPT_PORT))
            s.sendall(script.encode("utf-8"))
            s.close()
            return True
        except Exception as e:
            print(f"发送脚本失败: {e}")
            return False

    def get_runtime_state(self) -> Optional[int]:
        """获取运行时状态"""
        if not self.rr:
            return None
        try:
            return self.rr.getRuntimeState()
        except:
            return None

    def get_tcp_pose(self) -> Optional[list]:
        """获取 TCP 位置"""
        if not self.rr:
            return None
        try:
            return self.rr.getActualTCPPose()
        except:
            return None

    def is_program_running(self) -> bool:
        """检查程序是否在运行"""
        state = self.get_runtime_state()
        return state in (2, 3, 4, 5)

    def run_test_script(self) -> bool:
        """发送测试脚本：简单的移动脚本"""
        current_pose = self.get_tcp_pose()
        if current_pose:
            print(f"当前 TCP 位置: [{', '.join(f'{v:.4f}' for v in current_pose)}]")

        script = '''def test_motion():
    start_pose = get_actual_tcp_pose()

    i = 0
    while i < 2:
        textmsg("循环 ", i + 1, " / 5")
        target_up = pose_trans(start_pose, p[0, 0, 0.05, 0, 0, 0])
        movel(target_up, a=0.3, v=0.1)
        movel(start_pose, a=0.3, v=0.1)
        i = i + 1
    end

    textmsg("测试脚本执行完成")
end

test_motion()
'''
        print("发送测试脚本...")
        result = self.send_script(script)
        if result:
            print("脚本已发送（非阻塞，立即返回）")
        return result

    def stop(self) -> bool:
        """停止脚本执行"""
        script = '''sec emergency_stop():
    stopj(2.0)
end
'''
        print("发送停止指令...")
        result = self.send_script(script)
        if result:
            print("停止指令已发送")
        return result

    def print_status(self):
        """打印当前状态"""
        state = self.get_runtime_state()
        state_names = {
            0: "STOPPING",
            1: "STOPPED",
            2: "PLAYING",
            3: "PAUSING",
            4: "PAUSED",
            5: "RESUMING"
        }
        state_str = state_names.get(state, f"UNKNOWN({state})") if state is not None else "N/A"

        pose = self.get_tcp_pose()
        pose_str = f"[{', '.join(f'{v:.4f}' for v in pose)}]" if pose else "N/A"

        print(f"状态: {state_str}, TCP: {pose_str}")


def main():
    print("=" * 60)
    print("  直连模式测试 - 纯 30002 端口（运行 + 停止）")
    print("=" * 60)
    print()

    ip = input("请输入机器人 IP [192.168.145.128]: ").strip()
    if not ip:
        ip = "192.168.145.128"

    controller = Direct30002Controller(ip)
    controller.connect_monitor()

    print()
    print("=" * 60)
    print("  操作菜单")
    print("=" * 60)
    print("  1 - 运行测试脚本")
    print("  2 - 停止")
    print("  s - 查看状态")
    print("  q - 退出")
    print("=" * 60)
    print()

    try:
        while True:
            choice = input("请选择操作: ").strip().lower()

            if choice == "1":
                controller.run_test_script()
            elif choice == "2":
                controller.stop()
            elif choice == "s":
                controller.print_status()
            elif choice == "q":
                print("退出...")
                break
            else:
                print("无效选择")

            print()

    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        controller.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    main()
