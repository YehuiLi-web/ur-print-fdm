"""
可折叠状态监控栏组件 - 工业简洁风格
实现了垂直侧边栏结构，包含多个可折叠的逻辑块，支持拖拽排序

主要功能区块：
1. 打印统计 - 进度、时间、层数
2. 温度监控 - 喷头温度、热床温度
3. 打印参数 - 打印速度、挤出机速度、流量
4. 运动状态 - TCP速度
5. 关节角度 - J1-J6 关节角
6. TCP 位姿 - 工具中心点位置/姿态
7. Base 点动 - 基于 Base 坐标系的单步移动
8. TCP 偏移 - 工具偏移量
"""
import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QToolButton, QProgressBar, QGridLayout,
                             QListWidget, QListWidgetItem, QAbstractItemView,
                             QMenu, QApplication, QSizePolicy, QPushButton,
                             QButtonGroup)
from PyQt6.QtCore import Qt, QSize, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QPainter, QPen, QPolygonF
from ur_print_fdm.config import config_manager
from ur_print_fdm.ui import theme


# =============================================================================
# 主题感知样式生成函数
# =============================================================================
def get_panel_style(t):
    """获取面板样式"""
    return f"""
        CollapsibleBox {{
            background-color: transparent;
            border: 1px solid {t["border_light"]};
            border-radius: 4px;
        }}
    """

def get_header_style(t):
    """获取标题栏样式"""
    return f"""
        QFrame {{
            background-color: transparent;
            border-bottom: 1px solid {t["border_light"]};
        }}
    """

def get_header_collapsed_style(t):
    """获取折叠状态标题栏样式"""
    return f"""
        QFrame {{
            background-color: transparent;
        }}
    """

def get_toggle_btn_style(t):
    """获取折叠按钮样式"""
    return f"""
        QToolButton {{ border: none; background: transparent; color: {t["text_muted"]}; }}
        QToolButton:hover {{ color: {t["text"]}; }}
    """

def get_list_widget_style(t):
    """获取列表组件样式"""
    return f"""
        QListWidget {{
            background-color: {t["bg_secondary"]};
            border: none;
            outline: none;
        }}
        QListWidget::item {{
            background-color: transparent;
            border: none;
            padding: 0px;
            margin: 0px;
        }}
        QListWidget::item:selected {{
            background-color: transparent;
            border: none;
        }}
        QScrollBar:vertical {{
            width: 0px;
            background: transparent;
        }}
        QScrollBar:horizontal {{
            height: 0px;
            background: transparent;
        }}
    """

def get_content_frame_style(t):
    """获取内容框样式"""
    return f"background-color: {t['bg_panel']}; border-radius: 3px;"

def get_context_menu_style(t):
    """获取右键菜单样式"""
    return f"""
        QMenu {{
            background-color: {t["bg_tertiary"]};
            border: 1px solid {t["border"]};
            color: {t["text"]};
        }}
        QMenu::item:selected {{
            background-color: {t["accent"]};
            color: {t["text_on_accent"]};
        }}
        QMenu::item:checked {{
            background-color: {t["bg_hover"]};
        }}
    """

def get_restore_handle_style(t):
    """获取折叠后恢复把手样式"""
    return f"""
        QToolButton#StatusDockRestoreHandle {{
            background-color: {t["bg_secondary"]};
            border: 1px solid {t["border_light"]};
            border-right: none;
            border-top-left-radius: 8px;
            border-bottom-left-radius: 8px;
            color: {t["text_muted"]};
        }}
        QToolButton#StatusDockRestoreHandle:hover {{
            background-color: {t["bg_hover"]};
            color: {t["text"]};
        }}
        QToolButton#StatusDockRestoreHandle:pressed {{
            background-color: {t["bg_hover_strong"]};
        }}
    """

def get_progress_bar_style(t, chunk_color=None):
    """获取进度条样式"""
    color = chunk_color or t["accent_blue"]
    return f"""
        QProgressBar {{ border: 1px solid {t["border"]}; background-color: {t["bg_secondary"]}; border-radius: 2px; }}
        QProgressBar::chunk {{ background-color: {color}; }}
    """

def with_alpha(color_value, alpha):
    """返回带透明度的 QColor，用于自绘控件。"""
    color = QColor(color_value)
    color.setAlphaF(max(0.0, min(1.0, float(alpha))))
    return color


def get_segment_button_style(t):
    """获取紧凑分段按钮样式。"""
    return f"""
        QPushButton {{
            background-color: {t["bg_secondary"]};
            color: {t["text_muted"]};
            border: 1px solid {t["border"]};
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 7.5pt;
            font-weight: 600;
        }}
        QPushButton:hover:!checked {{
            background-color: {t["bg_hover"]};
            color: {t["text"]};
        }}
        QPushButton:pressed:!checked {{
            background-color: {t["bg_hover_strong"]};
        }}
        QPushButton:checked {{
            background-color: {t["accent_blue"]};
            border-color: {t["accent_blue"]};
            color: {t["text_on_accent"]};
        }}
        QPushButton:disabled {{
            background-color: {t["bg_secondary"]};
            border-color: {t["border_light"]};
            color: {t["text_dim"]};
        }}
    """


JOINT_DISPLAY_LIMIT_DEG = 360.0
JOINT_WARNING_THRESHOLD_DEG = 240.0
JOINT_DANGER_THRESHOLD_DEG = 320.0


def get_joint_state_color(t, angle_deg):
    """根据关节角绝对值选择强调色。"""
    magnitude = abs(angle_deg)
    if magnitude >= JOINT_DANGER_THRESHOLD_DEG:
        return t["danger"]
    if magnitude >= JOINT_WARNING_THRESHOLD_DEG:
        return t["warning"]
    return t["success"]


def get_joint_value_style(t, accent_color, available=True):
    """关节数值标签样式。"""
    if not available:
        return f"color: {t['text_dim']}; font-family: {t['font_mono']}; font-size: 8.5pt;"

    return (
        f"color: {accent_color}; "
        f"font-family: {t['font_mono']}; font-size: 8.5pt; font-weight: 600;"
    )


class StatusDockRestoreHandle(QToolButton):
    """状态监视 dock 折叠后的右侧恢复把手。"""

    restore_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusDockRestoreHandle")
        self.setFixedSize(18, 96)
        self.setArrowType(Qt.ArrowType.LeftArrow)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("展开状态监视")
        self.clicked.connect(lambda: self.restore_requested.emit())
        self.apply_theme()

    def apply_theme(self):
        """应用主题样式。"""
        t = theme.current_tokens()
        self.setStyleSheet(get_restore_handle_style(t))


