# UR Print FDM（UR5 Fiber Printer Studio）

一个基于 **PyQt6** 的桌面端 IDE/控制台，用于连接 **Universal Robots（UR，CB3/RTDE）** 机械臂，进行脚本编辑、样件生成、G-code 转换、队列化生产与运行状态监控。

> 项目当前形态更像“可直接运行的源码工程”（目录名就是包名 `ur_print_fdm`）。如果你在本目录内直接运行时遇到 `ModuleNotFoundError: No module named 'ur_print_fdm'`，请看下面的「启动方式」。

---

## 功能概览

- **连接与控制**
  - RTDE 接收（状态/位姿/速度/IO 等）+ Dashboard（加载/暂停/停止等）+ Script Socket（发送 URScript）
  - 只读降级：控制接口连接失败时可进入只读监控模式（见 `core/driver.py`）
- **生产队列（Batch/Queue）**
  - 依次发送脚本、等待运行、监控运行状态与 DO 完成标志、看门狗防“长时间静止仍挤出”（见 `ui/workers/production_processor.py`）
- **IDE 体验**
  - 左侧 **项目文件资源管理器**（VSCode 风格，支持新建/重命名/删除/刷新/搜索等）
  - 中央多标签编辑器（可选 QScintilla；缺失时自动降级为 QPlainTextEdit）
  - 状态面板、日志面板、工具/计算器等 Dock 组件
- **插件化**
  - 估时器 / 样件库提供者 / 机械臂后端 / G-code 转换器均走注册表（见 `plugins/registry.py` + `plugins/bootstrap.py`）

---

## 目录结构（你最关心的“每个文件夹干嘛的”）

> 以下路径均以“当前目录（`ur_print_fdm/`）”为基准。

### `config/`：配置系统（JSON 持久化 + 默认值）
- `config/manager.py`：线程安全配置管理器 `ConfigManager`（点号路径读写 + 落盘）
- `config/defaults.py`：默认配置（IP 列表、UI 面板折叠状态、打印参数等）
- `config/*.json`：一些 UI/状态相关的历史文件或样例（真正运行时的配置默认写入 `~/.ur_print_fdm/config.json`，见 `paths.py`）

### `core/`：机器人通信与打印核心逻辑
- `core/driver.py`：URDriver（RTDE/ Dashboard / Script 发送、上传/加载程序、急停/停机等）
- `core/dashboard_driver.py`：简化版 Dashboard TCP 控制器（29999 端口）
- `core/print_lib.py`：打印/挤出/转台协同的核心计算与脚本生成辅助
- `core/sample_library_manager.py`：样件（Sample）接口与注册管理
- `core/script_sanitizer.py`：脚本安全清理/检查相关逻辑
- `core/threads.py`：与 UI 解耦的监控线程/循环逻辑（被 UI 层 worker 调用/适配）
- `core/utils.py`：杂项工具函数

### `domain/`：领域模型（IR）
- `domain/trajectory.py`：`Trajectory`/`TrajectorySegment`，作为“时间估算/工艺算法”的中间表示（避免直接解析脚本文本）

### `estimators/`：时间估算器
- `estimators/simple_gcode.py`：基于轨迹段长度与速度的常速估时（插件形式注册）

### `plugins/`：插件契约与注册表
- `plugins/contracts.py`：插件协议/数据结构（估时器/样件/后端/转换器等）
- `plugins/registry.py`：全局 `registry`，并支持从 entry points 加载第三方插件
- `plugins/bootstrap.py`：启动时注册内置插件（UR 后端、G-code 转换器、估时器、样件提供者等）

### `processes/`：工艺/转换流程
- `processes/gcode_planar.py`：解析 G-code 并生成平面（planar）URScript
- `processes/gcode_planar_plugin.py`：将转换器包装成插件（供 UI/注册表调用）

