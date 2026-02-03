from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QStackedWidget,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
    QDialogButtonBox,
    QInputDialog,
)

from ur_print_fdm.config import config_manager
from ur_print_fdm.shared.net import is_valid_ip


@dataclass(frozen=True)
class _Category:
    id: str
    title: str
    keywords: tuple[str, ...]
    factory: Callable[[], QWidget]


class PreferencesDialog(QDialog):
    settings_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置中心 / 首选项")
        self.resize(920, 600)

        self._original_config = config_manager.snapshot()
        self._working_config = copy.deepcopy(self._original_config)
        self._dirty = False

        self._categories: list[_Category] = []
        self._category_items: dict[str, QListWidgetItem] = {}

        self._build_ui()
        self._build_categories()
        self._apply_search("")

    # -----------------------------
    # Config helpers (working copy)
    # -----------------------------

    def _get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split(".") if key_path else []
        current: Any = self._working_config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def _set(self, key_path: str, value: Any) -> None:
        keys = key_path.split(".") if key_path else []
        if not keys:
            return

        current: dict[str, Any] = self._working_config
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        old_value = current.get(keys[-1], None)
        if old_value == value:
            return

        current[keys[-1]] = copy.deepcopy(value)
        self._update_dirty_state()

    def _update_dirty_state(self) -> None:
        self.set_dirty(self._working_config != self._original_config)

    def _current_category_id(self) -> str | None:
        item = self.category_list.currentItem()
        if item is None:
            return None
        val = item.data(Qt.ItemDataRole.UserRole)
        return str(val) if val else None

    def _rebuild_from_working_config(self, *, keep_category: bool = True) -> None:
        current_id = self._current_category_id() if keep_category else None
        search = self.search_edit.text()
        self._build_categories(initial_category_id=current_id)
        self._apply_search(search)
        self._update_dirty_state()

    # -----------------------------
    # UI
    # -----------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Search bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索设置（例如：日志 / watchdog / SFTP / IP）…")
        self.search_edit.textChanged.connect(self._apply_search)
        self.search_edit.setMinimumHeight(32)
        layout.addWidget(self.search_edit)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        # Left: category list
        self.category_list = QListWidget()
        self.category_list.setMinimumWidth(230)
        self.category_list.currentRowChanged.connect(self._on_category_changed)
        splitter.addWidget(self.category_list)

        # Right: pages
        self.pages = QStackedWidget()
        splitter.addWidget(self.pages)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Bottom buttons: import/export/reset + Apply/OK/Cancel
        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        self.btn_reset = QPushButton("恢复默认")
        self.btn_reset.clicked.connect(self._reset_defaults)

        self.btn_import = QPushButton("导入…")
        self.btn_import.clicked.connect(self._import_json)

        self.btn_export = QPushButton("导出…")
        self.btn_export.clicked.connect(self._export_json)

        bottom.addWidget(self.btn_reset)
        bottom.addWidget(self.btn_import)
        bottom.addWidget(self.btn_export)
        bottom.addStretch(1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)
        self.button_box.accepted.connect(self._on_ok)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        bottom.addWidget(self.button_box)

        layout.addLayout(bottom)

    def _build_categories(self, *, initial_category_id: str | None = None) -> None:
        self._categories = [
            _Category("robot", "机器人与连接", ("robot", "ip", "backend", "连接"), self._page_robot),
            _Category("transfer", "传输 (SFTP)", ("sftp", "upload", "传输"), self._page_transfer),
            _Category("printing", "生产参数", ("printing", "modbus", "extruder", "挤出"), self._page_printing),
            _Category("safety", "安全", ("watchdog", "安全"), self._page_safety),
            _Category("project", "项目", ("project", "删除", "confirm"), self._page_project),
            _Category("ui", "界面", ("ui", "theme", "panel", "window"), self._page_ui),
            _Category("logging", "日志", ("log", "logging", "保存", "路径"), self._page_logging),
            _Category("advanced", "高级 (全部设置)", ("json", "advanced", "全部"), self._page_advanced),
        ]

        self.category_list.clear()
        while self.pages.count():
            page = self.pages.widget(0)
            self.pages.removeWidget(page)
            page.deleteLater()
        self._category_items.clear()

        for cat in self._categories:
            item = QListWidgetItem(cat.title)
            item.setData(Qt.ItemDataRole.UserRole, cat.id)
            self.category_list.addItem(item)
            self._category_items[cat.id] = item
            self.pages.addWidget(cat.factory())

        if initial_category_id:
            for i, cat in enumerate(self._categories):
                if cat.id == initial_category_id:
                    self.category_list.setCurrentRow(i)
                    break
            else:
                self.category_list.setCurrentRow(0)
        else:
            self.category_list.setCurrentRow(0)

    # -----------------------------
    # Pages
    # -----------------------------

    def _page_robot(self) -> QWidget:
        from ur_print_fdm.plugins.registry import registry

        w = QWidget()
        root = QVBoxLayout(w)

        # ---- Backend ----
        grp_backend = QGroupBox("后端 / 驱动")
        form_backend = QFormLayout(grp_backend)

        backend_combo = QComboBox()
        backend_combo.setEditable(False)
        backend_ids = sorted(registry.robot_backends.keys())
        backend_combo.addItems(backend_ids)
        backend_combo.setCurrentText(str(self._get("robot.backend_id", "ur_rtde_cb3")))
        backend_combo.currentTextChanged.connect(lambda v: self._set("robot.backend_id", str(v).strip()))
        form_backend.addRow("机器人后端：", backend_combo)

        lbl_restart = QLabel("提示：切换后端需要重启软件后生效。")
        lbl_restart.setProperty("ui_role", "warning")
        lbl_restart.setWordWrap(True)
        form_backend.addRow("", lbl_restart)
        root.addWidget(grp_backend)

        # ---- Connection ----
        grp_conn = QGroupBox("连接")
        form_conn = QFormLayout(grp_conn)

        chk_auto = QCheckBox("自动重连（断线后自动尝试重连）")
        chk_auto.setChecked(bool(self._get("robot.auto_reconnect", True)))
        chk_auto.stateChanged.connect(lambda _: self._set("robot.auto_reconnect", bool(chk_auto.isChecked())))
        form_conn.addRow(chk_auto)

        spin_speed = QSpinBox()
        spin_speed.setRange(1, 200)
        spin_speed.setSuffix(" %")
        spin_speed.setValue(int(self._get("robot.speed_slider_default", 100) or 100))
        spin_speed.valueChanged.connect(lambda v: self._set("robot.speed_slider_default", int(v)))
        form_conn.addRow("速度滑块默认值：", spin_speed)
        root.addWidget(grp_conn)

        # ---- IP list ----
        grp_ip = QGroupBox("IP 地址")
        v_ip = QVBoxLayout(grp_ip)

        ip_list = QListWidget()
        for ip in (self._get("robot.ip_addresses", []) or []):
            ip_list.addItem(str(ip))
        v_ip.addWidget(ip_list)

        default_ip = str(self._get("robot.default_ip", "") or "")
        lbl_default = QLabel(f"默认 IP：{default_ip if default_ip else '（未设置）'}")
        v_ip.addWidget(lbl_default)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("添加…")
        btn_remove = QPushButton("移除")
        btn_up = QPushButton("上移")
        btn_down = QPushButton("下移")
        btn_default = QPushButton("设为默认")
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_up)
        btn_row.addWidget(btn_down)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_default)
        v_ip.addLayout(btn_row)

        def _ip_items() -> list[str]:
            return [ip_list.item(i).text().strip() for i in range(ip_list.count()) if ip_list.item(i).text().strip()]

        def _write_ip_config(*, ensure_default: bool = True) -> None:
            ips = _ip_items()
            self._set("robot.ip_addresses", ips)
            if ensure_default:
                cur_default = str(self._get("robot.default_ip", "") or "")
                if cur_default and cur_default not in ips and ips:
                    self._set("robot.default_ip", ips[0])
                elif not cur_default and ips:
                    self._set("robot.default_ip", ips[0])
            lbl_default.setText(f"默认 IP：{str(self._get('robot.default_ip','') or '') or '（未设置）'}")

        def _selected_row() -> int:
            return ip_list.currentRow()

        def _refresh_buttons() -> None:
            row = _selected_row()
            has_sel = row >= 0
            btn_remove.setEnabled(has_sel)
            btn_default.setEnabled(has_sel)
            btn_up.setEnabled(has_sel and row > 0)
            btn_down.setEnabled(has_sel and row >= 0 and row < ip_list.count() - 1)

        ip_list.currentRowChanged.connect(lambda _: _refresh_buttons())
        ip_list.itemDoubleClicked.connect(lambda _: btn_default.click())

        def _add_ip() -> None:
            ip, ok = QInputDialog.getText(self, "添加 IP", "请输入机器人 IP 地址：")
            if not ok:
                return
            ip = str(ip).strip()
            if not ip:
                return
            if not is_valid_ip(ip):
                QMessageBox.warning(self, "IP 无效", f"不是有效的 IP 地址：{ip}")
                return
            existing = set(_ip_items())
            if ip in existing:
                QMessageBox.information(self, "已存在", f"该 IP 已在列表中：{ip}")
                return
            ip_list.addItem(ip)
            ip_list.setCurrentRow(ip_list.count() - 1)
            _write_ip_config()

        def _remove_ip() -> None:
            row = _selected_row()
            if row < 0:
                return
            item = ip_list.takeItem(row)
            del item
            _write_ip_config()
            _refresh_buttons()

        def _move(row_delta: int) -> None:
            row = _selected_row()
            if row < 0:
                return
            new_row = row + int(row_delta)
            if new_row < 0 or new_row >= ip_list.count():
                return
            item = ip_list.takeItem(row)
            ip_list.insertItem(new_row, item)
            ip_list.setCurrentRow(new_row)
            _write_ip_config(ensure_default=False)

        def _set_default() -> None:
            row = _selected_row()
            if row < 0:
                return
            ip = ip_list.item(row).text().strip()
            if ip:
                self._set("robot.default_ip", ip)
                lbl_default.setText(f"默认 IP：{ip}")
                self._update_dirty_state()

        btn_add.clicked.connect(_add_ip)
        btn_remove.clicked.connect(_remove_ip)
        btn_up.clicked.connect(lambda: _move(-1))
        btn_down.clicked.connect(lambda: _move(1))
        btn_default.clicked.connect(_set_default)
        _refresh_buttons()
        _write_ip_config()

        root.addWidget(grp_ip)
        root.addStretch(1)
        return w

    def _page_transfer(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)

        grp = QGroupBox("SFTP 上传参数")
        form = QFormLayout(grp)

        spin_port = QSpinBox()
        spin_port.setRange(1, 65535)
        spin_port.setValue(int(self._get("robot.sftp.port", 22) or 22))
        spin_port.valueChanged.connect(lambda v: self._set("robot.sftp.port", int(v)))
        form.addRow("端口：", spin_port)

        edit_user = QLineEdit(str(self._get("robot.sftp.username", "ur") or ""))
        edit_user.setPlaceholderText("例如：ur")
        edit_user.editingFinished.connect(lambda: self._set("robot.sftp.username", edit_user.text().strip()))
        form.addRow("用户名：", edit_user)

        edit_pwd = QLineEdit(str(self._get("robot.sftp.password", "") or ""))
        edit_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        edit_pwd.editingFinished.connect(lambda: self._set("robot.sftp.password", edit_pwd.text()))
        form.addRow("密码：", edit_pwd)

        edit_dir = QLineEdit(str(self._get("robot.sftp.remote_dir", "") or ""))
        edit_dir.setPlaceholderText("/home/ur/ursim-current/programs")
        edit_dir.editingFinished.connect(lambda: self._set("robot.sftp.remote_dir", edit_dir.text().strip()))
        form.addRow("远端目录：", edit_dir)

        lbl_tip = QLabel("提示：密码会以明文保存在本机配置文件中，请注意权限与备份。")
        lbl_tip.setProperty("ui_role", "muted")
        lbl_tip.setWordWrap(True)
        form.addRow("", lbl_tip)

        root.addWidget(grp)

        grp_dash = QGroupBox("Dashboard / Loader (生产控制)")
        form_dash = QFormLayout(grp_dash)

        edit_loader = QLineEdit(str(self._get("robot.dashboard.loader_urp_path", "") or ""))
        edit_loader.setPlaceholderText("/home/ur/ursim-current/programs/loader.urp")
        edit_loader.editingFinished.connect(
            lambda: self._set("robot.dashboard.loader_urp_path", edit_loader.text().strip())
        )
        form_dash.addRow("loader.urp 路径：", edit_loader)

        edit_remote = QLineEdit(str(self._get("robot.dashboard.remote_loader_name", "") or ""))
        edit_remote.setPlaceholderText("remote_loader.script")
        edit_remote.editingFinished.connect(
            lambda: self._set("robot.dashboard.remote_loader_name", edit_remote.text().strip())
        )
        form_dash.addRow("remote_loader 文件名：", edit_remote)

        lbl_dash_tip = QLabel(
            "提示：推荐在机器人端预先建立 loader.urp（内部引用 remote_loader.script）。\n"
            "URSim 常见路径：/home/ur/ursim-current/programs/loader.urp；真机 CB3 常见路径：/programs/loader.urp。"
        )
        lbl_dash_tip.setProperty("ui_role", "muted")
        lbl_dash_tip.setWordWrap(True)
        form_dash.addRow("", lbl_dash_tip)

        root.addWidget(grp_dash)
        root.addStretch(1)
        return w

    def _page_printing(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)

        # Extruder / IO
        grp_io = QGroupBox("挤出与 IO")
        form_io = QFormLayout(grp_io)

        spin_do = QSpinBox()
        spin_do.setRange(0, 15)
        spin_do.setValue(int(self._get("printing.extruder_io_pin", 0) or 0))
        spin_do.valueChanged.connect(lambda v: self._set("printing.extruder_io_pin", int(v)))
        form_io.addRow("挤出 DO 引脚：", spin_do)

        edit_modbus = QLineEdit(str(self._get("printing.modbus_extruder", "MODBUS_1") or ""))
        edit_modbus.setPlaceholderText("例如：MODBUS_1")
        edit_modbus.editingFinished.connect(lambda: self._set("printing.modbus_extruder", edit_modbus.text().strip()))
        form_io.addRow("挤出 Modbus 寄存器：", edit_modbus)

        root.addWidget(grp_io)

        # Defaults
        grp_defaults = QGroupBox("默认工艺参数")
        form_def = QFormLayout(grp_defaults)

        spin_dia = QDoubleSpinBox()
        spin_dia.setRange(0.1, 10.0)
        spin_dia.setSingleStep(0.05)
        spin_dia.setDecimals(2)
        spin_dia.setValue(float(self._get("printing.default_filament_diameter", 1.75) or 1.75))
        spin_dia.valueChanged.connect(lambda v: self._set("printing.default_filament_diameter", float(v)))
        form_def.addRow("丝径 (mm)：", spin_dia)

        spin_reg = QSpinBox()
        spin_reg.setRange(0, 65535)
        spin_reg.setValue(int(self._get("printing.default_base_register", 4000) or 4000))
        spin_reg.valueChanged.connect(lambda v: self._set("printing.default_base_register", int(v)))
        form_def.addRow("Modbus 基址寄存器：", spin_reg)

        spin_w = QDoubleSpinBox()
        spin_w.setRange(0.01, 50.0)
        spin_w.setSingleStep(0.1)
        spin_w.setDecimals(3)
        spin_w.setValue(float(self._get("printing.default_line_width", 1.0) or 1.0))
        spin_w.valueChanged.connect(lambda v: self._set("printing.default_line_width", float(v)))
        form_def.addRow("线宽 (mm)：", spin_w)

        spin_h = QDoubleSpinBox()
        spin_h.setRange(0.01, 20.0)
        spin_h.setSingleStep(0.05)
        spin_h.setDecimals(3)
        spin_h.setValue(float(self._get("printing.default_layer_height", 0.5) or 0.5))
        spin_h.valueChanged.connect(lambda v: self._set("printing.default_layer_height", float(v)))
        form_def.addRow("层高 (mm)：", spin_h)

        spin_speed = QDoubleSpinBox()
        spin_speed.setRange(0.01, 200.0)
        spin_speed.setSingleStep(0.5)
        spin_speed.setDecimals(2)
        spin_speed.setValue(float(self._get("printing.default_print_speed", 5.0) or 5.0))
        spin_speed.valueChanged.connect(lambda v: self._set("printing.default_print_speed", float(v)))
        form_def.addRow("打印速度：", spin_speed)

        root.addWidget(grp_defaults)

        # Turntable
        grp_tt = QGroupBox("转台 (Modbus)")
        form_tt = QFormLayout(grp_tt)

        edit_pin = QLineEdit(str(self._get("printing.modbus_turntable_pin", "") or ""))
        edit_pin.editingFinished.connect(lambda: self._set("printing.modbus_turntable_pin", edit_pin.text().strip()))
        form_tt.addRow("Pin：", edit_pin)

        edit_bu = QLineEdit(str(self._get("printing.modbus_turntable_bu", "") or ""))
        edit_bu.editingFinished.connect(lambda: self._set("printing.modbus_turntable_bu", edit_bu.text().strip()))
        form_tt.addRow("BU：", edit_bu)

        root.addWidget(grp_tt)
        root.addStretch(1)
        return w

    def _page_safety(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)

        grp = QGroupBox("看门狗 (Watchdog)")
        form = QFormLayout(grp)

        spin_timeout = QSpinBox()
        spin_timeout.setRange(5, 3600)
        spin_timeout.setSuffix(" 秒")
        spin_timeout.setValue(int(float(self._get("safety.watchdog_timeout", 120.0) or 120.0)))
        spin_timeout.valueChanged.connect(lambda v: self._set("safety.watchdog_timeout", float(v)))
        form.addRow("静止判定超时：", spin_timeout)

        spin_speed = QDoubleSpinBox()
        spin_speed.setRange(0.0, 0.1)
        spin_speed.setSingleStep(0.001)
        spin_speed.setDecimals(4)
        spin_speed.setSuffix(" m/s")
        spin_speed.setValue(float(self._get("safety.watchdog_speed_threshold", 0.002) or 0.002))
        spin_speed.valueChanged.connect(lambda v: self._set("safety.watchdog_speed_threshold", float(v)))
        form.addRow("静止速度阈值：", spin_speed)

        lbl = QLabel("建议：0.001 ~ 0.005。阈值过大可能误判静止，过小可能误判运动。")
        lbl.setProperty("ui_role", "muted")
        lbl.setWordWrap(True)
        form.addRow("", lbl)

        root.addWidget(grp)
        root.addStretch(1)
        return w

    def _page_project(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)

        grp = QGroupBox("项目")
        form = QFormLayout(grp)

        edit_path = QLineEdit(str(self._get("project.last_project_path", "") or ""))
        edit_path.setPlaceholderText("最近打开的项目路径")

        btn_browse = QPushButton("浏览…")
        btn_clear = QPushButton("清空")
        h = QHBoxLayout()
        h.addWidget(edit_path, 1)
        h.addWidget(btn_browse)
        h.addWidget(btn_clear)

        def _browse() -> None:
            p = QFileDialog.getExistingDirectory(self, "选择项目目录", str(Path(edit_path.text() or "").expanduser()))
            if p:
                edit_path.setText(p)
                self._set("project.last_project_path", p)

        def _clear() -> None:
            edit_path.setText("")
            self._set("project.last_project_path", "")

        btn_browse.clicked.connect(_browse)
        btn_clear.clicked.connect(_clear)
        edit_path.editingFinished.connect(lambda: self._set("project.last_project_path", edit_path.text().strip()))
        form.addRow("最近项目：", h)

        chk_confirm = QCheckBox("删除/清理项目文件前需要二次确认")
        chk_confirm.setChecked(bool(self._get("project.confirm_deletion", True)))
        chk_confirm.stateChanged.connect(lambda _: self._set("project.confirm_deletion", bool(chk_confirm.isChecked())))
        form.addRow(chk_confirm)

        root.addWidget(grp)
        root.addStretch(1)
        return w

    def _page_ui(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)

        grp_theme = QGroupBox("主题与窗口")
        form_theme = QFormLayout(grp_theme)

        chk_dark = QCheckBox("启用深色主题")
        chk_dark.setChecked(bool(self._get("ui.dark_theme", True)))
        chk_dark.stateChanged.connect(lambda _: self._set("ui.dark_theme", bool(chk_dark.isChecked())))
        # Theme selector (Dark / Light). Keep the existing boolean config key for compatibility.
        chk_dark.setVisible(False)

        cmb_theme = QComboBox()
        cmb_theme.addItem("暗色（推荐）", True)
        cmb_theme.addItem("白色", False)
        cmb_theme.setCurrentIndex(0 if chk_dark.isChecked() else 1)
        cmb_theme.currentIndexChanged.connect(lambda _: chk_dark.setChecked(bool(cmb_theme.currentData())))
        form_theme.addRow("主题：", cmb_theme)

        window_size = self._get("ui.window_size", [1400, 900]) or [1400, 900]
        try:
            width = int(window_size[0])
            height = int(window_size[1])
        except Exception:
            width, height = 1400, 900

        spin_w = QSpinBox()
        spin_w.setRange(600, 8000)
        spin_w.setValue(width)
        spin_h = QSpinBox()
        spin_h.setRange(400, 8000)
        spin_h.setValue(height)

        def _set_size() -> None:
            self._set("ui.window_size", [int(spin_w.value()), int(spin_h.value())])

        spin_w.valueChanged.connect(lambda _: _set_size())
        spin_h.valueChanged.connect(lambda _: _set_size())
        row = QHBoxLayout()
        row.addWidget(QLabel("宽："))
        row.addWidget(spin_w)
        row.addSpacing(12)
        row.addWidget(QLabel("高："))
        row.addWidget(spin_h)
        row.addStretch(1)
        form_theme.addRow("窗口大小：", row)

        lbl_restart = QLabel("提示：主题切换会在点击 Apply/确定 后立即生效；窗口大小也会在退出时自动保存。")
        lbl_restart.setProperty("ui_role", "muted")
        lbl_restart.setWordWrap(True)
        form_theme.addRow("", lbl_restart)

        root.addWidget(grp_theme)

        # Log viewer
        grp_log = QGroupBox("日志面板")
        form_log = QFormLayout(grp_log)

        chk_scroll = QCheckBox("自动滚动到最新日志")
        chk_scroll.setChecked(bool(self._get("ui.auto_scroll_log", True)))
        chk_scroll.stateChanged.connect(lambda _: self._set("ui.auto_scroll_log", bool(chk_scroll.isChecked())))
        form_log.addRow(chk_scroll)

        spin_lines = QSpinBox()
        spin_lines.setRange(100, 200000)
        spin_lines.setSingleStep(100)
        spin_lines.setValue(int(self._get("ui.log_max_lines", 2000) or 2000))
        spin_lines.valueChanged.connect(lambda v: self._set("ui.log_max_lines", int(v)))
        form_log.addRow("最大保留行数：", spin_lines)

        root.addWidget(grp_log)

        # Panels collapsed
        grp_panels = QGroupBox("面板默认折叠")
        form_panels = QFormLayout(grp_panels)

        def _panel_checkbox(title: str, key: str) -> QCheckBox:
            cb = QCheckBox(title)
            cb.setChecked(bool(self._get(f"ui.panels.{key}", False)))
            cb.stateChanged.connect(lambda _: self._set(f"ui.panels.{key}", bool(cb.isChecked())))
            return cb

        form_panels.addRow(_panel_checkbox("关节面板", "joint_panel_collapsed"))
        form_panels.addRow(_panel_checkbox("TCP 面板", "tcp_panel_collapsed"))
        form_panels.addRow(_panel_checkbox("偏移面板", "offset_panel_collapsed"))
        form_panels.addRow(_panel_checkbox("统计面板", "stats_panel_collapsed"))
        form_panels.addRow(_panel_checkbox("运动面板", "motion_panel_collapsed"))
        form_panels.addRow(_panel_checkbox("挤出面板", "extrusion_panel_collapsed"))

        root.addWidget(grp_panels)

        grp_script_est = QGroupBox("脚本估算")
        form_script_est = QFormLayout(grp_script_est)
        chk_est_on_run = QCheckBox("运行时自动估算打印时间/线材 (URScript)")
        chk_est_on_run.setChecked(bool(self._get("ui.urscript_estimate_on_run", False)))
        chk_est_on_run.stateChanged.connect(
            lambda _: self._set("ui.urscript_estimate_on_run", bool(chk_est_on_run.isChecked()))
        )
        form_script_est.addRow(chk_est_on_run)

        root.addWidget(grp_script_est)
        root.addStretch(1)
        return w

    def _page_logging(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)

        grp_file = QGroupBox("文件日志（持久化）")
        form_file = QFormLayout(grp_file)

        cmb_level = QComboBox()
        cmb_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        cmb_level.setCurrentText(str(self._get("logging.level", "INFO") or "INFO").upper())
        cmb_level.currentTextChanged.connect(lambda v: self._set("logging.level", str(v).upper()))
        form_file.addRow("写入级别：", cmb_level)

        spin_ret = QSpinBox()
        spin_ret.setRange(1, 365)
        spin_ret.setValue(int(self._get("logging.retention_days", 14) or 14))
        spin_ret.valueChanged.connect(lambda v: self._set("logging.retention_days", int(v)))
        form_file.addRow("保留天数：", spin_ret)

        edit_dir = QLineEdit(str(self._get("logging.dir", "") or ""))
        edit_dir.setPlaceholderText("留空使用默认目录（~/.ur_print_fdm/logs）")
        btn_dir = QPushButton("选择…")
        row = QHBoxLayout()
        row.addWidget(edit_dir, 1)
        row.addWidget(btn_dir)

        def _browse_dir() -> None:
            base = edit_dir.text().strip()
            start = str(Path(base).expanduser()) if base else str(Path.home())
            p = QFileDialog.getExistingDirectory(self, "选择日志目录", start)
            if p:
                edit_dir.setText(p)
                self._set("logging.dir", p)

        btn_dir.clicked.connect(_browse_dir)
        edit_dir.editingFinished.connect(lambda: self._set("logging.dir", edit_dir.text().strip()))
        form_file.addRow("日志目录：", row)

        root.addWidget(grp_file)

        grp_ui = QGroupBox("界面日志（面板显示）")
        form_ui = QFormLayout(grp_ui)

        cmb_ui = QComboBox()
        cmb_ui.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        cmb_ui.setCurrentText(str(self._get("logging.ui_level", "INFO") or "INFO").upper())
        cmb_ui.currentTextChanged.connect(lambda v: self._set("logging.ui_level", str(v).upper()))
        form_ui.addRow("显示级别：", cmb_ui)

        chk_third = QCheckBox("显示第三方库日志（可能更噪）")
        chk_third.setChecked(bool(self._get("logging.ui_show_third_party", False)))
        chk_third.stateChanged.connect(lambda _: self._set("logging.ui_show_third_party", bool(chk_third.isChecked())))
        form_ui.addRow(chk_third)

        root.addWidget(grp_ui)
        root.addStretch(1)
        return w

    def _page_advanced(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)

        label = QLabel(
            "高级（全部设置）\n\n"
            "此页提供完整配置的 JSON 视图/编辑入口：\n"
            "- 建议仅在明确知道含义时修改\n"
            "- 应用前请先“校验”确保 JSON 合法\n"
            "- 最终写入仍会按默认配置进行合并（缺失项会补默认值）"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        label.setWordWrap(True)
        root.addWidget(label)

        editor = QPlainTextEdit()
        editor.setPlaceholderText("{\n  \"robot\": { ... }\n}")
        editor.setPlainText(json.dumps(self._working_config, ensure_ascii=False, indent=2))
        root.addWidget(editor, 1)

        btn_row = QHBoxLayout()
        btn_reload = QPushButton("从当前设置生成")
        btn_validate = QPushButton("校验")
        btn_apply = QPushButton("应用到工作副本")
        btn_row.addWidget(btn_reload)
        btn_row.addWidget(btn_validate)
        btn_row.addWidget(btn_apply)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        def _reload() -> None:
            editor.setPlainText(json.dumps(self._working_config, ensure_ascii=False, indent=2))

        def _parse() -> dict[str, Any] | None:
            text = editor.toPlainText() or ""
            try:
                data = json.loads(text) if text.strip() else {}
            except Exception as e:
                QMessageBox.critical(self, "JSON 解析失败", f"无法解析 JSON：{e}")
                return None
            if not isinstance(data, dict):
                QMessageBox.critical(self, "JSON 无效", "JSON 根节点必须是对象（dict）。")
                return None
            return data

        def _validate() -> None:
            data = _parse()
            if data is None:
                return
            QMessageBox.information(self, "校验通过", "JSON 语法正确，且根节点为对象。")

        def _apply_json() -> None:
            data = _parse()
            if data is None:
                return
            self._working_config = data
            self._rebuild_from_working_config(keep_category=True)

        btn_reload.clicked.connect(_reload)
        btn_validate.clicked.connect(_validate)
        btn_apply.clicked.connect(_apply_json)
        return w

    # -----------------------------
    # State / Apply
    # -----------------------------

    def set_dirty(self, dirty: bool = True) -> None:
        self._dirty = bool(dirty)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).setEnabled(self._dirty)

    def apply(self) -> None:
        # Apply current working config to the global config manager.
        try:
            config_manager.apply_dict(self._working_config)
            if not config_manager.save_config():
                raise OSError("无法写入配置文件")
        except Exception as e:
            QMessageBox.critical(self, "应用失败", f"应用设置时出错：{e}")
            return

        self._original_config = config_manager.snapshot()
        self._working_config = copy.deepcopy(self._original_config)
        self._rebuild_from_working_config()
        self.settings_applied.emit()

    def _on_ok(self) -> None:
        if self._dirty:
            self.apply()
            if self._dirty:
                return
        self.accept()

    # -----------------------------
    # Import / Export / Reset
    # -----------------------------

    def _reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self,
            "恢复默认",
            "确定要恢复为默认设置吗？\n（需要点击“应用/确定”才会写入配置。）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._working_config = copy.deepcopy(config_manager.default_config)
        self._rebuild_from_working_config()

    def _export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出配置", "ur_print_fdm_config.json", "JSON (*.json)")
        if not path:
            return
        try:
            text = json.dumps(self._working_config, ensure_ascii=False, indent=2)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出配置失败：{e}")

    def _import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "JSON (*.json)")
        if not path:
            return
        try:
            text = open(path, "r", encoding="utf-8").read()
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("JSON 根节点必须是对象（dict）")
            self._working_config = data
            self._rebuild_from_working_config()
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入配置失败：{e}")

    # -----------------------------
    # Navigation / Search
    # -----------------------------

    def _on_category_changed(self, row: int) -> None:
        if row < 0:
            return
        self.pages.setCurrentIndex(row)

    def _apply_search(self, text: str) -> None:
        q = (text or "").strip().lower()
        for i, cat in enumerate(self._categories):
            item = self.category_list.item(i)
            if not q:
                item.setHidden(False)
                continue
            hay = " ".join((cat.title, cat.id, *cat.keywords)).lower()
            item.setHidden(q not in hay)
