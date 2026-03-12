from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget


def test_toolbar_mode_selector_keeps_compact_api_and_fused_popup():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.toolbar_mode_selector import ToolbarModeSelector

    host = QWidget()
    layout = QVBoxLayout(host)
    selector = ToolbarModeSelector()
    selector.setProperty("ui_variant", "mode_selector")
    selector.setFixedWidth(108)
    selector.setMinimumHeight(32)
    selector.addItem("生产模式", "production")
    selector.addItem("直连模式", "direct")
    layout.addWidget(selector)

    try:
        host.show()
        app.processEvents()

        assert selector.count() == 2
        assert selector.currentText() == "生产模式"
        assert selector.currentData() == "production"
        assert selector.findData("direct") == 1

        selector.setCurrentIndex(1)
        assert selector.currentText() == "直连模式"
        assert selector.currentData() == "direct"

        selector.showPopup()
        app.processEvents()

        assert selector.property("expanded") is True
        assert selector._popup.isVisible()
        assert selector._popup.width() == selector.width()
        assert len(selector._popup._rows) == 2
        assert selector._popup._rows[-1].property("last") is True

        selector.hidePopup()
        app.processEvents()

        assert selector.property("expanded") is False
    finally:
        host.close()
        host.deleteLater()
        selector.deleteLater()
        app.processEvents()
