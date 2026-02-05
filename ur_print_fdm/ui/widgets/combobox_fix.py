"""
ComboBox 修复工具函数
用于修复 PyQt6 + Fusion + QSS 环境下的弹出框覆盖问题
"""
from PyQt6.QtWidgets import QComboBox, QListView, QStyledItemDelegate
from PyQt6.QtCore import Qt, QSize, QMargins


class FixedItemDelegate(QStyledItemDelegate):
    """固定高度的项目代理，确保每个项目与 ComboBox 本身高度一致"""

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        # 设置为 22px，与 ComboBox 的 min-height 一致
        size.setHeight(22)
        return size


def fix_combobox_popup(combo: QComboBox, allow_edit: bool = False) -> None:
    """
    修复 ComboBox 弹出框覆盖问题

    关键发现：在 PyQt6 + Fusion 样式下，可编辑的 ComboBox 弹出行为正常，
    而不可编辑的 ComboBox 会出现覆盖问题。

    解决方案：将不可编辑的 ComboBox 设置为可编辑，但禁止插入新项，
    并设置为只读，这样既修复了弹出问题，又保持了只读行为。

    Args:
        combo: 要修复的 QComboBox 实例
        allow_edit: 是否真正允许编辑（默认 False，只是为了修复弹出问题）
    """
    # 检查是否有图标（检查第一个项目）
    has_icon = False
    if combo.count() > 0:
        has_icon = not combo.itemIcon(0).isNull()

    if not allow_edit:
        # 如果不需要真正的编辑功能，设置为可编辑但禁止插入
        # 这样可以修复弹出框问题，同时保持下拉框的只读行为
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        # 禁用编辑功能：让用户无法修改文本
        line_edit = combo.lineEdit()
        if line_edit:
            line_edit.setReadOnly(True)
            # 设置光标为箭头，表示不可编辑
            line_edit.setCursor(Qt.CursorShape.ArrowCursor)
            # 禁用文本选择，使其看起来更像只读下拉框
            line_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)

            # 移除 LineEdit 的默认样式，使其与 ComboBox 对齐
            # 设置透明背景和无边框，让它看起来像不可编辑的 ComboBox
            line_edit.setStyleSheet("""
                QLineEdit {
                    background: transparent;
                    border: none;
                    padding: 0px;
                    margin: 0px;
                }
            """)

            # 如果有图标，调整文本边距以避免遮挡
            if has_icon:
                # 为图标留出 24px 的空间（16px 图标 + 8px 间距）
                line_edit.setTextMargins(24, 0, 0, 0)
            else:
                # 没有图标时，设置为 0，让文字与 ComboBox 的 padding 对齐
                line_edit.setTextMargins(0, 0, 0, 0)

    # 创建自定义视图
    view = QListView()

    # 设置窗口标志
    view.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)

    # 设置项目代理以确保正确的高度
    view.setItemDelegate(FixedItemDelegate(view))

    # 应用视图
    combo.setView(view)
