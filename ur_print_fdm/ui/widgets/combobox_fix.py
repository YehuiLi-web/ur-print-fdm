"""
ComboBox 修复工具函数
用于修复 PyQt6 + Fusion + QSS 环境下的弹出框覆盖问题
"""
from PyQt6.QtWidgets import QComboBox, QListView, QStyledItemDelegate, QFrame
from PyQt6.QtCore import Qt
from ur_print_fdm.ui import theme as ui_theme


class FixedItemDelegate(QStyledItemDelegate):
    """固定高度的项目代理，确保每个项目与 ComboBox 本身高度一致"""

    ITEM_HEIGHT = 26

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        # 与工具栏/设置页中的紧凑型 ComboBox 高度保持一致。
        size.setHeight(self.ITEM_HEIGHT)
        return size


class FusedPopupListView(QListView):
    """Popup list view aligned flush with its owning combo box."""

    def __init__(self, owner_combo: QComboBox):
        super().__init__()
        self._owner_combo = owner_combo

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_geometry()

    def _sync_geometry(self) -> None:
        combo = self._owner_combo
        popup = self.window()
        if combo is None or popup is None:
            return

        t = ui_theme.current_tokens()
        radius_lg = t.get("radius_lg", "6px")

        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        popup.setContentsMargins(0, 0, 0, 0)
        if isinstance(popup, QFrame):
            popup.setFrameShape(QFrame.Shape.NoFrame)
        popup.setStyleSheet("QFrame { background: transparent; border: none; }")

        self.setStyleSheet(
            f"""
            QListView {{
                background: {t["bg_panel"]};
                color: {t["text"]};
                border: 1px solid {t["border_light"]};
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: {radius_lg};
                border-bottom-right-radius: {radius_lg};
                outline: none;
                padding: 0;
            }}
            QListView::item {{
                padding: 7px 10px;
                margin: 0;
                min-height: 26px;
                border: none;
                background: transparent;
            }}
            QListView::item:hover:!selected {{
                background: {t["bg_hover"]};
            }}
            QListView::item:selected {{
                background: {t["bg_tertiary"]};
                color: {t["text"]};
            }}
            QListView::item:selected:hover {{
                background: {t["bg_tertiary"]};
            }}
            """
        )

        origin = combo.mapToGlobal(combo.rect().bottomLeft())
        self.setFixedWidth(combo.width())
        popup.setFixedWidth(combo.width())
        popup.move(origin.x(), origin.y() - 1)


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
            line_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            line_edit.setContentsMargins(0, 0, 0, 0)

            # 移除 LineEdit 的默认样式，使其与 ComboBox 对齐
            # 设置透明背景和无边框，让它看起来像不可编辑的 ComboBox
            line_edit.setStyleSheet("""
                QLineEdit {
                    background: transparent;
                    border: none;
                    padding: 0px;
                    margin: 0px;
                    min-height: 0px;
                }
            """)

            # 如果有图标，调整文本边距以避免遮挡
            if has_icon:
                # 为图标留出 24px 的空间（16px 图标 + 8px 间距）
                line_edit.setTextMargins(24, 0, 0, 0)
            else:
                if str(combo.property("ui_variant") or "") == "mode_selector":
                    # mode_selector 已经通过 ComboBox 本体的 padding 留出了正文区，
                    # 这里不要再重复压缩 lineEdit，否则只会显示最后几个字。
                    line_edit.setTextMargins(0, 0, 0, 0)
                    line_edit.setCursorPosition(0)
                    combo.currentIndexChanged.connect(lambda _idx, le=line_edit: le.setCursorPosition(0))
                else:
                    line_edit.setTextMargins(0, 0, 0, 0)

    # 创建自定义视图
    if str(combo.property("ui_variant") or "") == "mode_selector":
        view = FusedPopupListView(combo)
    else:
        view = QListView()

    # 设置窗口标志
    view.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
    view.setFrameShape(QFrame.Shape.NoFrame)
    view.setSpacing(0)
    view.setUniformItemSizes(True)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    view.setContentsMargins(0, 0, 0, 0)
    view.viewport().setContentsMargins(0, 0, 0, 0)
    view.setViewportMargins(0, 0, 0, 0)

    if str(combo.property("ui_variant") or "") == "mode_selector":
        # 允许顶层弹出层真正显示圆角，而不是被方形窗口底色切出来。
        view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        view.viewport().setAutoFillBackground(False)

    # 设置项目代理以确保正确的高度
    view.setItemDelegate(FixedItemDelegate(view))

    # 应用视图
    combo.setView(view)
