#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 PC 直接连接 Modbus 设备（绑过 UR 机器人）

如果这个测试成功，意味着你可以：
- 用 RTDE 控制机器人运动
- 用 pymodbus 直接控制挤出机和转盘
- 两者互不干扰！
"""

import sys
import time

# 你的 Modbus 设备配置（从 UR 截图读取）
EXTRUDER_IP = "192.168.145.1"
EXTRUDER_PORT = 502  # Modbus TCP 标准端口（UR 显示的 65535 是 UR 内部端口）
EXTRUDER_REG = 0     # 寄存器地址

TURNTABLE_IP = "192.168.145.1"
TURNTABLE_PORT = 502
PIN_REG = 0  # 转盘方向/速度寄存器
BU_REG = 0   # 转盘步数寄存器（如果是同一个地址，可能需要调整）

def test_with_pymodbus():
    """使用 pymodbus 库测试"""
    try:
        from pymodbus.client import ModbusTcpClient
        print("✓ pymodbus 库已安装")
    except ImportError:
        print("✗ 未安装 pymodbus，请运行: pip install pymodbus")
        return False
    
    print("\n" + "="*60)
    print("测试 1: 连接挤出机 Modbus 设备")
    print("="*60)
    
    try:
        client = ModbusTcpClient(EXTRUDER_IP, port=EXTRUDER_PORT, timeout=3)
        if client.connect():
            print(f"✓ 成功连接到挤出机 {EXTRUDER_IP}:{EXTRUDER_PORT}")
            
            # 尝试读取寄存器
            try:
                result = client.read_holding_registers(EXTRUDER_REG, count=1)
                if not result.isError():
                    print(f"  当前寄存器值: {result.registers[0]}")
                else:
                    print(f"  读取失败: {result}")
            except Exception as e:
                print(f"  读取异常: {e}")
            
            client.close()
        else:
            print(f"✗ 无法连接到 {EXTRUDER_IP}:{EXTRUDER_PORT}")
            print("  可能原因：")
            print("  - Modbus 设备使用了非标准端口")
            print("  - 设备不支持 PC 直连（只接受 UR 的连接）")
            print("  - 防火墙阻止")
    except Exception as e:
        print(f"✗ 连接异常: {e}")
    
    print("\n" + "="*60)
    print("测试 2: 连接转盘 Modbus 设备")
    print("="*60)
    
    try:
        client = ModbusTcpClient(TURNTABLE_IP, port=TURNTABLE_PORT, timeout=3)
        if client.connect():
            print(f"✓ 成功连接到转盘 {TURNTABLE_IP}:{TURNTABLE_PORT}")
            
            try:
                result = client.read_holding_registers(PIN_REG, count=1)
                if not result.isError():
                    print(f"  PIN 寄存器值: {result.registers[0]}")
                else:
                    print(f"  读取失败: {result}")
            except Exception as e:
                print(f"  读取异常: {e}")
            
            client.close()
        else:
            print(f"✗ 无法连接到 {TURNTABLE_IP}:{TURNTABLE_PORT}")
    except Exception as e:
        print(f"✗ 连接异常: {e}")
    
    return True


def test_with_socket():
    """使用原始 socket 测试连通性"""
    import socket
    
    print("\n" + "="*60)
    print("测试 3: 基本网络连通性（Socket）")
    print("="*60)
    
    for name, ip, port in [
        ("挤出机", EXTRUDER_IP, 502),
        ("挤出机(65535)", EXTRUDER_IP, 65535),
        ("转盘", TURNTABLE_IP, 502),
        ("转盘(65535)", TURNTABLE_IP, 65535),
    ]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex((ip, port))
            if result == 0:
                print(f"  ✓ {name} ({ip}:{port}) - 端口开放")
            else:
                print(f"  ✗ {name} ({ip}:{port}) - 端口关闭或无响应")
        except Exception as e:
            print(f"  ✗ {name} ({ip}:{port}) - 异常: {e}")
        finally:
            sock.close()


def demo_rtde_with_modbus():
    """演示 RTDE + 直接 Modbus 控制的架构"""
    print("\n" + "="*60)
    print("演示: RTDE 运动 + 直接 Modbus 控制")
    print("="*60)
    
    print("""
如果上面的 Modbus 连接测试成功，你可以这样使用：

```python
from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from pymodbus.client import ModbusTcpClient

# 1. 连接 RTDE（控制运动）
rc = RTDEControlInterface("192.168.1.101")
rr = RTDEReceiveInterface("192.168.1.101")

# 2. 连接 Modbus 设备（直接控制，不经过 UR）
extruder = ModbusTcpClient("192.168.145.1", port=502)
turntable = ModbusTcpClient("192.168.145.2", port=502)
extruder.connect()
turntable.connect()

# 3. 同步控制示例
def print_move(target_pose, speed, extrude_value):
    # 开启挤出
    extruder.write_register(0, extrude_value)
    
    # RTDE 运动
    rc.moveL(target_pose, speed, 0.3)
    
    # 关闭挤出
    extruder.write_register(0, 0)

# 优点：
# - RTDE 原生方法不会被终止
# - 可以实现更精细的时序控制
# - 支持实时调整挤出量
```
""")


def main():
    print("="*60)
    print("Modbus 直连测试")
    print("="*60)
    print(f"挤出机 IP: {EXTRUDER_IP}")
    print(f"转盘 IP:   {TURNTABLE_IP}")
    print()
    
    # 测试网络连通性
    test_with_socket()
    
    # 测试 Modbus 连接
    test_with_pymodbus()
    
    # 演示架构
    demo_rtde_with_modbus()
    
    print("\n" + "="*60)
    print("结论")
    print("="*60)
    print("""
如果 Modbus 连接成功：
  → 你可以用 PC 直接控制挤出机和转盘
  → RTDE 只负责机器人运动
  → 两者完全独立，互不干扰！

如果 Modbus 连接失败：
  → 设备可能只接受 UR 的连接（专有协议）
  → 或者需要特殊的端口/配置
  → 这种情况只能继续用 URScript 方式
""")


if __name__ == "__main__":
    main()