# =============================================================================
# CollapsibleBox - 可折叠面板组件
# =============================================================================
class CollapsibleBox(QFrame):
    """工业风格可折叠面板"""
    toggled = pyqtSignal(bool)  # 折叠状态改变信号

    def __init__(self, title, state_key=None, default_collapsed=False, parent=None):
        super().__init__(parent)
        self.state_key = state_key
        self.default_collapsed = default_collapsed
        self._is_collapsed = False

        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Header Bar ---
        self.header = QFrame()
        self.header.setMinimumHeight(26)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(8)

        # Title
        self.title_label = QLabel(title.upper())
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.header_meta_label = QLabel("")
        self.header_meta_label.setVisible(False)
        header_layout.addWidget(self.header_meta_label)

        # Toggle Button
        self.toggle_btn = QToolButton()
        self.toggle_btn.setArrowType(Qt.ArrowType.DownArrow)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False)
        self.toggle_btn.clicked.connect(self.toggle_content)
        header_layout.addWidget(self.toggle_btn)

        self.main_layout.addWidget(self.header)

        # --- Content Area ---
        self.content_area = QWidget()
        self.content_area.setMinimumWidth(0)
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(4, 4, 4, 6)
        self.content_layout.setSpacing(4)
        self.main_layout.addWidget(self.content_area)

        # 应用主题
        self.apply_theme()

        # 加载保存的状态
        if self.state_key:
            self._load_state()

    def apply_theme(self):
        """应用主题样式"""
        t = theme.current_tokens()
        self.setStyleSheet(get_panel_style(t))
        self.header.setStyleSheet(
            get_header_collapsed_style(t) if self._is_collapsed else get_header_style(t)
        )
        self.title_label.setStyleSheet(
            f"font-weight: bold; color: {t['text']}; font-size: 8.5pt; letter-spacing: 0.5px;"
        )
        self.header_meta_label.setStyleSheet(
            f"color: {t['accent_blue']}; font-family: {t['font_mono']}; font-size: 7.5pt; font-weight: 600;"
        )
        self.toggle_btn.setStyleSheet(get_toggle_btn_style(t))

    def set_header_meta(self, text: str = ""):
        """设置标题栏右侧的辅助信息。"""
        self.header_meta_label.setText(text)
        self.header_meta_label.setVisible(bool(text))

    def toggle_content(self):
        """切换折叠状态"""
        self._is_collapsed = self.toggle_btn.isChecked()
        self.content_area.setVisible(not self._is_collapsed)
        self.toggle_btn.setArrowType(
            Qt.ArrowType.RightArrow if self._is_collapsed else Qt.ArrowType.DownArrow
        )
        # 更新header样式
        t = theme.current_tokens()
        self.header.setStyleSheet(
            get_header_collapsed_style(t) if self._is_collapsed else get_header_style(t)
        )
        self.toggled.emit(not self._is_collapsed)
        # 保存状态
        if self.state_key:
            self._save_state()

    def set_collapsed(self, collapsed):
        """设置折叠状态"""
        if collapsed != self._is_collapsed:
            self.toggle_btn.setChecked(collapsed)
            self.toggle_content()

    def add_widget(self, widget):
        """添加组件到内容区域"""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """添加布局到内容区域"""
        self.content_layout.addLayout(layout)

    def _save_state(self):
        """保存折叠状态"""
        try:
            config_manager.set(f"ui.panels.{self.state_key}", self._is_collapsed)
            config_manager.save_config()
        except Exception:
            pass

    def _load_state(self):
        """加载折叠状态"""
        try:
            collapsed = config_manager.get(f"ui.panels.{self.state_key}")
            if collapsed is not None:
                self.set_collapsed(bool(collapsed))
            elif self.default_collapsed:
                self.set_collapsed(True)
        except Exception:
            pass


# =============================================================================
# ReorderablePanel - 可拖拽排序的面板容器
# =============================================================================
class ReorderablePanel(QListWidget):
    """可拖拽排序的面板容器"""
    order_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 启用拖拽排序
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSpacing(0)

        self._panel_widgets = []
        self._items = []  # 保存 item 引用
        self._widget_to_item = {}  # widget -> item 映射

        # 应用主题
        self.apply_theme()

    def apply_theme(self):
        """应用主题样式"""
        t = theme.current_tokens()
        self.setStyleSheet(get_list_widget_style(t))
        # 确保 viewport 背景色也正确设置
        self.viewport().setStyleSheet(f"background-color: {t['bg_secondary']};")

    def _item_size_hint(self, widget):
        hint = widget.sizeHint()
        viewport_width = max(0, self.viewport().width())
        return QSize(viewport_width, hint.height())

    def _refresh_item_size_hints(self):
        for item, widget in zip(self._items, self._panel_widgets):
            if item and widget:
                item.setSizeHint(self._item_size_hint(widget))
        self.doItemsLayout()

    def add_section(self, widget):
        """添加面板"""
        widget.setMinimumWidth(0)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        item = QListWidgetItem(self)
        item.setSizeHint(self._item_size_hint(widget))
        self.addItem(item)
        self.setItemWidget(item, widget)
        self._panel_widgets.append(widget)
        self._items.append(item)
        self._widget_to_item[widget] = item

        # 连接折叠信号，更新 item 大小
        if isinstance(widget, CollapsibleBox):
            idx = len(self._items) - 1
            widget.toggled.connect(lambda _, i=idx: self._on_panel_toggled(i))

    def _on_panel_toggled(self, index):
        """面板折叠/展开时更新大小"""
        try:
            if 0 <= index < len(self._items) and 0 <= index < len(self._panel_widgets):
                item = self._items[index]
                widget = self._panel_widgets[index]
                if item and widget:
                    item.setSizeHint(self._item_size_hint(widget))
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_item_size_hints()

    def set_section_visible(self, widget, visible):
        """设置面板可见性"""
        item = self._widget_to_item.get(widget)
        if item:
            item.setHidden(not visible)
            self._refresh_item_size_hints()

    def get_panel_order(self):
        """获取面板顺序"""
        return [
            w.state_key for w in self._panel_widgets
            if hasattr(w, 'state_key') and w.state_key
        ]

    def set_panel_order(self, order):
        """设置面板顺序 - 暂时禁用"""
        pass


# =============================================================================
# 功能模块组件
# =============================================================================

