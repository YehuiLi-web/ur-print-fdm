from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QSpinBox, QLineEdit, QDialogButtonBox, QGroupBox,
                             QFormLayout, QMessageBox, QTabWidget, QWidget)
from PyQt6.QtCore import pyqtSignal
from ur_print_fdm.config import config_manager

class SettingsDialog(QDialog):
    settings_saved = pyqtSignal(dict)  # Signal emitted when settings are saved

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.resize(500, 400)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_io = QWidget()
        self.tab_general = QWidget() # Placeholder for future

        self.tabs.addTab(self.tab_io, "机器人与IO")
        self.tab_safety = QWidget()
        self.tabs.addTab(self.tab_safety, "安全设置")
        self.tabs.addTab(self.tab_general, "常规")

        layout.addWidget(self.tabs)

        # === IO Tab Setup ===
        io_layout = QVBoxLayout(self.tab_io)

        # Extruder Group
        grp_extruder = QGroupBox("挤出机硬件配置 (Extruder Hardware)")
        form_layout = QFormLayout()

        # IO Pin
        self.spin_io_pin = QSpinBox()
        self.spin_io_pin.setRange(0, 15) # Standard UR Digital Outs
        self.spin_io_pin.setToolTip("连接挤出机开关信号的数字输出端口 (DO)")
        form_layout.addRow("数字输出端口 (Digital Out):", self.spin_io_pin)

        # Modbus
        self.edit_modbus = QLineEdit()
        self.edit_modbus.setPlaceholderText("例如: MODBUS_1")
        self.edit_modbus.setToolTip("用于控制挤出速度的 Modbus 寄存器名称 (如果未使用可留空)")
        form_layout.addRow("Modbus 寄存器 (Speed Control):", self.edit_modbus)

        grp_extruder.setLayout(form_layout)
        io_layout.addWidget(grp_extruder)

        io_layout.addStretch()

        # === Safety Tab Setup ===
        safety_layout = QVBoxLayout(self.tab_safety)
        grp_watchdog = QGroupBox("看门狗安全阈值 (Watchdog Thresholds)")
        safety_form = QFormLayout()

        # Timeout
        self.spin_wd_timeout = QSpinBox()
        self.spin_wd_timeout.setRange(5, 3600)
        self.spin_wd_timeout.setSuffix(" 秒")
        self.spin_wd_timeout.setToolTip("机器人静止超过此时间将自动关闭挤出机")
        safety_form.addRow("静止判定超时:", self.spin_wd_timeout)

        # Speed Threshold
        from PyQt6.QtWidgets import QDoubleSpinBox
        self.spin_wd_speed = QDoubleSpinBox()
        self.spin_wd_speed.setRange(0.0, 0.1)
        self.spin_wd_speed.setSingleStep(0.001)
        self.spin_wd_speed.setDecimals(4)
        self.spin_wd_speed.setSuffix(" m/s")
        self.spin_wd_speed.setToolTip("低于此速度将被视为静止 (推荐 0.001 - 0.005)")
        safety_form.addRow("静止速度阈值:", self.spin_wd_speed)

        grp_watchdog.setLayout(safety_form)
        safety_layout.addWidget(grp_watchdog)
        safety_layout.addStretch()

        # === Buttons ===
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_settings(self):
        # Load from config manager
        io_pin = config_manager.get("printing.extruder_io_pin", 0)
        modbus_reg = config_manager.get("printing.modbus_extruder", "MODBUS_1")
        wd_timeout = config_manager.get("safety.watchdog_timeout", 120)
        wd_speed = config_manager.get("safety.watchdog_speed_threshold", 0.002)

        self.spin_io_pin.setValue(int(io_pin))
        self.edit_modbus.setText(str(modbus_reg))
        self.spin_wd_timeout.setValue(int(wd_timeout))
        self.spin_wd_speed.setValue(float(wd_speed))

    def save_settings(self):
        # Save to config manager
        io_pin = self.spin_io_pin.value()
        modbus_reg = self.edit_modbus.text().strip()
        wd_timeout = self.spin_wd_timeout.value()
        wd_speed = self.spin_wd_speed.value()

        try:
            config_manager.set("printing.extruder_io_pin", io_pin)
            config_manager.set("printing.modbus_extruder", modbus_reg)
            config_manager.set("safety.watchdog_timeout", wd_timeout)
            config_manager.set("safety.watchdog_speed_threshold", wd_speed)

            if config_manager.save_config():
                # Emit signal with new values relevant for driver
                driver_config = {
                    "extruder_io": io_pin,
                    "modbus_index": modbus_reg,
                    "wd_timeout": wd_timeout,
                    "wd_speed": wd_speed
                }
                self.settings_saved.emit(driver_config)
                self.accept()
            else:
                QMessageBox.warning(self, "保存失败", "无法写入配置文件")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置时出错: {e}")
