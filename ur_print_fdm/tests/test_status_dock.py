import copy
import logging
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from ur_print_fdm.config import config_manager
from ur_print_fdm.ui.widgets.collapsible_status_dock import StatusWidget


def _cleanup_window(win):
    win.close()
    win.deleteLater()

    app = QApplication.instance()
    if app is not None:
        app.processEvents()

    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "name", None) == "ur_print_fdm_ui":
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass


def test_status_widget_uses_compact_minimum_width():
    app = QApplication.instance() or QApplication([])

    widget = StatusWidget()
    try:
        assert widget.minimumWidth() == StatusWidget.COMPACT_MINIMUM_WIDTH
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_status_widget_keeps_cards_within_viewport_when_compact():
    app = QApplication.instance() or QApplication([])

    widget = StatusWidget()
    widget.resize(StatusWidget.COMPACT_MINIMUM_WIDTH, 640)
    widget.show()
    app.processEvents()
    try:
        assert widget.panel.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        viewport_width = widget.panel.viewport().width()
        assert viewport_width > 0
        for item in widget.panel._items:
            assert item.sizeHint().width() <= viewport_width
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_main_window_status_dock_can_collapse_and_restore():
    app = QApplication.instance() or QApplication([])
    original = config_manager.snapshot()
    updated = copy.deepcopy(original)
    updated.setdefault("ui", {}).setdefault("status_dock", {})
    updated["ui"]["status_dock"]["collapsed"] = False
    updated["ui"]["status_dock"]["expanded_width"] = 228
    config_manager.apply_dict(updated)

    from ur_print_fdm.ui.main_window import URPrintIDE

    win = URPrintIDE()
    win.show()
    app.processEvents()
    try:
        assert win.dock_status.isVisible() is True
        assert win._status_dock_collapsed is False

        win.collapse_status_dock(save=False)
        app.processEvents()

        assert win._status_dock_collapsed is True
        assert win.dock_status.isVisible() is False
        assert win._status_dock_restore_handle.isVisible() is True

        win.expand_status_dock(save=False)
        app.processEvents()
        app.processEvents()

        assert win._status_dock_collapsed is False
        assert win.dock_status.isVisible() is True
        assert win._status_dock_restore_handle.isVisible() is False
        assert win._status_dock_expanded_width >= StatusWidget.COMPACT_MINIMUM_WIDTH
    finally:
        _cleanup_window(win)
        config_manager.apply_dict(original)


def test_main_window_status_dock_collapses_after_dragging_past_min_width():
    app = QApplication.instance() or QApplication([])
    original = config_manager.snapshot()
    updated = copy.deepcopy(original)
    updated.setdefault("ui", {}).setdefault("status_dock", {})
    updated["ui"]["status_dock"]["collapsed"] = False
    updated["ui"]["status_dock"]["expanded_width"] = 240
    config_manager.apply_dict(updated)

    from ur_print_fdm.ui.main_window import URPrintIDE

    win = URPrintIDE()
    win.show()
    app.processEvents()
    try:
        win._handle_status_dock_resize(StatusWidget.COMPACT_MINIMUM_WIDTH)
        win._status_dock_drag_active = True
        win._status_dock_drag_start_x = 100
        class _Point:
            def __init__(self, x):
                self._x = x
            def x(self):
                return self._x

        with patch.object(win.dock_status, "width", return_value=StatusWidget.COMPACT_MINIMUM_WIDTH):
            win._maybe_collapse_status_dock_from_drag(_Point(140))
            assert win._status_dock_collapsed is False
            win._maybe_collapse_status_dock_from_drag(_Point(140 + win.STATUS_DOCK_COLLAPSE_DRAG_DISTANCE + 1))
        app.processEvents()

        assert win._status_dock_collapsed is True
        assert win.dock_status.isVisible() is False
    finally:
        _cleanup_window(win)
        config_manager.apply_dict(original)