class PrintStatsContent(QWidget):
    """打印统计内容组件"""
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # 时间信息网格
        grid = QGridLayout()
        grid.setSpacing(6)

        self.lbl_elapsed = QLabel("00:00:00")
        self.lbl_remain = QLabel("--:--:--")
        self.lbl_layer = QLabel("0 / 0")

        # 标签引用，用于主题更新
        self.lbl_elapsed_title = QLabel("已用时间:")
        self.lbl_remain_title = QLabel("剩余时间:")
        self.lbl_layer_title = QLabel("当前层:")

        grid.addWidget(self.lbl_elapsed_title, 0, 0)
        grid.addWidget(self.lbl_elapsed, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.lbl_remain_title, 1, 0)
        grid.addWidget(self.lbl_remain, 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.lbl_layer_title, 2, 0)
        grid.addWidget(self.lbl_layer, 2, 1, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(grid)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # 百分比
        self.lbl_percent = QLabel("0.0 %")
        self.lbl_percent.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.lbl_percent)

        # 应用主题
        self.apply_theme()

    def apply_theme(self):
        """应用主题样式"""
        t = theme.current_tokens()
        self.lbl_elapsed.setStyleSheet(f"font-family: Consolas; color: {t['text']}; font-weight: bold;")
        self.lbl_remain.setStyleSheet(f"font-family: Consolas; color: {t['text_muted']};")
        self.lbl_layer.setStyleSheet(f"font-family: Consolas; color: {t['text_muted']};")
        self.lbl_elapsed_title.setStyleSheet(f"color: {t['text_dim']};")
        self.lbl_remain_title.setStyleSheet(f"color: {t['text_dim']};")
        self.lbl_layer_title.setStyleSheet(f"color: {t['text_dim']};")
        self.progress_bar.setStyleSheet(get_progress_bar_style(t))
        self.lbl_percent.setStyleSheet(f"font-size: 8pt; color: {t['accent_blue']};")

    def update_data(self, elapsed_sec, total_sec, current_layer=0, total_layers=0):
        """更新数据"""
        def fmt(s):
            return f"{int(s//3600):02}:{int((s%3600)//60):02}:{int(s%60):02}"

        self.lbl_elapsed.setText(fmt(elapsed_sec))
        pct = 0
        if total_sec > 0:
            remain = max(0, total_sec - elapsed_sec)
            self.lbl_remain.setText(fmt(remain))
            pct = (elapsed_sec / total_sec) * 100
        self.progress_bar.setValue(int(pct))
        self.lbl_percent.setText(f"{pct:.1f} %")
        self.lbl_layer.setText(f"{current_layer} / {total_layers}")


class TemperatureContent(QWidget):
    """温度监控内容组件"""
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # 喷头温度
        self.nozzle_frame = QFrame()
        nozzle_layout = QHBoxLayout(self.nozzle_frame)
        nozzle_layout.setContentsMargins(8, 6, 8, 6)

        self.lbl_nozzle_title = QLabel("喷头")
        nozzle_layout.addWidget(self.lbl_nozzle_title)
        nozzle_layout.addStretch()
        self.lbl_nozzle = QLabel("0")
        nozzle_layout.addWidget(self.lbl_nozzle)
        self.lbl_nozzle_unit = QLabel("°C")
        nozzle_layout.addWidget(self.lbl_nozzle_unit)
        layout.addWidget(self.nozzle_frame)

        # 热床温度
        self.bed_frame = QFrame()
        bed_layout = QHBoxLayout(self.bed_frame)
        bed_layout.setContentsMargins(8, 6, 8, 6)

        self.lbl_bed_title = QLabel("热床")
        bed_layout.addWidget(self.lbl_bed_title)
        bed_layout.addStretch()
        self.lbl_bed = QLabel("0")
        bed_layout.addWidget(self.lbl_bed)
        self.lbl_bed_unit = QLabel("°C")
        bed_layout.addWidget(self.lbl_bed_unit)
        layout.addWidget(self.bed_frame)

        # 应用主题
        self.apply_theme()

    def apply_theme(self):
        """应用主题样式"""
        t = theme.current_tokens()
        frame_style = get_content_frame_style(t)
        self.nozzle_frame.setStyleSheet(frame_style)
        self.bed_frame.setStyleSheet(frame_style)
        self.lbl_nozzle_title.setStyleSheet(f"color: {t['text_dim']}; font-size: 8pt;")
        self.lbl_nozzle.setStyleSheet(f"color: {t['danger']}; font-size: 14pt; font-weight: bold; font-family: Consolas;")
        self.lbl_nozzle_unit.setStyleSheet(f"color: {t['text_dim']}; font-size: 8pt;")
        self.lbl_bed_title.setStyleSheet(f"color: {t['text_dim']}; font-size: 8pt;")
        self.lbl_bed.setStyleSheet(f"color: {t['warning']}; font-size: 14pt; font-weight: bold; font-family: Consolas;")
        self.lbl_bed_unit.setStyleSheet(f"color: {t['text_dim']}; font-size: 8pt;")

    def update_data(self, nozzle_temp, bed_temp):
        """更新温度数据"""
        self.lbl_nozzle.setText(f"{nozzle_temp:.0f}")
        self.lbl_bed.setText(f"{bed_temp:.0f}")


class PrintParamsContent(QWidget):
    """打印参数内容组件"""
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 打印速度
        speed_row = QHBoxLayout()
        self.lbl_speed_title = QLabel("打印速度")
        speed_row.addWidget(self.lbl_speed_title)
        speed_row.addStretch()
        self.lbl_print_speed = QLabel("0")
        speed_row.addWidget(self.lbl_print_speed)
        self.lbl_speed_unit = QLabel("mm/s")
        speed_row.addWidget(self.lbl_speed_unit)
        layout.addLayout(speed_row)

        # 挤出速度
        extr_row = QHBoxLayout()
        self.lbl_extr_title = QLabel("挤出速度")
        extr_row.addWidget(self.lbl_extr_title)
        extr_row.addStretch()
        self.lbl_extr_speed = QLabel("0")
        extr_row.addWidget(self.lbl_extr_speed)
        self.lbl_extr_unit = QLabel("mm/s")
        extr_row.addWidget(self.lbl_extr_unit)
        layout.addLayout(extr_row)

        # 流量
        flow_row = QHBoxLayout()
        self.lbl_flow_title = QLabel("流量")
        flow_row.addWidget(self.lbl_flow_title)
        flow_row.addStretch()
        self.lbl_flow = QLabel("100")
        flow_row.addWidget(self.lbl_flow)
        self.lbl_flow_unit = QLabel("%")
        flow_row.addWidget(self.lbl_flow_unit)
        layout.addLayout(flow_row)

        # 应用主题
        self.apply_theme()

    def apply_theme(self):
        """应用主题样式"""
        t = theme.current_tokens()
        title_style = f"color: {t['text_dim']}; font-size: 8.5pt;"
        unit_style = f"color: {t['text_dim']}; font-size: 8pt;"
        self.lbl_speed_title.setStyleSheet(title_style)
        self.lbl_extr_title.setStyleSheet(title_style)
        self.lbl_flow_title.setStyleSheet(title_style)
        self.lbl_speed_unit.setStyleSheet(unit_style)
        self.lbl_extr_unit.setStyleSheet(unit_style)
        self.lbl_flow_unit.setStyleSheet(unit_style)
        self.lbl_print_speed.setStyleSheet(f"color: {t['accent_blue']}; font-family: Consolas; font-size: 9pt;")
        self.lbl_extr_speed.setStyleSheet(f"color: {t['success']}; font-family: Consolas; font-size: 9pt;")
        self.lbl_flow.setStyleSheet(f"color: {t['warning']}; font-family: Consolas; font-size: 9pt;")

    def update_data(self, print_speed, extr_speed, flow_rate):
        """更新参数数据"""
        self.lbl_print_speed.setText(f"{print_speed:.1f}")
        self.lbl_extr_speed.setText(f"{extr_speed:.2f}")
        self.lbl_flow.setText(f"{flow_rate:.0f}")


