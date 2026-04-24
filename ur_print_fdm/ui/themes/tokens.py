"""
主题令牌类型定义
定义主题系统中使用的所有令牌类型
"""

from typing import TypedDict


class ColorTokens(TypedDict, total=False):
    """颜色令牌"""
    # 背景色
    bg_main: str
    bg_secondary: str
    bg_tertiary: str
    bg_panel: str
    bg_hover: str
    bg_hover_strong: str

    # 边框色
    border: str
    border_light: str

    # 文本色
    text: str
    text_muted: str
    text_dim: str
    text_on_accent: str

    # 图标色
    icon: str

    # 强调色
    accent: str
    accent_hover: str
    accent_blue: str
    accent_link: str

    # 选择背景
    selection_bg: str
    tree_selection_bg: str  # 文件树选中背景
    tree_hover_bg: str  # 文件树悬停背景

    # 状态色
    primary_green: str
    primary_green_hover: str
    primary_green_pressed: str
    danger: str
    danger_hover: str
    danger_pressed: str
    danger_checked: str
    neutral: str
    neutral_hover: str
    neutral_pressed: str
    success: str
    warning: str

    # 工具提示
    tooltip_bg: str
    tooltip_border: str
    tooltip_text: str

    # 按钮
    btn_bg: str
    btn_bg_hover: str
    btn_bg_pressed: str
    btn_border: str
    btn_border_hover: str
    btn_text: str
    btn_disabled_bg: str
    btn_disabled_border: str
    btn_disabled_text: str

    # 滚动条
    scroll_handle: str
    scroll_handle_hover: str
    scroll_handle_pressed: str

    # 树形控件图标
    tree_branch_closed_icon: str
    tree_branch_open_icon: str


class LayoutTokens(TypedDict, total=False):
    """布局令牌"""
    radius: str
    radius_lg: str
    space_sm: str
    space_md: str
    space_lg: str


class TypographyTokens(TypedDict, total=False):
    """字体令牌"""
    font_main: str
    font_mono: str
    size_base: str
    size_small: str
    size_large: str


class ThemeTokens(ColorTokens, LayoutTokens, TypographyTokens):
    """完整主题令牌集合"""
    pass
