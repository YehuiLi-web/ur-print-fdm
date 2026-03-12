# UR Print FDM

UR Print FDM 是一个基于 PyQt6 的 Universal Robots 打印控制桌面程序，当前代码已经具备插件化、集中配置和持久化日志的基础，但仍以保守重构为主。

## 当前重点

- 保留现有 GUI、插件入口、配置键名和两种运行模式。
- 默认自动化测试只跑 `ur_print_fdm/tests`。
- 历史手工联调脚本统一保存在 `manual_checks/`，不再散落在仓库根目录。

## 项目结构

- `ur_print_fdm/`: 主程序包、UI、核心逻辑、插件与自动化测试。
- `manual_checks/`: 需要真实设备、URSim 或人工观察的联调脚本。
- `URscript/`: 示例脚本、工艺脚本和相关输入文件。
- `docs/`: 架构说明、重构计划和补充文档；UI 调用链说明位于 `docs/ui/`。
- 根目录: 提供统一安装入口，包括 `pyproject.toml`、`requirements*.txt`、`pytest.ini`、打包脚本和安装器配置。

## 安装

- Python: 3.11+
- 依赖版本的唯一来源: 根目录 `pyproject.toml`
- 直接安装清单:
  - `requirements.txt`: 适合只需要运行程序的环境
  - `requirements-dev.txt`: 适合要参与开发、测试和打包的环境

运行环境安装:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.11 -m pip install -U pip
py -3.11 -m pip install -r requirements.txt
```

开发环境安装:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.11 -m pip install -U pip
py -3.11 -m pip install -r requirements-dev.txt
```

如果本机没有可用的 Python 解释器，先安装 Python 3.11，再执行以上命令。

如果需要完整的内置脚本编辑器增强能力，但又不想安装整套开发工具，也可以单独安装：

```powershell
py -3.11 -m pip install -e .[editor]
```

## 依赖版本

运行时依赖:

- `PyQt6>=6.5,<7`
- `numpy>=1.24,<3`
- `ur-rtde>=2.0,<3`
- `paramiko>=3,<4`

可选增强:

- `PyQt6-QScintilla>=2.14,<3`：启用更完整的脚本编辑器体验

开发与打包工具:

- `pytest>=7,<9`
- `pytest-qt>=4,<5`
- `pre-commit>=3.5,<5`
- `ruff>=0.6,<1`
- `mypy>=1.8,<2`
- `types-paramiko`
- `pyinstaller>=6,<7`

## 启动

```powershell
.\.venv\Scripts\Activate.ps1
py -3.11 -m ur_print_fdm
```

也可以使用打包入口：

```powershell
.\.venv\Scripts\Activate.ps1
ur-print-fdm
```

## 测试

自动化测试:

```powershell
.\.venv\Scripts\Activate.ps1
py -3.11 -m pytest -q
```

说明:

- `pytest.ini` 当前只收集 `ur_print_fdm/tests`。
- `manual_checks/` 中的脚本不会被默认测试命令收集。

## 打包

日常重新打包，直接运行根目录的 `build.bat` 即可。

```powershell
.\build.bat
```

如果想先手动补齐打包依赖，也可以直接使用开发依赖清单：

```powershell
py -3.11 -m pip install -r requirements-dev.txt
```

它会自动完成三件事：

- 生成目录版 `dist/UR Print FDM/`
- 生成绿色单文件版 `dist/UR Print FDM Portable.exe`
- 如果检测到 Inno Setup 6，再生成安装版 `installer_output/UR_Print_FDM_Setup_0.1.0.exe`

## 手工联调脚本

`manual_checks/` 目录下保留了历史联调脚本，例如 RTDE、Dashboard、主题切换、状态面板和直连端口验证。

这些脚本适合以下场景：

- 需要连接真实机器人或 URSim
- 需要人工观察界面或设备行为
- 需要验证非稳定自动化场景

## 运行模式

- `production`: 通过 SFTP 上传脚本，配合 `loader.urp` 和 Dashboard 控制，适合 CB3 的稳定暂停/恢复流程。
- `direct`: 通过 30002 端口直接发送脚本，启动快，但暂停/恢复能力较弱。

## 配置与日志

- 配置目录: `~/.ur_print_fdm/config.json`
- 日志目录: `~/.ur_print_fdm/logs`
- 默认配置来源: `ur_print_fdm/config/defaults.py`

兼容层说明:

- `ur_print_fdm/config.py`
- `ur_print_fdm/src/config.py`

以上两个文件仅用于兼容旧入口，新代码应统一从 `ur_print_fdm.config` 导入。

