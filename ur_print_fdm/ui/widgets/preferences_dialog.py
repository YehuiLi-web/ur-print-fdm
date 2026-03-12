from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QDialogButtonBox,
    QInputDialog,
    QScrollArea,
)

from ur_print_fdm.config import config_manager
from ur_print_fdm.config.robot_targets import (
    get_active_robot_target_id,
    get_robot_target_items,
    set_active_robot_target,
)
from ur_print_fdm.shared.net import is_valid_ip
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui.theme_manager import get_theme_manager
from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox


@dataclass(frozen=True)
class _Category:
    id: str
    title: str
    keywords: tuple[str, ...]
    factory: Callable[[], QWidget]


class _NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class _NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


def _rgba(color: str, alpha: float) -> str:
    color = str(color or "").strip()
    if color.startswith("#") and len(color) == 7:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return f"rgba({r}, {g}, {b}, {alpha:.3f})"
    return color


class PreferencesDialog(QDialog):
    settings_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置中心 / 首选项")
        self.resize(920, 600)
        self.setObjectName("preferencesDialog")

        self._original_config = config_manager.snapshot()
        self._normalize_supported_ui_settings(self._original_config)
        self._working_config = copy.deepcopy(self._original_config)
        self._dirty = False
        self._form_layouts: list[QFormLayout] = []
        self._compact_mode = False

        self._categories: list[_Category] = []
        self._category_items: dict[str, QListWidgetItem] = {}

        self._build_ui()
        self._build_categories()
        self._apply_search("")
        self._refresh_responsive_layout(force=True)

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

    @staticmethod
    def _normalize_supported_ui_settings(config: dict[str, Any]) -> None:
        ui_config = config.get("ui")
        if not isinstance(ui_config, dict):
            ui_config = {}
            config["ui"] = ui_config
        ui_config["dark_theme"] = True

    def _robot_target_items(self) -> dict[str, dict[str, Any]]:
        return get_robot_target_items(self._working_config)

    def _active_robot_target_id(self) -> str:
        return get_active_robot_target_id(self._working_config)

    def _robot_target_label(self, target_id: str) -> str:
        target = self._robot_target_items().get(target_id, {})
        label = str(target.get("label", "") or "").strip()
        return label or target_id

    def _switch_robot_target(self, target_id: str) -> None:
        current_id = self._active_robot_target_id()
        if not target_id or target_id == current_id:
            return
        if set_active_robot_target(self._working_config, target_id, persist_runtime=True):
            self._rebuild_from_working_config(keep_category=True)

    def _wrap_page(self, page: QWidget) -> QScrollArea:
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        page.setProperty("ui_role", "pref_page")
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        scroll = QScrollArea()
        scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scroll.setProperty("ui_role", "pref_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scroll.viewport().setProperty("ui_role", "pref_scroll_viewport")
        scroll.setWidget(page)
        return scroll

    def _should_use_compact_layout(self) -> bool:
        return self.width() < 1120

    def _new_page(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        page.setProperty("ui_role", "pref_page")
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 4, 8, 10)
        layout.setSpacing(8)
        return page, layout

    def _prepare_editor(self, editor: QWidget, *, max_width: int | None = None) -> QWidget:
        if max_width is not None:
            editor.setMaximumWidth(max_width)
        if isinstance(editor, QLineEdit):
            editor.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if editor.echoMode() != QLineEdit.EchoMode.Password:
                editor.setCursorPosition(0)
        if isinstance(editor, (QSpinBox, QDoubleSpinBox)):
            editor.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            editor.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return editor

    def _make_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("ui_role", "pref_card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setProperty("ui_role", "pref_card_title")
        layout.addWidget(title_lbl)
        return card, layout

    def _make_field_block(self, label: str, editor: QWidget, *, max_width: int | None = None) -> QWidget:
        block = QWidget()
        block.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        block.setProperty("ui_role", "pref_field_block")
        block.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        lbl = QLabel(label)
        lbl.setProperty("ui_role", "pref_field_label")
        layout.addWidget(lbl)

        self._prepare_editor(editor, max_width=max_width)
        if max_width is not None:
            layout.addWidget(editor, 0, Qt.AlignmentFlag.AlignLeft)
        else:
            layout.addWidget(editor)
        return block

    def _make_inline_field(
        self,
        label: str,
        editor: QWidget,
        *,
        label_width: int = 72,
        max_width: int | None = None,
        expand: bool = False,
    ) -> QWidget:
        field = QWidget()
        field.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        field.setProperty("ui_role", "pref_inline_field")
        field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(field)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        lbl = QLabel(f"{label}：")
        lbl.setProperty("ui_role", "pref_inline_label")
        lbl.setFixedWidth(label_width)
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl)

        self._prepare_editor(editor, max_width=None if expand else max_width)
        if expand:
            layout.addWidget(editor, 1)
        else:
            layout.addWidget(editor, 0)
            layout.addStretch(1)
        return field

    def _shared_inline_label_width(self, labels: list[str] | tuple[str, ...], *, minimum: int = 0) -> int:
        probe = QLabel("", self)
        probe.setProperty("ui_role", "pref_inline_label")
        probe.ensurePolished()
        metrics = probe.fontMetrics()
        measured = max((metrics.horizontalAdvance(f"{label}：") for label in labels), default=0)
        probe.deleteLater()
        return max(int(minimum), measured + 2)

    def _attach_password_toggle(self, editor: QLineEdit) -> None:
        icon_mgr = IconManager()
        show_icon = icon_mgr.get_svg_icon("eye", (14, 14))
        hide_icon = icon_mgr.get_svg_icon("eye_off", (14, 14))
        action = QAction(hide_icon, "", editor)
        action.setToolTip("显示密码")

        def _sync_icon() -> None:
            hidden = editor.echoMode() == QLineEdit.EchoMode.Password
            action.setIcon(hide_icon if hidden else show_icon)
            action.setToolTip("显示密码" if hidden else "隐藏密码")

        def _toggle() -> None:
            hidden = editor.echoMode() == QLineEdit.EchoMode.Password
            editor.setEchoMode(QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password)
            _sync_icon()

        action.triggered.connect(_toggle)
        editor.addAction(action, QLineEdit.ActionPosition.TrailingPosition)
        _sync_icon()

    def _make_row(self, *items: tuple[QWidget, int] | QWidget) -> QWidget:
        row = QWidget()
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row.setProperty("ui_role", "pref_row_host")
        row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        for item in items:
            if isinstance(item, tuple):
                widget, stretch = item
            else:
                widget, stretch = item, 1
            layout.addWidget(widget, stretch)
        return row

    def _make_left_row(self, *widgets: QWidget) -> QWidget:
        row = QWidget()
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row.setProperty("ui_role", "pref_row_host")
        row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        for widget in widgets:
            layout.addWidget(widget, 0)
        layout.addStretch(1)
        return row

    def _make_action_row(self, editor: QWidget, *buttons: QPushButton) -> QWidget:
        host = QWidget()
        host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        host.setProperty("ui_role", "pref_action_row")
        host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(editor, 1)
        for button in buttons:
            button.setMaximumWidth(80)
            row.addWidget(button)
        return host

    def _make_grid(self, widgets: list[QWidget], *, columns: int) -> QWidget:
        host = QWidget()
        host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        host.setProperty("ui_role", "pref_grid_host")
        host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        grid = QGridLayout(host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        columns = max(1, int(columns))
        for index, widget in enumerate(widgets):
            row = index // columns
            column = index % columns
            grid.addWidget(widget, row, column)
        for column in range(columns):
            grid.setColumnStretch(column, 1)
        return host

    def _build_robot_target_group(self) -> QWidget:
        card, layout = self._make_card("连接目标")
        label_width = self._shared_inline_label_width(["当前目标"], minimum=84)

        combo = FusedComboBox()
        combo.setMaximumWidth(260)
        active_id = self._active_robot_target_id()
        for target_id, target in self._robot_target_items().items():
            combo.addItem(str(target.get("label", target_id) or target_id), target_id)
        idx = combo.findData(active_id)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(lambda _: self._switch_robot_target(str(combo.currentData() or "")))

        layout.addWidget(self._make_inline_field("当前目标", combo, label_width=label_width, max_width=260))
        return card

    def _dialog_stylesheet(self) -> str:
        t = get_theme_manager().current_tokens()
        bg_main = str(t.get("bg_main", "#2b2b2b"))
        bg_secondary = str(t.get("bg_secondary", "#1e1e1e"))
        bg_panel = str(t.get("bg_panel", "#2d2d2d"))
        bg_hover = str(t.get("bg_hover", "#2a2a2a"))
        bg_hover_strong = str(t.get("bg_hover_strong", "#383838"))
        border = str(t.get("border", "#3a3a3e"))
        border_light = str(t.get("border_light", "#46464a"))
        text = str(t.get("text", "#e0e0e0"))
        text_muted = str(t.get("text_muted", "#8a8a8a"))
        text_dim = str(t.get("text_dim", "#6a6a6a"))
        accent = str(t.get("accent", "#094771"))
        accent_hover = str(t.get("accent_hover", "#0e639c"))
        accent_blue = str(t.get("accent_blue", "#2196F3"))
        selection_bg = str(t.get("selection_bg", "#264f78"))
        popup_surface_bg = _rgba(bg_secondary, 0.11)
        popup_hover_bg = "rgba(255, 255, 255, 0.020)"
        popup_selected_bg = "rgba(255, 255, 255, 0.055)"
        radius = str(t.get("radius", "4px"))
        radius_lg = str(t.get("radius_lg", "6px"))
        btn_bg = str(t.get("btn_bg", "#3c3c3c"))
        btn_bg_hover = str(t.get("btn_bg_hover", "#4a4a4a"))
        btn_bg_pressed = str(t.get("btn_bg_pressed", "#2a2a2a"))
        btn_border = str(t.get("btn_border", "#505050"))
        btn_border_hover = str(t.get("btn_border_hover", "#606060"))
        btn_text = str(t.get("btn_text", "#ffffff"))
        btn_disabled_bg = str(t.get("btn_disabled_bg", "#323232"))
        btn_disabled_border = str(t.get("btn_disabled_border", "#404040"))
        btn_disabled_text = str(t.get("btn_disabled_text", "#6a6a6a"))
        scroll_handle = str(t.get("scroll_handle", "rgba(121, 121, 121, 0.2)"))
        scroll_handle_hover = str(t.get("scroll_handle_hover", "rgba(121, 121, 121, 0.5)"))
        scroll_handle_pressed = str(t.get("scroll_handle_pressed", "rgba(121, 121, 121, 0.7)"))
        check_icon = (Path(__file__).resolve().parents[1] / "resources/icons/check.svg").as_posix()

        return f"""
            QDialog#preferencesDialog {{
                background: {bg_main};
                color: {text};
            }}
            QDialog#preferencesDialog QWidget[ui_role="pref_page"],
            QDialog#preferencesDialog QStackedWidget,
            QDialog#preferencesDialog QStackedWidget > QWidget,
            QDialog#preferencesDialog QScrollArea,
            QDialog#preferencesDialog QWidget[ui_role="pref_scroll_viewport"],
            QDialog#preferencesDialog QFrame#preferencesBody {{
                background: {bg_main};
                border: none;
            }}
            QDialog#preferencesDialog QLabel {{
                background: transparent;
                color: {text};
            }}
            QDialog#preferencesDialog QWidget[ui_role="pref_inline_field"],
            QDialog#preferencesDialog QWidget[ui_role="pref_field_block"],
            QDialog#preferencesDialog QWidget[ui_role="pref_row_host"],
            QDialog#preferencesDialog QWidget[ui_role="pref_action_row"],
            QDialog#preferencesDialog QWidget[ui_role="pref_grid_host"] {{
                background: transparent;
                border: none;
            }}
            QDialog#preferencesDialog QSplitter::handle {{
                background: transparent;
                width: 8px;
            }}
            QDialog#preferencesDialog QFrame#preferencesFooter {{
                background: {bg_main};
                border-top: 1px solid {border};
            }}
            QDialog#preferencesDialog QLineEdit#preferencesSearch {{
                min-height: 28px;
                padding: 0 12px;
                border-radius: {radius_lg};
                background: {bg_secondary};
                border: 1px solid {border};
                color: {text};
                font-size: 14px;
            }}
            QDialog#preferencesDialog QLineEdit#preferencesSearch:hover {{
                border-color: {border_light};
                background: {bg_panel};
            }}
            QDialog#preferencesDialog QLineEdit#preferencesSearch:focus {{
                border: 1px solid {accent_blue};
                background: {bg_panel};
            }}
            QDialog#preferencesDialog QLineEdit,
            QDialog#preferencesDialog QSpinBox,
            QDialog#preferencesDialog QDoubleSpinBox,
            QDialog#preferencesDialog QPlainTextEdit,
            QDialog#preferencesDialog QFrame[ui_role="fused_combo"] {{
                background: {bg_secondary};
                border: 1px solid {border};
                border-radius: {radius_lg};
                color: {text};
            }}
            QDialog#preferencesDialog QLineEdit,
            QDialog#preferencesDialog QSpinBox,
            QDialog#preferencesDialog QDoubleSpinBox {{
                min-height: 26px;
                padding: 0 10px;
                font-size: 13px;
            }}
            QDialog#preferencesDialog QPlainTextEdit {{
                padding: 10px 12px;
                font-size: 13px;
            }}
            QDialog#preferencesDialog QLineEdit:hover,
            QDialog#preferencesDialog QSpinBox:hover,
            QDialog#preferencesDialog QDoubleSpinBox:hover,
            QDialog#preferencesDialog QPlainTextEdit:hover,
            QDialog#preferencesDialog QFrame[ui_role="fused_combo"]:hover {{
                border-color: {border_light};
                background: {bg_panel};
            }}
            QDialog#preferencesDialog QLineEdit:focus,
            QDialog#preferencesDialog QSpinBox:focus,
            QDialog#preferencesDialog QDoubleSpinBox:focus,
            QDialog#preferencesDialog QPlainTextEdit:focus,
            QDialog#preferencesDialog QFrame[ui_role="fused_combo"][focused="true"] {{
                border: 1px solid {accent_blue};
                background: {bg_panel};
            }}
            QDialog#preferencesDialog QSpinBox::up-button,
            QDialog#preferencesDialog QSpinBox::down-button,
            QDialog#preferencesDialog QDoubleSpinBox::up-button,
            QDialog#preferencesDialog QDoubleSpinBox::down-button,
            QDialog#preferencesDialog QSpinBox::up-arrow,
            QDialog#preferencesDialog QSpinBox::down-arrow,
            QDialog#preferencesDialog QDoubleSpinBox::up-arrow,
            QDialog#preferencesDialog QDoubleSpinBox::down-arrow {{
                width: 0px;
                height: 0px;
                border: none;
                background: transparent;
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo"] {{
                min-height: 30px;
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo"][expanded="true"] {{
                border-color: {accent_blue};
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo"] QLabel[ui_role="fused_combo_label"],
            QDialog#preferencesDialog QFrame[ui_role="fused_combo"] QLineEdit[ui_role="fused_combo_edit"] {{
                background: transparent;
                border: none;
                padding: 0 8px 0 10px;
                color: {text};
                font-size: 13px;
                font-weight: 500;
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo"] QLineEdit[ui_role="fused_combo_edit"]:focus,
            QDialog#preferencesDialog QFrame[ui_role="fused_combo"] QLineEdit[ui_role="fused_combo_edit"]:hover {{
                background: transparent;
                border: none;
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo_arrow_host"] {{
                background: transparent;
                border: none;
                border-left: 1px solid {border};
                border-top-right-radius: {radius_lg};
                border-bottom-right-radius: {radius_lg};
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo_popup_surface"] {{
                background: {popup_surface_bg};
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-top: none;
                border-bottom-left-radius: {radius_lg};
                border-bottom-right-radius: {radius_lg};
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo_popup_item"] {{
                background: transparent;
                border: none;
                border-radius: 0px;
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo_popup_item"][highlighted="true"] {{
                background: {popup_hover_bg};
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo_popup_item"][selected="true"] {{
                background: {popup_selected_bg};
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo_popup_item"][selected="true"][highlighted="true"] {{
                background: {popup_selected_bg};
            }}
            QDialog#preferencesDialog QFrame[ui_role="fused_combo_popup_item"][last="true"] {{
                border-bottom-left-radius: {radius_lg};
                border-bottom-right-radius: {radius_lg};
            }}
            QDialog#preferencesDialog QPushButton {{
                min-height: 26px;
                padding: 0 12px;
                background: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: {radius_lg};
                color: {btn_text};
            }}
            QDialog#preferencesDialog QPushButton:hover {{
                background: {btn_bg_hover};
                border-color: {btn_border_hover};
            }}
            QDialog#preferencesDialog QPushButton:pressed {{
                background: {btn_bg_pressed};
            }}
            QDialog#preferencesDialog QPushButton:disabled {{
                color: {btn_disabled_text};
                background: {btn_disabled_bg};
                border-color: {btn_disabled_border};
            }}
            QDialog#preferencesDialog QPushButton[ui_variant="accent"] {{
                background: {accent_hover};
                border-color: {accent_blue};
                color: {btn_text};
            }}
            QDialog#preferencesDialog QPushButton[ui_variant="accent"]:hover {{
                background: {accent_blue};
                border-color: {accent_blue};
            }}
            QDialog#preferencesDialog QPushButton[ui_variant="accent"]:pressed {{
                background: {accent};
                border-color: {accent};
            }}
            QDialog#preferencesDialog QDialogButtonBox QPushButton {{
                min-width: 84px;
            }}
            QDialog#preferencesDialog QFrame#preferencesFooter QPushButton {{
                min-height: 24px;
                padding: 0 10px;
            }}
            QDialog#preferencesDialog QFrame#preferencesFooter QDialogButtonBox QPushButton {{
                min-width: 56px;
            }}
            QDialog#preferencesDialog QListWidget[ui_role="pref_nav"] {{
                border: 1px solid {border};
                border-radius: {radius_lg};
                background: {bg_panel};
                outline: none;
                padding: 8px 0;
            }}
            QDialog#preferencesDialog QListWidget[ui_role="pref_nav"]::item {{
                margin: 2px 8px;
                padding: 10px 14px;
                border-radius: {radius_lg};
            }}
            QDialog#preferencesDialog QListWidget[ui_role="pref_nav"]::item:selected {{
                background: {selection_bg};
                color: {text};
            }}
            QDialog#preferencesDialog QListWidget[ui_role="pref_nav"]::item:hover:!selected {{
                background: {bg_hover};
            }}
            QDialog#preferencesDialog QListWidget[ui_role="pref_list"] {{
                border: 1px solid {border};
                border-radius: {radius_lg};
                background: {bg_secondary};
                outline: none;
                padding: 4px;
            }}
            QDialog#preferencesDialog QListWidget[ui_role="pref_list"]::item {{
                margin: 0;
                padding: 8px 10px;
                border-radius: {radius};
            }}
            QDialog#preferencesDialog QListWidget[ui_role="pref_list"]::item:selected {{
                background: {accent};
                color: {btn_text};
            }}
            QDialog#preferencesDialog QListWidget[ui_role="pref_list"]::item:hover:!selected {{
                background: {bg_hover};
            }}
            QDialog#preferencesDialog QFrame[ui_role="pref_card"] {{
                border: 1px solid {border};
                border-radius: {radius_lg};
                background: {bg_panel};
            }}
            QDialog#preferencesDialog QLabel[ui_role="pref_card_title"] {{
                color: {text};
                font-size: 17px;
                font-weight: 650;
            }}
            QDialog#preferencesDialog QLabel[ui_role="pref_field_label"] {{
                color: {text};
                font-size: 13px;
                font-weight: 600;
                padding-left: 1px;
            }}
            QDialog#preferencesDialog QLabel[ui_role="pref_inline_label"] {{
                color: {text};
                font-size: 13px;
                font-weight: 600;
            }}
            QDialog#preferencesDialog QCheckBox {{
                spacing: 8px;
                color: {text};
            }}
            QDialog#preferencesDialog QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: {radius};
                border: 1px solid {btn_border};
                background: {bg_secondary};
            }}
            QDialog#preferencesDialog QCheckBox::indicator:checked {{
                background: {accent_hover};
                border-color: {accent_hover};
                image: url({check_icon});
            }}
            QDialog#preferencesDialog QCheckBox::indicator:hover {{
                border-color: {border_light};
            }}
            QDialog#preferencesDialog QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 10px;
                margin: 4px 2px 4px 0;
            }}
            QDialog#preferencesDialog QScrollBar:horizontal {{
                border: none;
                background: transparent;
                height: 10px;
                margin: 0 4px 2px 4px;
            }}
            QDialog#preferencesDialog QScrollBar::handle:vertical {{
                background: {scroll_handle};
                min-height: 36px;
                border-radius: {radius};
            }}
            QDialog#preferencesDialog QScrollBar::handle:horizontal {{
                background: {scroll_handle};
                min-width: 36px;
                border-radius: {radius};
            }}
            QDialog#preferencesDialog QScrollBar::handle:vertical:hover,
            QDialog#preferencesDialog QScrollBar::handle:horizontal:hover {{
                background: {scroll_handle_hover};
            }}
            QDialog#preferencesDialog QScrollBar::handle:vertical:pressed,
            QDialog#preferencesDialog QScrollBar::handle:horizontal:pressed {{
                background: {scroll_handle_pressed};
            }}
            QDialog#preferencesDialog QScrollBar::add-line:vertical,
            QDialog#preferencesDialog QScrollBar::sub-line:vertical,
            QDialog#preferencesDialog QScrollBar::add-line:horizontal,
            QDialog#preferencesDialog QScrollBar::sub-line:horizontal,
            QDialog#preferencesDialog QScrollBar::add-page:vertical,
            QDialog#preferencesDialog QScrollBar::sub-page:vertical,
            QDialog#preferencesDialog QScrollBar::add-page:horizontal,
            QDialog#preferencesDialog QScrollBar::sub-page:horizontal,
            QDialog#preferencesDialog QAbstractScrollArea::corner {{
                border: none;
                background: transparent;
            }}
            QDialog#preferencesDialog QLabel#preferencesCaption {{
                color: {text_dim};
            }}
        """

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
        self._refresh_responsive_layout(force=True)

    # -----------------------------
    # UI
    # -----------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        self.setStyleSheet(self._dialog_stylesheet())

        # Search bar
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("preferencesSearch")
        self.search_edit.setPlaceholderText("搜索设置（例如：日志 / watchdog / SFTP / IP）…")
        self.search_edit.textChanged.connect(self._apply_search)
        layout.addWidget(self.search_edit)

        body = QFrame()
        body.setObjectName("preferencesBody")
        body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        layout.addWidget(body, 1)

        self.splitter = QSplitter()
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(8)
        body_layout.addWidget(self.splitter, 1)

        # Left: category list
        self.category_list = QListWidget()
        self.category_list.setProperty("ui_role", "pref_nav")
        self.category_list.setMinimumWidth(168)
        self.category_list.setMaximumWidth(216)
        self.category_list.currentRowChanged.connect(self._on_category_changed)
        self.splitter.addWidget(self.category_list)

        # Right: pages
        self.pages = QStackedWidget()
        self.pages.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.splitter.addWidget(self.pages)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([176, 744])

        # Bottom buttons: import/export/reset + Apply/OK/Cancel
        footer = QFrame()
        footer.setObjectName("preferencesFooter")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout.addWidget(footer)

        bottom = QHBoxLayout(footer)
        bottom.setContentsMargins(0, 10, 0, 0)
        bottom.setSpacing(6)

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
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setProperty("ui_variant", "accent")
        ok_button.style().unpolish(ok_button)
        ok_button.style().polish(ok_button)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)
        self.button_box.accepted.connect(self._on_ok)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        bottom.addWidget(self.button_box)

    def _build_categories(self, *, initial_category_id: str | None = None) -> None:
        self._form_layouts = []
        self._categories = [
            _Category("robot", "机器人与连接", ("robot", "ip", "backend", "连接"), self._page_robot),
            _Category("transfer", "传输 (SFTP)", ("sftp", "upload", "传输"), self._page_transfer),
            _Category("printing", "生产参数", ("printing", "modbus", "extruder", "挤出"), self._page_printing),
            _Category("safety", "安全", ("watchdog", "安全"), self._page_safety),
            _Category("project", "项目", ("project", "删除", "confirm"), self._page_project),
            _Category("ui", "界面", ("ui", "theme", "panel", "window"), self._page_ui),
            _Category("logging", "日志", ("log", "logging", "保存", "路径"), self._page_logging),
            _Category("advanced", "高级", ("json", "advanced", "全部"), self._page_advanced),
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
            self.pages.addWidget(self._wrap_page(cat.factory()))

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

        w, root = self._new_page()
        current_target_label = self._robot_target_label(self._active_robot_target_id())
        compact = self._should_use_compact_layout()
        backend_label_width = self._shared_inline_label_width(["机器人后端"], minimum=92)

        root.addWidget(self._build_robot_target_group())

        backend_combo = FusedComboBox()
        backend_combo.setMaximumWidth(220)
        backend_ids = sorted(registry.robot_backends.keys())
        backend_combo.addItems(backend_ids)
        backend_combo.setCurrentText(str(self._get("robot.backend_id", "ur_rtde_cb3")))
        backend_combo.currentTextChanged.connect(lambda v: self._set("robot.backend_id", str(v).strip()))
        backend_card, backend_layout = self._make_card("后端")
        backend_layout.addWidget(
            self._make_inline_field("机器人后端", backend_combo, label_width=backend_label_width, max_width=220)
        )
        root.addWidget(backend_card)

        conn_card, conn_layout = self._make_card("连接")

        lbl_conn = QLabel("连接异常后请在工具栏手动执行“修复连接”。\n系统不再执行后台自动重连。")
        lbl_conn.setWordWrap(True)
        lbl_conn.setProperty("ui_role", "pref_field_label")
        conn_layout.addWidget(lbl_conn)
        root.addWidget(conn_card)

        ip_card, ip_layout = self._make_card(f"IP 地址 · {current_target_label}")

        ip_list = QListWidget()
        ip_list.setProperty("ui_role", "pref_list")
        ip_list.setMinimumHeight(130)
        for ip in (self._get("robot.ip_addresses", []) or []):
            ip_list.addItem(str(ip))
        ip_layout.addWidget(ip_list)

        default_ip = str(self._get("robot.default_ip", "") or "")
        lbl_default = QLabel(f"默认 IP：{default_ip if default_ip else '（未设置）'}")
        lbl_default.setProperty("ui_role", "pref_field_label")
        ip_layout.addWidget(lbl_default)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)
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
        if compact:
            btn_wrap = QWidget()
            btn_wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn_grid = QGridLayout(btn_wrap)
            btn_grid.setContentsMargins(0, 0, 0, 0)
            btn_grid.setHorizontalSpacing(8)
            btn_grid.setVerticalSpacing(8)
            btn_grid.addWidget(btn_add, 0, 0)
            btn_grid.addWidget(btn_remove, 0, 1)
            btn_grid.addWidget(btn_up, 1, 0)
            btn_grid.addWidget(btn_down, 1, 1)
            btn_grid.addWidget(btn_default, 2, 0, 1, 2)
            ip_layout.addWidget(btn_wrap)
        else:
            ip_layout.addLayout(btn_row)

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

        root.addWidget(ip_card)
        root.addStretch(1)
        return w

    def _page_transfer(self) -> QWidget:
        w, root = self._new_page()
        current_target_label = self._robot_target_label(self._active_robot_target_id())
        sftp_label_width = self._shared_inline_label_width(["端口", "用户名", "密码", "远端目录"], minimum=72)
        loader_label_width = self._shared_inline_label_width(
            ["loader.urp 路径", "remote_loader 文件名"],
            minimum=124,
        )

        root.addWidget(self._build_robot_target_group())

        spin_port = _NoWheelSpinBox()
        spin_port.setRange(1, 65535)
        spin_port.setValue(int(self._get("robot.sftp.port", 22) or 22))
        spin_port.valueChanged.connect(lambda v: self._set("robot.sftp.port", int(v)))
        spin_port.setMaximumWidth(130)

        edit_user = QLineEdit(str(self._get("robot.sftp.username", "ur") or ""))
        edit_user.editingFinished.connect(lambda: self._set("robot.sftp.username", edit_user.text().strip()))
        edit_user.setMaximumWidth(180)

        edit_pwd = QLineEdit(str(self._get("robot.sftp.password", "") or ""))
        edit_pwd.setObjectName("preferencesSftpPassword")
        edit_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._attach_password_toggle(edit_pwd)
        edit_pwd.editingFinished.connect(lambda: self._set("robot.sftp.password", edit_pwd.text()))
        edit_pwd.setMaximumWidth(180)

        edit_dir = QLineEdit(str(self._get("robot.sftp.remote_dir", "") or ""))
        edit_dir.editingFinished.connect(lambda: self._set("robot.sftp.remote_dir", edit_dir.text().strip()))
        edit_dir.setPlaceholderText("/programs")

        sftp_card, sftp_layout = self._make_card(f"SFTP 上传参数 · {current_target_label}")
        port_block = self._make_inline_field("端口", spin_port, label_width=sftp_label_width, max_width=86)
        user_block = self._make_inline_field("用户名", edit_user, label_width=sftp_label_width, max_width=156)
        pwd_block = self._make_inline_field("密码", edit_pwd, label_width=sftp_label_width, max_width=156)
        dir_block = self._make_inline_field("远端目录", edit_dir, label_width=sftp_label_width, expand=True)

        sftp_layout.addWidget(port_block)
        sftp_layout.addWidget(user_block)
        sftp_layout.addWidget(pwd_block)
        sftp_layout.addWidget(dir_block)

        root.addWidget(sftp_card)

        loader_card, loader_layout = self._make_card("Dashboard / Loader")

        edit_loader = QLineEdit(str(self._get("robot.dashboard.loader_urp_path", "") or ""))
        edit_loader.editingFinished.connect(
            lambda: self._set("robot.dashboard.loader_urp_path", edit_loader.text().strip())
        )
        edit_loader.setPlaceholderText("/programs/loader.urp")

        edit_remote = QLineEdit(str(self._get("robot.dashboard.remote_loader_name", "") or ""))
        edit_remote.setObjectName("preferencesRemoteLoaderName")
        edit_remote.setPlaceholderText("remote_loader.script")
        edit_remote.editingFinished.connect(
            lambda: self._set("robot.dashboard.remote_loader_name", edit_remote.text().strip())
        )

        loader_layout.addWidget(
            self._make_inline_field("loader.urp 路径", edit_loader, label_width=loader_label_width, expand=True)
        )
        loader_layout.addWidget(
            self._make_inline_field("remote_loader 文件名", edit_remote, label_width=loader_label_width, expand=True)
        )

        root.addWidget(loader_card)
        root.addStretch(1)
        return w

    def _page_printing(self) -> QWidget:
        w, root = self._new_page()
        io_label_width = self._shared_inline_label_width(
            ["挤出 DO 引脚", "挤出 Modbus 寄存器"],
            minimum=116,
        )
        defaults_label_width = self._shared_inline_label_width(["丝径", "基址", "线宽", "层高", "速度"], minimum=52)
        tt_label_width = self._shared_inline_label_width(["Pin", "BU"], minimum=64)

        io_card, io_layout = self._make_card("挤出与 IO")
        spin_do = _NoWheelSpinBox()
        spin_do.setRange(0, 15)
        spin_do.setValue(int(self._get("printing.extruder_io_pin", 0) or 0))
        spin_do.valueChanged.connect(lambda v: self._set("printing.extruder_io_pin", int(v)))
        do_block = self._make_inline_field("挤出 DO 引脚", spin_do, label_width=io_label_width, max_width=92)

        edit_modbus = QLineEdit(str(self._get("printing.modbus_extruder", "MODBUS_1") or ""))
        edit_modbus.setPlaceholderText("例如：MODBUS_1")
        edit_modbus.editingFinished.connect(lambda: self._set("printing.modbus_extruder", edit_modbus.text().strip()))
        modbus_block = self._make_inline_field(
            "挤出 Modbus 寄存器", edit_modbus, label_width=io_label_width, max_width=188
        )

        io_layout.addWidget(do_block)
        io_layout.addWidget(modbus_block)
        root.addWidget(io_card)

        defaults_card, defaults_layout = self._make_card("默认工艺参数")

        spin_dia = _NoWheelDoubleSpinBox()
        spin_dia.setRange(0.1, 10.0)
        spin_dia.setSingleStep(0.05)
        spin_dia.setDecimals(2)
        spin_dia.setValue(float(self._get("printing.default_filament_diameter", 1.75) or 1.75))
        spin_dia.valueChanged.connect(lambda v: self._set("printing.default_filament_diameter", float(v)))
        dia_block = self._make_inline_field("丝径", spin_dia, label_width=defaults_label_width, max_width=82)

        spin_reg = _NoWheelSpinBox()
        spin_reg.setRange(0, 65535)
        spin_reg.setValue(int(self._get("printing.default_base_register", 4000) or 4000))
        spin_reg.valueChanged.connect(lambda v: self._set("printing.default_base_register", int(v)))
        reg_block = self._make_inline_field("基址", spin_reg, label_width=defaults_label_width, max_width=96)

        spin_w = _NoWheelDoubleSpinBox()
        spin_w.setRange(0.01, 50.0)
        spin_w.setSingleStep(0.1)
        spin_w.setDecimals(3)
        spin_w.setValue(float(self._get("printing.default_line_width", 1.0) or 1.0))
        spin_w.valueChanged.connect(lambda v: self._set("printing.default_line_width", float(v)))
        width_block = self._make_inline_field("线宽", spin_w, label_width=defaults_label_width, max_width=82)

        spin_h = _NoWheelDoubleSpinBox()
        spin_h.setRange(0.01, 20.0)
        spin_h.setSingleStep(0.05)
        spin_h.setDecimals(3)
        spin_h.setValue(float(self._get("printing.default_layer_height", 0.5) or 0.5))
        spin_h.valueChanged.connect(lambda v: self._set("printing.default_layer_height", float(v)))
        height_block = self._make_inline_field("层高", spin_h, label_width=defaults_label_width, max_width=82)

        spin_speed = _NoWheelDoubleSpinBox()
        spin_speed.setRange(0.01, 200.0)
        spin_speed.setSingleStep(0.5)
        spin_speed.setDecimals(2)
        spin_speed.setValue(float(self._get("printing.default_print_speed", 5.0) or 5.0))
        spin_speed.valueChanged.connect(lambda v: self._set("printing.default_print_speed", float(v)))
        speed_block = self._make_inline_field("速度", spin_speed, label_width=defaults_label_width, max_width=90)

        for block in [dia_block, reg_block, width_block, height_block, speed_block]:
            defaults_layout.addWidget(block)
        root.addWidget(defaults_card)

        tt_card, tt_layout = self._make_card("转台 (Modbus)")

        edit_pin = QLineEdit(str(self._get("printing.modbus_turntable_pin", "") or ""))
        edit_pin.editingFinished.connect(lambda: self._set("printing.modbus_turntable_pin", edit_pin.text().strip()))
        pin_block = self._make_inline_field("Pin", edit_pin, label_width=tt_label_width, max_width=164)

        edit_bu = QLineEdit(str(self._get("printing.modbus_turntable_bu", "") or ""))
        edit_bu.editingFinished.connect(lambda: self._set("printing.modbus_turntable_bu", edit_bu.text().strip()))
        bu_block = self._make_inline_field("BU", edit_bu, label_width=tt_label_width, max_width=164)

        tt_layout.addWidget(pin_block)
        tt_layout.addWidget(bu_block)
        root.addWidget(tt_card)
        root.addStretch(1)
        return w

    def _page_safety(self) -> QWidget:
        w, root = self._new_page()
        label_width = self._shared_inline_label_width(["静止超时", "速度阈值"], minimum=88)

        card, layout = self._make_card("看门狗 (Watchdog)")

        spin_timeout = _NoWheelSpinBox()
        spin_timeout.setRange(5, 3600)
        spin_timeout.setSuffix(" 秒")
        spin_timeout.setValue(int(float(self._get("safety.watchdog_timeout", 120.0) or 120.0)))
        spin_timeout.valueChanged.connect(lambda v: self._set("safety.watchdog_timeout", float(v)))
        timeout_block = self._make_inline_field("静止超时", spin_timeout, label_width=label_width, max_width=118)

        spin_speed = _NoWheelDoubleSpinBox()
        spin_speed.setRange(0.0, 0.1)
        spin_speed.setSingleStep(0.001)
        spin_speed.setDecimals(4)
        spin_speed.setSuffix(" m/s")
        spin_speed.setValue(float(self._get("safety.watchdog_speed_threshold", 0.002) or 0.002))
        spin_speed.valueChanged.connect(lambda v: self._set("safety.watchdog_speed_threshold", float(v)))
        speed_block = self._make_inline_field("速度阈值", spin_speed, label_width=label_width, max_width=132)

        layout.addWidget(timeout_block)
        layout.addWidget(speed_block)
        root.addWidget(card)
        root.addStretch(1)
        return w

    def _page_project(self) -> QWidget:
        w, root = self._new_page()

        card, layout = self._make_card("项目")

        edit_path = QLineEdit(str(self._get("project.last_project_path", "") or ""))
        edit_path.setPlaceholderText("最近打开的项目路径")

        btn_browse = QPushButton("浏览…")
        btn_clear = QPushButton("清空")

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
        layout.addWidget(self._make_inline_field("最近项目", self._make_action_row(edit_path, btn_browse, btn_clear), label_width=72, expand=True))

        chk_confirm = QCheckBox("删除/清理项目文件前需要二次确认")
        chk_confirm.setChecked(bool(self._get("project.confirm_deletion", True)))
        chk_confirm.stateChanged.connect(lambda _: self._set("project.confirm_deletion", bool(chk_confirm.isChecked())))
        layout.addWidget(chk_confirm)

        root.addWidget(card)
        root.addStretch(1)
        return w

    def _page_ui(self) -> QWidget:
        w, root = self._new_page()
        compact = self._should_use_compact_layout()
        theme_label_width = self._shared_inline_label_width(["主题", "窗口宽度", "窗口高度"], minimum=76)
        log_label_width = self._shared_inline_label_width(["最大保留行数"], minimum=96)

        theme_card, theme_layout = self._make_card("主题与窗口")

        cmb_theme = FusedComboBox()
        cmb_theme.addItem("暗色（默认）", True)
        cmb_theme.setCurrentIndex(0)
        cmb_theme.setEnabled(False)
        theme_layout.addWidget(self._make_inline_field("主题", cmb_theme, label_width=theme_label_width, max_width=220))

        window_size = self._get("ui.window_size", [1400, 900]) or [1400, 900]
        try:
            width = int(window_size[0])
            height = int(window_size[1])
        except Exception:
            width, height = 1400, 900

        spin_w = _NoWheelSpinBox()
        spin_w.setRange(600, 8000)
        spin_w.setValue(width)
        spin_h = _NoWheelSpinBox()
        spin_h.setRange(400, 8000)
        spin_h.setValue(height)

        def _set_size() -> None:
            self._set("ui.window_size", [int(spin_w.value()), int(spin_h.value())])

        spin_w.valueChanged.connect(lambda _: _set_size())
        spin_h.valueChanged.connect(lambda _: _set_size())
        width_block = self._make_inline_field("窗口宽度", spin_w, label_width=theme_label_width, max_width=110)
        height_block = self._make_inline_field("窗口高度", spin_h, label_width=theme_label_width, max_width=110)
        theme_layout.addWidget(width_block)
        theme_layout.addWidget(height_block)

        root.addWidget(theme_card)

        log_card, log_layout = self._make_card("日志面板")

        chk_scroll = QCheckBox("自动滚动到最新日志")
        chk_scroll.setChecked(bool(self._get("ui.auto_scroll_log", True)))
        chk_scroll.stateChanged.connect(lambda _: self._set("ui.auto_scroll_log", bool(chk_scroll.isChecked())))
        log_layout.addWidget(chk_scroll)

        spin_lines = _NoWheelSpinBox()
        spin_lines.setRange(100, 200000)
        spin_lines.setSingleStep(100)
        spin_lines.setValue(int(self._get("ui.log_max_lines", 2000) or 2000))
        spin_lines.valueChanged.connect(lambda v: self._set("ui.log_max_lines", int(v)))
        log_layout.addWidget(self._make_inline_field("最大保留行数", spin_lines, label_width=log_label_width, max_width=132))

        root.addWidget(log_card)

        panels_card, panels_layout = self._make_card("面板默认折叠")

        def _panel_checkbox(title: str, key: str) -> QCheckBox:
            cb = QCheckBox(title)
            cb.setChecked(bool(self._get(f"ui.panels.{key}", False)))
            cb.stateChanged.connect(lambda _: self._set(f"ui.panels.{key}", bool(cb.isChecked())))
            return cb

        panels = [
            _panel_checkbox("关节面板", "joint_panel_collapsed"),
            _panel_checkbox("TCP 面板", "tcp_panel_collapsed"),
            _panel_checkbox("偏移面板", "offset_panel_collapsed"),
            _panel_checkbox("统计面板", "stats_panel_collapsed"),
            _panel_checkbox("运动面板", "motion_panel_collapsed"),
            _panel_checkbox("挤出面板", "extrusion_panel_collapsed"),
        ]
        panel_grid_host = QWidget()
        panel_grid_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        panel_grid = QGridLayout(panel_grid_host)
        panel_grid.setContentsMargins(0, 0, 0, 0)
        panel_grid.setHorizontalSpacing(14)
        panel_grid.setVerticalSpacing(10)
        columns = 1 if compact else 2
        for index, checkbox in enumerate(panels):
            row = index if columns == 1 else index // columns
            column = 0 if columns == 1 else index % columns
            panel_grid.addWidget(checkbox, row, column)
        panels_layout.addWidget(panel_grid_host)

        root.addWidget(panels_card)

        est_card, est_layout = self._make_card("脚本估算")
        chk_est_on_run = QCheckBox("运行时自动估算打印时间/线材 (URScript)")
        chk_est_on_run.setChecked(bool(self._get("ui.urscript_estimate_on_run", False)))
        chk_est_on_run.stateChanged.connect(
            lambda _: self._set("ui.urscript_estimate_on_run", bool(chk_est_on_run.isChecked()))
        )
        est_layout.addWidget(chk_est_on_run)

        root.addWidget(est_card)
        root.addStretch(1)
        return w

    def _page_logging(self) -> QWidget:
        w, root = self._new_page()
        file_label_width = self._shared_inline_label_width(["写入级别", "保留天数", "日志目录"], minimum=84)
        ui_label_width = self._shared_inline_label_width(["显示级别"], minimum=84)

        file_card, file_layout = self._make_card("文件日志（持久化）")

        cmb_level = FusedComboBox()
        cmb_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        cmb_level.setCurrentText(str(self._get("logging.level", "INFO") or "INFO").upper())
        cmb_level.currentTextChanged.connect(lambda v: self._set("logging.level", str(v).upper()))
        level_block = self._make_inline_field("写入级别", cmb_level, label_width=file_label_width, max_width=156)

        spin_ret = _NoWheelSpinBox()
        spin_ret.setRange(1, 365)
        spin_ret.setValue(int(self._get("logging.retention_days", 14) or 14))
        spin_ret.valueChanged.connect(lambda v: self._set("logging.retention_days", int(v)))
        retention_block = self._make_inline_field("保留天数", spin_ret, label_width=file_label_width, max_width=110)

        edit_dir = QLineEdit(str(self._get("logging.dir", "") or ""))
        edit_dir.setPlaceholderText("留空使用默认目录（~/.ur_print_fdm/logs）")
        btn_dir = QPushButton("选择…")

        def _browse_dir() -> None:
            base = edit_dir.text().strip()
            start = str(Path(base).expanduser()) if base else str(Path.home())
            p = QFileDialog.getExistingDirectory(self, "选择日志目录", start)
            if p:
                edit_dir.setText(p)
                self._set("logging.dir", p)

        btn_dir.clicked.connect(_browse_dir)
        edit_dir.editingFinished.connect(lambda: self._set("logging.dir", edit_dir.text().strip()))
        dir_block = self._make_inline_field(
            "日志目录", self._make_action_row(edit_dir, btn_dir), label_width=file_label_width, expand=True
        )

        file_layout.addWidget(level_block)
        file_layout.addWidget(retention_block)
        file_layout.addWidget(dir_block)
        root.addWidget(file_card)

        ui_card, ui_layout = self._make_card("界面日志（面板显示）")

        cmb_ui = FusedComboBox()
        cmb_ui.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        cmb_ui.setCurrentText(str(self._get("logging.ui_level", "INFO") or "INFO").upper())
        cmb_ui.currentTextChanged.connect(lambda v: self._set("logging.ui_level", str(v).upper()))
        ui_layout.addWidget(self._make_inline_field("显示级别", cmb_ui, label_width=ui_label_width, max_width=156))

        chk_third = QCheckBox("显示第三方库日志（可能更噪）")
        chk_third.setChecked(bool(self._get("logging.ui_show_third_party", False)))
        chk_third.stateChanged.connect(lambda _: self._set("logging.ui_show_third_party", bool(chk_third.isChecked())))
        ui_layout.addWidget(chk_third)

        root.addWidget(ui_card)
        root.addStretch(1)
        return w

    def _page_advanced(self) -> QWidget:
        w, root = self._new_page()
        card, layout = self._make_card("高级 JSON")

        editor = QPlainTextEdit()
        editor.setPlaceholderText("{\n  \"robot\": { ... }\n}")
        editor.setPlainText(json.dumps(self._working_config, ensure_ascii=False, indent=2))
        layout.addWidget(editor, 1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_reload = QPushButton("从当前设置生成")
        btn_validate = QPushButton("校验")
        btn_apply = QPushButton("应用到工作副本")
        btn_row.addWidget(btn_reload)
        btn_row.addWidget(btn_validate)
        btn_row.addWidget(btn_apply)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

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
        root.addWidget(card, 1)
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
            self._normalize_supported_ui_settings(self._working_config)
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
        self._normalize_supported_ui_settings(self._working_config)
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
            self._normalize_supported_ui_settings(self._working_config)
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

    def _refresh_responsive_layout(self, *, force: bool = False) -> None:
        compact = self._should_use_compact_layout()
        mode_changed = compact != self._compact_mode
        self._compact_mode = compact

        if mode_changed and not force and self._categories:
            self._rebuild_from_working_config(keep_category=True)
            return

        wrap_policy = (
            QFormLayout.RowWrapPolicy.WrapAllRows
            if compact
            else QFormLayout.RowWrapPolicy.DontWrapRows
        )
        h_spacing = 10 if compact else 16
        v_spacing = 8 if compact else 10
        sidebar_width = 156 if compact else 176

        for form in self._form_layouts:
            form.setRowWrapPolicy(wrap_policy)
            form.setHorizontalSpacing(h_spacing)
            form.setVerticalSpacing(v_spacing)

        self.category_list.setMinimumWidth(sidebar_width)
        self.category_list.setMaximumWidth(184 if compact else 216)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_responsive_layout()
