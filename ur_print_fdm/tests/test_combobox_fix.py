from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QComboBox, QFrame


def test_fix_combobox_popup_aligns_readonly_text_and_popup_items():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.combobox_fix import FusedPopupListView, FixedItemDelegate, fix_combobox_popup

    combo = QComboBox()
    combo.addItems(["生产模式", "直连模式"])
    combo.setProperty("ui_variant", "mode_selector")
    try:
        fix_combobox_popup(combo)

        assert combo.isEditable() is True
        assert combo.lineEdit() is not None
        assert combo.lineEdit().isReadOnly() is True
        assert combo.lineEdit().alignment() == (
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        assert combo.lineEdit().textMargins().left() == 0
        assert combo.lineEdit().textMargins().right() == 0
        assert combo.lineEdit().cursorPosition() == 0
        assert isinstance(combo.view().itemDelegate(), FixedItemDelegate)
        assert isinstance(combo.view(), FusedPopupListView)
        assert combo.view().frameShape() == QFrame.Shape.NoFrame
        assert combo.view().testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    finally:
        combo.deleteLater()
        app.processEvents()
