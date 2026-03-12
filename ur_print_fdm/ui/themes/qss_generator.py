"""
QSS样式表生成器
基于主题令牌生成完整的QSS样式表
"""

from typing import Dict, Any


def _rgba(color: str, alpha: float) -> str:
    color = str(color or "").strip()
    if color.startswith("#") and len(color) == 7:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return f"rgba({r}, {g}, {b}, {alpha:.3f})"
    return color


def generate_qss(t: Dict[str, Any]) -> str:
    """
    基于设计令牌生成主题 QSS

    Args:
        t: 主题令牌字典

    Returns:
        完整的QSS样式表字符串
    """
    popup_surface_bg = _rgba(t.get("bg_panel", "#2d2d2d"), 0.14)
    popup_alt_bg = _rgba(t.get("bg_secondary", "#1e1e1e"), 0.11)
    popup_hover_bg = "rgba(255, 255, 255, 0.020)"
    popup_selected_bg = "rgba(255, 255, 255, 0.055)"
    return f"""
        /* === 全局基础 === */
        QMainWindow, QWidget {{
            background-color: {t["bg_main"]};
            color: {t["text"]};
            font-family: {t["font_main"]};
            font-size: {t["size_base"]};
        }}

        /* === Phase C: QLabel 透明背景，防止文字出现背景块 === */
        QLabel {{
            background: transparent;
            color: {t["text"]};
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

        /* 工具栏 ComboBox - 透明背景，文字左对齐 */
        QComboBox[ui_role="toolbar_combo"] {{
            background-color: transparent;
            border: 1px solid {t["border"]};
            border-radius: {t["radius"]};
            padding: 4px 4px 4px 6px;
            color: {t["text"]};
            min-height: 20px;
            text-align: left;
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
        QFrame[ui_role="fused_combo"] {{
            border: 1px solid {t["border"]};
            border-radius: {t["radius_lg"]};
            min-height: 30px;
        }}
        QFrame[ui_role="fused_combo"][ui_variant="form_combo"],
        QFrame[ui_role="fused_combo"][ui_variant="toolbar_combo"] {{
            background-color: {t["bg_secondary"]};
        }}
        QFrame[ui_role="fused_combo"][ui_variant="mode_selector"] {{
            background-color: {t["bg_panel"]};
        }}
        QFrame[ui_role="fused_combo"]:hover {{
            border-color: {t["border_light"]};
        }}
        QFrame[ui_role="fused_combo"][ui_variant="form_combo"]:hover,
        QFrame[ui_role="fused_combo"][ui_variant="toolbar_combo"][focused="true"],
        QFrame[ui_role="fused_combo"][ui_variant="toolbar_combo"]:hover,
        QFrame[ui_role="fused_combo"][ui_variant="form_combo"][focused="true"] {{
            background-color: {t["bg_panel"]};
        }}
        QFrame[ui_role="fused_combo"][ui_variant="mode_selector"]:hover,
        QFrame[ui_role="fused_combo"][ui_variant="mode_selector"][focused="true"] {{
            background-color: {t["bg_panel"]};
        }}
        QFrame[ui_role="fused_combo"][focused="true"] {{
            border: 1px solid {t["border_light"]};
        }}
        QFrame[ui_role="fused_combo"][expanded="true"] {{
            border-color: {t["border_light"]};
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
        }}
        QFrame[ui_role="fused_combo"]:disabled {{
            background-color: {t["bg_secondary"]};
            border-color: {t["border"]};
        }}
        QFrame[ui_role="fused_combo"] QLabel[ui_role="fused_combo_label"] {{
            background: transparent;
            color: {t["text"]};
            padding: 0 8px 0 10px;
        }}
        QFrame[ui_role="fused_combo"][ui_variant="mode_selector"] QLabel[ui_role="fused_combo_label"] {{
            font-weight: 500;
        }}
        QFrame[ui_role="fused_combo"] QLineEdit[ui_role="fused_combo_edit"] {{
            background: transparent;
            border: none;
            color: {t["text"]};
            padding: 0 8px 0 10px;
            margin: 0;
            min-height: 0;
            selection-background-color: {t["selection_bg"]};
        }}
        QFrame[ui_role="fused_combo"] QLineEdit[ui_role="fused_combo_edit"]:focus,
        QFrame[ui_role="fused_combo"] QLineEdit[ui_role="fused_combo_edit"]:hover {{
            background: transparent;
            border: none;
        }}
        QFrame[ui_role="fused_combo"]:disabled QLabel[ui_role="fused_combo_label"],
        QFrame[ui_role="fused_combo"]:disabled QLineEdit[ui_role="fused_combo_edit"] {{
            color: {t["text_dim"]};
        }}
        QFrame[ui_role="fused_combo_arrow_host"] {{
            background: transparent;
            border: none;
            border-left: 1px solid rgba(255, 255, 255, 0.06);
        }}
        QFrame[ui_role="fused_combo"][expanded="true"] QFrame[ui_role="fused_combo_arrow_host"] {{
            border-left: 1px solid rgba(255, 255, 255, 0.08);
        }}
        QLabel[ui_role="fused_combo_arrow"] {{
            background: transparent;
            padding: 0;
        }}
        QComboBox[ui_variant="mode_selector"] {{
            background-color: {t["bg_panel"]};
            border: 1px solid {t["border"]};
            border-radius: {t["radius_lg"]};
            padding: 0 0 0 10px;
            min-height: 30px;
            font-weight: 500;
        }}
        QComboBox[ui_variant="mode_selector"]:hover {{
            background-color: {t["bg_tertiary"]};
            border-color: {t["border_light"]};
        }}
        QComboBox[ui_variant="mode_selector"]:on {{
            border: 1px solid {t["border_light"]};
            background-color: {t["bg_panel"]};
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
        }}
        QComboBox[ui_variant="mode_selector"]:focus {{
            border: 1px solid {t["border_light"]};
            background-color: {t["bg_panel"]};
        }}
        QComboBox[ui_variant="mode_selector"]::drop-down {{
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 22px;
            margin: 0;
            border: none;
            border-left: 1px solid rgba(255, 255, 255, 0.06);
            border-top-right-radius: {t["radius_lg"]};
            border-bottom-right-radius: {t["radius_lg"]};
            background: {t["bg_panel"]};
        }}
        QComboBox[ui_variant="mode_selector"]::drop-down:hover,
        QComboBox[ui_variant="mode_selector"]:on::drop-down {{
            background-color: {t["bg_panel"]};
            border-left: 1px solid rgba(255, 255, 255, 0.08);
        }}
        QComboBox[ui_variant="mode_selector"]:on::drop-down {{
            border-bottom-right-radius: 0px;
        }}
        QComboBox[ui_variant="mode_selector"]::down-arrow {{
            image: url({t["tree_branch_open_icon"]});
            width: 10px;
            height: 10px;
        }}
        QComboBox[ui_variant="mode_selector"] QLineEdit {{
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
            min-height: 0;
            selection-background-color: transparent;
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

        /* === 输入控件 (Phase B 优化: 增强交互反馈) === */
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit, QTextBrowser {{
            background-color: {t["bg_secondary"]};
            border: 1px solid {t["border"]};
            border-radius: {t["radius"]};
            padding: 6px {t["space_md"]};
            color: {t["text"]};
            selection-background-color: {t["selection_bg"]};
            min-height: 24px;
        }}
        QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
            border-color: {t["border_light"]};
            background-color: {t["bg_panel"]};
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus, QTextBrowser:focus {{
            border: 1.5px solid {t["accent_blue"]};
            background-color: {t["bg_panel"]};
        }}
        /* SpinBox 上下箭头按钮优化 */
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid {t["border"]};
            border-bottom: 1px solid {t["border"]};
            border-top-right-radius: {t["radius"]};
            background-color: {t["bg_tertiary"]};
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 20px;
            border-left: 1px solid {t["border"]};
            border-bottom-right-radius: {t["radius"]};
            background-color: {t["bg_tertiary"]};
        }}
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {t["bg_hover_strong"]};
        }}
        QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
        QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
            background-color: {t["bg_hover"]};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left: 1px solid {t["border"]};
            border-top-right-radius: {t["radius"]};
            border-bottom-right-radius: {t["radius"]};
            background-color: {t["bg_tertiary"]};
        }}
        QComboBox::drop-down:hover {{
            background-color: {t["bg_hover_strong"]};
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
        QComboBox[ui_variant="mode_selector"] QAbstractItemView {{
            background-color: {t["bg_panel"]};
            border: 1px solid {t["border_light"]};
            border-top: none;
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-left-radius: {t["radius_lg"]};
            border-bottom-right-radius: {t["radius_lg"]};
            color: {t["text"]};
            selection-background-color: transparent;
            selection-color: {t["text"]};
            outline: none;
            padding: 4px 0;
        }}
        QComboBox[ui_variant="mode_selector"] QAbstractItemView::item {{
            padding: 6px 10px;
            margin: 0;
            min-height: 24px;
            border: none;
            border-radius: 0px;
        }}
        QComboBox[ui_variant="mode_selector"] QAbstractItemView::item:hover:!selected {{
            background-color: {t["bg_hover"]};
        }}
        QComboBox[ui_variant="mode_selector"] QAbstractItemView::item:selected {{
            background-color: {t["bg_tertiary"]};
            color: {t["text"]};
            border: none;
        }}
        QWidget[ui_role="fused_combo_popup"] {{
            background: transparent;
            border: none;
        }}
        QFrame[ui_role="fused_combo_popup_surface"] {{
            background-color: {popup_surface_bg};
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-top: none;
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            border-bottom-left-radius: {t["radius_lg"]};
            border-bottom-right-radius: {t["radius_lg"]};
        }}
        QFrame[ui_role="fused_combo_popup_surface"][ui_variant="form_combo"],
        QFrame[ui_role="fused_combo_popup_surface"][ui_variant="toolbar_combo"] {{
            background-color: {popup_alt_bg};
        }}
        QFrame[ui_role="fused_combo_popup_surface"][ui_variant="mode_selector"] {{
            background-color: {popup_surface_bg};
        }}
        QScrollArea[ui_role="fused_combo_popup_scroll"],
        QWidget[ui_role="fused_combo_popup_content"] {{
            background: transparent;
            border: none;
        }}
        QFrame[ui_role="fused_combo_popup_item"] {{
            background: transparent;
            border: none;
            border-radius: 0px;
        }}
        QFrame[ui_role="fused_combo_popup_item"][highlighted="true"] {{
            background-color: {popup_hover_bg};
        }}
        QFrame[ui_role="fused_combo_popup_item"][selected="true"] {{
            background-color: {popup_selected_bg};
        }}
        QFrame[ui_role="fused_combo_popup_item"][selected="true"][highlighted="true"] {{
            background-color: {popup_selected_bg};
        }}
        QFrame[ui_role="fused_combo_popup_item"][last="true"] {{
            border-bottom-left-radius: {t["radius_lg"]};
            border-bottom-right-radius: {t["radius_lg"]};
        }}
        QLabel[ui_role="fused_combo_popup_item_label"] {{
            background: transparent;
            color: {t["text"]};
            padding: 0 8px 0 10px;
        }}
        QFrame[ui_role="fused_combo_popup_surface"][ui_variant="mode_selector"] QLabel[ui_role="fused_combo_popup_item_label"] {{
            font-weight: 500;
        }}

        /* === 按钮 (通用) - Phase B 优化: 增强圆角与交互动效 === */
        QPushButton {{
            background-color: {t["btn_bg"]};
            border: 1px solid {t["btn_border"]};
            border-radius: 6px;
            padding: 7px 16px;
            color: {t["btn_text"]};
            min-height: 26px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {t["btn_bg_hover"]};
            border-color: {t["btn_border_hover"]};
        }}
        QPushButton:pressed {{
            background-color: {t["btn_bg_pressed"]};
            border-color: {t["accent_blue"]};
        }}
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
            padding: 4px 0 4px 6px;
        }}

        /* === QDialogButtonBox === */
        QDialogButtonBox QPushButton {{
            min-width: 80px;
        }}

        /* === 选项卡 === */
        QTabWidget::pane {{
            border: 1px solid {t["border_light"]};
            border-top: none;
        }}
        QTabBar::tab {{
            background: {t["bg_panel"]};
            border: 1px solid {t["border_light"]};
            border-bottom: none;
            padding: 6px 16px;
            margin: 0;
            color: {t["text_muted"]};
        }}
        QTabBar::tab:selected {{
            background: {t["bg_main"]};
            color: {t["text"]};
            font-weight: bold;
        }}
        QTabBar::tab:hover:!selected {{ background: {t["bg_hover_strong"]}; }}

        /* === Dock - VSCode 风格 === */
        QDockWidget {{
            titlebar-close-icon: url(none);
            titlebar-normal-icon: url(none);
            background-color: {t["bg_secondary"]};
        }}
        QDockWidget::title {{
            background: {t["bg_tertiary"]};
            text-align: left;
            padding: 8px 12px;
            border-bottom: 1px solid {t["border_light"]};
            font-weight: 500;
            font-size: {t["size_base"]};
            color: {t["text_muted"]};
        }}
        QDockWidget > QWidget {{
            padding: 0px;
            margin: 0px;
            background-color: transparent;
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

        /* === 滚动条 - Phase B 优化: 更细腻的圆角滚动条 === */
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 12px;
            margin: 0;
            padding: 2px;
        }}
        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: 12px;
            margin: 0;
            padding: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {t["scroll_handle"]};
            min-height: 30px;
            border-radius: 4px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: {t["scroll_handle"]};
            min-width: 30px;
            border-radius: 4px;
            margin: 2px;
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

        /* === TreeWidget - 专业软件风格 === */
        QTreeWidget {{
            background-color: {t["bg_secondary"]};
            border: none;
            outline: none;
            font-size: {t["size_base"]};
            padding: 0;
        }}
        QTreeWidget::item {{
            padding: 4px 6px;
            border: none;
            border-radius: 0;
            margin: 0;
            min-height: 22px;
        }}
        QTreeWidget::item:hover {{
            background-color: {t["tree_hover_bg"]};
        }}
        QTreeWidget::item:selected {{
            background-color: {t["tree_selection_bg"]};
            color: {t["text"]};
        }}
        QTreeWidget::item:selected:active {{
            background-color: {t["tree_selection_bg"]};
            color: {t["text"]};
        }}
        QTreeWidget::item:selected:!active {{
            background-color: {t["tree_selection_bg"]};
            color: {t["text"]};
        }}
        /* Branch 区域样式 - 与 item 保持一致 */
        QTreeWidget::branch {{
            background-color: transparent;
            border: none;
        }}
        QTreeWidget::branch:hover {{
            background-color: {t["tree_hover_bg"]};
        }}
        QTreeWidget::branch:selected {{
            background-color: {t["tree_selection_bg"]};
        }}
        QTreeWidget::branch:selected:active {{
            background-color: {t["tree_selection_bg"]};
        }}
        QTreeWidget::branch:selected:!active {{
            background-color: {t["tree_selection_bg"]};
        }}
        /* TreeWidget 专用滚动条 - 默认隐藏，悬停显示 */
        QTreeWidget QScrollBar:vertical {{
            border: none;
            background: {t["bg_secondary"]};
            width: 10px;
            margin: 0;
            padding: 0;
        }}
        QTreeWidget QScrollBar::handle:vertical {{
            background: transparent;
            min-height: 30px;
            border-radius: 0;
            margin: 0;
        }}
        QTreeWidget QScrollBar::handle:vertical:hover {{
            background: {t["scroll_handle_hover"]};
        }}
        QTreeWidget QScrollBar::add-line:vertical,
        QTreeWidget QScrollBar::sub-line:vertical {{
            height: 0;
            background: transparent;
        }}
        QTreeWidget QScrollBar::add-page:vertical,
        QTreeWidget QScrollBar::sub-page:vertical {{
            background: transparent;
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
