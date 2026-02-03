from ur_print_fdm.ui import theme


def test_light_theme_qss_has_light_base_colors():
    qss = theme.get_light_theme().lower()
    assert "#f7f7f9" in qss
    assert "#1f2328" in qss


def test_light_theme_qss_does_not_use_dark_button_palette():
    qss = theme.get_light_theme().lower()
    # These were hard-coded for the dark theme and should never appear in the light theme.
    assert "#3c3c3c" not in qss
    assert "#505050" not in qss
