"""
QSS样式表生成器
基于主题令牌生成完整的QSS样式表
"""

from typing import Dict, Any


def generate_qss(t: Dict[str, Any]) -> str:
    """
    基于设计令牌生成主题 QSS

    Args:
        t: 主题令牌字典

    Returns:
        完整的QSS样式表字符串
    """
    return f"""
        /* === 全局基础 === */
        QMainWindow, QWidget {{
            background-color: {t["bg_main"]};
            color: {t["text"]};
            font-family: {t["font_main"]};
            font-size: {t["size_base"]};
        }}

        /* === ToolBar / StatusBar === */
        QToolBar {{
            background-color: {t["bg_secondary"]};
            border: none;
            border-bottom: 1px solid {t["border_light"]};
            spacing: {t["space_sm"]};
            padding: 2px;
        }}
        QToolBar::separator {{
            background: {t["border_light"]};
            width: 1px;
            margin: 4px 6px;
        }}

        QStatusBar {{
            background-color: {t["bg_secondary"]};
            color: {t["text_muted"]};
            border-top: 1px solid {t["border_light"]};
        }}
        QStatusBar::item {{ border: none; }}

        QLabel[ui_role="toolbar_label"] {{
            color: {t["text_muted"]};
            font-weight: 500;
            padding: 0 4px 0 0;
            background: transparent;
        }}

        /* 工具栏 ComboBox - 透明背景 */
        QComboBox[ui_role="toolbar_combo"] {{
            background-color: transparent;
            border: 1px solid {t["border"]};
            border-radius: {t["radius"]};
            padding: 4px {t["space_md"]};
            color: {t["text"]};
            min-height: 20px;
        }}
        QComboBox[ui_role="toolbar_combo"]:hover {{
            border-color: {t["border_light"]};
            background-color: {t["bg_hover"]};
        }}
        QComboBox[ui_role="toolbar_combo"]:focus {{
            border: 1px solid {t["accent_blue"]};
        }}
        QComboBox[ui_role="toolbar_combo"]::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: none;
            background: transparent;
        }}

        /* 工具栏 CheckBox - 透明背景 */
        QToolBar QCheckBox {{
            background: transparent;
            spacing: {t["space_md"]};
            padding: 2px 4px;
        }}

        QLabel[ui_role="muted"] {{
            color: {t["text_muted"]};
            font-size: {t["size_small"]};
        }}

        QLabel[ui_role="warning"] {{
            color: {t["warning"]};
            font-weight: 600;
        }}

        /* === Tooltip === */
        QToolTip {{
            background-color: {t["tooltip_bg"]};
            color: {t["tooltip_text"]};
            border: 1px solid {t["tooltip_border"]};
            padding: 6px {t["space_md"]};
            border-radius: {t["radius"]};
            font-family: {t["font_main"]};
            font-size: {t["size_small"]};
            max-width: 320px;
        }}

        /* === 菜单栏 === */
        QMenuBar {{
            background-color: {t["bg_secondary"]};
            color: {t["text"]};
            border-bottom: 1px solid {t["border_light"]};
            padding: 3px 0;
            spacing: {t["space_sm"]};
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 6px 14px;
            border-radius: {t["radius"]};
            margin: 0 1px;
        }}
        QMenuBar::item:selected {{ background-color: {t["bg_hover_strong"]}; }}
        QMenuBar::item:pressed {{ background-color: {t["accent_hover"]}; }}

        /* === 下拉菜单 === */
        QMenu {{
            background-color: {t["bg_tertiary"]};
            border: 1px solid {t["border_light"]};
            border-radius: {t["radius_lg"]};
            padding: {t["space_md"]} 0;
        }}
        QMenu::item {{
            padding: {t["space_md"]} 36px {t["space_md"]} 28px;
            margin: 1px {t["space_md"]};
            border-radius: {t["radius"]};
        }}
        QMenu::item:selected {{
            background-color: {t["accent"]};
            color: {t["text_on_accent"]};
        }}
        QMenu::item:disabled {{ color: {t["text_dim"]}; }}
        QMenu::separator {{
            height: 1px;
            background-color: {t["border_light"]};
            margin: 6px 14px;
        }}
        QMenu::icon {{ margin-left: 10px; }}
        QMenu::right-arrow {{ margin-right: 10px; }}
        QMenu::item[text^="---"] {{
            color: {t["text_dim"]};
            font-size: {t["size_small"]};
            padding-top: 12px;
            padding-bottom: 4px;
        }}

        /* === 输入控件 === */
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit, QTextBrowser {{
            background-color: {t["bg_secondary"]};
            border: 1px solid {t["border"]};
            border-radius: {t["radius"]};
            padding: 5px {t["space_md"]};
            color: {t["text"]};
            selection-background-color: {t["selection_bg"]};
            min-height: 22px;
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus, QTextBrowser:focus {{
            border: 1px solid {t["accent_blue"]};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 22px;
            border-left: 1px solid {t["border"]};
        }}

        /* Combo dropdown list */
        QComboBox QAbstractItemView {{
            background-color: {t["bg_tertiary"]};
            border: 1px solid {t["border_light"]};
            border-radius: {t["radius"]};
            color: {t["text"]};
            selection-background-color: {t["accent"]};
            selection-color: {t["text_on_accent"]};
            outline: none;
            padding: 2px 0;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 5px {t["space_md"]};
            margin: 0;
            min-height: 22px;
            height: 22px;
        }}
        QComboBox QAbstractItemView::item:hover:!selected {{
            background-color: {t["bg_hover"]};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {t["accent"]};
            color: {t["text_on_accent"]};
        }}

        /* === 按钮 (通用) - 带微交互动效 === */
        QPushButton {{
            background-color: {t["btn_bg"]};
            border: 1px solid {t["btn_border"]};
            border-radius: {t["radius"]};
            padding: 6px 14px;
            color: {t["btn_text"]};
            min-height: 24px;
        }}
        QPushButton:hover {{
            background-color: {t["btn_bg_hover"]};
            border-color: {t["btn_border_hover"]};
        }}
        QPushButton:pressed {{ background-color: {t["btn_bg_pressed"]}; }}
        QPushButton:disabled {{
            background-color: {t["btn_disabled_bg"]};
            color: {t["btn_disabled_text"]};
            border-color: {t["btn_disabled_border"]};
        }}

        /* === 按钮变体（通用，用于对话框等） === */
        QPushButton[ui_variant="accent"] {{
            background-color: {t["accent_blue"]};
            border: none;
            color: {t["text_on_accent"]};
            font-weight: 600;
        }}
        QPushButton[ui_variant="accent"]:hover {{ background-color: {t["accent_hover"]}; }}
        QPushButton[ui_variant="accent"]:pressed {{ background-color: {t["accent"]}; }}
        QPushButton:focus {{
            border-color: {t["accent_blue"]};
        }}
        QPushButton[ui_variant="accent"]:focus {{
            border: 1px solid {t["text_on_accent"]};
            padding: 5px 13px;
        }}

        /* === 工具栏按钮变体 (通过 objectName 应用) === */
        QPushButton#btn-toolbar-primary {{
            background-color: {t["primary_green"]};
            border: none;
            padding: 5px 14px;
            font-weight: bold;
            color: {t["text_on_accent"]};
        }}
        QPushButton#btn-toolbar-primary:hover {{ background-color: {t["primary_green_hover"]}; }}
        QPushButton#btn-toolbar-primary:pressed {{ background-color: {t["primary_green_pressed"]}; }}
        QPushButton#btn-toolbar-primary:disabled {{
            background-color: #1B5E20;
            color: #81C784;
        }}
        QPushButton#btn-toolbar-danger {{
            background-color: {t["danger"]};
            border: none;
            padding: 5px 10px;
            font-weight: bold;
            color: {t["text_on_accent"]};
        }}
        QPushButton#btn-toolbar-danger:hover {{ background-color: {t["danger_hover"]}; }}
        QPushButton#btn-toolbar-danger:pressed {{ background-color: {t["danger_pressed"]}; }}
        QPushButton#btn-toolbar-danger:disabled {{
            background-color: {t["danger_pressed"]};
            color: #EF9A9A;
        }}
        QPushButton#btn-toolbar-neutral {{
            background-color: {t["neutral"]};
            border: none;
            padding: 5px 10px;
            color: {t["text_on_accent"]};
        }}
        QPushButton#btn-toolbar-neutral:hover {{ background-color: {t["neutral_hover"]}; }}
        QPushButton#btn-toolbar-neutral:pressed {{ background-color: {t["neutral_pressed"]}; }}
        QPushButton#btn-toolbar-neutral:disabled {{
            background-color: {t["btn_disabled_bg"]};
            color: {t["btn_disabled_text"]};
        }}
        QPushButton#btn-toolbar-ghost {{
            background-color: transparent;
            border: 1px solid {t["border"]};
            border-radius: {t["radius"]};
            padding: 5px 10px;
            color: {t["text"]};
        }}
        QPushButton#btn-toolbar-ghost:hover {{
            background-color: {t["bg_hover_strong"]};
            border-color: {t["border_light"]};
        }}
        QPushButton#btn-toolbar-ghost:pressed {{ background-color: {t["bg_hover"]}; }}
        QPushButton#btn-toolbar-ghost:disabled {{
            background-color: transparent;
            color: {t["btn_disabled_text"]};
        }}
        QPushButton#btn-toolbar-connect:checked {{
            background-color: {t["danger_checked"]};
            color: {t["text_on_accent"]};
        }}
        QPushButton#btn-toolbar-icon {{
            border: none;
            background-color: transparent;
            padding: 4px;
        }}
        QPushButton#btn-toolbar-icon:hover {{ background-color: {t["bg_hover_strong"]}; }}
        QPushButton#btn-toolbar-icon:pressed {{ background-color: {t["bg_hover"]}; }}

        /* === QToolButton (文件浏览器、折叠面板等) === */
        QToolButton {{
            border: none;
            background-color: transparent;
            border-radius: {t["radius"]};
            padding: 3px;
        }}
        QToolButton:hover {{
            background-color: {t["bg_hover_strong"]};
        }}
        QToolButton:pressed {{
            background-color: {t["bg_hover"]};
        }}

        /* === 复选框 === */
        QCheckBox {{ spacing: {t["space_md"]}; padding: 2px 0; }}

        /* === 列表与表格 === */
        QListWidget, QTableWidget {{
            background-color: {t["bg_secondary"]};
            border: 1px solid {t["border"]};
            border-radius: {t["radius"]};
            gridline-color: {t["border_light"]};
            outline: none;
            padding: 2px;
        }}
        QListWidget::item {{
            padding: 8px 10px;
            border-radius: 3px;
            margin: 2px;
        }}
        QListWidget::item:selected, QTableWidget::item:selected {{
            background-color: {t["accent"]};
            color: {t["text_on_accent"]};
        }}
        QListWidget::item:hover:!selected, QTableWidget::item:hover:!selected {{
            background-color: {t["bg_hover"]};
        }}
        /* 导航列表（帮助/设置等侧边栏） */
        QListWidget#nav_list::item:selected {{
            border-left: 3px solid {t["accent_blue"]};
        }}
        QHeaderView::section {{
            background-color: {t["bg_panel"]};
            color: {t["text_muted"]};
            border: none;
            border-bottom: 1px solid {t["border"]};
            padding: 6px {t["space_md"]};
            font-weight: bold;
        }}

        /* === QMainWindow 分隔线 (Dock 之间) - VSCode 风格 === */
        QMainWindow::separator {{
            background: {t["border_light"]};
            width: 1px;
            height: 1px;
        }}
        QMainWindow::separator:hover {{
            background: {t["accent_blue"]};
        }}

        /* === QSplitter === */
        QSplitter::handle {{
            background-color: {t["border_light"]};
            width: 1px;
            height: 1px;
        }}

        /* === 文本编辑 / 浏览器 === */
        QTextEdit, QTextBrowser {{
            background-color: {t["bg_secondary"]};
            color: {t["text"]};
            border: 1px solid {t["border"]};
            border-radius: {t["radius"]};
            font-family: {t["font_mono"]};
            padding: 4px;
        }}
        QTextEdit#log_console {{
            border: none;
            font-size: {t["size_small"]};
            padding: 4px 6px;
        }}

        /* === QDialogButtonBox === */
        QDialogButtonBox QPushButton {{
            min-width: 80px;
        }}

        /* === 选项卡 === */
        QTabWidget::pane {{
            border: 1px solid {t["border_light"]};
            top: -1px;
            border-radius: 0 0 {t["radius"]} {t["radius"]};
        }}
        QTabBar::tab {{
            background: {t["bg_panel"]};
            border: 1px solid {t["border_light"]};
            padding: 6px 16px;
            margin-right: 2px;
            border-top-left-radius: {t["radius"]};
            border-top-right-radius: {t["radius"]};
            color: {t["text_muted"]};
        }}
        QTabBar::tab:selected {{
            background: {t["bg_main"]};
            border-bottom-color: {t["bg_main"]};
            color: {t["text"]};
            font-weight: bold;
        }}
        QTabBar::tab:hover:!selected {{ background: {t["bg_hover_strong"]}; }}

        /* === Dock - VSCode 风格 === */
        QDockWidget {{
            titlebar-close-icon: url(none);
            titlebar-normal-icon: url(none);
        }}
        QDockWidget::title {{
            background: {t["bg_tertiary"]};
            text-align: left;
            padding: 4px 8px;
            border: none;
            font-weight: 500;
            font-size: {t["size_small"]};
            color: {t["text_muted"]};
        }}

        /* === GroupBox === */
        QGroupBox {{
            background-color: {t["bg_panel"]};
            border: 1px solid {t["border"]};
            border-radius: {t["radius_lg"]};
            margin-top: 20px;
            padding: 12px 10px 10px 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            top: 0;
            padding: 2px {t["space_md"]};
            color: {t["text"]};
            font-weight: 600;
            font-size: {t["size_base"]};
            background-color: {t["bg_main"]};
        }}

        /* === 进度条 === */
        QProgressBar {{
            border: 1px solid {t["border"]};
            border-radius: {t["radius"]};
            text-align: center;
            background-color: {t["bg_secondary"]};
            color: {t["text"]};
            min-height: 20px;
        }}
        QProgressBar::chunk {{
            background-color: {t["success"]};
            border-radius: 3px;
        }}

        /* === 滚动条 - VSCode 风格（无轨道背景，直接浮在内容上） === */
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 14px;
            margin: 0;
            padding: 0;
        }}
        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: 14px;
            margin: 0;
            padding: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {t["scroll_handle"]};
            min-height: 20px;
            border-radius: 0;
            margin: 0 3px;
        }}
        QScrollBar::handle:horizontal {{
            background: {t["scroll_handle"]};
            min-width: 20px;
            border-radius: 0;
            margin: 3px 0;
        }}
        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
            background: {t["scroll_handle_hover"]};
        }}
        QScrollBar::handle:vertical:pressed, QScrollBar::handle:horizontal:pressed {{
            background: {t["scroll_handle_pressed"]};
        }}
        /* 轨道区域完全透明 */
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
            background: transparent;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
            background: transparent;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}
        /* 滚动条交界角落 */
        QAbstractScrollArea::corner {{
            background: transparent;
        }}

        /* === TreeWidget === */
        QTreeWidget {{
            background-color: {t["bg_secondary"]};
            border: none;
            outline: none;
            font-size: {t["size_base"]};
            padding: 4px 0;
        }}
        QTreeWidget::item {{
            padding: 4px 6px;
            border-radius: 3px;
            margin: 0;
        }}
        QTreeWidget::item:hover {{ background-color: {t["bg_hover"]}; }}
        QTreeWidget::item:selected {{
            background-color: {t["accent"]};
            color: {t["text_on_accent"]};
        }}
        QTreeWidget::item:selected:active {{ background-color: {t["accent_hover"]}; }}
        QTreeWidget::branch:has-children:!has-siblings:closed,
        QTreeWidget::branch:closed:has-children:has-siblings {{
            border: none;
            image: url({t["tree_branch_closed_icon"]});
        }}
        QTreeWidget::branch:open:has-children:!has-siblings,
        QTreeWidget::branch:open:has-children:has-siblings {{
            border: none;
            image: url({t["tree_branch_open_icon"]});
        }}
        QTreeWidget::branch:has-siblings:!adjoins-item,
        QTreeWidget::branch:has-siblings:adjoins-item {{ border: none; }}

        /* === QMessageBox / QDialog === */
        QMessageBox {{
            background-color: {t["bg_main"]};
            color: {t["text"]};
        }}
        QMessageBox QLabel {{
            color: {t["text"]};
            min-width: 300px;
        }}
        QMessageBox QPushButton {{
            min-width: 80px;
        }}
        """
