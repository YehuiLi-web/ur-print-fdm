# Preferences Center + Professional Logging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Add a professional “设置中心/首选项”配置入口（分类 + 搜索 + Apply/OK/Cancel + 导入/导出 + 重置），并升级日志系统为“可追溯、可持久化、可按日期滚动”的统一日志。

**Architecture:**  
1) 以 `ConfigManager` 为单一配置源；Preferences 维护“工作副本”，Apply 时写回并持久化。  
2) 以 Python `logging` 作为统一日志总线：文件日志（按天滚动）+ UI 日志（Qt handler 转发）。  
3) 引入 `session_id`（每次启动唯一）与 `trace_id`（每次操作唯一）实现追踪溯源。

**Tech Stack:** Python 3.11+, PyQt6, pytest, logging.handlers

---

### Task 1: Add logging config defaults + paths

**Files:**
- Modify: `ur_print_fdm/config/defaults.py`
- Modify: `ur_print_fdm/paths.py`

**Steps**
1. Add `logging.*` defaults: level/retention/dir/UI filtering.
2. Add `logs_dir()` helper in `paths.py`.

---

### Task 2: Implement logging context (session_id/trace_id) + file logging setup

**Files:**
- Create: `ur_print_fdm/shared/logging_context.py`
- Create: `ur_print_fdm/shared/logging_setup.py`
- Test: `ur_print_fdm/tests/test_logging_setup.py`
- Modify: `ur_print_fdm/__main__.py`

**Steps**
1. Implement contextvars for `trace_id` and a filter that injects `session_id/trace_id` into LogRecord.
2. Implement `setup_file_logging(config_manager)` that creates a TimedRotatingFileHandler under `~/.ur_print_fdm/logs/`.
3. Add tests to verify: file created, record contains `session_id/trace_id`.
4. Call setup from `__main__.py` before UI starts.

---

### Task 3: Forward logging records to UI (professional log console)

**Files:**
- Create: `ur_print_fdm/ui/services/qt_log_handler.py`
- Modify: `ur_print_fdm/ui/main_window.py`
- Modify: `ur_print_fdm/ui/services/log_service.py`

**Steps**
1. Add a Qt-safe logging handler (emit signal -> append to LogService) and filter to only show `ur_print_fdm*` by default.
2. Extend LogService to support `DEBUG` level and “auto_scroll on/off”.
3. Update `URPrintIDE.log()` to log via `logging` (not direct UI append), so all logs go to file + UI consistently.

---

### Task 4: Instrument long-running operations with trace_id

**Files:**
- Modify: `ur_print_fdm/shared/logging_context.py`
- Modify: `ur_print_fdm/ui/workers/threads.py`
- Modify: `ur_print_fdm/ui/workers/production_processor.py`
- Modify: `ur_print_fdm/ui/main_window.py`

**Steps**
1. Add `new_trace_id()` and helpers to set trace id in threads.
2. Pass `trace_id` into connect/send/upload/production operations; set trace_id in worker thread before logging.
3. Ensure key workflow logs include trace_id and can be grepped from file logs.

---

### Task 5: Build Preferences Center dialog shell (A: Apply/OK/Cancel)

**Files:**
- Create: `ur_print_fdm/ui/widgets/preferences_dialog.py`
- Modify: `ur_print_fdm/config/manager.py`
- Test: `ur_print_fdm/tests/test_config_apply_dict.py`

**Steps**
1. Add `ConfigManager.snapshot()` and `ConfigManager.apply_dict()` to support working-copy editing and safe apply.
2. Implement Preferences dialog layout: search box, category list, stacked pages, Apply/OK/Cancel, reset/import/export.
3. Add unit test for `apply_dict()` behavior (defaults merge + unknown keys preserved).

---

### Task 6: Add core pages (common settings forms)

**Files:**
- Modify: `ur_print_fdm/ui/widgets/preferences_dialog.py`

**Steps**
1. Implement pages with validation + tooltips: Robot/Connection, Transfer(SFTP), Safety, Project, UI, Logging.
2. Mark “requires restart” settings in UI (e.g., backend selection).

---

### Task 7: Add Advanced / All Settings page

**Files:**
- Modify: `ur_print_fdm/ui/widgets/preferences_dialog.py`

**Steps**
1. Add JSON editor page for full config with “Validate/Apply”.
2. Provide safe error handling + revert on invalid JSON.

---

### Task 8: Hook into menu + add quick log utilities

**Files:**
- Modify: `ur_print_fdm/ui/main_window.py`

**Steps**
1. Replace/extend existing Settings menu action to open Preferences Center (shortcut `Ctrl+,`).
2. Add “打开日志目录” action (optional under Settings/Help).
3. Verify: `python -m py_compile` and `pytest -q`.

