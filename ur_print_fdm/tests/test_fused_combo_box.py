from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget


def test_fused_combo_box_supports_selection_and_popup():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox

    host = QWidget()
    layout = QVBoxLayout(host)
    combo = FusedComboBox()
    combo.setFixedWidth(140)
    combo.addItem("生产模式", "production")
    combo.addItem("直连模式", "direct")
    layout.addWidget(combo)

    try:
        host.show()
        app.processEvents()

        assert combo.count() == 2
        assert combo.currentText() == "生产模式"
        assert combo.currentData() == "production"
        assert combo.findText("直连模式") == 1
        assert combo.findData("direct") == 1

        combo.showPopup()
        app.processEvents()

        assert combo.property("expanded") is True
        assert combo._popup.isVisible()
        assert combo._popup.width() >= combo.width()
        assert combo._popup._rows[0].layout().contentsMargins().left() == 0

        combo.setCurrentIndex(1)
        assert combo.currentText() == "直连模式"
        assert combo.currentData() == "direct"

        combo.hidePopup()
        app.processEvents()

        assert combo.property("expanded") is False
    finally:
        host.close()
        host.deleteLater()
        combo.deleteLater()
        app.processEvents()


def test_fused_combo_box_editable_mode_tracks_custom_text():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox

    combo = FusedComboBox(editable=True, variant="toolbar_combo")
    combo.addItems(["192.168.56.101", "192.168.56.102"])

    try:
        assert combo.isEditable() is True
        assert combo.lineEdit() is not None
        assert combo.currentText() == "192.168.56.101"

        combo.setCurrentText("192.168.56.102")
        assert combo.currentIndex() == 1
        assert combo.currentText() == "192.168.56.102"

        combo.setCurrentText("10.0.0.8")
        assert combo.currentIndex() == -1
        assert combo.currentText() == "10.0.0.8"
    finally:
        combo.deleteLater()
        app.processEvents()


def test_fused_combo_box_editable_toolbar_popup_text_column_stays_aligned():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui import theme
    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox

    app.setStyleSheet(theme.get_dark_theme())

    host = QWidget()
    layout = QVBoxLayout(host)
    combo = FusedComboBox(editable=True, variant="toolbar_combo")
    combo.setFixedWidth(140)
    combo.setControlHeight(32)
    combo.setPopupRowHeight(32)
    combo.addItems(["192.168.1.106", "192.168.56.101"])
    combo.setCurrentText("192.168.56.101")
    layout.addWidget(combo)

    try:
        host.show()
        app.processEvents()

        combo.showPopup()
        app.processEvents()

        host_text_x = combo.lineEdit().mapToGlobal(combo.lineEdit().contentsRect().topLeft()).x()
        popup_label = combo._popup._rows[0]._label
        popup_text_x = popup_label.mapToGlobal(popup_label.contentsRect().topLeft()).x()

        assert abs(host_text_x - popup_text_x) <= 1
    finally:
        combo.hidePopup()
        host.close()
        host.deleteLater()
        combo.deleteLater()
        app.processEvents()


def test_fused_combo_box_prefers_longest_option_for_width_hint():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox

    combo = FusedComboBox()
    combo.addItems(["真实机械臂", "虚拟机械臂 (URSim)"])

    try:
        assert combo.preferredWidthHint() > 160
        assert combo.popupWidthHint() >= combo.preferredWidthHint()
        assert combo.sizeHint().width() == combo.preferredWidthHint()
    finally:
        combo.deleteLater()
        app.processEvents()


def test_fused_combo_box_popup_stays_flush_with_fixed_width_host():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox

    host = QWidget()
    layout = QVBoxLayout(host)
    combo = FusedComboBox(editable=True, variant="toolbar_combo")
    combo.setFixedWidth(160)
    combo.addItems(["192.168.137.120", "192.168.137.100"])
    layout.addWidget(combo)

    try:
        host.show()
        app.processEvents()

        combo.showPopup()
        app.processEvents()

        owner_x = combo.mapToGlobal(combo.rect().topLeft()).x()
        assert combo.popupMatchesOwnerWidth() is True
        assert combo._popup.width() == combo.width()
        assert combo._popup.x() == owner_x
    finally:
        combo.hidePopup()
        host.close()
        host.deleteLater()
        combo.deleteLater()
        app.processEvents()


def test_fused_combo_box_popup_can_expand_for_long_content():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox

    host = QWidget()
    layout = QVBoxLayout(host)
    combo = FusedComboBox()
    combo.setFixedWidth(160)
    combo.addItems(["短", "这是一个需要更宽弹层才能完整展示的选项文本"])
    layout.addWidget(combo)

    try:
        host.show()
        app.processEvents()

        combo.showPopup()
        app.processEvents()

        assert combo._popup.width() > combo.width()
        owner_x = combo.mapToGlobal(combo.rect().topLeft()).x()
        assert combo._popup.x() <= owner_x
        assert combo._popup.x() + combo._popup.width() >= owner_x + combo.width()
    finally:
        combo.hidePopup()
        host.close()
        host.deleteLater()
        combo.deleteLater()
        app.processEvents()


