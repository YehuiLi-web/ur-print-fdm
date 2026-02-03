from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
                             QLabel, QListWidget, QListWidgetItem, QStackedWidget, QFormLayout,
                             QDoubleSpinBox, QSpinBox, QCheckBox, QLineEdit,
                             QPushButton, QGroupBox, QTextEdit,
                             QScrollArea, QFrame, QGraphicsDropShadowEffect)
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QIcon
from ur_print_fdm.core.print_lib import URPrintLib
from ur_print_fdm.core.sample_library_manager import SampleManager, SampleBase
from ur_print_fdm.estimators.sample_trajectory import trajectory_from_sample_params
from ur_print_fdm.plugins.bootstrap import bootstrap_plugins
from ur_print_fdm.plugins.registry import registry
from ur_print_fdm.samples.loader import load_samples

class LibraryWidget(QWidget):
    script_generated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        bootstrap_plugins()
        load_samples()
        self.print_lib = URPrintLib()
        self.current_sample = None
        self.param_inputs = {}
        self._init_ui()
        self._apply_styles()

    def _apply_styles(self):
        """仅保留样件库特有的样式覆盖，其余继承全局主题"""
        from ur_print_fdm.ui import theme

        t = theme.current_tokens()
        self.setStyleSheet(
            f"""
            QListWidget::item {{ padding: 12px 15px; margin-bottom: 4px; }}
            QPushButton#GenerateButton {{
                background-color: {t["accent_blue"]};
                color: {t["text_on_accent"]};
                border: none;
                border-radius: {t["radius_lg"]};
                padding: 12px 24px;
                font-size: 11pt;
                font-weight: 700;
                margin-top: 15px;
            }}
            QPushButton#GenerateButton:hover {{ background-color: {t["accent_hover"]}; }}
            QPushButton#GenerateButton:pressed {{ background-color: {t["accent"]}; }}
            QTextEdit#InfoArea {{
                background-color: {t["bg_tertiary"]};
                color: {t["text"]};
                border: 1px solid {t["border"]};
                border-radius: {t["radius_lg"]};
                padding: 10px;
            }}
            """
        )
        try:
            self.header_label.setStyleSheet(
                f"font-size: 14pt; font-weight: 700; color: {t['text']}; margin-bottom: 10px;"
            )
            self.lbl_title.setStyleSheet(
                f"font-size: 12pt; font-weight: 700; color: {t['accent_link']};"
            )
        except Exception:
            pass

    def apply_theme(self) -> None:
        self._apply_styles()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === LEFT PANEL ===
        left_container = QFrame()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(15, 20, 15, 20)

        self.header_label = QLabel("样件库")
        left_layout.addWidget(self.header_label)

        self.part_list = QListWidget()
        self.samples = SampleManager.get_all_samples()
        for sample in self.samples:
            item = QListWidgetItem(sample.title)
            # 可以在这里添加图标 item.setIcon(QIcon(...))
            self.part_list.addItem(item)

        left_layout.addWidget(self.part_list)
        splitter.addWidget(left_container)

        # === RIGHT PANEL ===
        right_container = QFrame()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(25, 20, 25, 20)
        right_layout.setSpacing(15)

        # Header with Sample Title
        self.lbl_title = QLabel("选择一个样件进行配置")
        right_layout.addWidget(self.lbl_title)

        # Description Area
        self.txt_info = QTextEdit()
        self.txt_info.setObjectName("InfoArea")
        self.txt_info.setReadOnly(True)
        self.txt_info.setFixedHeight(80)
        right_layout.addWidget(self.txt_info)

        # Form Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.form_container = QWidget()
        self.form_layout = QFormLayout(self.form_container)
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form_layout.setContentsMargins(10, 10, 10, 10)
        self.form_layout.setSpacing(12)
        scroll.setWidget(self.form_container)
        right_layout.addWidget(scroll)

        # Bottom Action
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_gen = QPushButton("生成 URScript 脚本")
        self.btn_gen.setObjectName("GenerateButton")
        self.btn_gen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gen.clicked.connect(self.do_gen_test_part)

        # 给按钮添加阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(64, 158, 255, 80))
        shadow.setOffset(0, 4)
        self.btn_gen.setGraphicsEffect(shadow)

        btn_layout.addWidget(self.btn_gen)
        right_layout.addLayout(btn_layout)

        splitter.addWidget(right_container)
        splitter.setSizes([220, 580])
        main_layout.addWidget(splitter)

        self.part_list.currentRowChanged.connect(self.on_part_selected)
        if self.samples:
            self.part_list.setCurrentRow(0)

    def on_part_selected(self, row):
        if row < 0 or row >= len(self.samples): return
        sample = self.samples[row]
        self.current_sample = sample

        self.lbl_title.setText(sample.title)

        # Update Info with cleaner format
        info_text = f"<b>简介:</b> {sample.description}"
        if sample.instructions:
            info_text += f"<br><b>建议:</b> {sample.instructions}"
        self.txt_info.setHtml(info_text)

        # Rebuild Form
        self._clear_form()
        self.param_inputs = {}

        # 逻辑分组展示参数 (简单实现：分为几何和基础)
        params = sample.get_parameters()
        for param in params:
            widget = self._create_input_widget(param)
            self.param_inputs[param.name] = widget

            # 漂亮的标签
            label = QLabel(f"{param.label}")
            label.setProperty("ui_role", "muted")
            self.form_layout.addRow(label, widget)

    def _clear_form(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _create_input_widget(self, param):
        # 针对不同类型优化展示
        if param.param_type == float:
            w = QDoubleSpinBox()
            w.setRange(param.min_val, param.max_val)
            w.setDecimals(param.decimals)
            w.setValue(param.default)
            if param.unit: w.setSuffix(f" {param.unit}")
            return w
        elif param.param_type == int:
            w = QSpinBox()
            w.setRange(int(param.min_val), int(param.max_val))
            w.setValue(param.default)
            if param.unit: w.setSuffix(f" {param.unit}")
            return w
        elif param.param_type == bool:
            w = QCheckBox(f"启用")
            w.setChecked(param.default)
            return w
        else:
            w = QLineEdit(str(param.default))
            return w

    def do_gen_test_part(self):
        if not self.current_sample: return
        params = {}
        for name, widget in self.param_inputs.items():
            if isinstance(widget, (QDoubleSpinBox, QSpinBox)): params[name] = widget.value()
            elif isinstance(widget, QCheckBox): params[name] = widget.isChecked()
            elif isinstance(widget, QLineEdit): params[name] = widget.text()

        try:
            code = self.current_sample.generate_script(params, context=self.print_lib)
            # 发送信号，这里稍微修改一下信号传递的内容或者方式，如果需要传递更多信息
            # 目前只传递了代码字符串，主窗口接收到后可以决定怎么处理
            self.script_generated.emit(code)

            estimate_msg = ""
            traj = trajectory_from_sample_params(self.current_sample.id, params)
            estimator = registry.estimators.get("simple_gcode_v1")
            if traj is not None and estimator is not None:
                result = estimator.estimate(traj)
                total_s = int(round(result.total_time_s))
                h = total_s // 3600
                m = (total_s % 3600) // 60
                s = total_s % 60
                estimate_msg = f"\n\n预计打印时间（估算）: {h:02d}:{m:02d}:{s:02d}"

            StyledMessageBox.information(
                self,
                "生成成功",
                "脚本已生成并发送到主编辑器。\n请在新建的标签页中查看。" + estimate_msg,
            )

        except Exception as e:
            StyledMessageBox.critical(self, "生成失败", f"错误详情：\n{str(e)}")
