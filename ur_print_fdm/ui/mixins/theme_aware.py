"""
主题感知混入类
让组件自动响应主题变化
"""

from typing import Any, Optional


class ThemeAwareMixin:
    """
    主题感知混入类

    使用方法：
        class MyWidget(QWidget, ThemeAwareMixin):
            def __init__(self):
                super().__init__()
                self.setup_theme_awareness()

            def on_theme_changed(self, theme_id: str):
                # 自定义主题更新逻辑
                self.update_my_styles()

    注意：
        - 必须在__init__中调用setup_theme_awareness()
        - 可以重写on_theme_changed()方法自定义刷新逻辑
        - 组件销毁时会自动清理订阅
    """

    def setup_theme_awareness(self):
        """
        设置主题感知

        在组件初始化时调用此方法以订阅主题变更通知
        """
        if getattr(self, "_theme_awareness_registered", False):
            return

        from ur_print_fdm.ui.theme_manager import get_theme_manager

        self._theme_manager = get_theme_manager()
        self._theme_manager.add_listener(self.on_theme_changed)
        self._theme_awareness_registered = True

        # 如果组件有destroyed信号，自动清理
        if hasattr(self, "destroyed"):
            self.destroyed.connect(self.cleanup_theme_awareness)

    def on_theme_changed(self, theme_id: str):
        """
        主题变更回调（子类可重写）

        默认行为：
        - 如果有apply_theme方法，调用它
        - 如果有refresh_theme方法，调用它
        - 否则不做任何操作

        Args:
            theme_id: 新主题的ID
        """
        if hasattr(self, "apply_theme") and callable(getattr(self, "apply_theme")):
            self.apply_theme()
        elif hasattr(self, "refresh_theme") and callable(
            getattr(self, "refresh_theme")
        ):
            self.refresh_theme()

    def get_token(self, key: str, default: Any = None) -> Any:
        """
        便捷方法：获取主题令牌

        Args:
            key: 令牌键名
            default: 默认值

        Returns:
            令牌值
        """
        if hasattr(self, "_theme_manager"):
            return self._theme_manager.get_token(key, default)
        return default

    def get_current_theme_id(self) -> Optional[str]:
        """
        获取当前主题ID

        Returns:
            当前主题ID，如果未初始化则返回None
        """
        if hasattr(self, "_theme_manager"):
            return self._theme_manager.current_theme_id()
        return None

    def cleanup_theme_awareness(self, *args):
        """
        清理主题感知（在组件销毁时调用）

        通常不需要手动调用，组件销毁时会自动调用
        """
        if hasattr(self, "_theme_manager"):
            try:
                self._theme_manager.remove_listener(self.on_theme_changed)
                self._theme_awareness_registered = False
            except Exception:
                pass  # 可能已经移除