def test_fused_combo_box_popup_rows_keep_uniform_size():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox, _ComboOption

    host = QWidget()
    layout = QVBoxLayout(host)
    combo = FusedComboBox()
    combo.setFixedWidth(180)
    combo.addItems(["短", "中等长度", "这是一个更长一些的选项"])
    layout.addWidget(combo)

    try:
        host.show()
        app.processEvents()

        combo.showPopup()
        app.processEvents()

        rows = combo._popup._rows
        assert len(rows) == 3
        expected_height = max(_ComboOption.DEFAULT_ITEM_HEIGHT, combo.height())

        heights = {row.height() for row in rows}
        widths = {row.width() for row in rows}
        label_heights = {row._label.height() for row in rows}
        label_widths = {row._label.width() for row in rows}

        assert heights == {expected_height}
        assert len(widths) == 1
        assert label_heights == {expected_height}
        assert len(label_widths) == 1
    finally:
        combo.hidePopup()
        host.close()
        host.deleteLater()
        combo.deleteLater()
        app.processEvents()


def test_fused_combo_box_popup_rows_follow_owner_height():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox

    host = QWidget()
    layout = QVBoxLayout(host)
    combo = FusedComboBox()
    combo.setFixedWidth(180)
    combo.setFixedHeight(36)
    combo.addItems(["虚拟机械臂 (URSim)", "真实机械臂"])
    layout.addWidget(combo)

    try:
        host.show()
        app.processEvents()

        combo.showPopup()
        app.processEvents()

        rows = combo._popup._rows
        assert rows
        assert {row.height() for row in rows} == {combo.height()}
        assert {row._label.height() for row in rows} == {combo.height()}
    finally:
        combo.hidePopup()
        host.close()
        host.deleteLater()
        combo.deleteLater()
        app.processEvents()


def test_fused_combo_box_popup_row_height_can_be_configured_independently():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox

    host = QWidget()
    layout = QVBoxLayout(host)
    combo = FusedComboBox()
    combo.setFixedWidth(220)
    combo.setControlHeight(28)
    combo.setPopupRowHeight(40)
    combo.addItems(["生产模式", "直连模式", "维护模式"])
    layout.addWidget(combo)

    try:
        host.show()
        app.processEvents()

        combo.showPopup()
        app.processEvents()

        rows = combo._popup._rows
        assert combo.height() == 28
        assert rows
        assert {row.height() for row in rows} == {40}
        assert {row._label.height() for row in rows} == {40}
    finally:
        combo.hidePopup()
        host.close()
        host.deleteLater()
        combo.deleteLater()
        app.processEvents()


def test_fused_combo_box_popup_maximum_width_can_clamp_expanded_popup():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox

    host = QWidget()
    layout = QVBoxLayout(host)
    combo = FusedComboBox()
    combo.setFixedWidth(160)
    combo.setPopupMaximumWidth(220)
    combo.addItems(["短", "这是一个需要更宽弹层才能完整展示的选项文本"])
    layout.addWidget(combo)

    try:
        host.show()
        app.processEvents()

        combo.showPopup()
        app.processEvents()

        assert combo._popup.width() == 220
        assert combo._popup.width() >= combo.width()
    finally:
        combo.hidePopup()
        host.close()
        host.deleteLater()
        combo.deleteLater()
        app.processEvents()


def test_fused_combo_box_popup_shell_keeps_transparent_corners_and_single_pixel_inset():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui import theme
    from ur_print_fdm.ui.widgets.toolbar_mode_selector import ToolbarModeSelector

    app.setStyleSheet(theme.get_dark_theme())

    host = QWidget()
    host.resize(220, 160)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(20, 20, 20, 20)
    combo = ToolbarModeSelector()
    combo.setFixedWidth(150)
    combo.addItems(["生产模式", "直连模式"])
    layout.addWidget(combo)

    try:
        host.show()
        app.processEvents()

        combo.showPopup()
        app.processEvents()

        popup_image = combo._popup.grab().toImage().convertToFormat(QImage.Format.Format_ARGB32)

        assert combo._popup.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert combo._popup._surface.layout().contentsMargins().left() == 0
        assert combo._popup._surface.layout().contentsMargins().right() == 0
        assert combo._popup._scroll.x() == 1
        assert popup_image.pixelColor(0, popup_image.height() - 1).alpha() == 0
        assert popup_image.pixelColor(popup_image.width() - 1, popup_image.height() - 1).alpha() == 0
    finally:
        combo.hidePopup()
        host.close()
        host.deleteLater()
        combo.deleteLater()
        app.processEvents()
