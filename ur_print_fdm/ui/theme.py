"""
主题与设计令牌 - 向后兼容层
统一管理颜色、字号、间距，确保全局 UI 风格一致

注意：此文件保留用于向后兼容。
新代码请使用 ur_print_fdm.ui.theme_manager.ThemeManager
"""

# 导入新的主题管理器
from ur_print_fdm.ui.theme_manager import get_theme_manager

# === 设计令牌 (Design Tokens) - 向后兼容 ===
# 这些全局变量保留用于旧代码，内部从ThemeManager获取
def _get_dark_tokens():
    """获取深色主题令牌"""
    theme_mgr = get_theme_manager()
    theme = theme_mgr.get_theme("dark")
    return theme.tokens if theme else {}

def _get_light_tokens():
    """获取浅色主题令牌"""
    theme_mgr = get_theme_manager()
    theme = theme_mgr.get_theme("light")
    return theme.tokens if theme else {}

# 深色主题（向后兼容）
DARK = {
    "bg_main": "#2b2b2b",
    "bg_secondary": "#1e1e1e",
    "bg_tertiary": "#252526",
    "bg_panel": "#2d2d2d",
    "bg_hover": "#2a2a2a",
    "bg_hover_strong": "#383838",
    "border": "#3a3a3e",
    "border_light": "#46464a",
    "text": "#e0e0e0",
    "text_muted": "#8a8a8a",
    "text_dim": "#6a6a6a",
    "text_on_accent": "#ffffff",
    "icon": "#d4d4d4",
    "accent": "#094771",
    "accent_hover": "#0e639c",
    "accent_blue": "#2196F3",
    "accent_link": "#569CD6",
    "selection_bg": "#264f78",
    "primary_green": "#388E3C",
    "primary_green_hover": "#43A047",
    "primary_green_pressed": "#2E7D32",
    "danger": "#D32F2F",
    "danger_hover": "#E53935",
    "danger_pressed": "#B71C1C",
    "danger_checked": "#c62828",
    "neutral": "#455A64",
    "neutral_hover": "#546E7A",
    "neutral_pressed": "#37474F",
    "success": "#4CAF50",
    "warning": "#FFA726",
    "tooltip_bg": "#353535",
    "tooltip_border": "#4a4a4a",
    "tooltip_text": "#f0f0f0",
    "radius": "4px",
    "radius_lg": "6px",
    "font_main": '"Segoe UI", "Microsoft YaHei", sans-serif',
    "font_mono": '"Consolas", "Courier New", monospace',
    "size_base": "10pt",
    "size_small": "9pt",
    "size_large": "11pt",
    "space_sm": "4px",
    "space_md": "8px",
    "space_lg": "12px",
    # Buttons (generic)
    "btn_bg": "#3c3c3c",
    "btn_bg_hover": "#4a4a4a",
    "btn_bg_pressed": "#2a2a2a",
    "btn_border": "#505050",
    "btn_border_hover": "#606060",
    "btn_text": "#ffffff",
    "btn_disabled_bg": "#323232",
    "btn_disabled_border": "#404040",
    "btn_disabled_text": "#6a6a6a",
    # Scrollbar handles
    "scroll_handle": "rgba(121, 121, 121, 0.2)",
    "scroll_handle_hover": "rgba(121, 121, 121, 0.5)",
    "scroll_handle_pressed": "rgba(121, 121, 121, 0.7)",
    # Tree branch icons (QSS cannot tint; pick per-theme assets)
    "tree_branch_closed_icon": "ur_print_fdm/ui/resources/icons/collapse.svg",
    "tree_branch_open_icon": "ur_print_fdm/ui/resources/icons/expand.svg",
}


LIGHT = {
    "bg_main": "#f7f7f9",
    "bg_secondary": "#ffffff",
    "bg_tertiary": "#f0f1f3",
    "bg_panel": "#fbfbfd",
    "bg_hover": "#eef0f4",
    "bg_hover_strong": "#e6e8ee",
    "border": "#d0d7de",
    "border_light": "#e6e8ee",
    "text": "#1f2328",
    "text_muted": "#57606a",
    "text_dim": "#8c959f",
    "text_on_accent": "#ffffff",
    "icon": "#57606a",
    "accent": "#0969da",
    "accent_hover": "#0758b8",
    "accent_blue": "#0969da",
    "accent_link": "#0969da",
    "selection_bg": "#cfe8ff",
    "primary_green": "#2da44e",
    "primary_green_hover": "#2c974b",
    "primary_green_pressed": "#238636",
    "danger": "#cf222e",
    "danger_hover": "#a40e26",
    "danger_pressed": "#82071e",
    "danger_checked": "#cf222e",
    "neutral": "#6e7781",
    "neutral_hover": "#5b646e",
    "neutral_pressed": "#48515a",
    "success": "#2da44e",
    "warning": "#bf8700",
    # Tooltips: keep dark for readability
    "tooltip_bg": "#1f2328",
    "tooltip_border": "#3d444d",
    "tooltip_text": "#f0f0f0",
    "radius": "4px",
    "radius_lg": "6px",
    "font_main": '"Segoe UI", "Microsoft YaHei", sans-serif',
    "font_mono": '"Consolas", "Courier New", monospace',
    "size_base": "10pt",
    "size_small": "9pt",
    "size_large": "11pt",
    "space_sm": "4px",
    "space_md": "8px",
    "space_lg": "12px",
    # Buttons (generic)
    "btn_bg": "#f6f8fa",
    "btn_bg_hover": "#eef2f6",
    "btn_bg_pressed": "#e7ebef",
    "btn_border": "#d0d7de",
    "btn_border_hover": "#b6bec8",
    "btn_text": "#1f2328",
    "btn_disabled_bg": "#f6f8fa",
    "btn_disabled_border": "#e6e8ee",
    "btn_disabled_text": "#8c959f",
    # Scrollbar handles
    "scroll_handle": "rgba(0, 0, 0, 0.18)",
    "scroll_handle_hover": "rgba(0, 0, 0, 0.28)",
    "scroll_handle_pressed": "rgba(0, 0, 0, 0.38)",
    # Tree branch icons (QSS cannot tint; pick per-theme assets)
    "tree_branch_closed_icon": "ur_print_fdm/ui/resources/icons/collapse_light.svg",
    "tree_branch_open_icon": "ur_print_fdm/ui/resources/icons/expand_light.svg",
}


