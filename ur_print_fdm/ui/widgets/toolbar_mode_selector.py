from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox


class ToolbarModeSelector(FusedComboBox):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, editable=False, variant="mode_selector")
        self.setControlHeight(32)
        self.setPopupRowHeight(32)
