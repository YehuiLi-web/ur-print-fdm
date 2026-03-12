"""
统一风格的消息对话框组件

设计原则：
1. 固定合理的宽度（350-400px），避免过宽或过窄
2. 与应用深色主题保持一致
3. 提供简洁的 API，兼容 QMessageBox 的常用场景
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class StyledMessageBox(QDialog):
    """
    统一风格的消息对话框
    
    宽度设计：350px（紧凑）适合大多数场景
    """
    
    # 按钮角色常量
    Yes = "yes"
    No = "no"
    Cancel = "cancel"
    Ok = "ok"
    
    # 图标类型
    Information = "info"
    Warning = "warning"
    Critical = "error"
    Question = "question"
    
    def __init__(self, parent=None, title="", message="", icon_type=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self._result = None
        self._buttons = {}
        
        # 固定宽度，避免过宽
        self.setFixedWidth(360)
        self.setMinimumHeight(120)
        
        # 移除默认标题栏样式，应用暗色主题
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowCloseButtonHint
        )
        
        self._icon_type = icon_type
        self._message = message
        self._init_ui()
        self._apply_style()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        # 内容区域（图标 + 文字）
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # 图标
        if self._icon_type:
            icon_label = QLabel()
            icon_label.setFixedSize(32, 32)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
            icon_char = self._get_icon_char()
            icon_label.setText(icon_char)
            icon_label.setFont(QFont("Segoe UI Emoji", 20))
            icon_label.setStyleSheet(self._get_icon_style())
            content_layout.addWidget(icon_label)
        
        # 消息文本
        from ur_print_fdm.ui.theme_manager import get_theme_manager

        t = get_theme_manager().current_tokens()
        self.message_label = QLabel(self._message)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.message_label.setStyleSheet(
            f"color: {t.get('text', '#CCCCCC')}; font-size: 13px; line-height: 1.5;"
        )
        content_layout.addWidget(self.message_label, 1)
        
        layout.addLayout(content_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {t.get('border_light', '#3C3C3C')};")
        line.setFixedHeight(1)
        layout.addWidget(line)
        
        # 按钮区域
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(8)
        self.button_layout.addStretch()
        layout.addLayout(self.button_layout)
    
    def _get_icon_char(self):
        """获取图标字符"""
        icons = {
            self.Information: "ℹ",
            self.Warning: "⚠",
            self.Critical: "✕",
            self.Question: "?"
        }
        return icons.get(self._icon_type, "")
    
    def _get_icon_style(self):
        """获取图标样式"""
        colors = {
            self.Information: "#3794FF",
            self.Warning: "#CCA700",
            self.Critical: "#F14C4C",
            self.Question: "#3794FF"
        }
        color = colors.get(self._icon_type, "#CCCCCC")
        return f"""
            QLabel {{
                color: {color};
                background-color: transparent;
            }}
        """
    
    def _apply_style(self):
        """应用当前主题样式"""
        from ur_print_fdm.ui.theme_manager import get_theme_manager

        t = get_theme_manager().current_tokens()
        self.setStyleSheet(
            f"background-color: {t.get('bg_panel', '#252526')}; "
            f"border: 1px solid {t.get('border', '#3C3C3C')}; "
            f"border-radius: {t.get('radius_lg', '6px')};"
        )
    
    def add_button(self, text, role, is_default=False, is_accent=False):
        """
        添加按钮
        
        Args:
            text: 按钮文本
            role: 按钮角色 (Yes/No/Cancel/Ok)
            is_default: 是否为默认按钮
            is_accent: 是否为强调按钮（蓝色）
        """
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setMinimumWidth(72)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if is_accent:
            btn.setProperty("ui_variant", "accent")
            # Force QSS refresh for property selectors.
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        if is_default:
            btn.setDefault(True)
        
        btn.clicked.connect(lambda: self._on_button_clicked(role))
        self._buttons[role] = btn
        self.button_layout.addWidget(btn)
        return btn
    
    def _on_button_clicked(self, role):
        """按钮点击处理"""
        self._result = role
        self.accept()
    
    def result_role(self):
        """获取结果角色"""
        return self._result
    
    # ============ 静态便捷方法 ============
    
    @staticmethod
    def information(parent, title, message):
        """信息提示框"""
        dialog = StyledMessageBox(parent, title, message, StyledMessageBox.Information)
        dialog.add_button("确定", StyledMessageBox.Ok, is_default=True, is_accent=True)
        dialog.exec()
        return StyledMessageBox.Ok
    
    @staticmethod
    def warning(parent, title, message):
        """警告提示框"""
        dialog = StyledMessageBox(parent, title, message, StyledMessageBox.Warning)
        dialog.add_button("确定", StyledMessageBox.Ok, is_default=True, is_accent=True)
        dialog.exec()
        return StyledMessageBox.Ok
    
    @staticmethod
    def critical(parent, title, message):
        """错误提示框"""
        dialog = StyledMessageBox(parent, title, message, StyledMessageBox.Critical)
        dialog.add_button("确定", StyledMessageBox.Ok, is_default=True, is_accent=True)
        dialog.exec()
        return StyledMessageBox.Ok
    
    @staticmethod
    def question(parent, title, message, buttons=None):
        """
        询问对话框
        
        Args:
            buttons: 按钮列表，默认 [Yes, No]
                     可选: [Yes, No, Cancel]
        
        Returns:
            StyledMessageBox.Yes / No / Cancel
        """
        if buttons is None:
            buttons = [StyledMessageBox.Yes, StyledMessageBox.No]
        
        dialog = StyledMessageBox(parent, title, message, StyledMessageBox.Question)
        
        # 添加按钮（根据配置）
        button_configs = {
            StyledMessageBox.Yes: ("是", True, True),
            StyledMessageBox.No: ("否", False, False),
            StyledMessageBox.Cancel: ("取消", False, False),
            StyledMessageBox.Ok: ("确定", True, True),
        }
        
        for i, btn_role in enumerate(buttons):
            text, is_default, is_accent = button_configs.get(btn_role, ("", False, False))
            # 只有第一个按钮是强调按钮
            dialog.add_button(text, btn_role, is_default=(i == 0), is_accent=(i == 0))
        
        dialog.exec()
        return dialog.result_role()
    
    @staticmethod
    def question_yes_no_cancel(parent, title, message):
        """带取消的询问对话框"""
        return StyledMessageBox.question(
            parent, title, message,
            [StyledMessageBox.Yes, StyledMessageBox.No, StyledMessageBox.Cancel]
        )
    
    @staticmethod
    def about(parent, title, message):
        """关于对话框"""
        dialog = StyledMessageBox(parent, title, message, StyledMessageBox.Information)
        dialog.setFixedWidth(420)  # 关于框稍宽一些
        dialog.add_button("确定", StyledMessageBox.Ok, is_default=True, is_accent=True)
        dialog.exec()
        return StyledMessageBox.Ok
