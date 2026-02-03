from __future__ import annotations

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ur_print_fdm.constants import DEFAULT_DO_INDEX, SCRIPT_PORT
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

    def queue_add_to_dialog(self, dialog_list) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self._window,
            "添加脚本",
            "",
            "URScript (*.script *.txt);;All (*.*)",
        )
        if files:
            for f in files:
                dialog_list.addItem(f)
            self._window.log(f"添加 {len(files)} 个文件到队列。")

    def queue_remove_from_dialog(self, dialog_list) -> None:
        for item in dialog_list.selectedItems():
            dialog_list.takeItem(dialog_list.row(item))

    def save_selected_script_dialog(self, dialog_list) -> None:
        selected_items = dialog_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self._window, "提示", "请先选择要保存的脚本")
            return

        file_path, _ = QFileDialog.getSaveFileName(self._window, "保存脚本", "", "URScript (*.script)")
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self._window.dockable_editor.current_text())
            self._window.log(f"已保存到文件: {file_path}")
        except Exception as e:
            self._window.log(f"保存文件失败: {e}", "ERROR")
            QMessageBox.critical(self._window, "错误", f"保存文件失败:\n{e}")

    def start_production_dialog(self, dialog_list, watchdog_enabled, prog_bar) -> None:
        if dialog_list.count() == 0:
            QMessageBox.warning(self._window, "提示", "队列为空")
            return

        ip = self._window.ip_combo.currentText()
        scripts = [dialog_list.item(i).text() for i in range(dialog_list.count())]

        self._window.processor = ProductionProcessor(
            ip,
            SCRIPT_PORT,
            scripts,
            do_index=DEFAULT_DO_INDEX,
            watchdog_enable=watchdog_enabled,
        )

        self._window.processor.log_signal.connect(self._window.log)
        self._window.processor.progress_signal.connect(lambda c, t: (prog_bar.setMaximum(t), prog_bar.setValue(c)))
        self._window.processor.finished_signal.connect(self._window.on_prod_finished_dialog)
        self._window.processor.error_signal.connect(lambda e: self._window.log(f"Error: {e}", "ERROR"))

        parent = dialog_list.parent()
        if hasattr(parent, "btn_start_batch") and hasattr(parent, "btn_stop_batch"):
            parent.btn_start_batch.setEnabled(False)
            parent.btn_stop_batch.setEnabled(True)

        self._window.processor.start()

    def stop_production_dialog(self) -> None:
        if self._window.processor and self._window.processor.isRunning():
            reply = QMessageBox.question(
                self._window,
                "急停",
                "确定要立即停止?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._window.processor.emergency_stop_action()

    def on_prod_finished_dialog(self) -> None:
        if self._window.queue_dialog:
            self._window.queue_dialog.btn_start_batch.setEnabled(True)
            self._window.queue_dialog.btn_stop_batch.setEnabled(False)
        self._window.log("生产任务结束")
