from __future__ import annotations

import os

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ur_print_fdm.core import toolbox as ur_toolbox
from ur_print_fdm.config import config_manager
from ur_print_fdm.estimators.simple_gcode import SimpleGCodeTimeEstimator
from ur_print_fdm.plugins.registry import registry


class ToolsController:
    def __init__(self, window, dockable_editor, log):
        self._window = window
        self._dockable_editor = dockable_editor
        self._log = log

    def tool_gcode_convert(self) -> None:
        gpath, _ = QFileDialog.getOpenFileName(self._window, "选择G-code", "", "G-code (*.gcode)")
        if not gpath:
            return

        out_path, _ = QFileDialog.getSaveFileName(self._window, "保存", gpath + ".script", "URScript (*.script)")
        if not out_path:
            return

        params = {
            "sp_print": 5.0,
            "sp_travel": 20.0,
            "line_width": 1.0,
            "layer_height": 0.5,
            "filament_d": 1.75,
            "flow_factor": 1.0,
            "acc": 0.3,
            "feature1": "0.544,0.286,0.5,0.0007,-0.0002,0.0",
            "tool_rxyz": "1.677,-2.626,0.072",
            "modbus_id": "MODBUS_1",
            "s_start": 0.4,
            "s_stop": 0.1,
            "use_tcp": True,
            "tcp_params": [0.09, 1.51, 164.41, 0, 0, 0],
        }

        try:
            converter = registry.gcode_converters.get("gcode_planar_v1")
            ok = (
                converter.convert(gpath, out_path, params)
                if converter is not None
                else ur_toolbox.gcode_to_urscript(gpath, out_path, params)
            )

            if not ok:
                return

            self._log(f"转换成功: {os.path.basename(out_path)}", "SUCCESS")

            try:
                ops = converter.parse(gpath) if converter is not None else ur_toolbox.parse_gcode(gpath)
                traj = SimpleGCodeTimeEstimator.trajectory_from_gcode_ops(ops)
                estimator = registry.estimators.get("simple_gcode_v1")
                if estimator is not None:
                    result = estimator.estimate(traj)
                    total_s = int(round(result.total_time_s))
                    h = total_s // 3600
                    m = (total_s % 3600) // 60
                    s = total_s % 60
                    self._log(f"预计打印时间（估算）: {h:02d}:{m:02d}:{s:02d}", "INFO")
            except Exception as e:
                self._log(f"时间估算失败: {e}", "WARN")

            with open(out_path, "r", encoding="utf-8") as f:
                self._dockable_editor.set_current_text(f.read())
        except Exception as e:
            self._log(f"转换失败: {e}", "ERROR")

    def tool_script_estimate(self, file_path: str | None = None) -> None:
        from ur_print_fdm.estimators.urscript import URScriptEstimateError, estimate_urscript

        script_text = ""
        display_name = ""

        if file_path:
            display_name = os.path.basename(file_path)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    script_text = f.read()
            except Exception as e:
                QMessageBox.critical(self._window, "错误", f"无法读取脚本文件:\n{e}")
                return
        else:
            script_text = self._dockable_editor.current_text() if self._dockable_editor else ""
            display_name = "当前脚本"

        if not script_text.strip():
            fpath, _ = QFileDialog.getOpenFileName(self._window, "选择脚本", "", "URScript (*.script);;Text (*.txt)")
            if not fpath:
                return
            return self.tool_script_estimate(fpath)

        extruder_modbus_id = str(config_manager.get("printing.modbus_extruder", "MODBUS_1") or "MODBUS_1").strip()

        current_tcp = None
        try:
            tcp, _, _, _ = self._window.driver.get_status()
            current_tcp = tcp if tcp is not None else None
        except Exception:
            current_tcp = None

        try:
            result = estimate_urscript(script_text, current_tcp_pose=current_tcp, extruder_modbus_id=extruder_modbus_id)
        except URScriptEstimateError as e:
            QMessageBox.warning(self._window, "脚本估算失败", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self._window, "脚本估算失败", f"{type(e).__name__}: {e}")
            return

        total_s = int(round(result.total_time_s))
        h = total_s // 3600
        m = (total_s % 3600) // 60
        s = total_s % 60
        time_str = f"{h:02d}:{m:02d}:{s:02d}"

        cf_m = result.cf_filament_mm / 1000.0
        ext_m = result.extruder_filament_mm / 1000.0
        msg_lines = [
            f"脚本: {display_name}",
            f"预估打印时间: {time_str}",
            f"连续碳纤维线长(按TCP路径): {cf_m:.3f} m",
            f"挤出机线长(MODBUS): {ext_m:.3f} m",
        ]
        if result.warnings:
            msg_lines.append("")
            msg_lines.append("提示:")
            msg_lines.extend(f"- {w}" for w in result.warnings)

        QMessageBox.information(self._window, "脚本估算", "\n".join(msg_lines))

    def tool_split_script(self) -> None:
        fpath, _ = QFileDialog.getOpenFileName(self._window, "选择脚本", "", "URScript (*.script)")
        if not fpath:
            return

        n = ur_toolbox.split_urscript(fpath, os.path.dirname(fpath) + "/split")
        self._log(f"分割完成: {n} 份", "INFO")

    def tool_insert_flag(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self._window, "选择脚本", "", "URScript (*.script)")
        if not files:
            return

        n = 0
        for f in files:
            if ur_toolbox.insert_flag(f):
                n += 1
        self._log(f"完成标志插入: {n} 个文件", "INFO")
