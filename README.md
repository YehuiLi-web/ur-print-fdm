# UR Print FDM

UR Print FDM 是一个基于 PyQt6 的 Universal Robots 打印控制桌面程序，当前代码已经具备插件化、集中配置和持久化日志的基础，但仍以保守重构为主。

## 当前重点

- 保留现有 GUI、插件入口、配置键名和两种运行模式。
- 默认自动化测试只跑 `ur_print_fdm/tests`。
- 根目录原先的 `test_*.py` 已迁移到 `manual_checks/`，作为手工联调脚本保留。

## 开发环境

- Python: 3.11+
- 依赖安装:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.11 -m pip install -U pip
py -3.11 -m pip install -e .\ur_print_fdm[dev]
```

如果本机没有可用的 Python 解释器，先安装 Python 3.11，再执行以上命令。

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

