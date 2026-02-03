# -*- coding: utf-8 -*-
"""
RTDE 行为测试脚本
================

用于测试 RTDE 控制接口在各种操作下的连接状态变化。

键盘操作：
- C: 连接机器人
- D: 断开连接
- S: 查看当前状态
- 1: 测试 - 发送简单移动脚本 (sendCustomScript)
- 2: 测试 - 发送 stopj 脚本
- 3: 测试 - 使用原生 moveJ 方法
- 4: 测试 - 使用原生 stopJ 方法
- 5: 测试 - Dashboard stop
- 6: 测试 - 长时间运动中监控连接
- 7: 测试 - 连续发送多个脚本
- 8: 测试 - 发送脚本后立即检查连接
- Q: 退出

作者: 测试脚本
"""

import time
import threading
import sys

# === 尝试导入 ur_rtde ===
try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
    from dashboard_client import DashboardClient
    print("[OK] ur_rtde 库导入成功")
except ImportError as e:
    print(f"[ERROR] 无法导入 ur_rtde: {e}")
    print("请安装: pip install ur_rtde")
    sys.exit(1)


class RTDETester:
    """RTDE 行为测试器"""
    
    def __init__(self, robot_ip: str):
        self.robot_ip = robot_ip
        self.rc = None  # RTDEControlInterface
        self.rr = None  # RTDEReceiveInterface
        self.db = None  # DashboardClient
        self.monitor_thread = None
        self.monitoring = False
        
    def log(self, msg: str):
        """带时间戳的日志"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")

    def _call_with_timeout(self, label: str, func, timeout: float = 30.0):
        """在后台线程调用函数，避免终端卡死"""
        result = [None]
        error = [None]

        def runner():
            try:
                result[0] = func()
            except Exception as e:
                error[0] = e

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            self.log(f"{label} 超时 ({timeout:.0f} 秒)，终端已恢复")
            self.log("提示: 后台线程仍在执行，建议先 stop/断开连接再继续测试")
            return None, "timeout"

        if error[0]:
            self.log(f"{label} 异常: {error[0]}")
            return None, "error"

        return result[0], "ok"
        
    def connect(self):
        """连接所有接口"""
        self.log(f"正在连接 {self.robot_ip} ...")
        self.log("提示: 如果卡住超过10秒，可能是旧连接未释放，请重启机器人或等待60秒")
        
        # 1. 连接 Receive 接口 (使用超时线程)
        try:
            self.log("  → 连接 RTDEReceiveInterface (超时10秒)...")
            
            result = [None]
            error = [None]
            
            def connect_rr():
                try:
                    result[0] = RTDEReceiveInterface(self.robot_ip)
                except Exception as e:
                    error[0] = e
            
            t = threading.Thread(target=connect_rr, daemon=True)
            t.start()
            t.join(timeout=10.0)
            
            if t.is_alive():
                self.log("  ✗ Receive 接口连接超时 (10秒)")
                self.log("    → 可能原因: 机器人不可达或旧连接未释放")
                return False
            
            if error[0]:
                self.log(f"  ✗ Receive 接口异常: {error[0]}")
                return False
                
            self.rr = result[0]
            if self.rr and self.rr.isConnected():
                self.log("  ✓ Receive 接口连接成功")
            else:
                self.log("  ✗ Receive 接口连接失败")
                return False
        except Exception as e:
            self.log(f"  ✗ Receive 接口异常: {e}")
            return False
            
        # 2. 连接 Dashboard
        try:
            self.log("  → 连接 DashboardClient...")
            self.db = DashboardClient(self.robot_ip)
            self.db.connect()
            if self.db.isConnected():
                self.log("  ✓ Dashboard 连接成功")
            else:
                self.log("  ✗ Dashboard 连接失败")
        except Exception as e:
            self.log(f"  ✗ Dashboard 异常: {e}")
            self.db = None
            
        # 3. 连接 Control 接口 (使用超时线程)
        try:
            self.log("  → 连接 RTDEControlInterface (超时10秒)...")
            self.log("    注意: Control 接口只允许1个连接！")
            
            result = [None]
            error = [None]
            
            def connect_rc():
                try:
                    result[0] = RTDEControlInterface(self.robot_ip, RTDEControlInterface.FLAG_UPLOAD_SCRIPT)
                except Exception as e:
                    error[0] = e
            
            t = threading.Thread(target=connect_rc, daemon=True)
            t.start()
            t.join(timeout=10.0)
            
            if t.is_alive():
                self.log("  ✗ Control 接口连接超时 (10秒)")
                self.log("    → 可能原因: 已有其他程序占用控制连接")
                self.log("    → 解决方法: 重启机器人 或 等待旧连接超时(约60秒)")
                return False
            
            if error[0]:
                self.log(f"  ✗ Control 接口异常: {error[0]}")
                return False
                
            self.rc = result[0]
            if self.rc and self.rc.isConnected():
                self.log("  ✓ Control 接口连接成功")
            else:
                self.log("  ✗ Control 接口连接失败")
                return False
        except Exception as e:
            self.log(f"  ✗ Control 接口异常: {e}")
            return False
            
        self.log("=== 所有接口连接完成 ===")
        return True
        
    def disconnect(self):
        """断开所有连接"""
        self.log("正在断开连接...")
        self.monitoring = False
        
        if self.rc:
            try:
                self.rc.disconnect()
                self.log("  ✓ Control 接口已断开")
            except Exception as e:
                self.log(f"  ✗ Control 断开异常: {e}")
            self.rc = None
            
        if self.rr:
            try:
                self.rr.disconnect()
                self.log("  ✓ Receive 接口已断开")
            except Exception as e:
                self.log(f"  ✗ Receive 断开异常: {e}")
            self.rr = None
            
        if self.db:
            try:
                self.db.disconnect()
                self.log("  ✓ Dashboard 已断开")
            except Exception as e:
                self.log(f"  ✗ Dashboard 断开异常: {e}")
            self.db = None
            
        self.log("=== 所有连接已断开 ===")
        
    def check_rtde_control_alive(self) -> tuple:
        """
        检测 rtde_control 后台脚本是否还在运行
        返回: (alive: bool, detail: str)
        
        检测方法:
        1. 检查 rc.isConnected() 
        2. 通过 RTDEReceiveInterface 获取 runtime_state
        3. 尝试执行一个无害的控制命令 (stopJ 微小值)
        """
        if not self.rc:
            return False, "rc 未创建"
        
        if not self.rc.isConnected():
            return False, "rc 连接已断开"
        
        # 方法1: 通过 RTDEReceiveInterface 检查 runtime state
        # runtime_state: 0=STOPPING, 1=STOPPED, 2=PLAYING, 3=PAUSING, 4=PAUSED, 5=RESUMING
        if self.rr and self.rr.isConnected():
            try:
                runtime_state = self.rr.getRuntimeState()
                # 如果 runtime_state 是 PLAYING (2)，说明有脚本在运行
                # 但这不能区分是 rtde_control 还是其他脚本
                state_names = {0: "STOPPING", 1: "STOPPED", 2: "PLAYING", 3: "PAUSING", 4: "PAUSED", 5: "RESUMING"}
                state_name = state_names.get(runtime_state, f"UNKNOWN({runtime_state})")
                
                if runtime_state == 2:  # PLAYING
                    # 有脚本在运行，可能是 rtde_control
                    pass
                elif runtime_state == 1:  # STOPPED
                    # 没有脚本在运行，rtde_control 肯定停止了
                    return False, f"runtime_state={state_name} (无脚本运行)"
            except Exception as e:
                self.log(f"  (getRuntimeState 异常: {e})")
        
        # 方法2: 尝试执行一个轻量级的控制命令
        # stopJ(0) 是无害的 - 如果已经停止就什么都不做
        # 如果 rtde_control 不在运行，这个调用会超时或返回 False
        try:
            # 使用超时包装，避免阻塞
            result = [None]
            error = [None]
            
            def try_stopj():
                try:
                    # stopJ(2.0) - 2.0 是减速度，数值大 = 停得快
                    # 如果机器人已经静止，这个调用几乎立即返回
                    result[0] = self.rc.stopJ(2.0)
                except Exception as e:
                    error[0] = e
            
            t = threading.Thread(target=try_stopj, daemon=True)
            t.start()
            t.join(timeout=2.0)  # 最多等 2 秒
            
            if t.is_alive():
                return False, "stopJ 超时 (rtde_control 可能无响应)"
            
            if error[0]:
                err_str = str(error[0]).lower()
                if "timeout" in err_str or "not running" in err_str:
                    return False, f"rtde_control 无响应: {error[0]}"
                return False, f"stopJ 异常: {error[0]}"
            
            if result[0] is True or result[0] is None:
                return True, "rtde_control 正常响应 (stopJ 成功)"
            else:
                return False, f"stopJ 返回 {result[0]} (rtde_control 可能已停止)"
                
        except Exception as e:
            return False, f"检测异常: {e}"

    def check_status(self, show_rtde_control: bool = True):
        """检查并显示当前连接状态"""
        self.log("--- 当前连接状态 ---")
        
        rc_status = "未创建"
        if self.rc:
            try:
                rc_status = "已连接" if self.rc.isConnected() else "已断开"
            except Exception as e:
                rc_status = f"检查异常: {e}"
        self.log(f"  Control (rc):   {rc_status}")
        
        # 检测 rtde_control 是否存活
        rtde_control_status = "未检测"
        if show_rtde_control and self.rc:
            alive, detail = self.check_rtde_control_alive()
            if alive:
                rtde_control_status = "✓ 存活"
            else:
                rtde_control_status = f"✗ 已停止 ({detail})"
        self.log(f"  rtde_control:   {rtde_control_status}")
        
        rr_status = "未创建"
        if self.rr:
            try:
                rr_status = "已连接" if self.rr.isConnected() else "已断开"
            except Exception as e:
                rr_status = f"检查异常: {e}"
        self.log(f"  Receive (rr):   {rr_status}")
        
        db_status = "未创建"
        if self.db:
            try:
                db_status = "已连接" if self.db.isConnected() else "已断开"
            except Exception as e:
                db_status = f"检查异常: {e}"
        self.log(f"  Dashboard (db): {db_status}")
        
        # 尝试获取机器人位置
        if self.rr and self.rr.isConnected():
            try:
                tcp = self.rr.getActualTCPPose()
                self.log(f"  TCP位置: [{tcp[0]:.4f}, {tcp[1]:.4f}, {tcp[2]:.4f}]")
            except Exception as e:
                self.log(f"  获取TCP位置失败: {e}")
                
        self.log("-------------------")
        return rc_status, rr_status, db_status
        
    # ===================== 测试方法 =====================
    
    def test_1_send_move_script(self):
        """测试1: 发送简单移动脚本"""
        self.log("=== 测试1: sendCustomScript 发送移动脚本 ===")
        
        if not self.rc or not self.rc.isConnected():
            self.log("Control 接口未连接，无法测试")
            return
            
        # 获取当前位置
        try:
            current_q = self.rr.getActualQ()
            self.log(f"当前关节角度: {[f'{q:.3f}' for q in current_q]}")
        except Exception as e:
            self.log(f"获取当前位置失败: {e}")
            return
            
        # 构建一个小幅度移动脚本
        target_q = list(current_q)
        target_q[0] += 0.05  # 第一关节移动约3度
        
        # 注意: def 需要显式调用，sec 是自动执行的 secondary 线程
        script = f"""
