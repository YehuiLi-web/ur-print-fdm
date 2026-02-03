"""
图标管理器 - 统一管理应用程序中的所有图标
提供基于 Qt 标准图标的跨平台图标解决方案
"""
import os
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import QStyle, QApplication
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray, Qt


class IconManager:
    """统一的图标管理系统"""

    # 文件类型到图标的映射
    FILE_TYPE_ICONS = {
        # Python 文件
        '.py': QStyle.StandardPixmap.SP_FileDialogDetailedView,
        '.pyw': QStyle.StandardPixmap.SP_FileDialogDetailedView,
        '.pyc': QStyle.StandardPixmap.SP_FileDialogDetailedView,

        # 脚本文件
        '.script': QStyle.StandardPixmap.SP_FileDialogListView,
        '.urp': QStyle.StandardPixmap.SP_FileDialogContentsView,

        # 文本文件
        '.txt': QStyle.StandardPixmap.SP_FileIcon,
        '.md': QStyle.StandardPixmap.SP_FileIcon,
        '.log': QStyle.StandardPixmap.SP_FileIcon,

        # 配置文件
        '.json': QStyle.StandardPixmap.SP_FileDialogInfoView,
        '.yaml': QStyle.StandardPixmap.SP_FileDialogInfoView,
        '.yml': QStyle.StandardPixmap.SP_FileDialogInfoView,
        '.xml': QStyle.StandardPixmap.SP_FileDialogInfoView,
        '.ini': QStyle.StandardPixmap.SP_FileDialogInfoView,
        '.cfg': QStyle.StandardPixmap.SP_FileDialogInfoView,

        # 默认文件图标
        'default': QStyle.StandardPixmap.SP_FileIcon,
    }

    # 操作到图标的映射
    ACTION_ICONS = {
        'open': QStyle.StandardPixmap.SP_DialogOpenButton,
        'delete': QStyle.StandardPixmap.SP_TrashIcon,
        'rename': QStyle.StandardPixmap.SP_FileDialogDetailedView,
        'copy': QStyle.StandardPixmap.SP_FileDialogListView,
        'copy_path': QStyle.StandardPixmap.SP_DialogSaveButton,
        'refresh': QStyle.StandardPixmap.SP_BrowserReload,
        'new_file': QStyle.StandardPixmap.SP_FileIcon,
        'new_folder': QStyle.StandardPixmap.SP_DirIcon,
        'open_explorer': QStyle.StandardPixmap.SP_DirOpenIcon,
        'collapse': QStyle.StandardPixmap.SP_TitleBarShadeButton,
        'expand': QStyle.StandardPixmap.SP_TitleBarUnshadeButton,
        'search': QStyle.StandardPixmap.SP_FileDialogEnd,
    }

    _icon_cache = {}  # 图标缓存

    # SVG图标文件路径映射
    SVG_ICONS = {
        'tree_expand': 'icons/expand.svg',
        'tree_collapse': 'icons/collapse.svg',
        'new_file': 'icons/new_file.svg',
        'new_folder': 'icons/new_folder.svg',
        'refresh': 'icons/refresh.svg',
        'collapse_all': 'icons/collapse_all.svg',
        # 专业图标（替代 emoji）
        'folder': 'icons/folder.svg',
        'robot': 'icons/robot.svg',
        'log': 'icons/log.svg',
        'queue': 'icons/queue.svg',
        'play': 'icons/play.svg',
        'pause': 'icons/pause.svg',
        'stop': 'icons/stop.svg',
        'save': 'icons/save.svg',
        'add': 'icons/add.svg',
        'trash': 'icons/trash.svg',
        'search': 'icons/search.svg',
        'home': 'icons/home.svg',
        'calculator': 'icons/calculator.svg',
        'library': 'icons/library.svg',
        'target': 'icons/target.svg',
        'settings': 'icons/settings.svg',
        'help': 'icons/help.svg',
        'recent': 'icons/recent.svg',
        'edit': 'icons/edit.svg',
        'reconnect': 'icons/refresh.svg',
        'app_icon': 'icons/app_icon.svg',
        'upload': 'icons/upload.svg',
    }

    @classmethod
    def get_svg_icon(cls, icon_name: str, size: tuple = (16, 16), *, color: str | None = None, tint: bool = True) -> QIcon:
        """
        从SVG文件加载图标

        Args:
            icon_name: SVG图标名称（如 'tree_expand', 'tree_collapse'）
            size: 图标尺寸，默认为 (16, 16)

        Returns:
            QIcon: SVG图标对象
        """
        # Some SVGs intentionally contain multiple colors (e.g. app icon) and should not be tinted.
        if icon_name in {"app_icon"}:
            tint = False

        effective_color = color
        if tint and not effective_color:
            try:
                from ur_print_fdm.ui import theme

                t = theme.current_tokens()
                effective_color = str(t.get("icon") or t.get("text_muted") or t.get("text") or "#d4d4d4")
            except Exception:
                effective_color = "#d4d4d4"

        cache_key = f"svg_{icon_name}_{size[0]}x{size[1]}_{effective_color}_{int(tint)}"
        if cache_key in cls._icon_cache:
            return cls._icon_cache[cache_key]

        # 获取SVG文件路径
        svg_relative_path = cls.SVG_ICONS.get(icon_name)
        if not svg_relative_path:
            return QIcon()  # 返回空图标

        # 构建完整路径
        resources_dir = Path(__file__).parent
        svg_path = resources_dir / svg_relative_path

        if not svg_path.exists():
            return QIcon()

        # 读取SVG内容
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # 使用QSvgRenderer渲染SVG
            renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
            pixmap = QPixmap(size[0], size[1])
            # 使用完全透明背景，避免深色主题下出现黑底
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            renderer.render(painter)
            painter.end()

            if tint and effective_color:
                pixmap = cls._tint_pixmap(pixmap, QColor(effective_color))

            icon = QIcon(pixmap)
            cls._icon_cache[cache_key] = icon
            return icon
        except Exception as e:
            print(f"Error loading SVG icon {icon_name}: {e}")
            return QIcon()

    @staticmethod
    def _tint_pixmap(pixmap: QPixmap, color: QColor) -> QPixmap:
        """Tint a pixmap using its alpha mask (monochrome icon rendering)."""
        tinted = QPixmap(pixmap.size())
        tinted.fill(Qt.GlobalColor.transparent)

        painter = QPainter(tinted)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        return tinted

    @classmethod
    def get_file_icon(cls, file_path: str) -> QIcon:
        """
        根据文件路径获取对应的文件类型图标

        Args:
            file_path: 文件路径

        Returns:
            QIcon: 对应的图标对象
        """
        # 获取文件扩展名
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        # 从缓存中获取
        cache_key = f"file_{ext}"
        if cache_key in cls._icon_cache:
            return cls._icon_cache[cache_key]

        # 获取对应的标准图标
        pixmap = cls.FILE_TYPE_ICONS.get(ext, cls.FILE_TYPE_ICONS['default'])
        icon = cls._get_standard_icon(pixmap)

        # 缓存图标
        cls._icon_cache[cache_key] = icon
        return icon

    @classmethod
    def get_folder_icon(cls, is_expanded: bool = False) -> QIcon:
        """
        获取文件夹图标

        Args:
            is_expanded: 是否展开状态

        Returns:
            QIcon: 文件夹图标
        """
        cache_key = f"folder_{'open' if is_expanded else 'closed'}"
        if cache_key in cls._icon_cache:
            return cls._icon_cache[cache_key]

        pixmap = QStyle.StandardPixmap.SP_DirOpenIcon if is_expanded else QStyle.StandardPixmap.SP_DirClosedIcon
        icon = cls._get_standard_icon(pixmap)

        cls._icon_cache[cache_key] = icon
        return icon

    @classmethod
    def get_action_icon(cls, action_name: str) -> QIcon:
        """
        获取操作图标（优先尝试加载自定义 SVG，失败则回退到标准图标）
        """
        # 1. 尝试作为 SVG 加载
        if action_name in cls.SVG_ICONS:
            return cls.get_svg_icon(action_name)

        # 2. 如果没有对应的 SVG，回退到标准图标映射
        cache_key = f"action_{action_name}"
        if cache_key in cls._icon_cache:
            return cls._icon_cache[cache_key]

        pixmap = cls.ACTION_ICONS.get(action_name, QStyle.StandardPixmap.SP_FileIcon)
        icon = cls._get_standard_icon(pixmap)

        cls._icon_cache[cache_key] = icon
        return icon

    @staticmethod
    def _get_standard_icon(pixmap: QStyle.StandardPixmap) -> QIcon:
        """
        从 Qt 标准图标获取 QIcon 对象

        Args:
            pixmap: Qt 标准图标枚举值

        Returns:
            QIcon: 图标对象
        """
        app = QApplication.instance()
        if app is None:
            # 如果没有 QApplication 实例，返回空图标
            return QIcon()

        style = app.style()
        return style.standardIcon(pixmap)

    @classmethod
    def clear_cache(cls):
        """清空图标缓存"""
        cls._icon_cache.clear()


# 便捷函数
def get_file_icon(file_path: str) -> QIcon:
    """获取文件图标的便捷函数"""
    return IconManager.get_file_icon(file_path)


def get_folder_icon(is_expanded: bool = False) -> QIcon:
    """获取文件夹图标的便捷函数"""
    return IconManager.get_folder_icon(is_expanded)


def get_action_icon(action_name: str) -> QIcon:
    """获取操作图标的便捷函数"""
    return IconManager.get_action_icon(action_name)


def get_svg_icon(icon_name: str, size: tuple = (16, 16)) -> QIcon:
    """获取SVG图标的便捷函数"""
    return IconManager.get_svg_icon(icon_name, size)
