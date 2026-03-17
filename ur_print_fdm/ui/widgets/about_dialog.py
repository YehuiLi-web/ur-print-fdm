from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from ur_print_fdm import __version__
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui.theme_manager import get_theme_manager


def _hex_to_rgba(color: str, alpha: int) -> str:
    """Convert #RRGGBB colors to rgba() strings for QSS."""
    value = (color or "").lstrip("#")
    if len(value) != 6:
        return color
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"


class AboutDialog(QDialog):
    """Compact product-style About dialog for ur-print-fdm."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aboutDialog")
        self.setWindowTitle("关于 ur-print-fdm")
        self.setModal(True)
        self.setFixedSize(660, 252)
        self.setWindowIcon(IconManager.get_svg_icon("app_icon", size=(24, 24)))

        self._init_ui()
        self.apply_theme()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)
        layout.addWidget(self._build_hero_card())

    def _build_hero_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("aboutHeroCard")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(18)

        logo_wrap = QFrame()
        logo_wrap.setObjectName("aboutLogoWrap")
        logo_wrap.setFixedSize(108, 108)
        logo_layout = QVBoxLayout(logo_wrap)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(0)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.logo_label = QLabel()
        self.logo_label.setObjectName("aboutLogoLabel")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = IconManager.get_svg_icon("app_icon", size=(56, 56))
        pixmap = icon.pixmap(56, 56)
        if pixmap.isNull():
            self.logo_label.setText("UF")
        else:
            self.logo_label.setPixmap(pixmap)
        logo_layout.addWidget(self.logo_label)

        layout.addWidget(logo_wrap, 0, Qt.AlignmentFlag.AlignVCenter)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.setSpacing(10)

        eyebrow = QLabel("UR Print FDM Control Suite")
        eyebrow.setObjectName("aboutEyebrow")
        content_layout.addWidget(eyebrow)

        self.product_name_label = QLabel("ur-print-fdm")
        self.product_name_label.setObjectName("aboutProductName")
        content_layout.addWidget(self.product_name_label)

        self.subtitle_label = QLabel(
            "面向 Universal Robots 的打印控制、轨迹执行与工艺调试软件"
        )
        self.subtitle_label.setObjectName("aboutSubtitle")
        self.subtitle_label.setWordWrap(True)
        content_layout.addWidget(self.subtitle_label)

        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 6, 0, 0)
        badge_row.setSpacing(10)
        badge_row.addWidget(self._build_badge(f"v{__version__}", "aboutVersionBadge"))
        badge_row.addWidget(self._build_badge("PyQt6 + ur_rtde", "aboutStackBadge"))
        badge_row.addStretch()
        content_layout.addLayout(badge_row)

        content_layout.addStretch()
        layout.addLayout(content_layout, 1)
        return card

    @staticmethod
    def _build_badge(text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        return label

    def apply_theme(self) -> None:
        t = get_theme_manager().current_tokens()
        accent_fill = _hex_to_rgba(t.get("accent_blue", "#2196F3"), 18)
        accent_border = _hex_to_rgba(t.get("accent_blue", "#2196F3"), 96)
        logo_fill = _hex_to_rgba(t.get("accent_blue", "#2196F3"), 20)
        hero_glow = _hex_to_rgba(t.get("accent_link", "#569CD6"), 24)

        self.setStyleSheet(
            f"""
            QDialog#aboutDialog {{
                background-color: {t.get("bg_panel", "#2d2d2d")};
            }}
            QFrame#aboutHeroCard {{
                background-color: {t.get("bg_main", "#2b2b2b")};
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {hero_glow},
                    stop:0.28 {t.get("bg_main", "#2b2b2b")},
                    stop:1 {t.get("bg_tertiary", "#252526")}
                );
                border: 1px solid {t.get("border_light", "#46464a")};
                border-radius: 18px;
            }}
            QFrame#aboutLogoWrap {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {logo_fill},
                    stop:1 {t.get("bg_secondary", "#1e1e1e")}
                );
                border: 1px solid {accent_border};
                border-radius: 24px;
            }}
            QLabel#aboutLogoLabel {{
                color: {t.get("text", "#e0e0e0")};
                font-size: 24px;
                font-weight: 700;
                border: none;
                background: transparent;
            }}
            QLabel#aboutEyebrow {{
                color: {t.get("text_muted", "#8a8a8a")};
                font-size: 12px;
                font-weight: 600;
                border: none;
                background: transparent;
            }}
            QLabel#aboutProductName {{
                color: {t.get("text", "#e0e0e0")};
                font-size: 32px;
                font-weight: 700;
                border: none;
                background: transparent;
            }}
            QLabel#aboutSubtitle {{
                color: {t.get("text", "#e0e0e0")};
                font-size: 14px;
                line-height: 1.45;
                border: none;
                background: transparent;
            }}
            QLabel#aboutVersionBadge,
            QLabel#aboutStackBadge {{
                color: {t.get("text", "#e0e0e0")};
                background-color: {accent_fill};
                border: 1px solid {accent_border};
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            """
        )
