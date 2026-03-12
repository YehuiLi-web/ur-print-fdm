from __future__ import annotations

from PyQt6.QtWidgets import QFileDialog

from ur_print_fdm.constants import DEFAULT_DO_INDEX, SCRIPT_PORT
from ur_print_fdm.shared.logging_context import new_trace_id, trace_context
from ur_print_fdm.shared.net import is_valid_ip
from ur_print_fdm.shared.operation_result import OperationResult
from ur_print_fdm.ui.services.file_service import file_service
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox
from ur_print_fdm.ui.workers.production_processor import ProductionProcessor


class QueueController:
    def __init__(self, window):
        self._window = window

    def show_queue_panel(self) -> None:
        if self._window.queue_dialog is None:
            from ur_print_fdm.ui.widgets.queue_dialog import QueueDialog

            self._window.queue_dialog = QueueDialog(self._window)
            self._window.queue_dialog.queue_list.itemDoubleClicked.connect(self._window.on_queue_item_double_clicked)
            self._window.queue_dialog.finished.connect(self._window.on_queue_dialog_closed)
        else:
            self._window.queue_dialog.show()

        self._window.queue_dialog.raise_()
        self._window.queue_dialog.activateWindow()

    def on_queue_dialog_closed(self) -> None:
        self._window.queue_dialog = None

    def _dialog_host(self, dialog_list):
        parent_getter = getattr(dialog_list, "parent", None)
        if callable(parent_getter):
            return parent_getter()
        return None

    def _queue_hosts(self, dialog_list) -> list[object]:
        hosts = []
        dialog_host = self._dialog_host(dialog_list)
        if dialog_host is not None:
            hosts.append(dialog_host)
        window = self._window
        if window is not None and window not in hosts:
            hosts.append(window)
        queue_dialog = getattr(window, "queue_dialog", None)
        if queue_dialog is not None and queue_dialog not in hosts:
            hosts.append(queue_dialog)
        return hosts

    def _set_queue_buttons_running(self, dialog_list) -> None:
        for host in self._queue_hosts(dialog_list):
            if getattr(host, "btn_start_batch", None) is not None:
                host.btn_start_batch.setEnabled(False)
            if getattr(host, "btn_stop_batch", None) is not None:
                host.btn_stop_batch.setEnabled(True)
            if getattr(host, "btn_pause_batch", None) is not None:
                host.btn_pause_batch.setEnabled(True)
                host.btn_pause_batch.setChecked(False)
                host.btn_pause_batch.setText("暂停")

    def _set_queue_buttons_idle(self) -> None:
        for host in self._queue_hosts(getattr(self._window, "queue_list", None) or object()):
            if getattr(host, "btn_start_batch", None) is not None:
                host.btn_start_batch.setEnabled(True)
            if getattr(host, "btn_stop_batch", None) is not None:
                host.btn_stop_batch.setEnabled(False)
            if getattr(host, "btn_pause_batch", None) is not None:
                host.btn_pause_batch.setEnabled(False)
                host.btn_pause_batch.setChecked(False)
                host.btn_pause_batch.setText("暂停")

    def _current_editor_text(self) -> str | None:
        editor = getattr(self._window, "dockable_editor", None)
        if editor is None:
            return None
        current_text = getattr(editor, "current_text", None)
        if callable(current_text):
            try:
                return str(current_text())
            except Exception:
                return None
        current_editor = getattr(self._window, "get_current_editor", None)
        if callable(current_editor):
            editor_obj = current_editor()
            if editor_obj is not None and hasattr(editor_obj, "toPlainText"):
                try:
                    return str(editor_obj.toPlainText())
                except Exception:
                    return None
        return None

    def queue_add(self, dialog_list) -> OperationResult:
        files, _ = QFileDialog.getOpenFileNames(
            self._window,
            "添加脚本",
            "",
            "URScript (*.script *.txt);;All (*.*)",
        )
        if not files:
            return OperationResult.fail("no queue files selected")

        for path in files:
            dialog_list.addItem(path)
        self._window.log(f"添加 {len(files)} 个文件到队列。")
        return OperationResult.ok("queue items added", payload=list(files))

    def queue_remove(self, dialog_list) -> OperationResult:
        removed = 0
        for item in dialog_list.selectedItems():
            dialog_list.takeItem(dialog_list.row(item))
            removed += 1
        if removed == 0:
            return OperationResult.fail("no queue selection")
        return OperationResult.ok("queue items removed", payload=removed)

    def save_selected_script(self, dialog_list) -> OperationResult:
        selected_items = list(dialog_list.selectedItems())
        if not selected_items:
            StyledMessageBox.warning(self._window, "提示", "请先选择要保存的脚本")
            return OperationResult.fail("no queue selection")

        if len(selected_items) > 1:
            StyledMessageBox.warning(self._window, "提示", "一次只能保存一个选中的脚本")
            return OperationResult.fail("multiple queue selections")

        content = self._current_editor_text()
        if content is None:
            StyledMessageBox.warning(self._window, "提示", "当前没有可保存的编辑器内容")
            return OperationResult.fail("no editor content")

        file_path = selected_items[0].text()
        result = file_service.write_text(file_path, content, action="save queue selection")
        if result.success:
            self._window.log(f"已保存到文件: {file_path}")
            return OperationResult.ok("queue selection saved", payload=file_path, detail=result.detail)

        self._window.log(f"保存文件失败: {result.detail}", "ERROR")
        StyledMessageBox.critical(self._window, "错误", f"保存文件失败：\n{result.detail}")
        return OperationResult.fail("save queue selection failed", detail=result.detail)

    def start_production(self, dialog_list, watchdog_enabled, prog_bar) -> OperationResult:
        if dialog_list.count() == 0:
            StyledMessageBox.warning(self._window, "提示", "队列为空")
            return OperationResult.fail("empty queue")

        active_task = getattr(self._window, "_has_connection_locked_operation", None)
        if callable(active_task) and active_task():
            StyledMessageBox.warning(self._window, "任务冲突", "机器人任务或停止操作进行中，请先等待当前操作结束。")
            return OperationResult.fail("task active")

        ip = str(self._window.ip_combo.currentText() or "").strip()
        if not is_valid_ip(ip):
            StyledMessageBox.warning(self._window, "IP 无效", f"不是有效的 IP 地址：{ip}")
            return OperationResult.fail("invalid ip")

        snapshot_getter = getattr(getattr(self._window, "driver", None), "get_connection_snapshot", None)
        if callable(snapshot_getter):
            snapshot = snapshot_getter()
            if snapshot is not None and not getattr(snapshot, "can_production_run", True):
                StyledMessageBox.warning(
                    self._window,
                    "连接不足",
                    "生产模式需要监控链路和 Dashboard 都可用，请先修复连接。",
                )
                return OperationResult.fail("insufficient connection")

        scripts = [dialog_list.item(i).text() for i in range(dialog_list.count())]

        trace_id = new_trace_id()
        self._window._active_production_trace_id = trace_id
        with trace_context(trace_id):
            self._window.log(f"[生产] 开始生产队列：{len(scripts)} 个脚本", "INFO")

        self._window.processor = ProductionProcessor(
            ip,
            SCRIPT_PORT,
            scripts,
            do_index=DEFAULT_DO_INDEX,
            watchdog_enable=watchdog_enabled,
            trace_id=trace_id,
        )
        self._window._direct_program_active = False

        driver = getattr(self._window, "driver", None)
        if driver is not None and hasattr(driver, "mark_control_stale"):
            driver.mark_control_stale("生产队列接管了控制脚本")
        refresher = getattr(self._window, "_apply_connection_snapshot", None)
        if callable(refresher) and callable(snapshot_getter):
            refresher(snapshot_getter())

        self._window.processor.log_signal.connect(self._window.log)
        if prog_bar is not None:
            self._window.processor.progress_signal.connect(lambda c, t: (prog_bar.setMaximum(t), prog_bar.setValue(c)))
        finished_cb = getattr(self._window, "on_prod_finished_dialog", None)
        if callable(finished_cb):
            self._window.processor.finished_signal.connect(finished_cb)
        else:
            self._window.processor.finished_signal.connect(self.on_prod_finished_dialog)
        error_cb = getattr(self._window, "_on_production_error", None)
        if callable(error_cb):
            self._window.processor.error_signal.connect(lambda e: error_cb(e, trace_id))
        else:
            self._window.processor.error_signal.connect(lambda e: self._window.log(f"Error: {e}", "ERROR"))
        progress_cb = getattr(self._window, "_on_single_run_file_progress", None)
        if callable(progress_cb):
            self._window.processor.file_progress_signal.connect(progress_cb)

        self._set_queue_buttons_running(dialog_list)

        if hasattr(self._window, "run_mode_combo"):
            try:
                self._window.run_mode_combo.setEnabled(False)
            except Exception:
                pass
        set_pause = getattr(self._window, "_set_play_pause_state", None)
        if callable(set_pause):
            set_pause("pause")

        self._window.processor.start()
        if callable(refresher) and callable(snapshot_getter):
            refresher(snapshot_getter())
        return OperationResult.ok("production started", payload=list(scripts))

    def stop_production(self) -> OperationResult:
        processor = getattr(self._window, "processor", None)
        if processor is None or not processor.isRunning():
            return OperationResult.fail("no active production")

        reply = StyledMessageBox.question(self._window, "急停", "确定要立即停止？")
        if reply != StyledMessageBox.Yes:
            return OperationResult.fail("cancelled")

        if hasattr(processor, "emergency_stop_action"):
            processor.emergency_stop_action()
        elif hasattr(processor, "stop"):
            processor.stop()
        resetter = getattr(self._window, "_reset_global_pause_button", None)
        if callable(resetter):
            resetter()
        if getattr(self._window, "queue_dialog", None) and hasattr(self._window.queue_dialog, "btn_pause_batch"):
            self._window.queue_dialog.btn_pause_batch.setEnabled(False)
        return OperationResult.ok("production stop requested")

    def pause_production(self, is_paused: bool) -> OperationResult:
        processor = getattr(self._window, "processor", None)
        if processor is None or not processor.isRunning():
            return OperationResult.fail("no active production")

        try:
            if is_paused and hasattr(processor, "request_pause"):
                processor.request_pause()
                self._window.log("生产已请求暂停", "INFO")
                setter = getattr(self._window, "_set_play_pause_state", None)
                if callable(setter):
                    setter("run")
                return OperationResult.ok("pause requested")
            if (not is_paused) and hasattr(processor, "request_resume"):
                processor.request_resume()
                self._window.log("生产已请求继续", "INFO")
                setter = getattr(self._window, "_set_play_pause_state", None)
                if callable(setter):
                    setter("pause")
                return OperationResult.ok("resume requested")
        except Exception as exc:
            self._window.log(f"暂停/继续失败: {exc}", "ERROR")
            return OperationResult.fail("pause resume failed", detail=str(exc))
        return OperationResult.fail("pause resume unsupported")

    def on_prod_finished_dialog(self) -> OperationResult:
        self._set_queue_buttons_idle()

        trace_id = getattr(self._window, "_active_production_trace_id", None)
        if trace_id:
            with trace_context(trace_id):
                self._window.log("生产任务结束")
            self._window._active_production_trace_id = None
        else:
            self._window.log("生产任务结束")

        if hasattr(self._window, "run_mode_combo"):
            try:
                self._window.run_mode_combo.setEnabled(True)
            except Exception:
                pass

        resetter = getattr(self._window, "_reset_global_pause_button", None)
        if callable(resetter):
            resetter()
        refresher = getattr(self._window, "_refresh_global_run_enabled", None)
        if callable(refresher):
            refresher()
        return OperationResult.ok("production finished")

    # Legacy aliases used by MainWindow / QueueDialog.
    def queue_add_to_dialog(self, dialog_list) -> OperationResult:
        return self.queue_add(dialog_list)

    def queue_remove_from_dialog(self, dialog_list) -> OperationResult:
        return self.queue_remove(dialog_list)

    def save_selected_script_dialog(self, dialog_list) -> OperationResult:
        return self.save_selected_script(dialog_list)

    def start_production_dialog(self, dialog_list, watchdog_enabled, prog_bar) -> OperationResult:
        return self.start_production(dialog_list, watchdog_enabled, prog_bar)

    def stop_production_dialog(self) -> OperationResult:
        return self.stop_production()
