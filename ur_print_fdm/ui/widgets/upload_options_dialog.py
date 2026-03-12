"""Compact upload option dialog aligned with the app's control-panel style."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui.theme_manager import get_theme_manager


def _rgba(color: str, alpha: float) -> str:
    color = str(color or "").strip()
    if color.startswith("#") and len(color) == 7:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return f"rgba({r}, {g}, {b}, {alpha:.3f})"
    return color


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class _UploadOptionRow(QFrame):
    clicked = pyqtSignal(str)

    def __init__(
        self,
        *,
        role: str,
        title: str,
        description: str,
        state_text: str,
        recommended: bool = False,
        enabled: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._role = role
        self._enabled = enabled
        self.setObjectName("uploadOptionRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("hovered", False)
        self.setProperty("pressed", False)
        self.setProperty("focused", False)
        self.setProperty("disabled_state", not enabled)
        self.setProperty("recommended", recommended)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus if enabled else Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(74)
        self.setEnabled(enabled)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        layout.addLayout(top_row)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("uploadOptionTitle")
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        top_row.addWidget(self.title_label, 1)

        self.state_label = QLabel(state_text, self)
        self.state_label.setObjectName("uploadOptionState")
        self.state_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.state_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        top_row.addWidget(self.state_label, 0, Qt.AlignmentFlag.AlignTop)

        self.description_label = QLabel(description, self)
        self.description_label.setObjectName("uploadOptionDescription")
        self.description_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.description_label.setWordWrap(True)
        self.description_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.description_label)

    def isDefault(self) -> bool:
        return bool(self.property("recommended"))

    def click(self) -> None:
        if self._enabled:
            self.clicked.emit(self._role)

    def mousePressEvent(self, event) -> None:
        if self._enabled and event.button() == Qt.MouseButton.LeftButton:
            self.setProperty("pressed", True)
            _repolish(self)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._enabled and event.button() == Qt.MouseButton.LeftButton:
            self.setProperty("pressed", False)
            _repolish(self)
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit(self._role)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        if self._enabled:
            self.setProperty("hovered", True)
            _repolish(self)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        if self._enabled:
            self.setProperty("hovered", False)
            self.setProperty("pressed", False)
            _repolish(self)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        if self._enabled:
            self.setProperty("focused", True)
            _repolish(self)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if self._enabled:
            self.setProperty("focused", False)
            self.setProperty("pressed", False)
            _repolish(self)

    def keyPressEvent(self, event) -> None:
        if self._enabled and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self._role)
            event.accept()
            return
        super().keyPressEvent(event)


class UploadOptionsDialog(QDialog):
    """Dedicated upload dialog focused on compact clarity."""

    UploadOnly = "upload_only"
    UploadAndLoad = "load"
    Cancel = "cancel"

    def __init__(
        self,
        parent=None,
        *,
        file_count: int = 1,
        file_paths: list[str] | None = None,
        target_dir: str = "",
    ) -> None:
        super().__init__(parent)
        self._file_count = max(0, int(file_count))
        self._file_paths = list(file_paths or [])
        self._target_dir = str(target_dir or "").strip() or "/home/ur/ursim-current/programs"
        self._result = None

        self.setObjectName("uploadOptionsDialog")
        self.setWindowTitle("上传选项")
        self.setModal(True)
        self.setFixedWidth(404)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        self.upload_only_button: _UploadOptionRow | None = None
        self.upload_and_load_button: _UploadOptionRow | None = None
        self.cancel_button: QPushButton | None = None
        self.header_icon_label: QLabel | None = None
        self.actions_panel: QFrame | None = None

        self._init_ui()
        self._apply_style()
        self._finalize_geometry()

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 9, 10, 10)
        root.setSpacing(8)

        root.addWidget(self._build_header())
        root.addWidget(self._build_actions_panel())
        root.addLayout(self._build_footer())

        if self.upload_only_button is not None:
            self.upload_only_button.setFocus()

    def _build_header(self) -> QWidget:
        header = QFrame(self)
        header.setObjectName("uploadHeaderPanel")
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(9)

        icon_wrap = QFrame(header)
        icon_wrap.setObjectName("uploadHeaderIconWrap")
        icon_wrap.setFixedSize(30, 30)

        icon_layout = QVBoxLayout(icon_wrap)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)

        icon = QLabel(icon_wrap)
        icon.setObjectName("uploadHeaderIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(IconManager().get_svg_icon("upload", (13, 13)).pixmap(13, 13))
        icon_layout.addWidget(icon)
        layout.addWidget(icon_wrap, 0, Qt.AlignmentFlag.AlignTop)
        self.header_icon_label = icon

        text_wrap = QWidget(header)
        text_layout = QVBoxLayout(text_wrap)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        title = QLabel("请选择上传方式", text_wrap)
        title.setObjectName("uploadHeaderTitle")
        text_layout.addWidget(title)

        subtitle = QLabel(self._build_header_caption(), text_wrap)
        subtitle.setObjectName("uploadHeaderCaption")
        subtitle.setWordWrap(True)
        text_layout.addWidget(subtitle)
        layout.addWidget(text_wrap, 1)
        return header

    def _build_actions_panel(self) -> QFrame:
        panel = QFrame(self)
        panel.setObjectName("uploadActionsPanel")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.actions_panel = panel

        self.upload_only_button = _UploadOptionRow(
            role=self.UploadOnly,
            title="仅上传",
            description="上传到 programs，保留当前程序",
            state_text="默认",
            recommended=True,
            enabled=True,
            parent=panel,
        )
        self.upload_only_button.clicked.connect(self._finish)
        layout.addWidget(self.upload_only_button)

        can_load = self._file_count == 1
        self.upload_and_load_button = _UploadOptionRow(
            role=self.UploadAndLoad,
            title="上传并加载",
            description=(
                "更新 loader 引用并切换当前程序"
                if can_load
                else "该模式仅支持单文件"
            ),
            state_text="单文件" if can_load else "不可用",
            recommended=False,
            enabled=can_load,
            parent=panel,
        )
        self.upload_and_load_button.clicked.connect(self._finish)
        layout.addWidget(self.upload_and_load_button)
        return panel

    def _build_footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)

        note_text = self._build_footer_note()
        if note_text:
            note = QLabel(note_text)
            note.setObjectName("uploadFooterNote")
            footer.addWidget(note, 1)
        else:
            footer.addStretch(1)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setObjectName("uploadCancelButton")
        self.cancel_button.setMinimumWidth(86)
        self.cancel_button.setFixedHeight(30)
        self.cancel_button.clicked.connect(self.reject)
        footer.addWidget(self.cancel_button, 0, Qt.AlignmentFlag.AlignBottom)
        return footer

    def _build_header_caption(self) -> str:
        if self._file_count == 1:
            return "仅上传会保留当前程序；上传并加载会同步切换到本次文件。"
        return f"已选择 {self._file_count} 个文件，当前仅支持“仅上传”。"

    def _build_footer_note(self) -> str:
        return ""

    def _finalize_geometry(self) -> None:
        self.ensurePolished()
        self.layout().activate()
        content_height = max(self.sizeHint().height(), self.minimumSizeHint().height())
        self.setMinimumHeight(content_height)
        self.setMaximumHeight(content_height)
        self.setSizeGripEnabled(False)

    def _apply_style(self) -> None:
        t = get_theme_manager().current_tokens()
        bg_main = str(t.get("bg_main", "#2b2b2b"))
        bg_panel = str(t.get("bg_panel", "#2d2d2d"))
        bg_secondary = str(t.get("bg_secondary", "#1e1e1e"))
        bg_hover = str(t.get("bg_hover", "#2a2a2a"))
        border = str(t.get("border", "#3a3a3e"))
        border_light = str(t.get("border_light", "#46464a"))
        text = str(t.get("text", "#e0e0e0"))
        text_muted = str(t.get("text_muted", "#8a8a8a"))
        text_dim = str(t.get("text_dim", "#6a6a6a"))
        btn_bg = str(t.get("btn_bg", "#3c3c3c"))
        btn_bg_hover = str(t.get("btn_bg_hover", "#4a4a4a"))
        btn_bg_pressed = str(t.get("btn_bg_pressed", "#2a2a2a"))
        btn_border = str(t.get("btn_border", "#505050"))
        btn_border_hover = str(t.get("btn_border_hover", "#606060"))
        btn_text = str(t.get("btn_text", "#ffffff"))
        font_main = str(t.get("font_main", '"Segoe UI", "Microsoft YaHei", sans-serif'))
        radius = str(t.get("radius", "4px"))
        radius_lg = str(t.get("radius_lg", "6px"))
        panel_soft = _rgba(border_light, 0.14)
        panel_lift = _rgba(border_light, 0.10)

        self.setStyleSheet(
            f"""
            QDialog#uploadOptionsDialog {{
                background: {bg_main};
                color: {text};
                font-family: {font_main};
            }}
            QFrame#uploadHeaderPanel {{
                background: {bg_panel};
                border: 1px solid {border};
                border-radius: {radius_lg};
            }}
            QFrame#uploadHeaderIconWrap {{
                background: {panel_soft};
                border: 1px solid {_rgba(border_light, 0.6)};
                border-radius: 10px;
            }}
            QLabel#uploadHeaderIcon {{
                background: transparent;
            }}
            QLabel#uploadHeaderTitle {{
                color: {text};
                font-size: 13px;
                font-weight: 650;
            }}
            QLabel#uploadHeaderCaption {{
                color: {text_muted};
                font-size: 10.5px;
                line-height: 1.35;
            }}
            QFrame#uploadActionsPanel {{
                background: {bg_panel};
                border: 1px solid {border};
                border-radius: {radius_lg};
            }}
            QFrame#uploadOptionRow {{
                background: {panel_lift};
                border: 1px solid {border_light};
                border-radius: {radius_lg};
            }}
            QFrame#uploadOptionRow[recommended="true"] {{
                border-color: {border_light};
                background: {panel_lift};
            }}
            QFrame#uploadOptionRow[hovered="true"] {{
                border-color: {text_muted};
                background: {panel_soft};
            }}
            QFrame#uploadOptionRow[recommended="true"][hovered="true"] {{
                border-color: {text_muted};
                background: {_rgba(border_light, 0.18)};
            }}
            QFrame#uploadOptionRow[focused="true"] {{
                border-color: {text_muted};
            }}
            QFrame#uploadOptionRow[pressed="true"] {{
                background: {bg_hover};
            }}
            QFrame#uploadOptionRow[disabled_state="true"] {{
                background: {bg_secondary};
                border-color: {border};
            }}
            QLabel#uploadOptionTitle {{
                color: {text};
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }}
            QFrame#uploadOptionRow[disabled_state="true"] QLabel#uploadOptionTitle {{
                color: {text_dim};
            }}
            QLabel#uploadOptionDescription {{
                color: {text_muted};
                font-size: 10.5px;
                background: transparent;
                line-height: 1.25;
            }}
            QFrame#uploadOptionRow[disabled_state="true"] QLabel#uploadOptionDescription {{
                color: {text_dim};
            }}
            QLabel#uploadOptionState {{
                color: {text};
                background: {_rgba(border_light, 0.16)};
                border: 1px solid {_rgba(border_light, 0.38)};
                border-radius: {radius};
                padding: 1px 7px;
                font-size: 9.5px;
                font-weight: 600;
            }}
            QFrame#uploadOptionRow[recommended="true"] QLabel#uploadOptionState {{
                color: {btn_text};
                background: {btn_bg_hover};
                border-color: {border_light};
            }}
            QFrame#uploadOptionRow[disabled_state="true"] QLabel#uploadOptionState {{
                color: {text_dim};
                background: {_rgba(border_light, 0.14)};
                border-color: {_rgba(border_light, 0.24)};
            }}
            QLabel#uploadFooterNote {{
                color: {text_muted};
                font-size: 10px;
                padding-left: 1px;
            }}
            QPushButton#uploadCancelButton {{
                min-height: 24px;
                padding: 0 12px;
                background: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: {radius_lg};
                color: {btn_text};
                font-size: 10.5px;
                font-weight: 600;
            }}
            QPushButton#uploadCancelButton:hover {{
                background: {btn_bg_hover};
                border-color: {btn_border_hover};
            }}
            QPushButton#uploadCancelButton:pressed {{
                background: {btn_bg_pressed};
            }}
            """
        )

    def _finish(self, role: str) -> None:
        self._result = role
        self.accept()

    def result_role(self):
        return self._result

    def reject(self) -> None:
        if self._result is None:
            self._result = self.Cancel
        super().reject()
