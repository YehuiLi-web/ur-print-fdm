# UR 机器人脚本执行机制与 RTDE 控制指南

> 基于 UR5 CB3 系列 + ur_rtde 库的实际测试总结

## 目录

1. [核心概念](#核心概念)
2. [UR 机器人的通信接口](#ur-机器人的通信接口)
3. [脚本执行模型](#脚本执行模型)
4. [rtde_control 的工作原理](#rtde_control-的工作原理)
5. [各种操作对 rtde_control 的影响](#各种操作对-rtde_control-的影响)
6. [两套控制逻辑的对比](#两套控制逻辑的对比)
7. [最佳实践](#最佳实践)
8. [常见问题排查](#常见问题排查)

---

## 核心概念

### 关键结论

| 结论 | 说明 |
|------|------|
| **UR 同一时间只能运行 1 个主脚本** | 新脚本会替换正在运行的脚本 |
| **30002 端口发送脚本会停止 rtde_control** | 静默替换，不打印日志 |
| **Dashboard stop 会停止 rtde_control** | 显式停止，会打印日志 |
| **sendCustomScript 会停止 rtde_control** | 阻塞式发送，等待执行完成 |
| **rtde_control 停止后需要重连才能恢复** | 调用 `rc.disconnect()` 再重新连接 |

---

## UR 机器人的通信接口

### 端口概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    UR 机器人通信端口                             │
├─────────┬──────────────┬────────────────────────────────────────┤
│  端口   │     名称     │                 用途                    │
├─────────┼──────────────┼────────────────────────────────────────┤
│  29999  │  Dashboard   │ 系统控制 (load/play/pause/stop)        │
│  30001  │  Primary     │ 主接口 (程序/状态)                     │
│  30002  │  Secondary   │ 脚本发送 (非阻塞，立即返回)            │
│  30003  │  Real-time   │ 实时数据流 (125Hz)                     │
│  30004  │  RTDE        │ 实时数据交换 (ur_rtde 使用)            │
└─────────┴──────────────┴────────────────────────────────────────┘
```

### 各接口详解

#### 1. Dashboard (29999)

```python
from dashboard_client import DashboardClient
db = DashboardClient("192.168.1.101")
db.connect()

# 主要功能
db.load("/programs/xxx.urp")  # 加载程序
db.play()                      # 运行
db.pause()                     # 暂停
db.stop()                      # 停止 ← 会终止 rtde_control
```

**特点**：
- 用于程序级别的控制
- `stop()` 会**显式终止**当前运行的脚本
- 支持暂停/继续

#### 2. Secondary Interface (30002)

```python
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("192.168.1.101", 30002))
sock.sendall(b"movej([0,0,0,0,0,0], a=1, v=0.5)\n")
sock.close()  # 发完立即关闭，机器人继续执行
```

**特点**：
- 直接发送 URScript 代码
- **非阻塞**：发送后立即返回
- 新脚本会**替换**当前运行的脚本（包括 rtde_control）
- 不等待执行完成

#### 3. RTDE (30004)

```python
from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface

rr = RTDEReceiveInterface("192.168.1.101")  # 只读，获取状态
rc = RTDEControlInterface("192.168.1.101")  # 控制，发送命令
```

**特点**：
- 二进制协议，高效
- `RTDEControlInterface` 连接时自动上传 `rtde_control` 脚本
- 提供原生方法：`moveJ()`, `moveL()`, `stopJ()`, `speedL()` 等
- **阻塞式**：等待命令执行完成

---

## 脚本执行模型

### UR 的单脚本限制

```
┌─────────────────────────────────────────────────────────────────┐
│                   UR 脚本执行引擎                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌─────────────────┐                                          │
│    │   当前运行脚本   │  ← 同一时间只能有 1 个主脚本运行        │
│    └─────────────────┘                                          │
│             │                                                    │
│             │ 新脚本到达时                                       │
│             ▼                                                    │
│    ┌─────────────────┐                                          │
│    │   旧脚本被替换   │  ← 旧脚本直接终止，不会有"停止"日志     │
│    └─────────────────┘                                          │
│             │                                                    │
│             ▼                                                    │
│    ┌─────────────────┐                                          │
│    │   新脚本开始执行  │                                         │
│    └─────────────────┘                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 脚本来源优先级

| 来源 | 行为 |
|------|------|
| PolyScope 手动运行 | 替换当前脚本 |
| Dashboard `play()` | 替换当前脚本 |
| 30002 端口发送 | 替换当前脚本 |
| `sendCustomScript()` | 替换当前脚本 |

**所有方式都会替换当前脚本，包括 rtde_control。**

---

## rtde_control 的工作原理

### 什么是 rtde_control？

当你创建 `RTDEControlInterface` 对象时：

```python
rc = RTDEControlInterface("192.168.1.101")
```

`ur_rtde` 库会自动：
1. 通过 RTDE 协议连接到机器人
2. **上传一个名为 `rtde_control` 的后台脚本到机器人**
3. 这个脚本在机器人端持续运行，监听来自 PC 的命令

### rtde_control 的生命周期

```
┌─────────────────────────────────────────────────────────────────┐
│                  rtde_control 生命周期                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ① RTDEControlInterface(ip)                                     │
│     │                                                            │
│     ▼                                                            │
│  ┌──────────────────────────────────┐                           │
│  │  rtde_control 脚本上传并开始运行  │                           │
│  └──────────────────────────────────┘                           │
│     │                                                            │
│     │  moveJ() / moveL() / stopJ() 等调用                       │
│     ▼                                                            │
│  ┌──────────────────────────────────┐                           │
│  │  rtde_control 接收命令并执行     │  ← 原生 RTDE 方法正常工作  │
│  └──────────────────────────────────┘                           │
│     │                                                            │
│     │  以下任一操作会终止 rtde_control:                         │
│     │    • 30002 端口发送其他脚本                               │
│     │    • sendCustomScript()                                   │
│     │    • Dashboard stop()                                     │
│     │    • Dashboard play() 加载其他程序                        │
│     │    • PolyScope 手动运行程序                               │
│     ▼                                                            │
│  ┌──────────────────────────────────┐                           │
│  │  rtde_control 被替换/终止        │  ← 原生方法失效           │
│  └──────────────────────────────────┘                           │
│     │                                                            │
│     │  恢复方法:                                                 │
│     │    rc.disconnect()                                        │
│     │    rc = RTDEControlInterface(ip)  # 重新连接              │
│     ▼                                                            │
│  ┌──────────────────────────────────┐                           │
│  │  rtde_control 重新上传并恢复     │                           │
│  └──────────────────────────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 各种操作对 rtde_control 的影响

### 测试结果汇总

| 操作 | 对 rtde_control 的影响 | 机器人日志 | 后续 moveJ 能否工作 |
|------|------------------------|-----------|-------------------|
| `rc.moveJ()` | 无影响 | 有运动日志 | ✓ 正常 |
| `rc.stopJ()` | 无影响 | 有 stopj 日志 | ✓ 正常 |
| `rc.sendCustomScript()` | **终止** | 有脚本启动日志 | ✗ 失败 |
| 30002 端口发送脚本 | **终止** | 有脚本启动日志 | ✗ 失败 |
| `db.stop()` | **终止** | 有停止日志 | ✗ 失败 |
| `db.play()` | **终止** | 有程序启动日志 | ✗ 失败 |

### 详细分析

#### 1. 原生 RTDE 方法（安全）

```python
rc.moveJ(target_q, 0.5, 0.3)   # ✓ 不影响 rtde_control
rc.moveL(target_pose, 0.1, 0.3) # ✓ 不影响 rtde_control
rc.stopJ(2.0)                   # ✓ 不影响 rtde_control
rc.speedL(velocity, 0.5)        # ✓ 不影响 rtde_control
```

这些方法通过 RTDE 协议发送命令，由 rtde_control 脚本执行。

#### 2. sendCustomScript（危险）

```python
script = """
def my_script():
    movej([0,0,0,0,0,0], a=1, v=0.5)
end
my_script()
"""
rc.sendCustomScript(script)  # ✗ 会终止 rtde_control
```

**问题**：
- 阻塞等待脚本执行完成
- 你的脚本替换了 rtde_control
- 执行完成后 rtde_control 不会自动恢复

#### 3. 30002 端口发送脚本（危险）

```python
import socket
sock = socket.socket()
sock.connect((ip, 30002))
sock.sendall(script.encode())
sock.close()  # ✗ 会终止 rtde_control
```

**问题**：
- 非阻塞，发送后立即返回
- 你的脚本替换了 rtde_control
- rtde_control 静默被终止（机器人不打印"已停止"日志）

#### 4. Dashboard stop（危险）

```python
db.stop()  # ✗ 会终止 rtde_control
```

**问题**：
- 显式停止当前脚本
- 机器人日志会显示"rtde_control 已停止"

---

## 两套控制逻辑的对比

### 方案 A：SFTP + Dashboard 模式（推荐用于生产）

```
┌─────────────────────────────────────────────────────────────────┐
│                SFTP + Dashboard 模式                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. SFTP 上传脚本文件到机器人                                    │
│     └─ /programs/remote_loader.script                           │
│                                                                  │
│  2. Dashboard 加载 loader.urp                                    │
│     └─ db.load("/programs/loader.urp")                          │
│                                                                  │
│  3. Dashboard 控制执行                                           │
│     ├─ db.play()   → 开始执行                                   │
│     ├─ db.pause()  → 暂停 ✓                                     │
│     └─ db.stop()   → 停止                                       │
│                                                                  │
│  优点:                                                           │
│    ✓ 支持暂停/继续                                              │
│    ✓ 脚本保存在机器人端                                         │
│    ✓ 不依赖 PC 持续连接                                         │
│    ✓ 不会阻塞 PC 端                                             │
│                                                                  │
│  缺点:                                                           │
│    ✗ 启动较慢（需要上传+加载）                                   │
│    ✗ 无法实时控制                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 方案 B：RTDE 实时控制模式（推荐用于实时控制）

```
┌─────────────────────────────────────────────────────────────────┐
│               RTDE 实时控制模式                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 建立 RTDE 连接                                               │
│     ├─ rr = RTDEReceiveInterface(ip)  # 状态读取                │
│     └─ rc = RTDEControlInterface(ip)  # 命令发送                │
│                                                                  │
│  2. 使用原生方法控制                                             │
│     ├─ rc.moveJ()    → 关节运动                                 │
│     ├─ rc.moveL()    → 直线运动                                 │
│     ├─ rc.speedL()   → 速度控制                                 │
│     ├─ rc.servoJ()   → 伺服控制 (125Hz)                         │
│     └─ rc.stopJ()    → 停止                                     │
│                                                                  │
│  优点:                                                           │
│    ✓ 实时控制 (125Hz)                                           │
│    ✓ 可用于力控、视觉伺服等                                      │
│    ✓ 响应快                                                     │
│                                                                  │
│  缺点:                                                           │
│    ✗ 不支持真正的暂停/继续                                       │
│    ✗ 依赖 PC 持续连接                                           │
│    ✗ 不要使用 sendCustomScript (会破坏 rtde_control)            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 方案 C：30002 端口直接发送（快速但不推荐）

```
┌─────────────────────────────────────────────────────────────────┐
│              30002 端口直接发送                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Socket 连接到 30002 端口                                     │
│  2. 发送 URScript 代码                                           │
│  3. 断开连接                                                     │
│                                                                  │
│  优点:                                                           │
│    ✓ 非阻塞，发送快                                             │
│    ✓ 简单直接                                                   │
│                                                                  │
│  缺点:                                                           │
│    ✗ 会终止 rtde_control                                        │
│    ✗ 无法获取执行状态                                           │
│    ✗ 不支持暂停/继续                                            │
│    ✗ 脚本不保存在机器人端                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 最佳实践

### 1. 生产队列场景

**推荐：SFTP + Dashboard 模式**

```python
# 1. 上传脚本
sftp.put(local_script, "/programs/remote_loader.script")

# 2. 加载并运行
db.load("/programs/loader.urp")
db.play()

# 3. 等待完成（轮询）
while db.running():
    if need_pause:
        db.pause()
    if need_resume:
        db.play()
    time.sleep(0.2)

# 4. 如果需要 RTDE 状态监控，使用 RTDEReceiveInterface（只读）
rr = RTDEReceiveInterface(ip)
tcp = rr.getActualTCPPose()
```

### 2. 实时控制场景（如力控、Jog）

**推荐：纯 RTDE 原生方法**

```python
rc = RTDEControlInterface(ip)
rr = RTDEReceiveInterface(ip)

# 使用原生方法
rc.moveJ(target_q, 0.5, 0.3)
rc.speedL([0, 0, -0.01, 0, 0, 0], 0.5)  # 速度控制
rc.stopJ(2.0)

# ❌ 不要使用 sendCustomScript
# rc.sendCustomScript(...)  # 会破坏 rtde_control
```

### 3. 需要发送自定义脚本时

**如果必须发送自定义脚本，发送后重连 RTDE：**

```python
import socket

# 1. 发送脚本
sock = socket.socket()
sock.connect((ip, 30002))
sock.sendall(script.encode())
sock.close()

# 2. 等待脚本执行完成（通过其他方式判断）
while robot_is_moving():
    time.sleep(0.1)

# 3. 重连 RTDE Control（恢复 rtde_control）
rc.disconnect()
rc = RTDEControlInterface(ip)
```

### 4. 紧急停止

**使用 Dashboard + 30002 双保险：**

```python
def emergency_stop():
    # 1. Dashboard stop
    try:
        db.stop()
    except:
        pass
    
    # 2. 30002 发送 stopj（以防万一）
    try:
        sock = socket.socket()
        sock.settimeout(1.0)
        sock.connect((ip, 30002))
        sock.sendall(b"stopj(2.0)\n")
        sock.close()
    except:
        pass
```

---

## 常见问题排查

### Q1: moveJ 返回 False，机器人不动

**可能原因**：rtde_control 已停止

**解决方法**：
```python
rc.disconnect()
rc = RTDEControlInterface(ip)
```

### Q2: sendCustomScript 卡住不返回

**原因**：sendCustomScript 会阻塞等待脚本执行完成

**解决方法**：
- 使用 30002 端口发送（非阻塞）
- 或在脚本中添加退出条件

### Q3: 30002 发送脚本后，RTDE 状态读取正常但控制失效

**原因**：
- `RTDEReceiveInterface` 是只读的，不受影响
- `RTDEControlInterface` 的 rtde_control 被替换了

**解决方法**：重连 `RTDEControlInterface`

### Q4: Dashboard pause 后无法继续

**可能原因**：
- 机器人进入保护停机
- 有安全弹窗

**解决方法**：
```python
db.closeSafetyPopup()
db.unlockProtectiveStop()
db.play()
```

---

## 附录：接口兼容性矩阵

| 操作 | RTDEReceive | RTDEControl | Dashboard | 30002 |
|------|-------------|-------------|-----------|-------|
| 读取位置 | ✓ | - | - | - |
| 读取力 | ✓ | - | - | - |
| moveJ/moveL | - | ✓ | - | ✓ |
| speedL/servoJ | - | ✓ | - | - |
| 暂停/继续 | - | - | ✓ | - |
| 停止 | - | ✓ | ✓ | ✓ |
| 发送完整脚本 | - | ⚠️ | - | ✓ |
| 加载 .urp 程序 | - | - | ✓ | - |

⚠️ = 可用但会破坏 rtde_control

---

## 参考资料

- [ur_rtde 官方文档](https://sdurobotics.gitlab.io/ur_rtde/)
- [UR Script Manual](https://www.universal-robots.com/download/)
- [UR Client Interfaces](https://www.universal-robots.com/articles/ur/interface-communication/overview-of-client-interfaces/)
