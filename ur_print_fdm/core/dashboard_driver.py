import socket
import logging

from ur_print_fdm.constants import DASHBOARD_PORT

# 状态查询命令（高频调用，使用 DEBUG 级别日志）
_QUIET_COMMANDS = {"running", "programstate", "programState"}


class SimpleDashboardDriver:
    """
    基于 test_sftp_dashboard.py 的简易 Dashboard 控制器
    不涉及 IO 接口，仅负责 29999 端口的字符串指令发送
    """
    def __init__(self):
        self.ip = None
        self.port = DASHBOARD_PORT
        self.sock = None
        self.timeout = 2.0

    def set_ip(self, ip):
        self.ip = ip

    def connect(self):
        if not self.ip:
            logging.error("[SimpleDB] IP 未设置")
            return False

        try:
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.ip, self.port))
            # 接收欢迎消息
            welcome = self.sock.recv(1024).decode('utf-8')
            logging.info(f"[SimpleDB] 已连接: {welcome.strip()}")
            return True
        except Exception as e:
            logging.error(f"[SimpleDB] 连接失败: {e}")
            self.sock = None
            return False

    def is_connected(self):
        return self.sock is not None

    def send(self, command):
        # 自动重连机制
        if not self.sock:
            if not self.connect():
                return "Not connected"

        try:
            cmd_str = command.strip() + "\n"
            self.sock.sendall(cmd_str.encode('utf-8'))
            response = self.sock.recv(1024).decode('utf-8').strip()
            # 状态查询命令使用 DEBUG 级别，避免刷屏
            if command.strip().lower() in _QUIET_COMMANDS:
                logging.debug(f"[SimpleDB] {command} -> {response}")
            else:
                logging.info(f"[SimpleDB] 指令: {command} -> 响应: {response}")
            return response
        except BrokenPipeError:
            logging.warning("[SimpleDB] 连接断开，尝试重连...")
            if self.connect():
                return self.send(command) # 重试一次
            return "Error: BrokenPipe"
        except Exception as e:
            logging.error(f"[SimpleDB] 通信错误: {e}")
            self.sock = None # 标记为断开
            return f"Error: {e}"

    def load_program(self, remote_path):
        """加载机器人端的脚本文件"""
        return self.send(f"load {remote_path}")

    def play(self):
        """开始/继续运行"""
        return self.send("play")

    def pause(self):
        """暂停"""
        return self.send("pause")

    def stop(self):
        """停止"""
        return self.send("stop")

    def running(self):
        """Query whether a program is currently running (Dashboard: `running`)."""
        resp = self.send("running")
        low = str(resp or "").strip().lower()
        if "true" in low:
            return True
        if "false" in low:
            return False
        return None

    def program_state(self):
        """Query program execution state (Dashboard: `programState`)."""
        resp = self.send("programState")
        up = str(resp or "").strip().upper()
        for key in ("STOPPED", "PLAYING", "PAUSED"):
            if key in up:
                return key
        return None

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
