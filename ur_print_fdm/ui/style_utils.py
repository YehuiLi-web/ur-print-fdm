"""
样式工具函数
提供样式处理辅助函数
"""

import re
from typing import Dict, Optional
from PyQt6.QtWidgets import QWidget


def themed_qss(qss: str, custom_replacements: Optional[Dict[str, str]] = None) -> str:
    """
    将QSS中的硬编码颜色替换为当前主题令牌

    这个函数用于迁移旧代码中的硬编码样式，使其能够响应主题变化。
    对于新代码，建议直接使用StyleFactory或主题令牌。

    Args:
        qss: 原始QSS字符串（可能包含硬编码颜色）
        custom_replacements: 自定义替换映射（可选）

    Returns:
        替换后的QSS字符串

    Example:
        >>> old_qss = "background-color: #2d2d2d; color: #e0e0e0;"
        >>> new_qss = themed_qss(old_qss)
        # 硬编码颜色会被替换为当前主题的对应颜色
    """
    if not qss:
        return qss

    from ur_print_fdm.ui.theme_manager import get_theme_manager

    theme_mgr = get_theme_manager()
    tokens = theme_mgr.current_tokens()

    # 标准颜色映射（深色主题常见硬编码值）
    color_map = {
        # 背景色
        "#1e1e1e": tokens.get("bg_secondary"),
        "#262628": tokens.get("bg_secondary"),
        "#2b2b2b": tokens.get("bg_main"),
        "#2d2d2d": tokens.get("bg_panel"),
        "#2d2d30": tokens.get("bg_tertiary"),
        "#252526": tokens.get("bg_tertiary"),
        "#353538": tokens.get("bg_panel"),
        "#2a2a2a": tokens.get("bg_hover"),
        "#2a2a2c": tokens.get("bg_hover"),
        "#2a2a2e": tokens.get("bg_hover"),
        "#383838": tokens.get("bg_hover_strong"),
        "#3a3a3c": tokens.get("bg_hover_strong"),
        "#3c3c3e": tokens.get("bg_hover_strong"),
        # 边框色
        "#3a3a3e": tokens.get("border"),
        "#323234": tokens.get("border"),
        "#404044": tokens.get("border_light"),
        "#46464a": tokens.get("border_light"),
        "#48484a": tokens.get("border_light"),
        "#38383c": tokens.get("border_light"),
        # 文本色
        "#e0e0e0": tokens.get("text"),
        "#e4e4e6": tokens.get("text"),
        "#e6e6e8": tokens.get("text"),
        "#cccccc": tokens.get("text"),
        "#d4d4d4": tokens.get("text"),
        "#8a8a8a": tokens.get("text_muted"),
        "#8e8e92": tokens.get("text_muted"),
        "#8a8a8c": tokens.get("text_muted"),
        "#6a6a6a": tokens.get("text_dim"),
        "#6e6e72": tokens.get("text_dim"),
        "#6e6e6e": tokens.get("text_dim"),
        "#5a5a5c": tokens.get("text_dim"),
        # 强调色
        "#2196F3": tokens.get("accent_blue"),
        "#4FC3F7": tokens.get("accent_blue"),
        "#007ACC": tokens.get("accent_blue"),
        "#569CD6": tokens.get("accent_link"),
        # 状态色
        "#4CAF50": tokens.get("success"),
        "#81C784": tokens.get("success"),
        "#D32F2F": tokens.get("danger"),
        "#f44": tokens.get("danger"),
        # 浅色主题常见硬编码值
        "#ffffff": tokens.get("bg_secondary"),
        "#f7f7f9": tokens.get("bg_main"),
        "#1f2328": tokens.get("text"),
        "#57606a": tokens.get("text_muted"),
    }

    # 合并自定义替换
    if custom_replacements:
        color_map.update(custom_replacements)

    # 执行替换
    result = qss
    for old_color, new_color in color_map.items():
        if new_color:
            # 使用正则表达式进行不区分大小写的替换
            result = re.sub(
                re.escape(old_color), new_color, result, flags=re.IGNORECASE
            )

    return result


def apply_themed_stylesheet(widget: QWidget, qss: str):
    """
    应用主题化样式表到组件

    这是themed_qss的便捷包装函数，直接应用到组件。

    Args:
        widget: 目标组件
        qss: QSS样式字符串

    Example:
        >>> button = QPushButton("Click me")
        >>> apply_themed_stylesheet(button, '''
        ...     QPushButton {
        ...         background-color: #2d2d2d;
        ...         color: #e0e0e0;
        ...     }
        ... ''')
    """
    themed = themed_qss(qss)
    widget.setStyleSheet(themed)


def get_component_style(component_type: str, **kwargs) -> str:
    """
    从样式工厂获取组件样式

    Args:
        component_type: 组件类型（如 "button_primary", "panel_collapsible"）
        **kwargs: 样式参数

    Returns:
        QSS样式字符串

    Example:
        >>> style = get_component_style("button_primary")
        >>> button.setStyleSheet(style)
    """
    from ur_print_fdm.ui.style_factory import StyleFactory

    return StyleFactory.get_style(component_type, **kwargs)