def test_move():
    movej([{','.join(str(q) for q in target_q)}], a=0.5, v=0.3)
end
test_move()
"""
        
        self.log("发送前状态:")
        self.check_status()
        
        self.log(f"发送脚本: movej 到目标位置...")
        result, status = self._call_with_timeout(
            "sendCustomScript",
            lambda: self.rc.sendCustomScript(script),
            timeout=30.0,
        )
        if status == "ok":
            self.log(f"sendCustomScript 返回: {result}")
            
        self.log("发送后立即检查状态:")
        self.check_status()
        
        # 等待一段时间后再检查
        self.log("等待 2 秒后再次检查...")
        time.sleep(2)
        self.check_status()
        
        self.log("等待 5 秒后再次检查...")
        time.sleep(3)
        self.check_status()
        
    def test_2_send_stopj_script(self):
        """测试2: 发送 stopj 脚本"""
        self.log("=== 测试2: sendCustomScript 发送 stopj ===")
        
        if not self.rc or not self.rc.isConnected():
            self.log("Control 接口未连接，无法测试")
            return
            
        # sec 定义后会自动执行 (secondary thread)
        # 但为了保险起见，我们也可以用 def + 调用
        script = """
def emergency_stop():
    stopj(2.0)
end
emergency_stop()
"""
        
        self.log("发送前状态:")
        self.check_status()
        
        self.log("发送 stopj 脚本...")
        result, status = self._call_with_timeout(
            "sendCustomScript",
            lambda: self.rc.sendCustomScript(script),
            timeout=30.0,
        )
        if status == "ok":
            self.log(f"sendCustomScript 返回: {result}")
            
        self.log("发送后立即检查状态:")
        self.check_status()
        
        time.sleep(1)
        self.log("1秒后状态:")
        self.check_status()
        
    def test_3_native_movej(self):
        """测试3: 使用原生 moveJ 方法"""
        self.log("=== 测试3: 原生 moveJ 方法 ===")
        
        if not self.rc or not self.rc.isConnected():
            self.log("Control 接口未连接，无法测试")
            return
            
        try:
            current_q = self.rr.getActualQ()
            target_q = list(current_q)
            target_q[0] += 0.05
            
            self.log("发送前状态:")
            self.check_status()
            
            self.log(f"调用 rc.moveJ()...")
            result, status = self._call_with_timeout(
                "moveJ",
                lambda: self.rc.moveJ(target_q, 0.5, 0.3, False),
                timeout=30.0,
            )
            if status == "ok":
                self.log(f"moveJ 返回: {result}")
            else:
                self.log(f"moveJ 结果: {status}")
            
            self.log("moveJ 返回后状态:")
            self.check_status()
            
        except Exception as e:
            self.log(f"moveJ 异常: {e}")
            self.check_status()
            
    def test_4_native_stopj(self):
        """测试4: 使用原生 stopJ 方法"""
        self.log("=== 测试4: 原生 stopJ 方法 ===")
        
        if not self.rc or not self.rc.isConnected():
            self.log("Control 接口未连接，无法测试")
            return
            
        self.log("发送前状态:")
        self.check_status()
        
        try:
            self.log("调用 rc.stopJ()...")
            _, status = self._call_with_timeout(
                "stopJ",
                lambda: self.rc.stopJ(2.0),
                timeout=30.0,
            )
            self.log(f"stopJ 结果: {status}")
        except Exception as e:
            self.log(f"stopJ 异常: {e}")
            
        self.log("stopJ 后状态:")
        self.check_status()
        
    def test_5_dashboard_stop(self):
        """测试5: Dashboard stop"""
        self.log("=== 测试5: Dashboard stop ===")
        
        if not self.db or not self.db.isConnected():
            self.log("Dashboard 未连接，无法测试")
            return
            
        self.log("发送前状态:")
        self.check_status()
        
        try:
            self.log("调用 db.stop()...")
            _, status = self._call_with_timeout(
                "db.stop",
                lambda: self.db.stop(),
                timeout=30.0,
            )
            self.log(f"db.stop() 结果: {status}")
        except Exception as e:
            self.log(f"db.stop() 异常: {e}")
            
        self.log("db.stop() 后状态:")
        self.check_status()
        
        time.sleep(1)
        self.log("1秒后状态:")
        self.check_status()
        
    def test_6_monitor_during_motion(self):
        """测试6: 长时间运动中持续监控连接状态"""
        self.log("=== 测试6: 运动过程中监控连接 ===")
        
        if not self.rc or not self.rc.isConnected():
            self.log("Control 接口未连接，无法测试")
            return
            
        try:
            current_q = self.rr.getActualQ()
            target_q = list(current_q)
            target_q[0] += 0.2  # 较大幅度移动
            
            self.log("开始异步移动，持续监控连接状态（按任意键停止）...")
            
            # 启动监控线程
            self.monitoring = True
            
            def monitor():
                count = 0
                while self.monitoring:
                    rc_ok = self.rc.isConnected() if self.rc else False
                    rr_ok = self.rr.isConnected() if self.rr else False
                    print(f"\r  [{count}] Control: {'✓' if rc_ok else '✗'}  Receive: {'✓' if rr_ok else '✗'}  ", end="", flush=True)
                    count += 1
                    time.sleep(0.2)
                print()  # 换行
                    
            monitor_thread = threading.Thread(target=monitor, daemon=True)
            monitor_thread.start()
            
            # 发送异步移动
            self.log("发送 moveJ (异步)...")
            result = self.rc.moveJ(target_q, 0.3, 0.2, True)  # asynchronous=True
            self.log(f"moveJ 返回: {result}")
            
            # 等待用户按键
            input("\n按 Enter 停止监控...")
            self.monitoring = False
            time.sleep(0.5)
            
            self.log("最终状态:")
            self.check_status()
            
        except Exception as e:
            self.log(f"测试异常: {e}")
            self.monitoring = False
            self.check_status()
            
    def test_7_multiple_scripts(self):
        """测试7: 连续发送多个脚本"""
        self.log("=== 测试7: 连续发送多个脚本 ===")
        
        if not self.rc or not self.rc.isConnected():
            self.log("Control 接口未连接，无法测试")
            return
            
        scripts = [
            ("sleep 0.1", "def s1():\n  sleep(0.1)\nend\ns1()\n"),
            ("textmsg", 'def s2():\n  textmsg("test1")\nend\ns2()\n'),
            ("sleep 0.1", "def s3():\n  sleep(0.1)\nend\ns3()\n"),
            ("textmsg", 'def s4():\n  textmsg("test2")\nend\ns4()\n'),
        ]
        
        for i, (desc, script) in enumerate(scripts, 1):
            self.log(f"发送脚本 {i}/{len(scripts)}: {desc}")
            rc_ok_before = self.rc.isConnected()
            result, status = self._call_with_timeout(
                "sendCustomScript",
                lambda: self.rc.sendCustomScript(script),
                timeout=30.0,
            )
            rc_ok_after = self.rc.isConnected()
            if status == "ok":
                self.log(f"  结果: {result}, 连接状态: {rc_ok_before} → {rc_ok_after}")
            else:
                self.log(f"  结果: {status}, 连接状态: {rc_ok_before} → {rc_ok_after}")
                self.check_status()
                break
            time.sleep(0.3)
                
        self.log("全部发送后状态:")
        self.check_status()
        
    def test_9_send_file_script(self, file_path: str = None):
        """测试9: 发送指定的脚本文件"""
        self.log("=== 测试9: 发送脚本文件 ===")
        
        if not self.rc or not self.rc.isConnected():
            self.log("Control 接口未连接，无法测试")
            return
        
        # 选择脚本
        print("\n可选脚本:")
        print("  1. fiber.script (原始版，含 modbus - 可能报错)")
        print("  2. fiber_test_no_modbus.script (简化版，无 modbus)")
        print("  3. 输入自定义路径")
        choice = input("选择 (1/2/3): ").strip()
        
        if choice == '1':
            file_path = r"D:\onedrive\桌面\Project\URscript\fiber.script"
        elif choice == '2':
            file_path = r"D:\onedrive\桌面\Project\URscript\fiber_test_no_modbus.script"
        elif choice == '3':
            file_path = input("输入脚本路径: ").strip()
        else:
            self.log("无效选择")
            return
            
        self.log(f"脚本文件: {file_path}")
        
        # 读取脚本文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                script = f.read()
            self.log(f"脚本大小: {len(script)} 字符, {len(script.splitlines())} 行")
        except Exception as e:
            self.log(f"读取脚本文件失败: {e}")
            return
            
        # 显示脚本前几行
        lines = script.splitlines()
        self.log("脚本预览 (前5行):")
        for i, line in enumerate(lines[:5]):
            self.log(f"  {i+1}: {line[:60]}{'...' if len(line) > 60 else ''}")
        if len(lines) > 5:
            self.log(f"  ... 共 {len(lines)} 行")
            
        self.log("\n发送前状态:")
        self.check_status()
        
        # 确认发送
        confirm = input("\n确认发送脚本? (y/n): ").strip().lower()
        if confirm != 'y':
            self.log("已取消")
            return
            
        self.log("发送脚本中 (最多等待30秒)...")
        t0 = time.time()
        result, status = self._call_with_timeout(
            "sendCustomScript",
            lambda: self.rc.sendCustomScript(script),
            timeout=30.0,
        )
        t1 = time.time()
        
        if status == "ok":
            self.log(f"sendCustomScript 返回: {result}, 耗时: {t1-t0:.3f}s")
        else:
            self.log("提示: 脚本可能有语法错误或运行时错误")
            self.log("      检查机器人示教器上的错误信息")
            
        self.log("\n发送后立即检查状态:")
        self.check_status()
        
        # 持续监控连接状态
        self.log("\n持续监控连接状态 (按 Ctrl+C 停止)...")
        try:
            for i in range(30):  # 监控30秒
                time.sleep(1)
                rc_ok = self.rc.isConnected() if self.rc else False
                rr_ok = self.rr.isConnected() if self.rr else False
                self.log(f"  t={i+1}s: Control={'✓' if rc_ok else '✗'}  Receive={'✓' if rr_ok else '✗'}")
                if not rc_ok:
                    self.log("  !!! Control 接口断开 !!!")
                    break
        except KeyboardInterrupt:
            self.log("\n监控已停止")
            
        self.log("\n最终状态:")
        self.check_status()

    def test_0_send_script_socket(self):
        """测试0: 通过 30002 端口发送脚本 (非阻塞) - 检测对 rtde_control 的影响"""
        self.log("=== 测试0: 通过 Socket 30002 发送脚本 ===")
        self.log("目的: 测试 30002 端口发送脚本是否会停止 rtde_control")
        self.log("说明: 30002端口发送后立即返回，不等待执行完成")
        
        # 选择脚本
        print("\n可选脚本:")
        print("  1. fiber.script (原始版)")
        print("  2. fiber_test_no_modbus.script (简化版)")
        print("  3. 简单测试脚本 (sleep 2秒)")
        print("  4. 输入自定义路径")
        choice = input("选择 (1/2/3/4): ").strip()
        
        if choice == '1':
            file_path = r"D:\onedrive\桌面\Project\URscript\fiber.script"
            script = None
        elif choice == '2':
            file_path = r"D:\onedrive\桌面\Project\URscript\fiber_test_no_modbus.script"
            script = None
        elif choice == '3':
            file_path = None
            # 简单的测试脚本
            script = """def test_30002():
  textmsg("30002 script started")
  sleep(2)
  textmsg("30002 script done")
