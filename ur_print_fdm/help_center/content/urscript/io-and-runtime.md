# 系统、I/O 与 RPC

这页整理 URScript 里最常见的系统函数、状态读取、I/O 接口、RPC 调用和容器方法。

## 1. TCP 与状态读取

### set_tcp

```urscript
set_tcp(p[0, 0, 0.12, 0, 0, 0])
set_tcp(p[0, 0, 0.12, 0, 0, 0], tcp_name = "nozzle")
```

用途:

- 设置 TCP 偏置

对工艺型应用很关键:

- 3D 打印
- 点胶
- 焊接
- 探针测量

### 常见状态函数

- `get_actual_tcp_pose()`
- `get_actual_tool_flange_pose()`
- `get_actual_joint_positions()`
- `get_target_joint_positions()`

## 2. 运动学辅助

常用函数:

- `get_forward_kin(...)`
- `get_inverse_kin(...)`
- `get_inverse_kin_has_solution(...)`

更详细的位姿和运动学内容见 [位姿与数学](./pose-math.md)。

## 3. 同步、日志与交互

### sleep

```urscript
sleep(0.1)
```

### sync

```urscript
sync()
```

### textmsg / popup

```urscript
textmsg("state", value)
popup("Check nozzle", title = "warning")
```

用途:

- 节拍控制
- 调试输出
- 现场提示

## 4. I/O

### 数字量输出

```urscript
set_digital_out(0, True)
set_configurable_digital_out(1, False)
set_tool_digital_out(0, True)
```

### 模拟量与输入

```urscript
set_analog_out(0, 0.5)
di = get_digital_in(0)
ai = get_analog_in(0)
```

## 5. RPC

RPC 通过 `rpc_factory` 建立:

```urscript
camera = rpc_factory("xmlrpc", "http://127.0.0.1/RPC2")
target = camera.getTarget()
camera.closeXMLRPCClientConnection()
```

特点:

- 调用期间会阻塞等待远端返回
- 远端函数签名必须匹配
- 很适合视觉、外部规划和数据库查询

注意:

- 不要把阻塞 RPC 放进 `sec` 程序
- 也不要在高频线程里无节制调用

## 6. 容器方法

从 PolyScope 5.15 起，list / struct / matrix 支持方法调用。

### List 常见方法

- `append(element)`
- `extend(list)`
- `insert(index, element)`
- `pop()`
- `remove(index)`
- `clear()`
- `length()`
- `capacity()`
- `excess_capacity()`
- `slice(begin, end)`
- `to_string()`

示例:

```urscript
l1 = make_list(0, 0, 10)
l1.append(88)
```

### Matrix 常见方法

- `get_row(index)`
- `get_column(index)`
- `shape()`
- `to_string()`

## 7. 软件文档写法建议

如果你要把这部分接进软件帮助中心，建议把这一页继续按功能拆小:

- `tcp-and-state.md`
- `io.md`
- `rpc.md`
- `containers.md`

但在当前阶段，先保留成一页最省维护成本。

## 8. 相关页面

- [位姿与数学](./pose-math.md)
- [作用域与线程](./scope-and-threads.md)
- [常见坑](./pitfalls.md)
