# 架构重构与插件化落地方案（v0.1 基线）

本仓库已引入 `ur_print_fdm/` 作为**新架构主包**，并保留现有 `core/`、`ui/` 作为 legacy 层，支持**渐进迁移**而不中断现有功能。

## 1. 目标：可扩展工艺/算法插件 + 可扩展机械臂

### 1.1 插件类型（第一阶段）
- **Time Estimator**：打印时间估算（输入：`Trajectory` 中间表示）
- **Sample Provider**：样件库提供者（输出：`core.sample_library_manager.SampleBase` 实例）
- **Robot Backend**：机械臂适配器工厂（输出：`RobotBackend`）

对应代码：
- 插件契约：`ur_print_fdm/plugins/contracts.py`
- 插件注册表：`ur_print_fdm/plugins/registry.py`
- 内置插件启动：`ur_print_fdm/plugins/bootstrap.py`

### 1.2 Entry Points（支持 pip 安装的外部插件）
外部插件包可在其 `pyproject.toml` 中声明 entry points：
- `ur_print_fdm.time_estimators`
- `ur_print_fdm.sample_providers`
- `ur_print_fdm.robot_backends`

应用启动时会自动加载（见 `ur_print_fdm/plugins/registry.py`）。

## 2. 中间表示（Trajectory IR）
时间估算/工艺算法避免直接解析 `.script` 字符串，优先基于 IR：
- `ur_print_fdm/domain/trajectory.py`

内置示例估算器：
- `ur_print_fdm/estimators/simple_gcode.py`（常速估算；后续可加入加速度/停顿/挤出开关等）

## 3. 机械臂适配层（Backend）
已提供 UR 的适配器包装层（不改动现有 UI）：
- 契约：`ur_print_fdm/robots/contracts.py`
- UR 适配：`ur_print_fdm/robots/ur_backend.py`（内部复用 `core.driver.URDriver`）

后续扩展其他机械臂（示例路线）：
- 新建 `ur_print_fdm/robots/<brand>_backend.py` 实现 `RobotBackend`
- 通过 entry point 注册为 `ur_print_fdm.robot_backends`
- UI 仅根据“能力集”启用/禁用按钮（不写死 UR）

## 4. 配置系统收敛（兼容现有 imports）
新配置实现：
- `ur_print_fdm/config/manager.py`
- `ur_print_fdm/config/defaults.py`

兼容层：
- 根目录 `config.py` 继续提供 `config_manager`，确保 `from config import config_manager` 不破坏 legacy 代码。

## 5. v0.1 -> v0.2 迁移里程碑（推荐顺序）
1) **测试基线可跑**：删除/替换残留测试引用（已移除 `tests/test_components.py`）。
2) **把 core 与 Qt 解耦**：将 `core/threads.py`、`core/processor.py` 的业务逻辑下沉到 `ur_print_fdm/app/`，Qt 线程只做调度与信号转发。
3) **样件库插件化**：UI 不再直接 `import core.samples`，改为 `bootstrap_plugins()` + `load_samples()`。
4) **时间估算接入 UI**：从 G-code/样件生成链路输出 `Trajectory`，选择估算器显示结果。
5) **多机械臂 UI**：连接面板改为“选择后端 + IP/参数”，并根据后端能力显示功能。