end
test_30002()
"""
            self.log("使用内置简单测试脚本 (sleep 2秒)")
        elif choice == '4':
            file_path = input("输入脚本路径: ").strip()
            script = None
        else:
            self.log("无效选择")
            return
        
        # 读取脚本文件
        if script is None:
            self.log(f"脚本文件: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    script = f.read()
                self.log(f"脚本大小: {len(script)} 字符, {len(script.splitlines())} 行")
            except Exception as e:
                self.log(f"读取脚本文件失败: {e}")
                return
        
        # === 发送前检测 rtde_control ===
        self.log("\n" + "="*50)
        self.log("【发送前】检测 rtde_control 状态:")
        alive_before, detail_before = self.check_rtde_control_alive()
        self.log(f"  rtde_control: {'✓ 存活' if alive_before else '✗ 已停止'}")
        self.log(f"  详情: {detail_before}")
        self.check_status()
        
        if not alive_before:
            self.log("警告: rtde_control 在发送前就已停止，测试结果可能不准确", )
        
        # 确认发送
        confirm = input("\n确认发送脚本? (y/n): ").strip().lower()
        if confirm != 'y':
            self.log("已取消")
            return
        
        # === 通过 30002 端口发送 ===
        import socket
        self.log("\n通过 30002 端口发送脚本...")
        t0 = time.time()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.robot_ip, 30002))
            sock.sendall(script.encode('utf-8'))
            sock.close()
            t1 = time.time()
            self.log(f"✓ 发送完成! 耗时: {t1-t0:.3f}s")
        except Exception as e:
            self.log(f"✗ 发送失败: {e}")
            return
        
        # === 发送后立即检测 ===
        self.log("\n" + "="*50)
        self.log("【发送后立即】检测 rtde_control 状态:")
        alive_after_0, detail_after_0 = self.check_rtde_control_alive()
        self.log(f"  rtde_control: {'✓ 存活' if alive_after_0 else '✗ 已停止'}")
        self.log(f"  详情: {detail_after_0}")
        
        # === 持续监控 ===
        self.log("\n" + "="*50)
        self.log("持续监控 rtde_control 状态 (按 Ctrl+C 停止)...")
        self.log("观察点: 30002 发送的脚本执行期间/结束后，rtde_control 是否还在")
        
        rtde_control_died_at = None
        
        try:
            for i in range(30):  # 监控30秒
                time.sleep(1)
                
                # 检测各项状态
                rc_connected = self.rc.isConnected() if self.rc else False
                rr_connected = self.rr.isConnected() if self.rr else False
                alive, _ = self.check_rtde_control_alive()
                
                # 尝试获取运动状态
                moving = "?"
                if self.rr and rr_connected:
                    try:
                        speed = self.rr.getActualTCPSpeed()
                        speed_mag = (speed[0]**2 + speed[1]**2 + speed[2]**2) ** 0.5
                        moving = "运动中" if speed_mag > 0.001 else "静止"
                    except:
                        pass
                
                # 格式化输出
                rc_str = "✓" if rc_connected else "✗"
                rr_str = "✓" if rr_connected else "✗"
                rtde_str = "✓存活" if alive else "✗停止"
                
                self.log(f"  t={i+1:2d}s: rc={rc_str} rr={rr_str} rtde_control={rtde_str} 机器人={moving}")
                
                # 记录 rtde_control 停止的时间点
                if not alive and rtde_control_died_at is None:
                    rtde_control_died_at = i + 1
                    self.log(f"  >>> rtde_control 在 t={rtde_control_died_at}s 停止!")
                
        except KeyboardInterrupt:
            self.log("\n监控已停止")
        
        # === 最终结论 ===
        self.log("\n" + "="*50)
        self.log("【测试结论】")
        alive_final, detail_final = self.check_rtde_control_alive()
        
        self.log(f"  发送前 rtde_control: {'存活' if alive_before else '已停止'}")
        self.log(f"  发送后 rtde_control: {'存活' if alive_final else '已停止'}")
        
        if alive_before and not alive_final:
            self.log(f"\n  ★ 结论: 30002 端口发送脚本【会】停止 rtde_control!")
            if rtde_control_died_at:
                self.log(f"         停止发生在发送后 ~{rtde_control_died_at} 秒")
        elif alive_before and alive_final:
            self.log(f"\n  ★ 结论: 30002 端口发送脚本【不会】停止 rtde_control")
            self.log(f"         (可能是因为脚本使用了 sec 而不是 def)")
        else:
            self.log(f"\n  ★ 结论: 无法判断 (rtde_control 在发送前就已停止)")
        
        self.log("="*50)
        self.log("\n最终完整状态:")
        self.check_status()

    def test_8_script_then_check(self):
        """测试8: 发送脚本后精确检查连接时间点"""
        self.log("=== 测试8: 发送脚本后精确检查连接 ===")
        
        if not self.rc or not self.rc.isConnected():
            self.log("Control 接口未连接，无法测试")
            return
            
        script = """
