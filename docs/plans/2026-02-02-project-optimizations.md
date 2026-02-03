# Project Optimizations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Make the repo reliably testable and improve runtime robustness (plugins/config/logging), while keeping changes minimal and low-risk.

**Architecture:** Keep `ur_print_fdm/` as the main package, but add repo-level test configuration (`pytest.ini`) so `pytest` works from the project root without manual `PYTHONPATH` hacks.

**Tech Stack:** Python 3.11+, PyQt6, pytest

---

### Task 1: Fix pytest import/collection

**Files:**
- Create: `pytest.ini`
- Modify: `ur_print_fdm/tests/test_gcode_time_estimate.py`

**Steps**
1. Add `pytest.ini` to set `testpaths`, `pythonpath`, and ignore unreadable cache dirs.
2. Fix legacy `from core import ...` import in tests.
3. Verify: `pytest -q` → all tests pass.

---

### Task 2: Harden plugin entrypoint loading

**Files:**
- Modify: `ur_print_fdm/plugins/registry.py`
- Test: `ur_print_fdm/tests/test_plugin_registry_entrypoints.py`

**Steps**
1. Wrap entry point loading in try/except per plugin; continue on failure.
2. Prevent silent ID overrides; warn and keep the existing plugin.
3. Verify: `pytest -q` → all tests pass.

---

### Task 3: Move SFTP credentials into config

**Files:**
- Modify: `ur_print_fdm/config/defaults.py`
- Modify: `ur_print_fdm/ui/workers/threads.py`

**Steps**
1. Add `robot.sftp` defaults (port/username/password/remote_dir).
2. Read SFTP settings from `config_manager` with safe fallbacks.
3. Verify: `pytest -q` → all tests pass.

---

### Task 4: Make config writes atomic

**Files:**
- Modify: `ur_print_fdm/config/manager.py`

**Steps**
1. Write JSON to a temp file in the same directory, then `replace()` onto `config.json`.
2. Verify: `pytest -q` → all tests pass.

---

### Task 5: Log backend init failures

**Files:**
- Modify: `ur_print_fdm/ui/main_window.py`

**Steps**
1. Capture backend init failure reason (missing backend ID / exception).
2. Log a warning to the UI after docks are initialized.
3. Verify: `python -m py_compile ur_print_fdm/ui/main_window.py`.

---

### Task 6: Add bounded UI log buffer

**Files:**
- Modify: `ur_print_fdm/config/defaults.py`
- Modify: `ur_print_fdm/ui/services/log_service.py`
- Modify: `ur_print_fdm/ui/main_window.py`

**Steps**
1. Add `ui.log_max_lines` default.
2. Use `QTextDocument.setMaximumBlockCount()` to bound memory growth.
3. Respect `ui.auto_scroll_log` for scroll behavior.

---

### Task 7: Optimize G-code parsing hotpaths

**Files:**
- Modify: `ur_print_fdm/processes/gcode_planar.py`

**Steps**
1. Avoid per-line regex scanning for X/Y/Z/E/F by tokenizing once.
2. Verify: `pytest -q` → all tests pass.

---

### Task 8: Make script sanitizer honest + useful

**Files:**
- Modify: `ur_print_fdm/core/script_sanitizer.py`
- Modify: `ur_print_fdm/core/driver.py`
- Test: `ur_print_fdm/tests/test_script_sanitizer.py`

**Steps**
1. Centralize `sanitize_script_content()` in `core/script_sanitizer.py`.
2. Define sanitizer as *normalization* (strip control chars, normalize newlines), not a security sandbox.
3. Verify: `pytest -q` → all tests pass.

