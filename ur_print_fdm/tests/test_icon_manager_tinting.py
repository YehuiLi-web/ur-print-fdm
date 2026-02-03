from PyQt6.QtWidgets import QApplication


def _first_visible_rgb(pixmap):
    img = pixmap.toImage()
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() >= 200:  # prefer non-antialiased pixels for stable assertions
                return c.red(), c.green(), c.blue()
    # Fall back to any non-transparent pixel
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() > 0:
                return c.red(), c.green(), c.blue()
    raise AssertionError("No visible pixels found in pixmap")


def test_svg_icon_can_be_tinted_with_explicit_color():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.resources.icon_manager import IconManager

    icon = IconManager.get_svg_icon("settings", size=(24, 24), color="#ff0000")
    r, g, b = _first_visible_rgb(icon.pixmap(24, 24))
    assert r >= 200 and g <= 80 and b <= 80


def test_svg_icon_defaults_to_theme_icon_color():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui import theme
    from ur_print_fdm.ui.resources.icon_manager import IconManager

    theme.apply_app_theme(use_dark=False)  # light theme
    icon = IconManager.get_svg_icon("settings", size=(24, 24))
    r, g, b = _first_visible_rgb(icon.pixmap(24, 24))

    # LIGHT theme icon color is "#57606a" -> (87, 96, 106)
    assert abs(r - 87) <= 25
    assert abs(g - 96) <= 25
    assert abs(b - 106) <= 25
