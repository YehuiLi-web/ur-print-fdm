from __future__ import annotations

from typing import Any, Iterable

from PyQt6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ur_print_fdm.ui.resources.icon_manager import IconManager


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class _ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._full_text = ""
        self._elide_mode = Qt.TextElideMode.ElideRight
        self._manual_tooltip: str | None = None
        self.setText(text)

    def fullText(self) -> str:
        return self._full_text

    def setText(self, text: str) -> None:  # type: ignore[override]
        self._full_text = str(text)
        self._refresh_elision()

    def setToolTip(self, text: str) -> None:  # type: ignore[override]
        self._manual_tooltip = str(text) if text else None
        super().setToolTip(text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_elision()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.EnabledChange,
        ):
            self._refresh_elision()

    def _refresh_elision(self) -> None:
        text = self._full_text
        width = self.contentsRect().width()
        if width > 0 and text:
            rendered = self.fontMetrics().elidedText(text, self._elide_mode, width)
        else:
            rendered = text
        super().setText(rendered)
        tooltip = self._manual_tooltip if self._manual_tooltip is not None else (text if rendered != text else "")
        super().setToolTip(tooltip)


class _ComboOption(QFrame):
    clicked = pyqtSignal(int)
    hovered = pyqtSignal(int)

    MIN_ITEM_HEIGHT = 22
    DEFAULT_ITEM_HEIGHT = 30

    def __init__(self, text: str, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._index = index
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("ui_role", "fused_combo_popup_item")
        self.setProperty("selected", False)
        self.setProperty("highlighted", False)
        self.setProperty("first", False)
        self.setProperty("last", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._label = _ElidedLabel(text, self)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._label.setProperty("ui_role", "fused_combo_popup_item_label")
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._label)
        self.set_item_height(self.DEFAULT_ITEM_HEIGHT)

    def set_item_height(self, height: int) -> None:
        resolved_height = max(self.MIN_ITEM_HEIGHT, int(height))
        self.setFixedHeight(resolved_height)
        self._label.setFixedHeight(resolved_height)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        _repolish(self)

    def set_highlighted(self, highlighted: bool) -> None:
        self.setProperty("highlighted", highlighted)
        _repolish(self)

    def set_edge_flags(self, *, first: bool, last: bool) -> None:
        self.setProperty("first", first)
        self.setProperty("last", last)
        _repolish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.clicked.emit(self._index)
            return
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.hovered.emit(self._index)


class _ComboPopup(QWidget):
    indexSelected = pyqtSignal(int)
    popupHidden = pyqtSignal()

    def __init__(self, owner: "FusedComboBox"):
        super().__init__(
            owner,
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self._owner = owner
        self._rows: list[_ComboOption] = []
        self._highlighted_index = -1
        self._row_height = _ComboOption.DEFAULT_ITEM_HEIGHT
        self._popup_side = "below"

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("ui_role", "fused_combo_popup")
        self.setProperty("ui_variant", owner.variant())
        self.setProperty("popup_side", self._popup_side)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._surface = QFrame(self)
        self._surface.setFrameShape(QFrame.Shape.NoFrame)
        self._surface.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._surface.setProperty("ui_role", "fused_combo_popup_surface")
        self._surface.setProperty("ui_variant", owner.variant())
        self._surface.setProperty("popup_side", self._popup_side)
        outer.addWidget(self._surface)

        self._surface_layout = QVBoxLayout(self._surface)
        self._surface_layout.setContentsMargins(0, 0, 0, 0)
        self._surface_layout.setSpacing(0)

        self._scroll = QScrollArea(self._surface)
        self._scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._scroll.setProperty("ui_role", "fused_combo_popup_scroll")
        self._scroll.setProperty("ui_variant", owner.variant())
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._surface_layout.addWidget(self._scroll)
        self._viewport = self._scroll.viewport()
        self._viewport.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._viewport.setProperty("ui_role", "fused_combo_popup_viewport")
        self._viewport.setProperty("ui_variant", owner.variant())

        self._content = QWidget(self._scroll)
        self._content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._content.setProperty("ui_role", "fused_combo_popup_content")
        self._content.setProperty("ui_variant", owner.variant())
        self._scroll.setWidget(self._content)

        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

    def set_variant(self, variant: str) -> None:
        self.setProperty("ui_variant", variant)
        self._surface.setProperty("ui_variant", variant)
        self._scroll.setProperty("ui_variant", variant)
        self._viewport.setProperty("ui_variant", variant)
        self._content.setProperty("ui_variant", variant)
        _repolish(self)
        _repolish(self._surface)
        _repolish(self._scroll)
        _repolish(self._viewport)
        _repolish(self._content)

    def set_items(self, items: list[tuple[str, Any]], current_index: int) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._rows = []
        for index, (text, _data) in enumerate(items):
            row = _ComboOption(text, index, self._content)
            row.setProperty("popup_side", self._popup_side)
            row.clicked.connect(self._on_row_clicked)
            row.hovered.connect(self._set_highlighted_index)
            row.set_edge_flags(first=index == 0, last=index == len(items) - 1)
            self._content_layout.addWidget(row)
            self._rows.append(row)

        self.set_current_index(current_index)

    def set_current_index(self, index: int) -> None:
        valid_index = index if 0 <= index < len(self._rows) else -1
        for row_index, row in enumerate(self._rows):
            row.set_selected(row_index == valid_index)
        self._set_highlighted_index(valid_index)

    def show_for_owner(self) -> None:
        if not self._rows:
            return
        self._apply_row_height(self._resolved_row_height())
        self._sync_geometry()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.PopupFocusReason)
        self._scroll_to_highlighted()

    def _on_row_clicked(self, index: int) -> None:
        self.indexSelected.emit(index)
        self.hide()

    def _set_highlighted_index(self, index: int) -> None:
        self._highlighted_index = index
        for row_index, row in enumerate(self._rows):
            row.set_highlighted(row_index == index)

    def _move_highlight(self, step: int) -> None:
        if not self._rows:
            return
        if self._highlighted_index < 0:
            next_index = 0
        else:
            next_index = (self._highlighted_index + step) % len(self._rows)
        self._set_highlighted_index(next_index)
        self._scroll_to_highlighted()

    def _sync_geometry(self) -> None:
        geometry, side = self._resolved_geometry()
        width = geometry.width()
        outer_height = geometry.height()
        left_inset, top_inset, right_inset, bottom_inset = self._surface_insets_for_side(side)
        content_width = max(1, width - left_inset - right_inset)
        content_height = max(1, outer_height - top_inset - bottom_inset)

        self._set_popup_side(side)
        self._owner._set_popup_side(side)

        self._scroll.setFixedSize(content_width, content_height)
        self._surface.setFixedSize(width, outer_height)
        self.setFixedSize(width, outer_height)
        self.move(geometry.topLeft())

    def _scroll_to_highlighted(self) -> None:
        if self._highlighted_index < 0:
            return
        scroll_bar = self._scroll.verticalScrollBar()
        item_top = self._highlighted_index * self._row_height
        item_bottom = item_top + self._row_height
        view_top = scroll_bar.value()
        view_bottom = view_top + self._scroll.viewport().height()
        if item_top < view_top:
            scroll_bar.setValue(item_top)
        elif item_bottom > view_bottom:
            scroll_bar.setValue(item_bottom - self._scroll.viewport().height())

    def _resolved_row_height(self) -> int:
        explicit_height = self._owner.popupRowHeight()
        if explicit_height > 0:
            return max(_ComboOption.MIN_ITEM_HEIGHT, explicit_height)
        return max(_ComboOption.DEFAULT_ITEM_HEIGHT, self._owner.controlHeightHint())

    def _apply_row_height(self, height: int) -> None:
        resolved_height = max(_ComboOption.MIN_ITEM_HEIGHT, int(height))
        self._row_height = resolved_height
        for row in self._rows:
            row.set_item_height(resolved_height)

    def _set_popup_side(self, side: str) -> None:
        resolved_side = "above" if side == "above" else "below"
        if resolved_side == self._popup_side:
            return
        self._popup_side = resolved_side
        self.setProperty("popup_side", resolved_side)
        self._surface.setProperty("popup_side", resolved_side)
        for row in self._rows:
            row.setProperty("popup_side", resolved_side)
            _repolish(row)
        _repolish(self)
        _repolish(self._surface)

    def _surface_insets_for_side(self, side: str) -> tuple[int, int, int, int]:
        if side == "above":
            return (1, 1, 1, 0)
        return (1, 0, 1, 1)

    def _available_geometry(self) -> QRect:
        owner_center = self._owner.mapToGlobal(self._owner.rect().center())
        screen = QGuiApplication.screenAt(owner_center) or self._owner.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            top_left = self._owner.mapToGlobal(QPoint(0, 0))
            return QRect(top_left.x() - 640, top_left.y() - 360, 1280, 720)
        return screen.availableGeometry()

    def _resolved_geometry(self) -> tuple[QRect, str]:
        available = self._available_geometry()
        owner_top_left = self._owner.mapToGlobal(QPoint(0, 0))
        owner_rect = QRect(owner_top_left, self._owner.size())

        if self._owner.popupMatchesOwnerWidth():
            popup_width = self._owner.width()
        else:
            popup_width = max(self._owner.width(), self._owner.popupWidthHint())
            popup_maximum_width = self._owner.popupMaximumWidth()
            if popup_maximum_width > 0:
                popup_width = min(popup_width, popup_maximum_width)
        popup_width = min(max(1, popup_width), max(1, available.width()))

        max_x = available.right() - popup_width + 1
        x = min(max(owner_rect.left(), available.left()), max_x)

        desired_rows = max(1, min(len(self._rows), self._owner.maxVisibleItems()))
        desired_height = desired_rows * self._row_height

        below_top = owner_rect.bottom()
        below_space = max(1, available.bottom() - below_top + 1)
        above_space = max(1, owner_rect.top() - available.top() + 1)

        _below_left, below_top_margin, _below_right, below_bottom_margin = self._surface_insets_for_side("below")
        _above_left, above_top_margin, _above_right, above_bottom_margin = self._surface_insets_for_side("above")
        below_content_space = max(1, below_space - below_top_margin - below_bottom_margin)
        above_content_space = max(1, above_space - above_top_margin - above_bottom_margin)

        below_rows_fit = max(1, below_content_space // self._row_height)
        above_rows_fit = max(1, above_content_space // self._row_height)

        open_below = below_space >= desired_height or below_rows_fit >= above_rows_fit
        visible_rows = min(desired_rows, below_rows_fit if open_below else above_rows_fit)
        content_height = max(self._row_height, visible_rows * self._row_height)
        _left_margin, top_margin, _right_margin, bottom_margin = self._surface_insets_for_side(
            "below" if open_below else "above"
        )
        outer_height = content_height + top_margin + bottom_margin

        if open_below:
            y = below_top
            side = "below"
        else:
            y = owner_rect.top() - outer_height + 1
            side = "above"

        return QRect(x, y, popup_width, outer_height), side

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Tab):
            self._move_highlight(1)
            event.accept()
            return
        if key == Qt.Key.Key_Up:
            self._move_highlight(-1)
            event.accept()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if 0 <= self._highlighted_index < len(self._rows):
                self.indexSelected.emit(self._highlighted_index)
            self.hide()
            event.accept()
            return
        if key == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.popupHidden.emit()


class FusedComboBox(QFrame):
    currentIndexChanged = pyqtSignal(int)
    currentTextChanged = pyqtSignal(str)
    editTextChanged = pyqtSignal(str)
    _EDITABLE_TEXT_LEFT_INSET = 7
    _EDITABLE_TEXT_RIGHT_INSET = 8

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        editable: bool = False,
        variant: str = "form_combo",
    ):
        super().__init__(parent)
        self._items: list[tuple[str, Any]] = []
        self._editable = editable
        self._variant = variant
        self._current_index = -1
        self._max_visible_items = 8
        self._icon_manager = IconManager()
        self._updating_text = False
        self._popup_row_height = 0
        self._popup_maximum_width = 0
        self._popup_side = "below"
        self._popup_match_owner_width = bool(editable and variant == "toolbar_combo")

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setProperty("ui_role", "fused_combo")
        self.setProperty("ui_variant", variant)
        self.setProperty("expanded", False)
        self.setProperty("focused", False)
        self.setProperty("popup_side", self._popup_side)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self._editable:
            self._edit_host = QWidget(self)
            self._edit_host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self._edit_host.setProperty("ui_role", "fused_combo_edit_host")
            self._edit_host.setContentsMargins(0, 0, 0, 0)
            edit_layout = QHBoxLayout(self._edit_host)
            edit_layout.setContentsMargins(
                self._EDITABLE_TEXT_LEFT_INSET,
                0,
                self._EDITABLE_TEXT_RIGHT_INSET,
                0,
            )
            edit_layout.setSpacing(0)

            self._line_edit = QLineEdit(self)
            self._line_edit.setProperty("ui_role", "fused_combo_edit")
            self._line_edit.setFrame(False)
            self._line_edit.setTextMargins(0, 0, 0, 0)
            self._line_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._line_edit.installEventFilter(self)
            self._line_edit.textChanged.connect(self._on_line_edit_text_changed)
            edit_layout.addWidget(self._line_edit, 1)
            layout.addWidget(self._edit_host, 1)
            self._label = None
        else:
            self._edit_host = None
            self._label = _ElidedLabel("", self)
            self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._label.setProperty("ui_role", "fused_combo_label")
            self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(self._label, 1)
            self._line_edit = None

        self._arrow_host = QFrame(self)
        self._arrow_host.setFrameShape(QFrame.Shape.NoFrame)
        self._arrow_host.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._arrow_host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._arrow_host.setProperty("ui_role", "fused_combo_arrow_host")
        self._arrow_host.setFixedWidth(24 if variant == "mode_selector" else 22)
        layout.addWidget(self._arrow_host, 0)

        arrow_layout = QHBoxLayout(self._arrow_host)
        arrow_layout.setContentsMargins(0, 0, 0, 0)
        arrow_layout.setSpacing(0)

        self._arrow_icon = QLabel(self._arrow_host)
        self._arrow_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._arrow_icon.setProperty("ui_role", "fused_combo_arrow")
        self._arrow_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_layout.addWidget(self._arrow_icon)
        self._update_arrow_icon()

        self._popup = _ComboPopup(self)
        self._popup.indexSelected.connect(self.setCurrentIndex)
        self._popup.popupHidden.connect(self._on_popup_hidden)

    def variant(self) -> str:
        return self._variant

    def isEditable(self) -> bool:
        return self._editable

    def lineEdit(self) -> QLineEdit | None:
        return self._line_edit

    def setPlaceholderText(self, text: str) -> None:
        if self._line_edit is not None:
            self._line_edit.setPlaceholderText(text)

    def setMaxVisibleItems(self, count: int) -> None:
        self._max_visible_items = max(1, int(count))

    def maxVisibleItems(self) -> int:
        return self._max_visible_items

    def setControlHeight(self, height: int) -> None:
        resolved_height = max(_ComboOption.MIN_ITEM_HEIGHT, int(height))
        self.setFixedHeight(resolved_height)
        self.updateGeometry()
        if self._popup.isVisible():
            self._popup._apply_row_height(self._popup._resolved_row_height())
            self._popup._sync_geometry()

    def controlHeightHint(self) -> int:
        candidates = [super().sizeHint().height(), self.minimumHeight(), self.height()]
        positive_values = [value for value in candidates if value > 0]
        return max(positive_values) if positive_values else _ComboOption.MIN_ITEM_HEIGHT

    def setPopupRowHeight(self, height: int) -> None:
        self._popup_row_height = max(_ComboOption.MIN_ITEM_HEIGHT, int(height))
        if self._popup.isVisible():
            self._popup._apply_row_height(self._popup_row_height)
            self._popup._sync_geometry()

    def popupRowHeight(self) -> int:
        return self._popup_row_height

    def setPopupMaximumWidth(self, width: int) -> None:
        self._popup_maximum_width = max(0, int(width))
        if self._popup.isVisible():
            self._popup._sync_geometry()

    def popupMaximumWidth(self) -> int:
        return self._popup_maximum_width

    def setPopupMatchesOwnerWidth(self, matches: bool) -> None:
        self._popup_match_owner_width = bool(matches)
        if self._popup.isVisible():
            self._popup._sync_geometry()

    def popupMatchesOwnerWidth(self) -> bool:
        return self._popup_match_owner_width

    def clear(self) -> None:
        self._items.clear()
        self._current_index = -1
        self._popup.set_items([], -1)
        if self._line_edit is not None:
            self._set_line_edit_text("")
        elif self._label is not None:
            self._label.setText("")
        self.updateGeometry()

    def addItem(self, text: str, user_data: Any = None) -> None:
        self._items.append((text, user_data))
        self._popup.set_items(self._items, self._current_index)
        if self._current_index < 0:
            self._set_current_index(0, emit_signals=False)
        self.updateGeometry()

    def addItems(self, texts: Iterable[str]) -> None:
        for text in texts:
            self.addItem(str(text))

    def count(self) -> int:
        return len(self._items)

    def itemText(self, index: int) -> str:
        if 0 <= index < len(self._items):
            return self._items[index][0]
        return ""

    def currentIndex(self) -> int:
        return self._current_index

    def currentText(self) -> str:
        if self._line_edit is not None:
            return self._line_edit.text()
        return self.itemText(self._current_index)

    def currentData(self) -> Any:
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][1]
        return None

    def findText(self, value: str) -> int:
        for index, (text, _data) in enumerate(self._items):
            if text == value:
                return index
        return -1

    def findData(self, value: Any) -> int:
        for index, (_text, data) in enumerate(self._items):
            if data == value:
                return index
        return -1

    def setCurrentIndex(self, index: int) -> None:
        self._set_current_index(index, emit_signals=True)

    def setCurrentText(self, text: str) -> None:
        match_index = self.findText(text)
        if match_index >= 0:
            self._set_current_index(match_index, emit_signals=True)
            return
        if not self._editable:
            return

        previous_text = self.currentText()
        previous_index = self._current_index
        self._current_index = -1
        self._popup.set_current_index(-1)
        self._set_line_edit_text(text)

        if previous_index != -1:
            self.currentIndexChanged.emit(-1)
        if previous_text != text:
            self.currentTextChanged.emit(text)

    def showPopup(self) -> None:
        if not self.isEnabled() or not self._items:
            return
        self._popup.set_items(self._items, self._current_index)
        self._set_expanded(True)
        self._popup.show_for_owner()

    def sizeHint(self) -> QSize:
        base_height = max(super().sizeHint().height(), self.controlHeightHint())
        return QSize(self.preferredWidthHint(), base_height)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def hidePopup(self) -> None:
        self._popup.hide()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            if self._editable:
                arrow_rect = self._arrow_host.geometry()
                if arrow_rect.contains(event.position().toPoint()):
                    if self._popup.isVisible():
                        self.hidePopup()
                    else:
                        self.showPopup()
                    event.accept()
                    return
            else:
                if self._popup.isVisible():
                    self.hidePopup()
                else:
                    self.showPopup()
                event.accept()
                return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Down, Qt.Key.Key_F4):
            self.showPopup()
            event.accept()
            return
        if key == Qt.Key.Key_Escape and self._popup.isVisible():
            self.hidePopup()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self._set_focused(True)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if self._line_edit is None:
            self._set_focused(False)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._popup.isVisible():
            self._popup._sync_geometry()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if self._popup.isVisible():
            self._popup._sync_geometry()

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        if not enabled and self._popup.isVisible():
            self.hidePopup()

    def setToolTip(self, text: str) -> None:
        super().setToolTip(text)
        if self._label is not None:
            self._label.setToolTip(text)
        if self._line_edit is not None:
            self._line_edit.setToolTip(text)
        self._arrow_host.setToolTip(text)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange:
            self._update_arrow_icon()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[name-defined]
        if watched is self._line_edit:
            if event.type() == QEvent.Type.FocusIn:
                self._set_focused(True)
            elif event.type() == QEvent.Type.FocusOut and not self._popup.isVisible():
                self._set_focused(False)
            elif event.type() == QEvent.Type.KeyPress:
                key = event.key()
                if key in (Qt.Key.Key_Down, Qt.Key.Key_F4):
                    self.showPopup()
                    event.accept()
                    return True
                if key == Qt.Key.Key_Escape and self._popup.isVisible():
                    self.hidePopup()
                    event.accept()
                    return True
        return super().eventFilter(watched, event)

    def _set_current_index(self, index: int, *, emit_signals: bool) -> None:
        if not 0 <= index < len(self._items):
            return

        new_text = self._items[index][0]
        previous_text = self.currentText()
        previous_index = self._current_index
        self._current_index = index
        self._popup.set_current_index(index)

        if self._line_edit is not None:
            self._set_line_edit_text(new_text)
        elif self._label is not None:
            self._label.setText(new_text)

        if emit_signals and previous_index != index:
            self.currentIndexChanged.emit(index)
        if emit_signals and previous_text != new_text:
            self.currentTextChanged.emit(new_text)
        self.updateGeometry()

    def _set_line_edit_text(self, text: str) -> None:
        if self._line_edit is None:
            return
        self._updating_text = True
        self._line_edit.setText(text)
        self._updating_text = False

    def _set_expanded(self, expanded: bool) -> None:
        self.setProperty("expanded", expanded)
        _repolish(self)
        _repolish(self._arrow_host)

    def _set_popup_side(self, side: str) -> None:
        resolved_side = "above" if side == "above" else "below"
        if resolved_side == self._popup_side:
            return
        self._popup_side = resolved_side
        self.setProperty("popup_side", resolved_side)
        _repolish(self)
        _repolish(self._arrow_host)

    def _set_focused(self, focused: bool) -> None:
        self.setProperty("focused", focused)
        _repolish(self)

    def _on_popup_hidden(self) -> None:
        self._set_expanded(False)
        if self._line_edit is not None and self._line_edit.hasFocus():
            self._set_focused(True)
        elif not self.hasFocus():
            self._set_focused(False)

    def _on_line_edit_text_changed(self, text: str) -> None:
        if self._updating_text:
            return

        previous_index = self._current_index
        self._current_index = self.findText(text)
        self._popup.set_current_index(self._current_index)

        if previous_index != self._current_index:
            self.currentIndexChanged.emit(self._current_index)
        self.currentTextChanged.emit(text)
        self.editTextChanged.emit(text)
        self.updateGeometry()

    def _update_arrow_icon(self) -> None:
        icon = self._icon_manager.get_svg_icon("tree_expand", (10, 10))
        self._arrow_icon.setPixmap(icon.pixmap(10, 10))

    def preferredWidthHint(self) -> int:
        fm = self._line_edit.fontMetrics() if self._line_edit is not None else self.fontMetrics()
        texts = [str(text) for text, _data in self._items if str(text)]
        current_text = self.currentText().strip()
        if current_text:
            texts.append(current_text)
        if self._line_edit is not None:
            placeholder = self._line_edit.placeholderText().strip()
            if placeholder:
                texts.append(placeholder)

        text_width = max((fm.horizontalAdvance(text) for text in texts), default=0)
        arrow_width = self._arrow_host.width() or self._arrow_host.minimumWidth() or 22
        left_padding = self._EDITABLE_TEXT_LEFT_INSET if self._line_edit is not None else 10
        right_padding = 8
        frame_padding = 12
        return max(88, text_width + left_padding + right_padding + arrow_width + frame_padding)

    def popupWidthHint(self) -> int:
        fm = self._line_edit.fontMetrics() if self._line_edit is not None else self.fontMetrics()
        texts = [str(text) for text, _data in self._items if str(text)]
        text_width = max((fm.horizontalAdvance(text) for text in texts), default=0)
        popup_padding = 32
        return max(self.preferredWidthHint(), text_width + popup_padding)
