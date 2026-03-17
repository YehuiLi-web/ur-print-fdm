from __future__ import annotations

import os

from PyQt6.QtCore import QTimer
from ur_print_fdm.constants import DEFAULT_DO_INDEX, SCRIPT_PORT
from ur_print_fdm.shared.net import is_valid_ip
from ur_print_fdm.shared.logging_context import new_trace_id, trace_context
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox
from ur_print_fdm.ui.workers.direct_mode_processor import DirectModeProcessor
from ur_print_fdm.ui.workers.production_processor import ProductionProcessor
from ur_print_fdm.ui.workers.threads import StopThread, StopExtrusionThread


class RunController:
    def __init__(self, window) -> None:
        self._window = window

    def _get_active_production_processor(self):
        for proc in (getattr(self._window, "_single_run_processor", None), getattr(self._window, "processor", None)):
            if proc is not None and hasattr(proc, "isRunning") and proc.isRunning():
                return proc
        return None

    def _start_urscript_estimate_on_run(self, script_content: str, *, trace_id: str | None = None) -> None:
        starter = getattr(self._window, "start_urscript_estimate_on_run", None)
        if callable(starter):
            starter(script_content, trace_id=trace_id)
            return
        legacy_starter = getattr(self._window, "_start_urscript_estimate_on_run", None)
        if callable(legacy_starter):
            legacy_starter(script_content, trace_id=trace_id)

    def _set_play_pause_state(self, state: str) -> None:
        setter = getattr(self._window, "set_play_pause_state", None)
        if callable(setter):
            setter(state)
            return
        legacy_setter = getattr(self._window, "_set_play_pause_state", None)
        if callable(legacy_setter):
            legacy_setter(state)

    def _reset_global_pause_button(self) -> None:
        resetter = getattr(self._window, "reset_global_pause_button", None)
        if callable(resetter):
            resetter()
            return
        legacy_resetter = getattr(self._window, "_reset_global_pause_button", None)
        if callable(legacy_resetter):
            legacy_resetter()

    def _reset_urscript_estimate_run(self) -> None:
        resetter = getattr(self._window, "reset_urscript_estimate_run", None)
        if callable(resetter):
            resetter()
            return
        legacy_resetter = getattr(self._window, "_reset_urscript_estimate_run", None)
        if callable(legacy_resetter):
            legacy_resetter()

    def _start_robot_stop_thread(self, *, trace_id: str) -> bool:
        snapshot_getter = getattr(self._window.driver, "get_connection_snapshot", None)
        snapshot = snapshot_getter() if callable(snapshot_getter) else None
        if snapshot is not None:
            can_stop = bool(getattr(snapshot, "can_stop", False))
            preserve_control = bool(getattr(snapshot, "can_direct_control", False))
        else:
            can_stop = bool(self._window.driver.is_connected())
            preserve_control = not bool(self._window.driver.is_read_only())

        if not can_stop:
            self._window.log("未连接，无法发送停止指令。", "WARN")
            return False

        if self._window.stop_thread is not None and self._window.stop_thread.isRunning():
            with trace_context(trace_id):
                self._window.log("停止指令正在执行中，请稍候...", "WARN")
            return False

        with trace_context(trace_id):
            if preserve_control:
                self._window.log("[停止] 正在发送机械臂原生停止指令... (保留控制通道)")
            else:
                self._window.log("[停止] 正在发送机械臂停止指令...")

        self._window.btn_global_stop.setEnabled(False)
        self._window.stop_thread = StopThread(
            self._window.driver,
            preserve_control=preserve_control,
            trace_id=trace_id,
        )
        self._window.stop_thread.finished_signal.connect(self._window.on_stop_finished)

        self._window.stop_timeout_timer = QTimer()
        self._window.stop_timeout_timer.setSingleShot(True)
        self._window.stop_timeout_timer.timeout.connect(self._window.on_stop_timeout)
        self._window.stop_timeout_timer.start(5000)

        self._window.stop_thread.finished.connect(self._window.stop_thread.deleteLater)
        self._window.stop_thread.finished.connect(lambda: setattr(self._window, "stop_thread", None))
        self._window.stop_thread.finished.connect(self._window.stop_timeout_timer.stop)
        self._window.stop_thread.start()
        refresher = getattr(self._window, "_refresh_global_run_enabled", None)
        if callable(refresher):
            refresher()
        return True

    def _save_current_script_for_run(self) -> str | None:
        current_editor = self._window.get_current_editor()
        if current_editor is None:
            return None

        current_text = getattr(self._window.dockable_editor, "current_text", None)
        if callable(current_text):
            script_content = current_text()
        else:
            script_content = current_editor.toPlainText()
        if not script_content.strip():
            StyledMessageBox.information(self._window, "空脚本", "编辑器内容为空，无法运行。")
            return None

        current_tab_index = self._window.dockable_editor.tabs.currentIndex()
        file_path = ""
        try:
            maybe_path = self._window.dockable_editor.tab_paths.get(current_tab_index, "")
            if maybe_path and os.path.isabs(str(maybe_path)):
                file_path = str(maybe_path)
        except Exception:
            file_path = ""

        default_save_path = ""
        if not file_path and hasattr(self._window, "project_widget") and getattr(
            self._window.project_widget, "current_project_path", ""
        ):
            default_save_path = os.path.join(self._window.project_widget.current_project_path, "新脚本.script")

        return self._window.dockable_editor.save_current_tab(
            prompt_title="保存脚本以运行（生产模式）",
            default_save_path=default_save_path if not file_path else "",
            dialog_parent=self._window,
        )

    def _start_single_run_production(self, script_path: str) -> None:
        if not os.path.isfile(script_path):
            StyledMessageBox.warning(self._window, "文件不存在", f"脚本文件不存在：\n{script_path}")
            return

        if self._get_active_production_processor() is not None:
            StyledMessageBox.information(self._window, "正在运行", "已有生产任务在运行中，请先停止/等待完成。")
            return

        ip = str(self._window.ip_combo.currentText() or "").strip()
        if not is_valid_ip(ip):
            StyledMessageBox.warning(self._window, "IP 无效", f"不是有效的 IP 地址：{ip}")
            return

        trace_id = new_trace_id()
        self._window._single_run_trace_id = trace_id
        with trace_context(trace_id):
            self._window.log(f"[运行] 单文件生产运行：{os.path.basename(script_path)}", "INFO")

        script_text = ""
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                script_text = f.read()
        except Exception:
            script_text = ""

        self._start_urscript_estimate_on_run(script_text, trace_id=trace_id)

        watchdog_enabled = self._window.chk_watchdog.isChecked() if self._window.chk_watchdog else True
        proc = ProductionProcessor(
            ip,
            SCRIPT_PORT,
            [script_path],
            do_index=DEFAULT_DO_INDEX,
            watchdog_enable=watchdog_enabled,
            trace_id=trace_id,
        )
        self._window._single_run_processor = proc
        if hasattr(self._window.driver, "mark_control_stale"):
            self._window.driver.mark_control_stale("生产模式接管了控制脚本")
        refresher = getattr(self._window, "_apply_connection_snapshot", None)
        snapshot_getter = getattr(self._window.driver, "get_connection_snapshot", None)
        if callable(refresher) and callable(snapshot_getter):
            refresher(snapshot_getter())

        try:
            self._window.run_mode_combo.setEnabled(False)
        except Exception:
            pass
        self._set_play_pause_state("pause")

        progress_cb = getattr(self._window, "on_single_run_file_progress", None)
        if not callable(progress_cb):
            progress_cb = getattr(self._window, "_on_single_run_file_progress", None)
        if callable(progress_cb):
            proc.file_progress_signal.connect(progress_cb)

        error_cb = getattr(self._window, "on_production_error", None)
        if not callable(error_cb):
            error_cb = getattr(self._window, "_on_production_error", None)
        if callable(error_cb):
            proc.error_signal.connect(lambda e: error_cb(e, trace_id))
        else:
            proc.error_signal.connect(lambda e: self._window.log(f"生产错误: {e}", "ERROR"))

        finished_cb = getattr(self._window, "on_single_run_finished", None)
        if not callable(finished_cb):
            finished_cb = getattr(self._window, "_on_single_run_finished", None)
        if callable(finished_cb):
            proc.finished_signal.connect(finished_cb)

        proc.start()
        if callable(refresher) and callable(snapshot_getter):
            refresher(snapshot_getter())

    def stop_direct_mode(self) -> None:
        trace_id = new_trace_id()

        with trace_context(trace_id):
            self._window.log("[停止] 正在发送机械臂停止指令... (直连模式)")

        if (
            getattr(self._window, "_direct_mode_stop_processor", None) is not None
            and self._window._direct_mode_stop_processor.isRunning()
        ):
            with trace_context(trace_id):
                self._window.log("直连停止指令正在执行中，请稍候...", "WARN")
            return

        ip = str(self._window.driver.get_ip_address() or "").strip()
        if not is_valid_ip(ip):
            StyledMessageBox.warning(self._window, "连接错误", "当前没有可用于直连停止的机器人 IP。")
            return

        self._window.btn_global_stop.setEnabled(False)
        proc = DirectModeProcessor(ip, trace_id=trace_id)
        proc.set_action_stop()
        proc.log_signal.connect(lambda msg: self._window.log(msg))

        stop_cb = getattr(self._window, "on_direct_mode_stop_completed", None)
        if not callable(stop_cb):
            stop_cb = getattr(self._window, "_on_direct_mode_stop_completed", None)
        if callable(stop_cb):
            proc.stop_completed_signal.connect(stop_cb)

        proc.error_signal.connect(lambda msg: self._window.log(msg, "ERROR"))
        proc.finished_signal.connect(proc.deleteLater)
        proc.finished_signal.connect(lambda: setattr(self._window, "_direct_mode_stop_processor", None))

        refresher = getattr(self._window, "_refresh_global_run_enabled", None)
        if callable(refresher):
            proc.finished_signal.connect(refresher)

        self._window._direct_mode_stop_processor = proc
        proc.start()
        refresher = getattr(self._window, "_refresh_global_run_enabled", None)
        if callable(refresher):
            refresher()

    def run_current_script(self) -> None:
        current_editor = self._window.get_current_editor()
        if current_editor is None:
            return

        if self._get_active_production_processor() is not None:
            StyledMessageBox.information(self._window, "正在运行", "已有生产任务在运行中，请先停止/等待完成。")
            return

        if bool(getattr(self._window, "_direct_program_active", False)):
            StyledMessageBox.information(self._window, "正在运行", "直连脚本仍在执行中，请先停止或等待完成。")
            return

        if not self._window.driver.is_connected():
            StyledMessageBox.warning(self._window, "连接错误", "请先连接机器人（右上角 IP -> 连接）！")
            return

        snapshot_getter = getattr(self._window.driver, "get_connection_snapshot", None)
        snapshot = snapshot_getter() if callable(snapshot_getter) else None

        selected_mode = "production"
        try:
            selected_mode = str(self._window.run_mode_combo.currentData() or "production")
        except Exception:
            selected_mode = "production"

        if selected_mode == "production":
            if snapshot is not None and not getattr(snapshot, "can_production_run", False):
                StyledMessageBox.warning(
                    self._window,
                    "连接不足",
                    "生产模式需要监控链路和 Dashboard 都可用，请先修复连接。",
                )
                return
            script_path = self._save_current_script_for_run()
            if not script_path:
                return
            self._start_single_run_production(script_path)
            return

        if snapshot is not None and not getattr(snapshot, "can_direct_run", False):
            StyledMessageBox.warning(
                self._window,
                "连接不足",
                "直连模式需要至少保持监控链路可用，请先连接机器人。",
            )
            return

        script_content = current_editor.toPlainText()
        if not script_content.strip():
            StyledMessageBox.information(self._window, "空脚本", "编辑器内容为空，无法运行。")
            return

        if self._window._direct_mode_processor is not None and self._window._direct_mode_processor.isRunning():
            self._window.log("直连模式正在运行中，请稍候...")
            return

        trace_id = new_trace_id()
        with trace_context(trace_id):
            self._window.log("[运行] 正在发送当前脚本... (直连模式 - 30002端口)")

        self._start_urscript_estimate_on_run(script_content, trace_id=trace_id)
        self._window.btn_play_pause.setEnabled(False)

        ip = self._window.driver.get_ip_address()
        if not is_valid_ip(ip):
            StyledMessageBox.warning(self._window, "连接错误", f"当前机器人 IP 无效：{ip}")
            self._window.btn_play_pause.setEnabled(True)
            return

        self._window._direct_mode_processor = DirectModeProcessor(ip, script_content, trace_id=trace_id)
        self._window._direct_mode_processor.set_action_run(script_content)
        self._window._direct_mode_processor.log_signal.connect(lambda msg: self._window.log(msg))
        script_sent_cb = getattr(self._window, "on_direct_mode_script_sent", None)
        if not callable(script_sent_cb):
            script_sent_cb = getattr(self._window, "_on_direct_mode_script_sent", None)
        if callable(script_sent_cb):
            self._window._direct_mode_processor.script_sent_signal.connect(script_sent_cb)

        finished_cb = getattr(self._window, "on_direct_mode_finished", None)
        if not callable(finished_cb):
            finished_cb = getattr(self._window, "_on_direct_mode_finished", None)
        if callable(finished_cb):
            self._window._direct_mode_processor.finished_signal.connect(finished_cb)
        self._window._direct_mode_processor.error_signal.connect(lambda msg: self._window.log(msg, "ERROR"))
        self._window._direct_mode_processor.start()
        refresher = getattr(self._window, "_refresh_global_run_enabled", None)
        if callable(refresher):
            refresher()

    def stop_current_script(self) -> None:
        trace_id = new_trace_id()

        active = self._get_active_production_processor()
        if active is not None and active.isRunning():
            try:
                if hasattr(active, "stop"):
                    active.stop()
                elif hasattr(active, "emergency_stop_action"):
                    active.emergency_stop_action()
                self._reset_global_pause_button()
                self._reset_urscript_estimate_run()
                with trace_context(trace_id):
                    self._window.log("[停止] 已请求停止机械臂/当前程序（生产模式）。", "WARN")
            except Exception as e:
                with trace_context(trace_id):
                    self._window.log(f"停止失败: {e}", "ERROR")
            return

        selected_mode = "production"
        try:
            selected_mode = str(self._window.run_mode_combo.currentData() or "production")
        except Exception:
            selected_mode = "production"

        if selected_mode == "direct":
            self.stop_direct_mode()
            return
        self._start_robot_stop_thread(trace_id=trace_id)

    def stop_extrusion(self) -> None:
        trace_id = new_trace_id()

        snapshot_getter = getattr(self._window.driver, "get_connection_snapshot", None)
        snapshot = snapshot_getter() if callable(snapshot_getter) else None
        if snapshot is not None:
            can_stop = bool(getattr(snapshot, "can_stop", False))
        else:
            can_stop = bool(self._window.driver.is_connected())

        if not can_stop:
            self._window.log("未连接，无法发送停止挤出指令。", "WARN")
            return

        if (
            getattr(self._window, "extrusion_stop_thread", None) is not None
            and self._window.extrusion_stop_thread.isRunning()
        ):
            with trace_context(trace_id):
                self._window.log("停止挤出指令正在执行中，请稍候...", "WARN")
            return

        with trace_context(trace_id):
            self._window.log("[挤出] 正在发送停止挤出指令...")

        self._window.btn_extrusion_stop.setEnabled(False)
        self._window.extrusion_stop_thread = StopExtrusionThread(self._window.driver, trace_id=trace_id)
        self._window.extrusion_stop_thread.finished_signal.connect(self._window.on_extrusion_stop_finished)

        self._window.extrusion_stop_timeout_timer = QTimer()
        self._window.extrusion_stop_timeout_timer.setSingleShot(True)
        self._window.extrusion_stop_timeout_timer.timeout.connect(self._window.on_extrusion_stop_timeout)
        self._window.extrusion_stop_timeout_timer.start(5000)

        self._window.extrusion_stop_thread.finished.connect(self._window.extrusion_stop_thread.deleteLater)
        self._window.extrusion_stop_thread.finished.connect(
            lambda: setattr(self._window, "extrusion_stop_thread", None)
        )
        self._window.extrusion_stop_thread.finished.connect(
            self._window.extrusion_stop_timeout_timer.stop
        )
        self._window.extrusion_stop_thread.start()
        refresher = getattr(self._window, "_refresh_global_run_enabled", None)
        if callable(refresher):
            refresher()
