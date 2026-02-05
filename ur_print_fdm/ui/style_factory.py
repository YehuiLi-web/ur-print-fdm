"""
组件样式工厂
提供预定义的组件样式模板
"""

from typing import Dict, Any, Callable


class StyleFactory:
    """
    组件样式工厂

    提供预定义的组件样式模板，基于当前主题令牌生成QSS样式。

    使用方法：
        >>> from ur_print_fdm.ui.style_factory import StyleFactory
        >>> button_style = StyleFactory.get_style("button_primary")
        >>> button.setStyleSheet(button_style)

    可用样式：
        - button_primary: 主要按钮（绿色）
        - button_danger: 危险按钮（红色）
        - button_neutral: 中性按钮（灰色）
        - button_accent: 强调按钮（蓝色）
        - panel_collapsible: 可折叠面板
        - editor_statusbar: 编辑器状态栏
    """

    _style_generators: Dict[str, Callable] = {}

    @classmethod
    def register(cls, component_type: str, generator: Callable):
        """
        注册样式生成器

        Args:
            component_type: 组件类型名称
            generator: 样式生成函数，接收tokens和kwargs参数
        """
        cls._style_generators[component_type] = generator

    @classmethod
    def get_style(cls, component_type: str, **kwargs) -> str:
        """
        获取组件样式

        Args:
            component_type: 组件类型名称
            **kwargs: 额外的样式参数

        Returns:
            QSS样式字符串
        """
        if component_type not in cls._style_generators:
            return ""

        from ur_print_fdm.ui.theme_manager import get_theme_manager

        theme_mgr = get_theme_manager()
        tokens = theme_mgr.current_tokens()

        return cls._style_generators[component_type](tokens, **kwargs)

    @staticmethod
    def button_primary(tokens: Dict[str, Any], **kwargs) -> str:
        """主要按钮样式（绿色）"""
        return f"""
            QPushButton {{
                background-color: {tokens['primary_green']};
                border: none;
                border-radius: {tokens['radius']};
                padding: 6px 14px;
                color: {tokens['text_on_accent']};
                font-weight: bold;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {tokens['primary_green_hover']};
            }}
            QPushButton:pressed {{
                background-color: {tokens['primary_green_pressed']};
            }}
            QPushButton:disabled {{
                background-color: {tokens['btn_disabled_bg']};
                color: {tokens['btn_disabled_text']};
            }}
        """

    @staticmethod
    def button_danger(tokens: Dict[str, Any], **kwargs) -> str:
        """危险按钮样式（红色）"""
        return f"""
            QPushButton {{
                background-color: {tokens['danger']};
                border: none;
                border-radius: {tokens['radius']};
                padding: 6px 14px;
                color: {tokens['text_on_accent']};
                font-weight: bold;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {tokens['danger_hover']};
            }}
            QPushButton:pressed {{
                background-color: {tokens['danger_pressed']};
            }}
            QPushButton:disabled {{
                background-color: {tokens['btn_disabled_bg']};
                color: {tokens['btn_disabled_text']};
            }}
        """

    @staticmethod
    def button_neutral(tokens: Dict[str, Any], **kwargs) -> str:
        """中性按钮样式（灰色）"""
        return f"""
            QPushButton {{
                background-color: {tokens['neutral']};
                border: none;
                border-radius: {tokens['radius']};
                padding: 6px 14px;
                color: {tokens['text_on_accent']};
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {tokens['neutral_hover']};
            }}
            QPushButton:pressed {{
                background-color: {tokens['neutral_pressed']};
            }}
            QPushButton:disabled {{
                background-color: {tokens['btn_disabled_bg']};
                color: {tokens['btn_disabled_text']};
            }}
        """

    @staticmethod
    def button_accent(tokens: Dict[str, Any], **kwargs) -> str:
        """强调按钮样式（蓝色）"""
        return f"""
            QPushButton {{
                background-color: {tokens['accent_blue']};
                border: none;
                border-radius: {tokens['radius']};
                padding: 6px 14px;
                color: {tokens['text_on_accent']};
                font-weight: 600;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {tokens['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {tokens['accent']};
            }}
            QPushButton:disabled {{
                background-color: {tokens['btn_disabled_bg']};
                color: {tokens['btn_disabled_text']};
            }}
        """

    @staticmethod
    def panel_collapsible(tokens: Dict[str, Any], **kwargs) -> str:
        """可折叠面板样式"""
        return f"""
            QGroupBox {{
                background-color: {tokens['bg_panel']};
                border: 1px solid {tokens['border']};
                border-radius: {tokens['radius_lg']};
                margin-top: 20px;
                padding: 12px 10px 10px 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 2px {tokens['space_md']};
                color: {tokens['text']};
                font-weight: 600;
                background-color: {tokens['bg_main']};
            }}
        """

    @staticmethod
    def editor_statusbar(tokens: Dict[str, Any], **kwargs) -> str:
        """编辑器状态栏样式"""
        return f"""
            QFrame {{
                background-color: {tokens['bg_tertiary']};
                border-top: 1px solid {tokens['border_light']};
            }}
            QLabel {{
                color: {tokens['text_muted']};
                font-size: 11px;
                padding: 3px 12px;
            }}
            QLabel:hover {{
                background-color: {tokens['bg_hover_strong']};
                color: {tokens['text']};
            }}
        """


# 注册所有样式生成器
StyleFactory.register("button_primary", StyleFactory.button_primary)
StyleFactory.register("button_danger", StyleFactory.button_danger)
StyleFactory.register("button_neutral", StyleFactory.button_neutral)
StyleFactory.register("button_accent", StyleFactory.button_accent)
StyleFactory.register("panel_collapsible", StyleFactory.panel_collapsible)
StyleFactory.register("editor_statusbar", StyleFactory.editor_statusbar)