class MotionContent(QWidget):
    """运动状态内容组件"""
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        # TCP速度显示
        self.vel_frame = QFrame()
        vel_layout = QHBoxLayout(self.vel_frame)
        vel_layout.setContentsMargins(8, 6, 8, 6)

        self.lbl_vel_title = QLabel("TCP 速度")
        vel_layout.addWidget(self.lbl_vel_title)
        vel_layout.addStretch()
        self.lbl_velocity = QLabel("0.0")
        vel_layout.addWidget(self.lbl_velocity)
        self.lbl_vel_unit = QLabel("mm/s")
        vel_layout.addWidget(self.lbl_vel_unit)
        layout.addWidget(self.vel_frame)

        # 应用主题
        self.apply_theme()

    def apply_theme(self):
        """应用主题样式"""
        t = theme.current_tokens()
        self.vel_frame.setStyleSheet(get_content_frame_style(t))
        self.lbl_vel_title.setStyleSheet(f"color: {t['text_dim']}; font-size: 8pt;")
        self.lbl_velocity.setStyleSheet(f"color: {t['accent_blue']}; font-size: 14pt; font-weight: bold; font-family: Consolas;")
        self.lbl_vel_unit.setStyleSheet(f"color: {t['text_dim']}; font-size: 8pt;")

    def update_data(self, velocity):
        """更新速度数据"""
        self.lbl_velocity.setText(f"{velocity:.1f}")


class JogArrowButton(QToolButton):
    """为 Base 点动卡片绘制大号方向箭头。"""

    LARGE_SIZE = QSize(58, 58)
    COMPACT_SIZE = QSize(46, 40)

    def __init__(self, direction, axis_label, tooltip, *, compact=False, parent=None):
        super().__init__(parent)
        self._direction = str(direction)
        self._axis_label = str(axis_label)
        self._compact = bool(compact)
        self._theme = theme.current_tokens()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoRaise(True)
        self.setToolTip(tooltip)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(self.COMPACT_SIZE if self._compact else self.LARGE_SIZE)

    def sizeHint(self):
        return self.COMPACT_SIZE if self._compact else self.LARGE_SIZE

    def apply_theme(self):
        self._theme = theme.current_tokens()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = self._theme
        rect = QRectF(self.rect()).adjusted(0.8, 0.8, -0.8, -0.8)
        radius = 8.0 if not self._compact else 7.0

        if self.isEnabled():
            if self.isDown():
                bg_color = QColor(t["bg_hover_strong"])
                border_color = QColor(t["accent_blue"])
            elif self.underMouse():
                bg_color = QColor(t["bg_hover"])
                border_color = QColor(t["border"])
            else:
                bg_color = QColor(t["bg_panel"])
                border_color = QColor(t["border_light"])
            arrow_color = QColor(t["accent_blue"])
            label_color = QColor(t["text"])
        else:
            bg_color = QColor(t["bg_secondary"])
            border_color = QColor(t["border_light"])
            arrow_color = with_alpha(t["text_dim"], 0.7)
            label_color = QColor(t["text_dim"])

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(bg_color)
        painter.drawRoundedRect(rect, radius, radius)

        icon_rect = rect.adjusted(8.0, 6.0, -8.0, -16.0 if not self._compact else -13.0)
        polygon = self._build_arrow_polygon(icon_rect)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(arrow_color)
        painter.drawPolygon(polygon)

        label_rect = QRectF(rect.left() + 3.0, rect.bottom() - 15.0, rect.width() - 6.0, 11.0)
        painter.setPen(QPen(label_color))
        label_font = painter.font()
        label_font.setPointSizeF(7.0 if self._compact else 7.4)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._axis_label)

    def _build_arrow_polygon(self, rect):
        templates = {
            "up": (
                (0.50, 0.00), (1.00, 0.44), (0.74, 0.44),
                (0.74, 1.00), (0.26, 1.00), (0.26, 0.44), (0.00, 0.44),
            ),
            "down": (
                (0.00, 0.56), (0.26, 0.56), (0.26, 0.00),
                (0.74, 0.00), (0.74, 0.56), (1.00, 0.56), (0.50, 1.00),
            ),
            "left": (
                (0.00, 0.50), (0.44, 0.00), (0.44, 0.26),
                (1.00, 0.26), (1.00, 0.74), (0.44, 0.74), (0.44, 1.00),
            ),
            "right": (
                (0.00, 0.26), (0.56, 0.26), (0.56, 0.00),
                (1.00, 0.50), (0.56, 1.00), (0.56, 0.74), (0.00, 0.74),
            ),
        }
        points = templates.get(self._direction, templates["up"])
        return QPolygonF(
            [
                QPointF(rect.left() + rect.width() * x, rect.top() + rect.height() * y)
                for x, y in points
            ]
        )


class BaseMoveContent(QWidget):
    """Base 坐标系单步点动卡片。"""

    move_requested = pyqtSignal(float, float, float)

    STEP_OPTIONS_MM = (1.0, 5.0, 10.0)

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._available = False
        self._busy = False
        self._status_text = "需要监控和控制通道都在线"
        self.buttons = {}
        self.step_buttons = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        self.lbl_step_title = QLabel("Base 步长")
        header_row.addWidget(self.lbl_step_title)
        header_row.addStretch()

        self.step_group = QButtonGroup(self)
        self.step_group.setExclusive(True)
        for step_mm in self.STEP_OPTIONS_MM:
            button = QPushButton(f"{int(step_mm)} mm")
            button.setCheckable(True)
            button.setFixedHeight(24)
            button.setProperty("step_mm", float(step_mm))
            button.clicked.connect(self._on_step_button_clicked)
            self.step_group.addButton(button)
            self.step_buttons[float(step_mm)] = button
            header_row.addWidget(button)
        self.step_buttons[1.0].setChecked(True)
        layout.addLayout(header_row)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(6)
        self.grid.setVerticalSpacing(6)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(2, 1)

        self._add_move_button("y_pos", 0, 1, "up", "+Y", "Base +Y 方向点动")
        self._add_move_button("x_neg", 1, 0, "left", "-X", "Base -X 方向点动")
        self._add_move_button("z_pos", 1, 1, "up", "+Z", "Base +Z 方向点动", compact=True)
        self._add_move_button("x_pos", 1, 2, "right", "+X", "Base +X 方向点动")
        self._add_move_button("y_neg", 2, 1, "down", "-Y", "Base -Y 方向点动")
        self._add_move_button("z_neg", 3, 1, "down", "-Z", "Base -Z 方向点动", compact=True)
        layout.addLayout(self.grid)

        self.lbl_status = QLabel(self._status_text)
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        self.apply_theme()
        self.set_interaction_state(False, busy=False, reason=self._status_text)

    def _add_move_button(self, key, row, column, direction, axis_label, tooltip, *, compact=False):
        button = JogArrowButton(direction, axis_label, tooltip, compact=compact)
        button.clicked.connect(lambda _checked=False, move_key=key: self._emit_move(move_key))
        self.buttons[key] = button
        self.grid.addWidget(button, row, column, alignment=Qt.AlignmentFlag.AlignCenter)

    def _on_step_button_clicked(self):
        step = self.current_step_mm()
        if not self._busy:
            reason = f"Base 点动就绪，步长 {step:.0f} mm" if self._available else self._status_text
            self.set_interaction_state(self._available, busy=False, reason=reason)

    def current_step_mm(self):
        for step_mm, button in self.step_buttons.items():
            if button.isChecked():
                return float(step_mm)
        return self.STEP_OPTIONS_MM[0]

    def apply_theme(self):
        t = theme.current_tokens()
        self.lbl_step_title.setStyleSheet(f"color: {t['text_dim']}; font-size: 8pt;")
        self.lbl_status.setStyleSheet(f"color: {t['text_muted']}; font-size: 8pt;")
        step_style = get_segment_button_style(t)
        for button in self.step_buttons.values():
            button.setStyleSheet(step_style)
        for button in self.buttons.values():
            button.apply_theme()

    def set_interaction_state(self, enabled, *, busy=False, reason=""):
        self._available = bool(enabled)
        self._busy = bool(busy)

        status_text = str(reason or "").strip()
        if not status_text:
            if busy:
                status_text = "Base 点动执行中..."
            elif enabled:
                status_text = f"Base 点动就绪，步长 {self.current_step_mm():.0f} mm"
            else:
                status_text = "需要监控和控制通道都在线"
        self._status_text = status_text

        can_click = self._available and not self._busy
        for button in self.buttons.values():
            button.setEnabled(can_click)
        for button in self.step_buttons.values():
            button.setEnabled(not self._busy)

        t = theme.current_tokens()
        if self._busy:
            color = t["accent_blue"]
        elif self._available:
            color = t["success"]
        else:
            color = t["text_muted"]
        self.lbl_status.setStyleSheet(f"color: {color}; font-size: 8pt;")
        self.lbl_status.setText(self._status_text)

    def _emit_move(self, key):
        if not self._available or self._busy:
            return

        step_m = self.current_step_mm() / 1000.0
        moves = {
            "x_neg": (-step_m, 0.0, 0.0),
            "x_pos": (step_m, 0.0, 0.0),
            "y_pos": (0.0, step_m, 0.0),
            "y_neg": (0.0, -step_m, 0.0),
            "z_pos": (0.0, 0.0, step_m),
            "z_neg": (0.0, 0.0, -step_m),
        }
        dx, dy, dz = moves[key]
        self.move_requested.emit(dx, dy, dz)