def test_script():
    sleep(0.5)
    textmsg("script done")
end
test_script()
"""
        
        self.log("发送脚本 (包含 0.5秒 sleep)...")
        
        timestamps = []
        
        t0 = time.time()
        result, status = self._call_with_timeout(
            "sendCustomScript",
            lambda: self.rc.sendCustomScript(script),
            timeout=30.0,
        )
        t1 = time.time()
        timestamps.append((f"sendCustomScript {status}", t1 - t0, self.rc.isConnected()))

        if status != "ok":
            self.log("sendCustomScript 未完成，跳过后续时间线采样")
        else:
            for delay in [0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]:
                time.sleep(delay - (time.time() - t0) if delay > (time.time() - t0) else 0)
                t = time.time() - t0
                connected = self.rc.isConnected()
                timestamps.append((f"t={delay}s", t, connected))
            
        self.log("时间线:")
        for desc, t, connected in timestamps:
            status = "✓ 连接" if connected else "✗ 断开"
            self.log(f"  {desc}: 实际 {t:.3f}s, {status}")

    def reconnect_control(self):
        """重连 RTDEControlInterface (恢复 rtde_control)"""
        self.log("=== 重连 RTDEControlInterface ===")
        self.log("这将断开旧的 Control 连接并重新建立，同时重新上传 rtde_control 脚本")
        
        # 检测当前状态
        self.log("\n重连前状态:")
        alive_before, _ = self.check_rtde_control_alive()
        self.log(f"  rtde_control: {'存活' if alive_before else '已停止'}")
        
        # 断开旧连接
        if self.rc:
            try:
                self.log("断开旧的 Control 连接...")
                self.rc.disconnect()
            except Exception as e:
                self.log(f"  断开异常 (可忽略): {e}")
            self.rc = None
        
        # 等待一小段时间
        self.log("等待 1 秒...")
        time.sleep(1)
        
        # 重新连接
        self.log("重新连接 RTDEControlInterface...")
        try:
            result = [None]
            error = [None]
            
            def connect_rc():
                try:
                    result[0] = RTDEControlInterface(self.robot_ip, RTDEControlInterface.FLAG_UPLOAD_SCRIPT)
                except Exception as e:
                    error[0] = e
            
            t = threading.Thread(target=connect_rc, daemon=True)
            t.start()
            t.join(timeout=10.0)
            
            if t.is_alive():
                self.log("  ✗ 连接超时 (10秒)")
                return False
            
            if error[0]:
                self.log(f"  ✗ 连接异常: {error[0]}")
                return False
            
            self.rc = result[0]
            if self.rc and self.rc.isConnected():
                self.log("  ✓ Control 接口重连成功")
            else:
                self.log("  ✗ Control 接口重连失败")
                return False
                
        except Exception as e:
            self.log(f"  ✗ 重连异常: {e}")
            return False
        
        # 检测重连后状态
        self.log("\n重连后状态:")
        alive_after, detail = self.check_rtde_control_alive()
        self.log(f"  rtde_control: {'✓ 存活' if alive_after else '✗ 已停止'}")
        self.log(f"  详情: {detail}")
        
        if not alive_before and alive_after:
            self.log("\n★ rtde_control 已恢复!")
        elif alive_before and alive_after:
            self.log("\n★ rtde_control 状态正常")
        else:
            self.log("\n★ rtde_control 仍未恢复，可能需要等待机器人空闲")
        
        return alive_after


def try_release_control(robot_ip):
    """尝试释放被占用的 Control 接口"""
    import socket
    
    print(f"\n=== 尝试释放 Control 接口: {robot_ip} ===")
    print("\n方法1: 通过 Dashboard 停止程序...")
    
    try:
        # 连接 Dashboard (29999)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((robot_ip, 29999))
        
        # 读取欢迎消息
        welcome = sock.recv(1024).decode('utf-8', errors='replace')
        print(f"  Dashboard 连接成功: {welcome.strip()[:50]}")
        
        # 发送 stop 命令
        print("  发送 stop 命令...")
        sock.sendall(b"stop\n")
        resp = sock.recv(1024).decode('utf-8', errors='replace')
        print(f"  响应: {resp.strip()}")
        
        # 发送 close safety popup (如果有安全弹窗)
        print("  发送 close safety popup...")
        sock.sendall(b"close safety popup\n")
        resp = sock.recv(1024).decode('utf-8', errors='replace')
        print(f"  响应: {resp.strip()}")
        
        # 发送 unlock protective stop (如果有保护性停止)
        print("  发送 unlock protective stop...")
        sock.sendall(b"unlock protective stop\n")
        resp = sock.recv(1024).decode('utf-8', errors='replace')
        print(f"  响应: {resp.strip()}")
        
        sock.close()
        print("\n  Dashboard 命令已发送")
        
    except Exception as e:
        print(f"  Dashboard 连接失败: {e}")
    
    print("\n方法2: 断开现有 RTDE 连接...")
    print("  (RTDE 没有远程断开命令，只能等待超时)")
    
    print("\n=== 建议 ===")
    print("  1. 等待 30-60 秒让旧连接自动超时")
    print("  2. 或者重启机器人控制器 (最可靠)")
    print("  3. 如果是 URSim，重启 URSim 虚拟机")
    print("\n  提示: 程序异常退出时未调用 disconnect() 会导致连接残留")
    print("        建议在程序中使用 try/finally 确保断开连接")
    
    # 询问是否等待
    wait = input("\n是否等待 30 秒后重试连接? (y/n): ").strip().lower()
    if wait == 'y':
        print("等待中", end="", flush=True)
        for i in range(30):
            time.sleep(1)
            print(".", end="", flush=True)
        print(" 完成!")
        return True
    return False


def print_menu():
    """打印菜单"""
    print("\n" + "="*55)
    print("RTDE 行为测试 - 操作菜单")
    print("="*55)
    print("  C - 连接机器人")
    print("  D - 断开连接")
    print("  S - 查看当前状态 (含 rtde_control 检测)")
    print("  P - Ping/端口检测 (排查网络)")
    print("  R - 尝试释放 Control 接口")
    print("  K - 重连 Control 接口 (恢复 rtde_control) ★")
    print("  ─" * 27)
    print("  1 - 测试: sendCustomScript 移动脚本")
    print("  2 - 测试: sendCustomScript stopj 脚本")
    print("  3 - 测试: 原生 moveJ 方法")
    print("  4 - 测试: 原生 stopJ 方法")
    print("  5 - 测试: Dashboard stop")
    print("  6 - 测试: 运动中持续监控连接")
    print("  7 - 测试: 连续发送多个脚本")
    print("  8 - 测试: 发送脚本后精确检查连接")
    print("  9 - 测试: 发送脚本文件 (sendCustomScript, 阻塞)")
    print("  0 - 测试: 30002端口发送 → 检测 rtde_control ★★")
    print("  ─" * 27)
    print("  Q - 退出")
    print("="*55)


def check_network(robot_ip):
    """检查网络连通性和端口"""
    import socket
    import subprocess
    
    print(f"\n=== 网络诊断: {robot_ip} ===")
    
    # 1. Ping 测试
    print("\n[1] Ping 测试...")
    try:
        # Windows ping
        result = subprocess.run(
            ["ping", "-n", "2", "-w", "1000", robot_ip],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"    ✓ Ping 成功")
        else:
            print(f"    ✗ Ping 失败 - 机器人可能不在线")
            print(f"      {result.stdout.splitlines()[-1] if result.stdout else ''}")
    except Exception as e:
        print(f"    ✗ Ping 异常: {e}")
    
    # 2. 端口检测
    ports = [
        (29999, "Dashboard", "系统控制"),
        (30001, "Primary", "主接口"),
        (30002, "Secondary", "脚本发送"),
        (30003, "Real-time", "实时数据"),
        (30004, "RTDE", "实时数据交换"),
    ]
    
    print("\n[2] 端口检测 (超时2秒)...")
    for port, name, desc in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            result = sock.connect_ex((robot_ip, port))
            sock.close()
            
            if result == 0:
                print(f"    ✓ 端口 {port} ({name}): 开放 - {desc}")
            else:
                print(f"    ✗ 端口 {port} ({name}): 关闭/超时")
        except Exception as e:
            print(f"    ✗ 端口 {port} ({name}): 检测异常 - {e}")
    
    print("\n=== 诊断完成 ===")
    print("提示: 如果 30004 (RTDE) 端口关闭，请检查:")
    print("  1. 机器人是否开机并完成启动")
    print("  2. 机器人与电脑是否在同一网段")
    print("  3. 是否有防火墙阻止连接")


def main():
    print("\n" + "="*60)
    print("  RTDE 行为测试工具")
    print("  用于分析脚本发送对 rtde_control 状态的影响")
    print("="*60)
    
    # 获取机器人IP
    default_ip = "192.168.145.128"  # 修改为你的机器人IP
    ip_input = input(f"\n请输入机器人IP地址 [{default_ip}]: ").strip()
    robot_ip = ip_input if ip_input else default_ip
    
    tester = RTDETester(robot_ip)
    
    while True:
        print_menu()
        choice = input("\n请选择操作: ").strip().upper()
        
        if choice == 'C':
            tester.connect()
        elif choice == 'D':
            tester.disconnect()
        elif choice == 'S':
            tester.check_status()
        elif choice == 'P':
            check_network(robot_ip)
        elif choice == 'R':
            if try_release_control(robot_ip):
                print("\n现在尝试重新连接...")
                tester.connect()
        elif choice == 'K':
            tester.reconnect_control()
        elif choice == '1':
            tester.test_1_send_move_script()
        elif choice == '2':
            tester.test_2_send_stopj_script()
        elif choice == '3':
            tester.test_3_native_movej()
        elif choice == '4':
            tester.test_4_native_stopj()
        elif choice == '5':
            tester.test_5_dashboard_stop()
        elif choice == '6':
            tester.test_6_monitor_during_motion()
        elif choice == '7':
            tester.test_7_multiple_scripts()
        elif choice == '8':
            tester.test_8_script_then_check()
        elif choice == '9':
            tester.test_9_send_file_script()
        elif choice == '0':
            tester.test_0_send_script_socket()
        elif choice == 'Q':
            tester.disconnect()
            print("\n再见！")
            break
        else:
            print("无效选择，请重试")


if __name__ == "__main__":
    main()