### `robots/`：机械臂后端适配层
- `robots/contracts.py`：`RobotBackend` 协议与 `RobotStatus`
- `robots/ur_backend.py`：UR 的后端实现（复用 `core.driver.URDriver`）

### `samples/`：样件库（Sample）与加载
- `samples/api.py`：对外导出 Sample API（`SampleBase`/`SampleParameter`）
- `samples/loader.py`：从已注册的 SampleProvider 加载样件到 `SampleManager`
- `samples/legacy_provider.py`：兼容 legacy 的样件提供者（会触发 `core/samples` 注册）

### `shared/`：跨层共享的小工具
- `shared/net.py`：IP 地址校验等通用函数

### `ui/`：PyQt6 图形界面（IDE 主体）
- `ui/main_window.py`：主窗口 `URPrintIDE`（菜单/工具栏/停靠面板/编辑器/连接与监控联动）
- `ui/theme.py`：深色主题与 QSS
- `ui/controllers/`：控制器（如队列、工具栏动作编排）
- `ui/widgets/`：UI 组件（文件管理器、编辑器、状态面板、计算器、对话框等）
- `ui/workers/`：后台线程/工作者（连接、监控、上传、生产队列执行等）
- `ui/services/`：服务层（如日志服务）
- `ui/resources/`：SVG 图标、图标管理等资源

### `tests/`：测试
- `pytest` 用例（配置、估时、样件加载、IP 校验、G-code 转换器插件等）

### `docs/`：项目文档
- `docs/development.md`：开发/安装/启动（推荐阅读）
- `docs/*_guide.md`：文件浏览器、编辑器、菜单栏、工具栏等 UI 说明
- `docs/数据接口测试文档.md`：RTDE/状态采集/时间估算等接口测试与方案

---

## 启动方式（两种任选其一）

### 方式 A：从“上一级目录”直接运行（最稳妥）

原因：当前目录名就是包名 `ur_print_fdm`，Python 需要在 **其父目录** 才能 `import ur_print_fdm`。

**Windows PowerShell：**

```powershell
cd ..            # 进入包含 ur_print_fdm/ 的目录
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install PyQt6 numpy ur_rtde paramiko
python -m ur_print_fdm
```

### 方式 B：在本目录运行（设置 PYTHONPATH）

**Windows PowerShell：**

```powershell
$env:PYTHONPATH = ".."
python -m ur_print_fdm
```

---

## 关键端口与网络要求

默认端口在 `constants.py`：
- Dashboard：`29999`
- Script：`30002`
- RTDE：`30004`

确保你的电脑与机械臂在同一网段、端口未被防火墙拦截，并且 UR 控制器允许 RTDE/脚本连接。

---

## 配置文件位置

运行时配置默认写在用户目录下：
- `~/.ur_print_fdm/config.json`（见 `paths.py` 与 `config/manager.py`）

可配置内容示例（见 `config/defaults.py`）：
- 机器人 IP 列表/默认 IP、后端 ID
- IO/Modbus 名称与默认寄存器基值
- UI 窗口大小、面板折叠状态、日志自动滚动等

---

## 开发与测试

在本目录执行测试时，建议先设置 `PYTHONPATH`：

```powershell
$env:PYTHONPATH = ".."
pytest -q
```

代码风格（见 `docs/development.md`）：

```bash
python -m pip install pre-commit
pre-commit install
pre-commit run -a
```

---

## 可选增强

- 编辑器高亮/补全基于 `PyQt6.Qsci`（QScintilla）。如果环境里没有该模块，项目会自动降级为基础编辑器实现（见 `ui/widgets/editor/core.py` 的兼容逻辑）。

---

## 进一步阅读（项目自带文档）

- `docs/development.md`：安装/启动/开发约定
- `docs/file_explorer_guide.md`：文件资源管理器（VSCode 风格）说明
- `docs/editor_guide.md`：编辑器模块规格
- `docs/数据接口测试文档.md`：RTDE 数据采集与打印时间估算方案