def _dark_theme(t: dict) -> str:
    """
    基于设计令牌生成主题 QSS（向后兼容）

    注意：此函数保留用于向后兼容。
    新代码请使用 ur_print_fdm.ui.themes.qss_generator.generate_qss
    """
    from ur_print_fdm.ui.themes.qss_generator import generate_qss
    return generate_qss(t)

def _dark_theme_legacy(t: dict) -> str:
    """原始的QSS生成函数（已废弃，保留用于参考）"""
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
            background: transparent;
            width: 2px;
            border-left: 1px solid {t["border_light"]};
            margin: 4px 3px 4px 5px;
        }}
        QWidget#toolbarIndicatorGroup,
        QWidget#toolbarControlGroup {{
            background-color: transparent;
            border: none;
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
            color: {t["text"]};
            selection-background-color: {t["accent"]};
            selection-color: {t["text_on_accent"]};
            outline: none;
            padding: 4px 0;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 6px 8px;
            margin: 1px 0;
            border-radius: {t["radius"]};
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
        QPushButton#btn-toolbar-connect {{
            padding: 5px 8px;
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
            padding: 5px 6px;
            border-radius: 0;
            margin: 0;
            min-height: 22px;
        }}
        QTreeWidget::item:hover {{ background-color: {t["bg_hover"]}; }}
        QTreeWidget::item:selected {{
            background-color: {t["accent"]};
            color: {t["text_on_accent"]};
        }}
        QTreeWidget::item:selected:active {{
            background-color: {t["accent"]};
            color: {t["text_on_accent"]};
        }}
        QTreeWidget::item:selected:!active {{
            background-color: {t["accent"]};
            color: {t["text_on_accent"]};
        }}
        /* Branch 区域样式 - 统一选择颜色，消除分层效果 */
        QTreeWidget::branch {{
            background-color: transparent;
        }}
        QTreeWidget::branch:hover {{
            background-color: {t["bg_hover"]};
        }}
        QTreeWidget::branch:selected {{
            background-color: {t["accent"]};
        }}
        QTreeWidget::branch:selected:active {{
            background-color: {t["accent"]};
        }}
        QTreeWidget::branch:selected:!active {{
            background-color: {t["accent"]};
        }}
        /* 折叠状态箭头 - 包括选中状态 */
        QTreeWidget::branch:has-children:!has-siblings:closed,
        QTreeWidget::branch:closed:has-children:has-siblings {{
            border: none;
            image: url({t["tree_branch_closed_icon"]});
        }}
        QTreeWidget::branch:has-children:!has-siblings:closed:selected,
        QTreeWidget::branch:closed:has-children:has-siblings:selected {{
            border: none;
            image: url({t["tree_branch_closed_icon"]});
        }}
        /* 展开状态箭头 - 包括选中状态 */
        QTreeWidget::branch:open:has-children:!has-siblings,
        QTreeWidget::branch:open:has-children:has-siblings {{
            border: none;
            image: url({t["tree_branch_open_icon"]});
        }}
        QTreeWidget::branch:open:has-children:!has-siblings:selected,
        QTreeWidget::branch:open:has-children:has-siblings:selected {{
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


def get_dark_theme() -> str:
    """
    应用现代深色工程主题（向后兼容）

    注意：此函数保留用于向后兼容。
    新代码请使用 ThemeManager.set_theme("dark")
    """
    theme_mgr = get_theme_manager()
    theme = theme_mgr.get_theme("dark")
    return theme.generate_qss() if theme else ""


def get_light_theme() -> str:
    """
    浅色主题（向后兼容）

    注意：此函数保留用于向后兼容。
    新代码请使用 ThemeManager.set_theme("light")
    """
    theme_mgr = get_theme_manager()
    theme = theme_mgr.get_theme("light")
    return theme.generate_qss() if theme else ""


def apply_app_theme(use_dark: bool):
    """
    将主题应用到 QApplication（向后兼容）

    注意：此函数保留用于向后兼容。
    新代码请使用 ThemeManager.set_theme(theme_id)

    Args:
        use_dark: True使用深色主题，False使用浅色主题
    """
    theme_mgr = get_theme_manager()
    theme_id = "dark" if use_dark else "light"
    theme_mgr.set_theme(theme_id)


# 保留全局变量（用于旧代码）
_CURRENT_TOKENS = None
_CURRENT_MODE = "dark"


def current_tokens() -> dict:
    """
    获取当前主题令牌（向后兼容）

    注意：此函数保留用于向后兼容。
    新代码请使用 ThemeManager.current_tokens()

    Returns:
        当前主题的令牌字典
    """
    theme_mgr = get_theme_manager()
    return theme_mgr.current_tokens()


# 初始化全局变量
def _init_legacy_globals():
    """初始化遗留的全局变量"""
    global _CURRENT_TOKENS, _CURRENT_MODE
    theme_mgr = get_theme_manager()
    _CURRENT_TOKENS = theme_mgr.current_tokens()
    _CURRENT_MODE = theme_mgr.current_theme_id()

# 延迟初始化，避免循环导入
# _init_legacy_globals() 将在首次调用 current_tokens() 时自动执行


