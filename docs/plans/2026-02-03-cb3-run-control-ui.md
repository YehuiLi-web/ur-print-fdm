# UR5 CB3 运行/暂停/停止 + 工具栏集成 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复主窗口运行/暂停/停止逻辑失效的问题，并把 UR5 CB3 推荐的“生产模式（SFTP + loader.urp + Dashboard）”与“直连 RTDE（调试）”在 UI 中清晰呈现，同时补齐独立上传功能。

**Architecture:**  
UR5 CB3 上“可靠暂停/继续”必须依赖 PolyScope 程序运行态，因此将生产运行统一走 Dashboard（29999）控制；脚本通过 SFTP 上传到 programs 目录，并由机器人端固定 `loader.urp` 读取 `remote_loader.script` 来实现“每次只替换脚本、始终加载同一个 URP”。直连模式仅用于调试：直接发送 URScript 到控制器，不承诺可暂停/继续。

**Tech Stack:** Python, PyQt6, `ur_rtde`, Dashboard Server (29999), SFTP/Paramiko, `pytest`.

---

### Task 1: 回归测试（主窗口可初始化）

**Files:**
- Create: `ur_print_fdm/tests/test_main_window_toolbar.py`

**Step 1:** 写测试：实例化 `URPrintIDE()` 不应因缺少 `_on_play_pause_clicked/upload_files` 崩溃。  
**Step 2:** 运行：`pytest -q ur_print_fdm/tests/test_main_window_toolbar.py::test_main_window_can_initialize_toolbar`（期望先失败）。  
**Step 3:** 修复最小代码后再运行直到通过。

---

### Task 2: 工具栏运行/暂停按钮状态机

**Files:**
- Modify: `ur_print_fdm/ui/main_window.py`

**Changes:**
- 增加 `_on_play_pause_clicked`：无任务时启动单文件运行；有 `ProductionProcessor` 时切换 pause/resume。
- 增加 `_set_play_pause_state/_sync_play_pause_button_state`：运行后按钮显示“暂停”，暂停后显示“运行”（视觉+语义一致）。
- 清理旧的 `_on_pause_clicked`（原逻辑依赖不存在的 `btn_global_pause`）。

---

### Task 3: 生产模式与独立上传（SFTP）打通

**Files:**
- Modify: `ur_print_fdm/ui/main_window.py`

**Changes:**
- 单文件生产运行：使用 `ProductionProcessor`（双份上传 + Dashboard `load loader.urp` + `play/pause/stop`），并把上传进度接到工具栏进度条。
- 队列生产：同样把 `file_progress_signal` 接到工具栏进度条，运行时锁定模式选择。
- 独立上传：实现 `upload_files()`，支持“仅上传原名 / 同时覆盖 remote_loader.script”。

---

### Task 4: 修复配置写入在受限环境下卡死

**Files:**
- Modify: `ur_print_fdm/config/manager.py`

**Rationale:**
`NamedTemporaryFile` 在某些受限环境/沙箱里会在创建临时文件时卡死，导致 UI 初始化被阻塞。将写入改为“固定 tmp 文件 + replace”，写入失败则快速返回 `False`。

---

### Task 5: 验证

Run: `pytest -q`  
Expected: 全部通过。

