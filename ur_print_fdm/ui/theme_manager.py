"""
主题管理器
统一管理应用程序的主题系统
"""

from __future__ import annotations
from typing import Dict, Callable, Optional, Any, List
from PyQt6.QtWidgets import QApplication


class ThemeDefinition:
    """主题定义"""

    def __init__(
        self,
        theme_id: str,
        name: str,
        tokens: Dict[str, Any],
        qss_generator: Callable[[Dict[str, Any]], str],
    ):
        self.id = theme_id
        self.name = name
        self.tokens = tokens
        self.qss_generator = qss_generator

    def generate_qss(self) -> str:
        """生成QSS样式表"""
        return self.qss_generator(self.tokens)


class ThemeManager:
    """
    统一主题管理器 - 单例模式

    职责：
    1. 管理主题令牌（tokens）和主题定义
    2. 提供主题切换功能
    3. 通知所有订阅者主题变更
    4. 支持主题导入/导出
    5. 管理主题缓存
    """

    _instance: Optional[ThemeManager] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._current_theme_id: str = "dark"
        self._themes: Dict[str, ThemeDefinition] = {}
        self._listeners: List[Callable[[str], None]] = []

        # 加载内置主题
        self._load_builtin_themes()
        self._initialized = True

    def _load_builtin_themes(self):
        """加载内置主题定义"""
        from ur_print_fdm.ui.themes import DARK, LIGHT, generate_qss

        self.register_theme(
            ThemeDefinition(
                theme_id="dark", name="暗色主题", tokens=DARK, qss_generator=generate_qss
            )
        )

        self.register_theme(
            ThemeDefinition(
                theme_id="light",
                name="白色主题",
                tokens=LIGHT,
                qss_generator=generate_qss,
            )
        )

    def register_theme(self, definition: ThemeDefinition):
        """注册主题"""
        self._themes[definition.id] = definition

    def add_listener(self, callback: Callable[[str], None]):
        """添加主题变更监听器"""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str], None]):
        """移除主题变更监听器"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def set_theme(self, theme_id: str) -> bool:
        """
        切换主题

        Args:
            theme_id: 主题ID

        Returns:
            是否切换成功
        """
        if theme_id not in self._themes:
            return False

        self._current_theme_id = theme_id
        theme_def = self._themes[theme_id]

        # 应用到QApplication
        app = QApplication.instance()
        if app:
            qss = theme_def.generate_qss()
            app.setStyleSheet(qss)
            app.setProperty("ui_theme", theme_id)

        # 清除图标缓存（因为图标颜色需要重新着色）
        try:
            from ur_print_fdm.ui.resources.icon_manager import IconManager

            IconManager.clear_cache()
        except Exception:
            pass  # IconManager可能还未初始化

        # 通知所有订阅者
        for listener in self._listeners:
            try:
                listener(theme_id)
            except Exception:
                pass  # 忽略监听器错误

        return True

    def current_theme_id(self) -> str:
        """获取当前主题ID"""
        return self._current_theme_id

    def current_tokens(self) -> Dict[str, Any]:
        """获取当前主题令牌"""
        if self._current_theme_id not in self._themes:
            # 如果当前主题不存在，返回深色主题
            return self._themes.get("dark", ThemeDefinition("", "", {}, lambda x: "")).tokens
        return self._themes[self._current_theme_id].tokens

    def get_token(self, key: str, default: Any = None) -> Any:
        """
        获取单个令牌值

        Args:
            key: 令牌键名
            default: 默认值

        Returns:
            令牌值
        """
        return self.current_tokens().get(key, default)

    def list_themes(self) -> List[ThemeDefinition]:
        """列出所有可用主题"""
        return list(self._themes.values())

    def get_theme(self, theme_id: str) -> Optional[ThemeDefinition]:
        """获取指定主题定义"""
        return self._themes.get(theme_id)


# 全局访问函数
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """
    获取主题管理器单例

    Returns:
        ThemeManager实例
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
