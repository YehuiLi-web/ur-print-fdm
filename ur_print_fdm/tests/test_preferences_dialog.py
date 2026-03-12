import copy

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit, QListWidget, QScrollArea, QSizePolicy

from ur_print_fdm.config import config_manager
from ur_print_fdm.ui.widgets.preferences_dialog import (
    PreferencesDialog,
    _NoWheelDoubleSpinBox,
    _NoWheelSpinBox,
)
from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox


def test_preferences_dialog_can_rebuild_categories():
    app = QApplication.instance() or QApplication([])

    dlg = PreferencesDialog()
    dlg._build_categories()
    dlg._rebuild_from_working_config()

    assert dlg.pages.count() > 0
    assert isinstance(dlg.pages.widget(0), QScrollArea)


def test_preferences_dialog_only_exposes_dark_theme():
    app = QApplication.instance() or QApplication([])
    original = config_manager.snapshot()
    legacy = copy.deepcopy(original)
    legacy.setdefault("ui", {})["dark_theme"] = False
    config_manager.apply_dict(legacy)

    try:
        dlg = PreferencesDialog()
        ui_index = next(i for i, cat in enumerate(dlg._categories) if cat.id == "ui")
        ui_page = dlg.pages.widget(ui_index)
        cmb_theme = ui_page.findChild(FusedComboBox)

        assert dlg._get("ui.dark_theme") is True
        assert cmb_theme is not None
        assert cmb_theme.count() == 1
        assert cmb_theme.itemText(0) == "暗色（默认）"
        assert not cmb_theme.isEnabled()
    finally:
        config_manager.apply_dict(original)


def test_preferences_dialog_switches_to_compact_form_layout_when_narrow():
    app = QApplication.instance() or QApplication([])

    dlg = PreferencesDialog()
    dlg.resize(860, 640)
    dlg._refresh_responsive_layout(force=True)

    assert dlg._compact_mode is True
    assert dlg.category_list.maximumWidth() == 184
    assert all(
        form.rowWrapPolicy() == form.RowWrapPolicy.WrapAllRows
        for form in dlg._form_layouts
    )


def test_preferences_dialog_uses_distinct_nav_and_content_list_roles():
    app = QApplication.instance() or QApplication([])

    dlg = PreferencesDialog()
    robot_index = next(i for i, cat in enumerate(dlg._categories) if cat.id == "robot")
    robot_page = dlg.pages.widget(robot_index)
    lists = robot_page.findChildren(QListWidget)

    assert dlg.category_list.property("ui_role") == "pref_nav"
    assert any(widget.property("ui_role") == "pref_list" for widget in lists)


def test_preferences_dialog_uses_no_wheel_numeric_editors():
    app = QApplication.instance() or QApplication([])

    dlg = PreferencesDialog()
    printing_index = next(i for i, cat in enumerate(dlg._categories) if cat.id == "printing")
    printing_page = dlg.pages.widget(printing_index)

    assert printing_page.findChildren(_NoWheelSpinBox)
    assert printing_page.findChildren(_NoWheelDoubleSpinBox)


def test_preferences_dialog_fixed_inline_fields_expand_and_stay_left_aligned():
    app = QApplication.instance() or QApplication([])

    dlg = PreferencesDialog()
    _, card_layout = dlg._make_card("连接目标")
    field = dlg._make_inline_field("当前目标", FusedComboBox(), label_width=72, max_width=220)
    block = dlg._make_field_block("当前目标", FusedComboBox(), max_width=220)
    layout = field.layout()
    block_layout = block.layout()
    label = field.findChild(QLabel)

    assert card_layout.spacing() == 8
    assert field.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
    assert layout is not None
    assert block_layout is not None
    assert field.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    assert block.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    assert layout.count() == 3
    assert layout.spacing() == 3
    assert block_layout.spacing() == 3
    assert layout.itemAt(2).spacerItem() is not None
    assert label is not None
    assert label.alignment() == (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    assert 'QWidget[ui_role="pref_inline_field"]' in dlg.styleSheet()


def test_preferences_dialog_scroll_pages_anchor_to_top_left():
    app = QApplication.instance() or QApplication([])

    dlg = PreferencesDialog()
    scroll = dlg.pages.widget(0)

    assert isinstance(scroll, QScrollArea)
    assert scroll.alignment() == (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)


def test_preferences_dialog_transfer_card_uses_shared_label_column():
    app = QApplication.instance() or QApplication([])

    dlg = PreferencesDialog()
    transfer_index = next(i for i, cat in enumerate(dlg._categories) if cat.id == "transfer")
    transfer_page = dlg.pages.widget(transfer_index)
    sftp_labels = []
    loader_labels = []
    remote_loader_edit = transfer_page.findChild(QLineEdit, "preferencesRemoteLoaderName")

    for label in transfer_page.findChildren(QLabel):
        if label.property("ui_role") != "pref_inline_label":
            continue
        if label.text() in {"端口：", "用户名：", "密码：", "远端目录："}:
            sftp_labels.append(label)
        if label.text() in {"loader.urp 路径：", "remote_loader 文件名："}:
            loader_labels.append(label)

    assert len(sftp_labels) == 4
    assert len({label.width() for label in sftp_labels}) == 1
    assert len(loader_labels) == 2
    assert len({label.width() for label in loader_labels}) == 1
    assert all(label.width() >= label.sizeHint().width() for label in loader_labels)
    assert remote_loader_edit is not None
    assert remote_loader_edit.cursorPosition() == 0
    assert remote_loader_edit.alignment() == (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


def test_preferences_dialog_password_field_can_toggle_visibility():
    app = QApplication.instance() or QApplication([])

    dlg = PreferencesDialog()
    transfer_index = next(i for i, cat in enumerate(dlg._categories) if cat.id == "transfer")
    transfer_page = dlg.pages.widget(transfer_index)
    password_edit = transfer_page.findChild(QLineEdit, "preferencesSftpPassword")

    assert password_edit is not None
    assert password_edit.echoMode() == QLineEdit.EchoMode.Password
    assert len(password_edit.actions()) == 1

    password_edit.actions()[0].trigger()
    assert password_edit.echoMode() == QLineEdit.EchoMode.Normal

    password_edit.actions()[0].trigger()
    assert password_edit.echoMode() == QLineEdit.EchoMode.Password
