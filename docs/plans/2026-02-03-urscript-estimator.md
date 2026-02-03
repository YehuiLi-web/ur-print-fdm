# URScript 估算器（时间/线材）集成说明

## 目标

在不执行 URScript 的前提下，对脚本文本做**静态/受限解释**，输出：

- **预估打印时间**（秒）
- **连续碳纤维线长**（按 TCP 路径长度累计，单位 mm）
- **挤出机线长**（按 MODBUS 挤出速度 * 时间积分，单位 mm）

并在运行脚本时（可选）把预估总时长写入状态面板的打印计时器，用于显示剩余时间/ETA。

## 使用入口

### 手动估算（对话框）

- 菜单：`工具 -> 脚本处理 -> 脚本估算...`
- 文件树右键：对 `.script/.txt` 文件右键 -> `脚本估算...`

### 运行时自动估算（默认关闭）

设置项：`设置中心 -> UI -> 脚本估算 -> 运行时自动估算打印时间/线材 (URScript)`

启用后点击“运行”会：

1) 立即启动状态面板打印计时器（elapsed 开始走）
2) 后台估算脚本，估算完成后更新状态面板的 `estimated_total_seconds`（用于 remaining/ETA）

## 关键规则/假设

- **默认 feature**：优先使用脚本中的 `feature1` 作为初始 TCP 位姿
  - 若脚本无 `feature1`：优先使用“当前机器人 TCP”（运行时/手动估算且已连接时可读到）
  - 再不行：用“脚本中第一个出现的目标位姿”作为起点，并给出 warning
- **速度近似**：按 TCP 位移距离，把 `v` 当作 m/s 近似；时间使用（近似的）梯形/三角加减速模型
- **线材长度**
  - 连续碳纤维：`movel/movep/movec` 的 TCP 路径**全部计入**（含 travel 段），`movej` **不计入长度**
  - 挤出机：仅当 `modbus_set_output_register(MODBUS_1, reg)` 使挤出速度 > 0 时，按 `E(mm/s) * dt` 累计
- **寄存器编码**：
  - `reg >= 4000`：`E_mm_s = (reg - 4000) / 100`
  - `reg < 4000`：视为停止（例如 1000/3000/0）

## 覆盖的 URScript 子集

估算器支持最常见的子集（足以覆盖当前 `URscript/*.script`）：

- 语句：`def/end`、赋值（local/global）、`if/elif/else/end`、`while/end`
- 表达式：算术/比较/逻辑、列表、`p[...]` 位姿、索引 `a[3]`
- 常用函数：`movel/movep/movec/movej/sleep/modbus_set_output_register/pose_trans/d2r/get_actual_tcp_pose`
- 其他未知调用：忽略并生成 warning（不影响总流程）

## 相关代码位置

- 估算核心：`ur_print_fdm/estimators/urscript.py`
- 后台线程：`ur_print_fdm/ui/workers/threads.py`（`URScriptEstimateThread`）
- 菜单入口：`ur_print_fdm/ui/main_window.py`（脚本处理子菜单）
- 文件树右键入口：`ur_print_fdm/ui/widgets/file_explorer.py`
- 设置开关：`ur_print_fdm/ui/widgets/preferences_dialog.py` + 默认值 `ur_print_fdm/config/defaults.py`