class JointAngleGauge(QWidget):
    """以 0° 为中心的双向关节角度指示条。"""

    DISPLAY_LIMIT_DEG = JOINT_DISPLAY_LIMIT_DEG
    WARNING_THRESHOLD_DEG = JOINT_WARNING_THRESHOLD_DEG
    DANGER_THRESHOLD_DEG = JOINT_DANGER_THRESHOLD_DEG

    def __init__(self):
        super().__init__()
        self._angle_deg = None
        self._theme = theme.current_tokens()
        self.setMinimumWidth(72)
        self.setFixedHeight(14)

    def apply_theme(self):
        """刷新主题令牌。"""
        self._theme = theme.current_tokens()
        self.update()

    def set_angle(self, angle_deg):
        """设置当前角度，None 表示无数据。"""
        self._angle_deg = angle_deg
        self.update()

    def sizeHint(self):
        return QSize(128, 14)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1.0, 2.0, -1.0, -2.0)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        t = self._theme
        radius = rect.height() / 2.0
        center_x = rect.center().x()
        half_width = rect.width() / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(t["bg_hover"]))
        painter.drawRoundedRect(rect, radius, radius)

        painter.setBrush(with_alpha(t["warning"], 0.12))
        warning_width = half_width * (1.0 - self.WARNING_THRESHOLD_DEG / self.DISPLAY_LIMIT_DEG)
        if warning_width > 0:
            painter.drawRoundedRect(QRectF(rect.left(), rect.top(), warning_width, rect.height()), radius, radius)
            painter.drawRoundedRect(
                QRectF(rect.right() - warning_width, rect.top(), warning_width, rect.height()),
                radius,
                radius,
            )

        painter.setBrush(with_alpha(t["danger"], 0.16))
        danger_width = half_width * (1.0 - self.DANGER_THRESHOLD_DEG / self.DISPLAY_LIMIT_DEG)
        if danger_width > 0:
            painter.drawRoundedRect(QRectF(rect.left(), rect.top(), danger_width, rect.height()), radius, radius)
            painter.drawRoundedRect(
                QRectF(rect.right() - danger_width, rect.top(), danger_width, rect.height()),
                radius,
                radius,
            )

        center_pen = QPen(with_alpha(t["border_light"], 0.26))
        center_pen.setWidth(1)
        painter.setPen(center_pen)
        painter.drawLine(int(center_x), int(rect.top()) + 1, int(center_x), int(rect.bottom()) - 1)

        outline_pen = QPen(QColor(t["border"]))
        outline_pen.setWidth(1)
        painter.setPen(outline_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        if self._angle_deg is None:
            return

        normalized = max(-1.0, min(1.0, self._angle_deg / self.DISPLAY_LIMIT_DEG))
        if abs(normalized) < 1e-4:
            marker_color = QColor(get_joint_state_color(t, 0.0))
            marker_color.setAlphaF(0.75)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(marker_color)
            painter.drawEllipse(QRectF(center_x - 2.0, rect.center().y() - 2.0, 4.0, 4.0))
            return

        fill_color = QColor(get_joint_state_color(t, self._angle_deg))
        fill_rect = QRectF(rect)
        if normalized > 0:
            fill_rect.setLeft(center_x)
            fill_rect.setWidth(max(3.0, half_width * normalized))
        else:
            fill_rect.setLeft(center_x + half_width * normalized)
            fill_rect.setWidth(max(3.0, half_width * abs(normalized)))

        inner_rect = fill_rect.adjusted(0.0, 1.0, 0.0, -1.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill_color)
        painter.drawRoundedRect(inner_rect, min(radius - 1.0, inner_rect.width() / 2.0), radius - 1.0)

        marker_x = center_x + half_width * normalized
        marker = QRectF(marker_x - 3.5, rect.center().y() - 3.5, 7.0, 7.0)
        painter.setBrush(fill_color)
        painter.setPen(QPen(QColor(t["bg_secondary"]), 1))
        painter.drawEllipse(marker)


class JointRow(QWidget):
    """单个关节的标签、双向角度条和数值读数。"""

    ROW_SPACING = 2

    def __init__(self, joint_id, name):
        super().__init__()
        self.joint_id = joint_id
        self.joint_name = name
        self._angle_deg = None
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(self.ROW_SPACING)

        self.lbl_joint_id = QLabel(joint_id)
        self.lbl_joint_name = QLabel(name)
        self.lbl_value = QLabel("--")
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.gauge = JointAngleGauge()
        self.gauge.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.main_layout.addWidget(self.lbl_joint_id)
        self.main_layout.addWidget(self.gauge, 1)
        self.main_layout.addWidget(self.lbl_value)

        self.apply_theme()
        self.set_angle(None)

    def apply_theme(self):
        """应用关节行主题样式。"""
        t = theme.current_tokens()
        self.lbl_joint_id.setStyleSheet(
            f"color: {t['accent_blue']}; font-size: 8pt; font-weight: 700; letter-spacing: 0.2px;"
        )
        self.lbl_joint_name.setVisible(False)
        self.lbl_joint_name.setStyleSheet(f"color: {t['text_muted']}; font-size: 7.5pt;")
        self.gauge.apply_theme()
        accent = get_joint_state_color(t, self._angle_deg or 0.0) if self._angle_deg is not None else t["text_dim"]
        self.lbl_value.setStyleSheet(get_joint_value_style(t, accent, available=self._angle_deg is not None))

    def set_label_width(self, width):
        """设置左侧关节标签列宽度。"""
        self.lbl_joint_id.setFixedWidth(width)

    def set_value_width(self, width):
        """设置右侧数值列宽度。"""
        self.lbl_value.setFixedWidth(width)

    def set_angle(self, angle_deg):
        """更新关节角显示。"""
        self._angle_deg = angle_deg
        t = theme.current_tokens()

        if angle_deg is None:
            self.gauge.set_angle(None)
            self.lbl_value.setText("--")
            self.lbl_value.setVisible(True)
            self.lbl_value.setStyleSheet(get_joint_value_style(t, t["text_dim"], available=False))
            self.setToolTip(f"{self.joint_id} {self.joint_name}: 无数据")
            return

        accent = get_joint_state_color(t, angle_deg)
        self.gauge.set_angle(angle_deg)
        self.lbl_value.setText(f"{angle_deg:+.2f}°")
        self.lbl_value.setVisible(True)
        self.lbl_value.setStyleSheet(get_joint_value_style(t, accent, available=True))
        self.setToolTip(f"{self.joint_id} {self.joint_name}: {angle_deg:+.2f}°")


class JointsContent(QWidget):
    """关节角度内容组件"""
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._label_column_width = 0
        self._value_column_width = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        self.rows = []
        joint_defs = [
            ("J1", "Base"),
            ("J2", "Shoulder"),
            ("J3", "Elbow"),
            ("J4", "Wrist 1"),
            ("J5", "Wrist 2"),
            ("J6", "Wrist 3"),
        ]

        self.legend_neg = QLabel("-360°")
        self.legend_zero = QLabel("0°")
        self.legend_pos = QLabel("+360°")

        self.legend_left_spacer = QWidget()
        self.legend_right_spacer = QWidget()

        self.legend_track_layout = QGridLayout()
        self.legend_track_layout.setContentsMargins(0, 0, 0, 0)
        self.legend_track_layout.setHorizontalSpacing(0)
        self.legend_track_layout.setVerticalSpacing(0)
        self.legend_track_layout.addWidget(self.legend_neg, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.legend_track_layout.addWidget(self.legend_zero, 0, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.legend_track_layout.addWidget(self.legend_pos, 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
        self.legend_track_layout.setColumnStretch(0, 1)
        self.legend_track_layout.setColumnStretch(1, 1)
        self.legend_track_layout.setColumnStretch(2, 1)

        self.legend_track = QWidget()
        self.legend_track.setLayout(self.legend_track_layout)

        self.legend_layout = QHBoxLayout()
        self.legend_layout.setContentsMargins(0, 0, 0, 0)
        self.legend_layout.setSpacing(0)
        self.legend_layout.addWidget(self.legend_left_spacer)
        self.legend_layout.addWidget(self.legend_track, 1)
        self.legend_layout.addWidget(self.legend_right_spacer)
        layout.addLayout(self.legend_layout)

        for joint_id, name in joint_defs:
            row = JointRow(joint_id, name)
            self.rows.append(row)
            layout.addWidget(row)

        # 应用主题
        self.apply_theme()
        self._sync_column_widths()

    def apply_theme(self):
        """应用主题样式"""
        t = theme.current_tokens()
        legend_style = f"color: {t['text_dim']}; font-size: 7pt;"
        self.legend_neg.setStyleSheet(legend_style)
        self.legend_pos.setStyleSheet(legend_style)
        self.legend_zero.setStyleSheet(f"color: {t['accent_blue']}; font-size: 7pt; font-weight: 600;")
        for row in self.rows:
            row.apply_theme()
        self._sync_column_widths()

    def update_data(self, joints):
        """更新关节数据 (joints为弧度)"""
        if not joints:
            self.clear_data()
            return
        for index, row in enumerate(self.rows):
            if index < len(joints):
                row.set_angle(math.degrees(joints[index]))
            else:
                row.set_angle(None)
        self._sync_column_widths()

    def clear_data(self):
        """清空关节实时数据。"""
        for row in self.rows:
            row.set_angle(None)
        self._sync_column_widths()

    def _measure_text_width(self, label, text):
        """按当前字体计算文本宽度。"""
        metrics = label.fontMetrics()
        return max(1, metrics.horizontalAdvance(text))

    def _sync_column_widths(self):
        """根据当前内容自适应左右列宽度，并同步顶部刻度对齐。"""
        if not self.rows:
            return

        label_width = max(self._measure_text_width(row.lbl_joint_id, row.joint_id) for row in self.rows)
        value_width = max(
            self._measure_text_width(row.lbl_value, row.lbl_value.text() or "--")
            for row in self.rows
        )

        self._label_column_width = label_width
        self._value_column_width = value_width

        for row in self.rows:
            row.set_label_width(label_width)
            row.set_value_width(value_width)

        self.legend_left_spacer.setFixedWidth(label_width + JointRow.ROW_SPACING)
        self.legend_right_spacer.setFixedWidth(value_width + JointRow.ROW_SPACING)


class TCPPoseContent(QWidget):
    """TCP位姿内容组件"""
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # 存储当前TCP位姿原始值 (m 和 rad)，便于直接导出为 UR pose 字符串
        self._current_pose = [0.0] * 6

        # 启用右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.labels = []
        self.name_labels = []
        self.unit_labels = []
        names = [("X", "mm"), ("Y", "mm"), ("Z", "mm"), ("Rx", "rad"), ("Ry", "rad"), ("Rz", "rad")]

        for name, unit in names:
            row = QHBoxLayout()
            row.setSpacing(8)

            lbl = QLabel(name)
            lbl.setFixedWidth(25)
            self.name_labels.append(lbl)

            val = QLabel("0.00" if unit == "mm" else "0.000")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)

            unit_lbl = QLabel(unit)
            unit_lbl.setFixedWidth(25)
            self.unit_labels.append(unit_lbl)

            row.addWidget(lbl)
            row.addWidget(val, 1)
            row.addWidget(unit_lbl)
            layout.addLayout(row)

            self.labels.append(val)

        # 应用主题
        self.apply_theme()

    def apply_theme(self):
        """应用主题样式"""
        t = theme.current_tokens()
        for lbl in self.name_labels:
            lbl.setStyleSheet(f"color: {t['text_dim']}; font-size: 8.5pt;")
        for lbl in self.unit_labels:
            lbl.setStyleSheet(f"color: {t['text_dim']}; font-size: 8pt;")
        for val in self.labels:
            val.setStyleSheet(f"color: {t['text']}; font-family: Consolas; font-size: 9pt;")

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        t = theme.current_tokens()
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(t))

        action_copy = QAction("复制全部坐标", self)
        action_copy.triggered.connect(self._copy_all_coordinates)
        menu.addAction(action_copy)

        menu.exec(self.mapToGlobal(pos))

    def _copy_all_coordinates(self):
        """复制全部坐标到剪贴板"""
        text = (f"p[{self._current_pose[0]:.6f}, {self._current_pose[1]:.6f}, "
                f"{self._current_pose[2]:.6f}, {self._current_pose[3]:.6f}, "
                f"{self._current_pose[4]:.6f}, {self._current_pose[5]:.6f}]")
        QApplication.clipboard().setText(text)

    def update_data(self, tcp):
        """更新TCP数据 (tcp为[x,y,z,rx,ry,rz], 位置单位m, 角度单位rad)"""
        if not tcp:
            return
        for i, val in enumerate(tcp[:6]):
            self._current_pose[i] = val
            if i < 3:  # 位置 m -> mm
                converted = val * 1000
                self.labels[i].setText(f"{converted:.2f}")
            else:  # 角度保持 rad 显示
                self.labels[i].setText(f"{val:.3f}")


class TCPOffsetContent(QWidget):
    """TCP偏移内容组件"""
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.labels = []
        self.name_labels = []
        self.unit_labels = []
        names = [("dX", "mm"), ("dY", "mm"), ("dZ", "mm"), ("dRx", "°"), ("dRy", "°"), ("dRz", "°")]

        for name, unit in names:
            row = QHBoxLayout()
            row.setSpacing(8)

            lbl = QLabel(name)
            lbl.setFixedWidth(30)
            self.name_labels.append(lbl)

            val = QLabel("0.00")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)

            unit_lbl = QLabel(unit)
            unit_lbl.setFixedWidth(25)
            self.unit_labels.append(unit_lbl)

            row.addWidget(lbl)
            row.addWidget(val, 1)
            row.addWidget(unit_lbl)
            layout.addLayout(row)

            self.labels.append(val)

        # 应用主题
        self.apply_theme()

    def apply_theme(self):
        """应用主题样式"""
        t = theme.current_tokens()
        for lbl in self.name_labels:
            lbl.setStyleSheet(f"color: {t['text_dim']}; font-size: 8.5pt;")
        for lbl in self.unit_labels:
            lbl.setStyleSheet(f"color: {t['text_dim']}; font-size: 8pt;")
        for val in self.labels:
            val.setStyleSheet(f"color: {t['text_muted']}; font-family: Consolas; font-size: 9pt;")

    def update_data(self, offset):
        """更新偏移数据"""
        if not offset:
            return
        for i, val in enumerate(offset[:6]):
            if i < 3:  # 位置 m -> mm
                self.labels[i].setText(f"{val * 1000:.2f}")
            else:  # 角度 rad -> deg
                self.labels[i].setText(f"{val * 57.2958:.2f}")


# =============================================================================
# StatusWidget - 主状态监控组件
# =============================================================================
class StatusWidget(QWidget):
    """状态监控组件 - 工业简洁风格，支持拖拽排序"""
    panels_reordered = pyqtSignal(list)
    base_move_requested = pyqtSignal(float, float, float)
    COMPACT_MINIMUM_WIDTH = 208

    # 面板定义: (state_key, 显示名称, 默认是否显示)
    PANEL_DEFS = [
        ("print_stats", "打印统计", True),
        ("temperature", "温度监控", True),
        ("print_params", "打印参数", True),
        ("joints", "关节角度", True),
        ("tcp_pose", "TCP 位姿(Base)", True),
        ("base_move", "Base 点动", True),
        ("tcp_offset", "TCP 偏移", True),
    ]

    def __init__(self):
        super().__init__()
        self.setObjectName("StatusWidget")  # 设置对象名称用于样式选择器
        self.setMinimumWidth(self.COMPACT_MINIMUM_WIDTH)

        # 打印计时器
        self._elapsed_seconds = 0
        self._total_seconds = 0
        self._current_layer = 0
        self._total_layers = 0

        # 面板可见性
        self._panel_visibility = {}

        # 启用右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_panel_menu)

        self._init_ui()
        # 应用主题
        self.apply_theme()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 可拖拽面板容器
        self.panel = ReorderablePanel()
        self.panel.order_changed.connect(self._on_order_changed)
        layout.addWidget(self.panel)

        # 加载面板可见性设置
        self._load_panel_visibility()

        # 创建各个面板
        self._create_panels()

        # 加载保存的顺序
        self._load_panel_order()

    def _create_panels(self):
        """创建所有面板"""
        # 面板映射表
        self._sections = {}

        # 1. 打印统计
        self.print_stats = PrintStatsContent()
        self.sec_print = CollapsibleBox("打印统计", state_key="print_stats")
        self.sec_print.add_widget(self.print_stats)
        self.panel.add_section(self.sec_print)
        self._sections["print_stats"] = self.sec_print

        # 2. 温度监控
        self.temperature = TemperatureContent()
        self.sec_temp = CollapsibleBox("温度监控", state_key="temperature")
        self.sec_temp.add_widget(self.temperature)
        self.panel.add_section(self.sec_temp)
        self._sections["temperature"] = self.sec_temp

        # 3. 打印参数
        self.print_params = PrintParamsContent()
        self.sec_params = CollapsibleBox("打印参数", state_key="print_params")
        self.sec_params.add_widget(self.print_params)
        self.panel.add_section(self.sec_params)
        self._sections["print_params"] = self.sec_params

        self.motion = MotionContent()

        # 4. 关节角度
        self.joints = JointsContent()
        self.sec_joints = CollapsibleBox("关节角度", state_key="joints")
        self.sec_joints.add_widget(self.joints)
        self.panel.add_section(self.sec_joints)
        self._sections["joints"] = self.sec_joints

        # 5. TCP位姿
        self.tcp_pose = TCPPoseContent()
        self.sec_tcp = CollapsibleBox("TCP 位姿(Base)", state_key="tcp_pose")
        self.sec_tcp.set_header_meta("--.- mm/s")
        self.sec_tcp.add_widget(self.tcp_pose)
        self.panel.add_section(self.sec_tcp)
        self._sections["tcp_pose"] = self.sec_tcp

        # 6. Base 点动
        self.base_move = BaseMoveContent()
        self.base_move.move_requested.connect(self.base_move_requested.emit)
        self.sec_base_move = CollapsibleBox("Base 点动", state_key="base_move")
        self.sec_base_move.add_widget(self.base_move)
        self.panel.add_section(self.sec_base_move)
        self._sections["base_move"] = self.sec_base_move

        # 7. TCP偏移 (默认折叠)
        self.tcp_offset = TCPOffsetContent()
        self.sec_offset = CollapsibleBox("TCP 偏移", state_key="tcp_offset", default_collapsed=True)
        self.sec_offset.add_widget(self.tcp_offset)
        self.panel.add_section(self.sec_offset)
        self._sections["tcp_offset"] = self.sec_offset

        # 应用保存的可见性设置
        self._apply_panel_visibility()

    def _show_panel_menu(self, pos):
        """显示面板选择菜单"""
        t = theme.current_tokens()
        menu = QMenu(self)
        menu.setStyleSheet(get_context_menu_style(t))

        for state_key, name, _ in self.PANEL_DEFS:
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(self._panel_visibility.get(state_key, True))
            action.triggered.connect(lambda checked, key=state_key: self._toggle_panel(key, checked))
            menu.addAction(action)

        menu.exec(self.mapToGlobal(pos))

    def _toggle_panel(self, state_key, visible):
        """切换面板显示/隐藏"""
        self._panel_visibility[state_key] = visible
        if state_key in self._sections:
            # 使用 panel 的方法隐藏 item，这样下面的面板会自动上移
            self.panel.set_section_visible(self._sections[state_key], visible)
        self._save_panel_visibility()

    def _apply_panel_visibility(self):
        """应用面板可见性设置"""
        for state_key, section in self._sections.items():
            visible = self._panel_visibility.get(state_key, True)
            self.panel.set_section_visible(section, visible)

    def _save_panel_visibility(self):
        """保存面板可见性设置"""
        try:
            config_manager.set("ui.panels.visibility", self._panel_visibility)
            config_manager.save_config()
        except Exception:
            pass

    def _load_panel_visibility(self):
        """加载面板可见性设置"""
        try:
            visibility = config_manager.get("ui.panels.visibility")
            if visibility:
                self._panel_visibility = visibility
            else:
                # 默认全部显示
                self._panel_visibility = {key: default for key, _, default in self.PANEL_DEFS}
        except Exception:
            self._panel_visibility = {key: default for key, _, default in self.PANEL_DEFS}

    def _on_order_changed(self, order):
        """面板顺序改变"""
        self._save_panel_order(order)
        self.panels_reordered.emit(order)

    def _save_panel_order(self, order=None):
        """保存面板顺序"""
        try:
            if order is None:
                order = self.panel.get_panel_order()
            config_manager.set("ui.panels.order", order)
            config_manager.save_config()
        except Exception:
            pass

    def _load_panel_order(self):
        """加载面板顺序"""
        try:
            order = config_manager.get("ui.panels.order")
            if order:
                self.panel.set_panel_order(order)
        except Exception:
            pass

    # =========================================================================
    # 数据更新接口
    # =========================================================================
    def update_status(self, tcp, joints, offset):
        """更新机器人状态 (兼容旧接口)"""
        self.tcp_pose.update_data(tcp)
        self.joints.update_data(joints)
        self.tcp_offset.update_data(offset)

    def update_print_progress(self, elapsed_sec, total_sec, current_layer=0, total_layers=0):
        """更新打印进度"""
        self._elapsed_seconds = elapsed_sec
        self._total_seconds = total_sec
        self._current_layer = current_layer
        self._total_layers = total_layers
        self.print_stats.update_data(elapsed_sec, total_sec, current_layer, total_layers)

    def update_temperature(self, nozzle_temp, bed_temp):
        """更新温度"""
        self.temperature.update_data(nozzle_temp, bed_temp)

    def update_print_params(self, print_speed, extr_speed, flow_rate):
        """更新打印参数"""
        self.print_params.update_data(print_speed, extr_speed, flow_rate)

    def update_velocity(self, velocity):
        """更新TCP速度"""
        self.motion.update_data(velocity)
        self._set_tcp_speed_header(velocity)

    def update_joints(self, joints):
        """更新关节角度"""
        self.joints.update_data(joints)

    def update_tcp_pose(self, tcp):
        """更新TCP位姿"""
        self.tcp_pose.update_data(tcp)

    def update_tcp_offset(self, offset):
        """更新TCP偏移"""
        self.tcp_offset.update_data(offset)

    def update_tcp_speed(self, speed):
        """更新TCP速度 (兼容main_window接口, speed单位m/s)"""
        # 转换为 mm/s
        velocity_mm_s = speed * 1000.0
        self.motion.update_data(velocity_mm_s)
        self._set_tcp_speed_header(velocity_mm_s)

    def set_connection_status(self, is_connected, config_name=""):
        """设置连接状态 (兼容main_window接口)"""
        summary = str(config_name or ("已连接" if is_connected else "未连接"))
        self.setToolTip(f"连接状态: {summary}")

    def set_motion_status(self, action="", motion_type=""):
        """设置运动状态 (兼容main_window接口)"""
        # 当前UI没有专门的运动状态文字显示，可以在未来添加
        pass

    def set_base_move_availability(self, enabled, *, busy=False, reason=""):
        """设置 Base 点动卡片的交互状态。"""
        self.base_move.set_interaction_state(enabled, busy=busy, reason=reason)

    def clear_live_data(self):
        """清空实时监控数据，避免断线后保留陈旧值。"""
        self.motion.update_data(0.0)
        self._set_tcp_speed_header(None)
        self.joints.clear_data()

        for i, val in enumerate(self.tcp_pose.labels):
            val.setText("--")
            self.tcp_pose._current_pose[i] = 0.0

        for val in self.tcp_offset.labels:
            val.setText("--")

    def apply_theme(self):
        """应用主题样式"""
        t = theme.current_tokens()

        # 直接使用样式表设置背景色，确保与文件资源管理器一致
        self.setStyleSheet(f"""
            QWidget#StatusWidget {{
                background-color: {t['bg_secondary']};
                border-left: 1px solid {t['border_light']};
            }}
        """)

        # 更新面板容器样式
        self.panel.apply_theme()

        # 更新所有子面板样式
        for section in self._sections.values():
            if hasattr(section, 'apply_theme'):
                section.apply_theme()

        # 更新所有内容组件样式
        content_widgets = [
            self.print_stats, self.temperature, self.print_params,
            self.motion, self.joints, self.tcp_pose, self.base_move, self.tcp_offset
        ]
        for widget in content_widgets:
            if hasattr(widget, 'apply_theme'):
                widget.apply_theme()

    def _set_tcp_speed_header(self, velocity_mm_s):
        """将 TCP 速度以紧凑方式显示在 TCP 位姿标题栏右侧。"""
        if velocity_mm_s is None:
            self.sec_tcp.set_header_meta("--.- mm/s")
            return

        self.sec_tcp.set_header_meta(f"{velocity_mm_s:.1f} mm/s")

    def start_print_timer(self, start_seconds=0):
        """开始打印计时器 (兼容main_window接口)"""
        self._elapsed_seconds = start_seconds
        self.print_stats.update_data(
            self._elapsed_seconds, self._total_seconds,
            self._current_layer, self._total_layers
        )

    def update_print_time(self, estimated_total_seconds):
        """更新打印预计总时间 (兼容main_window接口)"""
        self._total_seconds = estimated_total_seconds
        self.print_stats.update_data(
            self._elapsed_seconds, self._total_seconds,
            self._current_layer, self._total_layers
        )

    def reset_print_stats(self):
        """重置打印统计 (兼容main_window接口)"""
        self._elapsed_seconds = 0
        self._total_seconds = 0
        self._current_layer = 0
        self._total_layers = 0
        self.print_stats.update_data(0, 0, 0, 0)
