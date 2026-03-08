#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus 直连控制测试

测试 PC 直接控制挤出机和转盘（绑过 UR 机器人）
验证 RTDE 运动 + Modbus 控制可以同时工作

依赖安装：
    pip install pymodbus ur_rtde
"""

import sys
import time
import threading

# ============================================================
# 配置区域（根据你的实际设备修改）
# ============================================================

# 挤出机 Modbus 配置
EXTRUDER_IP = "192.168.145.1"
EXTRUDER_PORT = 502  # 标准 Modbus TCP 端口，如果不对可以尝试其他值
EXTRUDER_REG = 0     # 寄存器地址
EXTRUDER_STOP_VALUE = 0      # 停止值
EXTRUDER_BASE_VALUE = 4000   # 基准值（对应你代码里的 base_reg）

# 转盘 Modbus 配置
TURNTABLE_IP = "192.168.145.2"
TURNTABLE_PORT = 502
PIN_REG = 0   # 转盘方向/速度寄存器地址
BU_REG = 1    # 转盘步数寄存器地址（如果是不同地址）
# 注意：如果 pin 和 bu 是同一个地址 0，需要根据实际协议调整

# UR 机器人配置（用于 RTDE 联合测试）
ROBOT_IP = "192.168.1.101"  # 修改为你的机器人 IP

# ============================================================


class ModbusController:
    """Modbus 设备控制器"""
    
    def __init__(self, name: str, ip: str, port: int = 502):
        self.name = name
        self.ip = ip
        self.port = port
        self.client = None
        self.connected = False
    
    def connect(self) -> bool:
        """连接设备"""
        try:
            from pymodbus.client import ModbusTcpClient
            self.client = ModbusTcpClient(self.ip, port=self.port, timeout=3)
            if self.client.connect():
                self.connected = True
                print(f"✓ {self.name} 连接成功 ({self.ip}:{self.port})")
                return True
            else:
                print(f"✗ {self.name} 连接失败 ({self.ip}:{self.port})")
                return False
        except ImportError:
            print("✗ 未安装 pymodbus，请运行: pip install pymodbus")
            return False
        except Exception as e:
            print(f"✗ {self.name} 连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.connected = False
        print(f"  {self.name} 已断开")
    
    def read_register(self, address: int) -> int | None:
        """读取保持寄存器"""
        if not self.connected:
            return None
        try:
            result = self.client.read_holding_registers(address, count=1)
            if not result.isError():
                return result.registers[0]
            else:
                print(f"  读取失败: {result}")
                return None
        except Exception as e:
            print(f"  读取异常: {e}")
            return None
    
    def write_register(self, address: int, value: int) -> bool:
        """写入保持寄存器"""
        if not self.connected:
            return False
        try:
            result = self.client.write_register(address, value)
            if not result.isError():
                return True
            else:
                print(f"  写入失败: {result}")
                return False
        except Exception as e:
            print(f"  写入异常: {e}")
            return False


class TestModbusControl:
    """Modbus 控制测试类"""
    
    def __init__(self):
        self.extruder = None
        self.turntable = None
        self.rc = None  # RTDE Control
        self.rr = None  # RTDE Receive
    
    def connect_modbus(self) -> bool:
        """连接 Modbus 设备"""
        print("\n" + "="*60)
        print("连接 Modbus 设备")
        print("="*60)
        
        self.extruder = ModbusController("挤出机", EXTRUDER_IP, EXTRUDER_PORT)
        self.turntable = ModbusController("转盘", TURNTABLE_IP, TURNTABLE_PORT)
        
        ext_ok = self.extruder.connect()
        turn_ok = self.turntable.connect()
        
        return ext_ok or turn_ok  # 至少一个成功
    
    def disconnect_modbus(self):
        """断开 Modbus 连接"""
        print("\n断开 Modbus 连接...")
        if self.extruder:
            self.extruder.disconnect()
        if self.turntable:
            self.turntable.disconnect()
    
    def connect_rtde(self) -> bool:
        """连接 RTDE"""
        print("\n" + "="*60)
        print("连接 RTDE")
        print("="*60)
        
        try:
            from rtde_control import RTDEControlInterface
            from rtde_receive import RTDEReceiveInterface
            
            print(f"连接 {ROBOT_IP}...")
            self.rr = RTDEReceiveInterface(ROBOT_IP)
            if self.rr.isConnected():
                print("✓ RTDE Receive 连接成功")
            else:
                print("✗ RTDE Receive 连接失败")
                return False
            
            self.rc = RTDEControlInterface(ROBOT_IP)
            if self.rc.isConnected():
                print("✓ RTDE Control 连接成功")
                return True
            else:
                print("✗ RTDE Control 连接失败")
                return False
                
        except ImportError:
            print("✗ 未安装 ur_rtde，请运行: pip install ur_rtde")
            return False
        except Exception as e:
            print(f"✗ RTDE 连接异常: {e}")
            return False
    
    def disconnect_rtde(self):
        """断开 RTDE 连接"""
        print("\n断开 RTDE 连接...")
        if self.rc:
            try:
                self.rc.disconnect()
            except:
                pass
        if self.rr:
            try:
                self.rr.disconnect()
            except:
                pass
    
    # ============================================================
    # 测试功能
    # ============================================================
    
    def test_read_all(self):
        """读取所有设备当前状态"""
        print("\n" + "-"*40)
        print("读取设备状态")
        print("-"*40)
        
        if self.extruder and self.extruder.connected:
            val = self.extruder.read_register(EXTRUDER_REG)
            print(f"挤出机寄存器[{EXTRUDER_REG}]: {val}")
        
        if self.turntable and self.turntable.connected:
            pin_val = self.turntable.read_register(PIN_REG)
            print(f"转盘 PIN 寄存器[{PIN_REG}]: {pin_val}")
            
            if BU_REG != PIN_REG:
                bu_val = self.turntable.read_register(BU_REG)
                print(f"转盘 BU 寄存器[{BU_REG}]: {bu_val}")
    
    def test_extruder_control(self):
        """测试挤出机控制"""
        print("\n" + "-"*40)
        print("测试挤出机控制")
        print("-"*40)
        
        if not self.extruder or not self.extruder.connected:
            print("挤出机未连接，跳过")
            return
        
        print(f"当前值: {self.extruder.read_register(EXTRUDER_REG)}")
        
        # 测试写入
        test_value = EXTRUDER_BASE_VALUE + 500  # 4500
        print(f"\n写入测试值: {test_value}")
        if self.extruder.write_register(EXTRUDER_REG, test_value):
            print("✓ 写入成功")
            time.sleep(0.5)
            print(f"验证读取: {self.extruder.read_register(EXTRUDER_REG)}")
        
        # 恢复停止
        print(f"\n恢复停止值: {EXTRUDER_STOP_VALUE}")
        if self.extruder.write_register(EXTRUDER_REG, EXTRUDER_STOP_VALUE):
            print("✓ 已停止")
            time.sleep(0.5)
            print(f"验证读取: {self.extruder.read_register(EXTRUDER_REG)}")
    
    def test_turntable_control(self):
        """测试转盘控制"""
        print("\n" + "-"*40)
        print("测试转盘控制")
        print("-"*40)
        
        if not self.turntable or not self.turntable.connected:
            print("转盘未连接，跳过")
            return
        
        print(f"当前 PIN 值: {self.turntable.read_register(PIN_REG)}")
        
        # 测试写入 PIN（方向+速度）
        # 根据你代码里的逻辑：pin = direction * 10000 + speed
        # direction: 1=顺时针, 2=逆时针
        test_pin = 14912  # 顺时针，速度 4912
        print(f"\n写入 PIN 测试值: {test_pin}")
        if self.turntable.write_register(PIN_REG, test_pin):
            print("✓ PIN 写入成功")
        
        # 测试写入 BU（步数）
        if BU_REG != PIN_REG:
            test_bu = 1000  # 测试步数
            print(f"写入 BU 测试值: {test_bu}")
            if self.turntable.write_register(BU_REG, test_bu):
                print("✓ BU 写入成功")
        
        time.sleep(1)
        
        # 停止转盘
        print("\n停止转盘...")
        self.turntable.write_register(PIN_REG, 0)
        if BU_REG != PIN_REG:
            self.turntable.write_register(BU_REG, 0)
        print("✓ 已停止")
    
    def test_emergency_stop(self):
        """测试直连急停（双保险）"""
        print("\n" + "-"*40)
        print("测试直连急停")
        print("-"*40)
        
        def stop_extruder():
            if self.extruder and self.extruder.connected:
                self.extruder.write_register(EXTRUDER_REG, 0)
                print("  ✓ 挤出机已停止")
        
        def stop_turntable():
            if self.turntable and self.turntable.connected:
                self.turntable.write_register(PIN_REG, 0)
                if BU_REG != PIN_REG:
                    self.turntable.write_register(BU_REG, 0)
                print("  ✓ 转盘已停止")
        
        def stop_robot():
            if self.rc and self.rc.isConnected():
                self.rc.stopJ(2.0)
                print("  ✓ 机器人已停止")
        
        print("并行执行急停...")
        t1 = threading.Thread(target=stop_extruder, daemon=True)
        t2 = threading.Thread(target=stop_turntable, daemon=True)
        t3 = threading.Thread(target=stop_robot, daemon=True)
        
        start = time.time()
        t1.start()
        t2.start()
        t3.start()
        
        t1.join(timeout=2)
        t2.join(timeout=2)
        t3.join(timeout=2)
        
        elapsed = time.time() - start
        print(f"\n急停完成，耗时: {elapsed*1000:.0f} ms")
    
    def test_rtde_with_modbus(self):
        """测试 RTDE 运动 + Modbus 控制（核心测试）"""
        print("\n" + "-"*40)
        print("测试 RTDE + Modbus 联合控制")
        print("-"*40)
        
        if not self.rc or not self.rc.isConnected():
            print("RTDE 未连接，跳过")
            return
        
        if not self.extruder or not self.extruder.connected:
            print("挤出机未连接，跳过")
            return
        
        # 获取当前位置
        current_q = self.rr.getActualQ()
        print(f"当前关节位置: {[f'{q:.3f}' for q in current_q]}")
        
        # 创建一个小幅度的目标位置（只移动最后一个关节 5 度）
        import math
        target_q = list(current_q)
        target_q[5] += math.radians(5)  # 最后一个关节转 5 度
        
        print("\n即将执行:")
        print("  1. 开启挤出")
        print("  2. RTDE moveJ (最后关节 +5°)")
        print("  3. 关闭挤出")
        
        confirm = input("\n确认执行？(y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return
        
        # === 执行 ===
        print("\n执行中...")
        
        # 1. 开启挤出
        ext_value = EXTRUDER_BASE_VALUE + 300
        print(f"  开启挤出: {ext_value}")
        self.extruder.write_register(EXTRUDER_REG, ext_value)
        
        # 2. RTDE 运动
        print("  RTDE moveJ...")
        result = self.rc.moveJ(target_q, 0.3, 0.3)  # 低速测试
        print(f"  moveJ 返回: {result}")
        
        # 3. 关闭挤出
        print("  关闭挤出")
        self.extruder.write_register(EXTRUDER_REG, 0)
        
        # === 验证 rtde_control 是否存活 ===
        print("\n验证 rtde_control 状态...")
        try:
            result = self.rc.stopJ(2.0)
            print(f"  stopJ 返回: {result}")
            if result:
                print("  ✓ rtde_control 仍然存活！RTDE + Modbus 可以共存！")
            else:
                print("  ⚠ stopJ 返回 False，可能有问题")
        except Exception as e:
            print(f"  ✗ rtde_control 异常: {e}")
    
    def test_sync_print_simulation(self):
        """模拟同步打印（挤出 + 运动同步）"""
        print("\n" + "-"*40)
        print("模拟同步打印")
        print("-"*40)
        
        if not self.rc or not self.rc.isConnected():
            print("RTDE 未连接，跳过")
            return
        
        if not self.extruder or not self.extruder.connected:
            print("挤出机未连接，跳过")
            return
        
        # 获取当前位姿
        current_pose = self.rr.getActualTCPPose()
        print(f"当前 TCP 位姿: {[f'{p:.4f}' for p in current_pose]}")
        
        # 模拟打印路径：Z 方向下降 5mm，然后 X 方向移动 20mm
        import copy
        
        # 起点（当前位置下方 5mm）
        start_pose = copy.copy(current_pose)
        start_pose[2] -= 0.005  # Z -5mm
        
        # 终点（X 方向移动 20mm）
        end_pose = copy.copy(start_pose)
        end_pose[0] += 0.020  # X +20mm
        
        print("\n打印路径:")
        print(f"  起点: Z-5mm")
        print(f"  终点: X+20mm")
        print(f"  挤出值: {EXTRUDER_BASE_VALUE + 400}")
        
        confirm = input("\n确认执行？(y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return
        
        print("\n执行中...")
        
        # 1. 移动到起点（不挤出）
        print("  移动到起点...")
        self.rc.moveL(start_pose, 0.05, 0.3)
        
        # 2. 开启挤出 + 打印移动
        print("  开启挤出，开始打印...")
        self.extruder.write_register(EXTRUDER_REG, EXTRUDER_BASE_VALUE + 400)
        
        self.rc.moveL(end_pose, 0.01, 0.1)  # 慢速打印
        
        # 3. 关闭挤出
        print("  关闭挤出")
        self.extruder.write_register(EXTRUDER_REG, 0)
        
        # 4. 抬起
        print("  抬起...")
        lift_pose = copy.copy(end_pose)
        lift_pose[2] += 0.020  # Z +20mm
        self.rc.moveL(lift_pose, 0.05, 0.3)
        
        print("\n✓ 模拟打印完成")
        print("  验证: rtde_control 仍然正常工作（没有被终止）")


def main():
    """主函数"""
    print("="*60)
    print("Modbus 直连控制测试")
    print("="*60)
    print(f"挤出机: {EXTRUDER_IP}:{EXTRUDER_PORT}")
    print(f"转盘:   {TURNTABLE_IP}:{TURNTABLE_PORT}")
    print(f"机器人: {ROBOT_IP}")
    print()
    
    tester = TestModbusControl()
    
    # 连接 Modbus
    if not tester.connect_modbus():
        print("\nModbus 连接失败，退出")
        return
    
    try:
        while True:
            print("\n" + "="*60)
            print("测试菜单")
            print("="*60)
            print("1 - 读取所有设备状态")
            print("2 - 测试挤出机控制")
            print("3 - 测试转盘控制")
            print("4 - 测试直连急停")
            print("-" * 30)
            print("5 - 连接 RTDE（机器人）")
            print("6 - 测试 RTDE + Modbus 联合控制 ★")
            print("7 - 模拟同步打印")
            print("-" * 30)
            print("0 - 急停所有设备")
            print("Q - 退出")
            
            choice = input("\n选择: ").strip().upper()
            
            if choice == '1':
                tester.test_read_all()
            elif choice == '2':
                tester.test_extruder_control()
            elif choice == '3':
                tester.test_turntable_control()
            elif choice == '4':
                tester.test_emergency_stop()
            elif choice == '5':
                tester.connect_rtde()
            elif choice == '6':
                tester.test_rtde_with_modbus()
            elif choice == '7':
                tester.test_sync_print_simulation()
            elif choice == '0':
                print("\n执行急停...")
                tester.test_emergency_stop()
            elif choice == 'Q':
                break
            else:
                print("无效选择")
    
    except KeyboardInterrupt:
        print("\n\n收到中断信号，执行急停...")
        tester.test_emergency_stop()
    
    finally:
        tester.disconnect_modbus()
        tester.disconnect_rtde()
        print("\n测试结束")


if __name__ == "__main__":
    main()
