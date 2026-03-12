from __future__ import annotations

from typing import Any, Iterable

from PyQt6.QtCore import QEvent, QObject, QPoint, QSize, Qt, pyqtSignal
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


class _ComboOption(QFrame):
    clicked = pyqtSignal(int)
    hovered = pyqtSignal(int)

    ITEM_HEIGHT = 30

    def __init__(self, text: str, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._index = index
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

        self._label = QLabel(text, self)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._label.setProperty("ui_role", "fused_combo_popup_item_label")
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._label)
        self.set_item_height(self.ITEM_HEIGHT)

    def set_item_height(self, height: int) -> None:
        resolved_height = max(self.ITEM_HEIGHT, int(height))
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
        self._row_height = _ComboOption.ITEM_HEIGHT

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("ui_role", "fused_combo_popup")
        self.setProperty("ui_variant", owner.variant())
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._surface = QFrame(self)
        self._surface.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._surface.setProperty("ui_role", "fused_combo_popup_surface")
        self._surface.setProperty("ui_variant", owner.variant())
        outer.addWidget(self._surface)

        surface_layout = QVBoxLayout(self._surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)

        self._scroll = QScrollArea(self._surface)
        self._scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._scroll.setProperty("ui_role", "fused_combo_popup_scroll")
        self._scroll.setProperty("ui_variant", owner.variant())
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        surface_layout.addWidget(self._scroll)

        self._content = QWidget(self._scroll)
        self._content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._content.setProperty("ui_role", "fused_combo_popup_content")
        self._scroll.setWidget(self._content)

        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

    def set_variant(self, variant: str) -> None:
        self.setProperty("ui_variant", variant)
        self._surface.setProperty("ui_variant", variant)
        self._scroll.setProperty("ui_variant", variant)
        _repolish(self)
        _repolish(self._surface)
        _repolish(self._scroll)

    def set_items(self, items: list[tuple[str, Any]], current_index: int) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._rows = []
        for index, (text, _data) in enumerate(items):
            row = _ComboOption(text, index, self._content)
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
        width = self._owner.width()
        visible_rows = max(1, min(len(self._rows), self._owner.maxVisibleItems()))
        viewport_height = visible_rows * self._row_height

        self.setFixedWidth(width)
        self._scroll.setFixedHeight(viewport_height)
        self._surface.setFixedSize(width, viewport_height)
        self.setFixedSize(width, viewport_height)

        origin = self._owner.mapToGlobal(QPoint(0, self._owner.height() - 1))
        self.move(origin)

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
        return max(_ComboOption.ITEM_HEIGHT, self._owner.height())

    def _apply_row_height(self, height: int) -> None:
        resolved_height = max(_ComboOption.ITEM_HEIGHT, int(height))
        self._row_height = resolved_height
        for row in self._rows:
            row.set_item_height(resolved_height)

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

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setProperty("ui_role", "fused_combo")
        self.setProperty("ui_variant", variant)
        self.setProperty("expanded", False)
        self.setProperty("focused", False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self._editable:
            self._line_edit = QLineEdit(self)
            self._line_edit.setProperty("ui_role", "fused_combo_edit")
            self._line_edit.setFrame(False)
            self._line_edit.installEventFilter(self)
            self._line_edit.textChanged.connect(self._on_line_edit_text_changed)
            layout.addWidget(self._line_edit, 1)
            self._label = None
        else:
            self._label = QLabel("", self)
            self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._label.setProperty("ui_role", "fused_combo_label")
            self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(self._label, 1)
            self._line_edit = None

        self._arrow_host = QFrame(self)
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
        base_height = max(32, super().sizeHint().height(), self.minimumHeight())
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
        if key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Down):
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
                if key == Qt.Key.Key_Down:
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
        left_padding = 10
        right_padding = 8
        frame_padding = 12
        return max(88, text_width + left_padding + right_padding + arrow_width + frame_padding)

    def popupWidthHint(self) -> int:
        fm = self._line_edit.fontMetrics() if self._line_edit is not None else self.fontMetrics()
        texts = [str(text) for text, _data in self._items if str(text)]
        text_width = max((fm.horizontalAdvance(text) for text in texts), default=0)
        popup_padding = 24
        return max(self.preferredWidthHint(), text_width + popup_padding)
