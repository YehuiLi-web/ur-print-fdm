from __future__ import annotations

import os

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QFileDialog

from ur_print_fdm.constants import DEFAULT_DO_INDEX, SCRIPT_PORT
from ur_print_fdm.shared.net import is_valid_ip
from ur_print_fdm.shared.logging_context import new_trace_id, trace_context
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox
from ur_print_fdm.ui.workers.direct_mode_processor import DirectModeProcessor
from ur_print_fdm.ui.workers.production_processor import ProductionProcessor
from ur_print_fdm.ui.workers.threads import StopThread


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

    def _save_current_script_for_run(self) -> str | None:
        current_editor = self._window.get_current_editor()
        if current_editor is None:
            return None

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

        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self._window,
                "保存脚本以运行（生产模式）",
                default_save_path,
                "URScript Files (*.script);;Text Files (*.txt);;All Files (*)",
            )

        if not file_path:
            return None

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            file_name = os.path.basename(file_path)
            try:
                self._window.dockable_editor.tabs.setTabText(current_tab_index, file_name)
                self._window.dockable_editor.tab_paths[current_tab_index] = file_path
            except Exception:
                pass

            try:
                old_paths_to_remove = []
                for path, editor in self._window.dockable_editor.editors.items():
                    if editor == current_editor and path != file_path:
                        old_paths_to_remove.append(path)
                for old_path in old_paths_to_remove:
                    if old_path in self._window.dockable_editor.editors:
                        del self._window.dockable_editor.editors[old_path]
                self._window.dockable_editor.editors[file_path] = current_editor
            except Exception:
                pass

            return file_path
        except Exception as e:
            self._window.log(f"保存失败: {e}", "ERROR")
            StyledMessageBox.critical(self._window, "错误", f"保存文件失败：\n{e}")
            return None

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

    def stop_direct_mode(self) -> None:
        trace_id = new_trace_id()

        if not self._window.driver.is_connected():
            self._window.log("未连接，无法发送停止指令。", "WARN")
            return

        with trace_context(trace_id):
            self._window.log("[停止] 正在发送停止指令... (直连模式 - 30002端口)")

        self._window.btn_global_stop.setEnabled(False)

        ip = self._window.driver.get_ip_address()
        stop_processor = DirectModeProcessor(ip, trace_id=trace_id)
        stop_processor.set_action_stop()
        stop_processor.connect_monitor()
        stop_processor.log_signal.connect(lambda msg: self._window.log(msg))
        stop_completed_cb = getattr(self._window, "on_direct_mode_stop_completed", None)
        if not callable(stop_completed_cb):
            stop_completed_cb = getattr(self._window, "_on_direct_mode_stop_completed", None)
        if callable(stop_completed_cb):
            stop_processor.stop_completed_signal.connect(stop_completed_cb)
        stop_processor.finished_signal.connect(stop_processor.deleteLater)
        stop_processor.start()

        self._window._direct_mode_stop_processor = stop_processor

    def run_current_script(self) -> None:
        current_editor = self._window.get_current_editor()
        if current_editor is None:
            return

        if self._get_active_production_processor() is not None:
            StyledMessageBox.information(self._window, "正在运行", "已有生产任务在运行中，请先停止/等待完成。")
            return

        if not self._window.driver.is_connected():
            StyledMessageBox.warning(self._window, "连接错误", "请先连接机器人（右上角 IP -> 连接）！")
            return

        selected_mode = "production"
        try:
            selected_mode = str(self._window.run_mode_combo.currentData() or "production")
        except Exception:
            selected_mode = "production"

        if self._window.driver.is_read_only():
            selected_mode = "production"
            try:
                idx = self._window.run_mode_combo.findData("production")
                if idx >= 0:
                    self._window.run_mode_combo.setCurrentIndex(idx)
            except Exception:
                pass

        if selected_mode == "production":
            script_path = self._save_current_script_for_run()
            if not script_path:
                return
            self._start_single_run_production(script_path)
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

    def stop_current_script(self) -> None:
        trace_id = new_trace_id()

        active = self._get_active_production_processor()
        if active is not None and active.isRunning():
            reply = StyledMessageBox.question(
                self._window,
                "停止生产",
                "确认停止当前生产任务？\n将发送 Dashboard stop，并尝试关闭挤出输出。",
            )
            if reply == StyledMessageBox.Yes:
                try:
                    if hasattr(active, "emergency_stop_action"):
                        active.emergency_stop_action()
                    else:
                        active.stop()
                    self._reset_global_pause_button()
                    self._reset_urscript_estimate_run()
                    with trace_context(trace_id):
                        self._window.log("[停止] 已请求停止（生产模式）。", "WARN")
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

        if not self._window.driver.is_connected():
            self._window.log("未连接，无法发送停止指令。", "WARN")
            return

        if self._window.stop_thread is not None and self._window.stop_thread.isRunning():
            with trace_context(trace_id):
                self._window.log("停止指令正在执行中，请稍候...", "WARN")
            return

        self._window.btn_global_stop.setEnabled(False)
        self._window.stop_thread = StopThread(self._window.driver, trace_id=trace_id)
        self._window.stop_thread.finished_signal.connect(self._window.on_stop_finished)

        self._window.stop_timeout_timer = QTimer()
        self._window.stop_timeout_timer.setSingleShot(True)
        self._window.stop_timeout_timer.timeout.connect(self._window.on_stop_timeout)
        self._window.stop_timeout_timer.start(5000)

        self._window.stop_thread.finished.connect(self._window.stop_thread.deleteLater)
        self._window.stop_thread.finished.connect(lambda: setattr(self._window, "stop_thread", None))
        self._window.stop_thread.finished.connect(self._window.stop_timeout_timer.stop)
        self._window.stop_thread.start()
