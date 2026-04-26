from pathlib import Path
import gc

from ur_print_fdm.ui import theme
from ur_print_fdm.ui.theme_manager import get_theme_manager


def test_light_theme_qss_has_light_base_colors():
    qss = theme.get_light_theme().lower()
    assert "#f0f1f4" in qss
    assert "#1f2328" in qss


def test_light_theme_qss_does_not_use_dark_button_palette():
    qss = theme.get_light_theme().lower()
    # These were hard-coded for the dark theme and should never appear in the light theme.
    assert "#3c3c3c" not in qss
    assert "#505050" not in qss


def test_toolbar_separator_qss_draws_a_line_instead_of_filling_the_box():
    qss = theme.get_dark_theme().lower()
    section = qss.split("qtoolbar::separator {", 1)[1].split("}", 1)[0]
    assert "background: transparent;" in section
    assert "width: 2px;" in section
    assert "border-left: 1px solid" in section


def test_toolbar_group_qss_keeps_helper_containers_transparent():
    qss = theme.get_dark_theme().lower()
    assert 'qwidget#toolbarindicatorgroup,' in qss
    assert 'qwidget#toolbarcontrolgroup {' in qss
    group_section = qss.split('qwidget#toolbarindicatorgroup,', 1)[1].split("}", 1)[0]
    assert "background-color: transparent;" in group_section
    assert "border: none;" in group_section


def test_spinbox_qss_uses_compact_buttonless_style():
    qss = theme.get_dark_theme().lower()

    spin_section = qss.split("qspinbox, qdoublespinbox {", 1)[1].split("}", 1)[0]
    assert "padding: 0 8px 0 6px;" in spin_section
    assert "min-height: 20px;" in spin_section

    button_section = qss.split("qspinbox::up-button, qdoublespinbox::up-button,", 1)[1].split("}", 1)[0]
    assert "width: 0px;" in button_section
    assert "height: 0px;" in button_section
    assert "padding: 0px;" in button_section

    arrow_section = qss.split("qspinbox::up-arrow, qdoublespinbox::up-arrow,", 1)[1].split("}", 1)[0]
    assert "image: none;" in arrow_section


def test_fused_combo_qss_matches_compact_form_controls():
    qss = theme.get_dark_theme().lower()

    combo_section = qss.split('qframe[ui_role="fused_combo"] {', 1)[1].split("}", 1)[0]
    assert "min-height: 22px;" in combo_section

    focused_section = qss.split('qframe[ui_role="fused_combo"][focused="true"] {', 1)[1].split("}", 1)[0]
    assert "border: 1px solid #46464a;" in focused_section

    assert 'padding: 0 8px 0 6px;' in qss


def test_toolbar_combo_qss_uses_panel_fill_and_hides_join_border_when_expanded():
    qss = theme.get_dark_theme().lower()

    toolbar_section = qss.split('qframe[ui_role="fused_combo"][ui_variant="toolbar_combo"] {', 1)[1].split("}", 1)[0]
    assert "background-color: #1e1e1e;" in toolbar_section

    edit_host_section = qss.split('qframe[ui_role="fused_combo"][ui_variant="toolbar_combo"] qwidget[ui_role="fused_combo_edit_host"] {', 1)[1].split("}", 1)[0]
    assert "background-color: #1e1e1e;" in edit_host_section
    assert "border-top-left-radius: 6px;" in edit_host_section

    edit_section = qss.split('qframe[ui_role="fused_combo"][ui_variant="toolbar_combo"] qlineedit[ui_role="fused_combo_edit"] {', 1)[1].split("}", 1)[0]
    assert "background-color: transparent;" in edit_section

    expanded_below = qss.split('qframe[ui_role="fused_combo"][expanded="true"][popup_side="below"] {', 1)[1].split("}", 1)[0]
    assert "border-bottom: none;" in expanded_below

    popup_toolbar = qss.split('qframe[ui_role="fused_combo_popup_surface"][ui_variant="toolbar_combo"] {', 1)[1].split("}", 1)[0]
    assert "background-color: #1e1e1e;" in popup_toolbar


def test_fused_combo_popup_qss_uses_viewport_backing_and_side_specific_joining():
    qss = theme.get_dark_theme().lower()

    popup_section = qss.split('qframe[ui_role="fused_combo_popup_surface"] {', 1)[1].split("}", 1)[0]
    assert "background-color: #1e1e1e;" in popup_section
    assert "border: 1px solid #46464a;" in popup_section
    assert 'qframe[ui_role="fused_combo"][expanded="true"][popup_side="above"] {' in qss
    assert 'qframe[ui_role="fused_combo_popup_surface"][popup_side="below"] {' in qss
    assert 'qwidget[ui_role="fused_combo_popup_viewport"],' in qss

    item_section = qss.split('qframe[ui_role="fused_combo_popup_item"] {', 1)[1].split("}", 1)[0]
    assert "background: transparent;" in item_section

    selected_section = qss.split('qframe[ui_role="fused_combo_popup_item"][selected="true"] {', 1)[1].split("}", 1)[0]
    assert "background-color: #383838;" in selected_section
    assert "#264f78" not in selected_section


def test_dark_theme_qss_uses_absolute_icon_paths_for_tree_and_combo_arrows():
    qss = theme.get_dark_theme().lower()
    icons_dir = Path(__file__).resolve().parents[1] / "ui" / "resources" / "icons"
    collapse_icon = (icons_dir / "collapse.svg").resolve().as_posix().lower()
    expand_icon = (icons_dir / "expand.svg").resolve().as_posix().lower()

    assert f"image: url({collapse_icon});" in qss
    assert f"image: url({expand_icon});" in qss
    assert "image: url(ur_print_fdm/ui/resources/icons/collapse.svg);" not in qss
    assert "image: url(ur_print_fdm/ui/resources/icons/expand.svg);" not in qss


def test_light_theme_qss_uses_absolute_icon_paths_for_tree_and_combo_arrows():
    qss = theme.get_light_theme().lower()
    icons_dir = Path(__file__).resolve().parents[1] / "ui" / "resources" / "icons"
    collapse_icon = (icons_dir / "collapse_light.svg").resolve().as_posix().lower()
    expand_icon = (icons_dir / "expand_light.svg").resolve().as_posix().lower()

    assert f"image: url({collapse_icon});" in qss
    assert f"image: url({expand_icon});" in qss
    assert "image: url(ur_print_fdm/ui/resources/icons/collapse_light.svg);" not in qss
    assert "image: url(ur_print_fdm/ui/resources/icons/expand_light.svg);" not in qss


def test_theme_manager_drops_dead_bound_method_listeners():
    theme_mgr = get_theme_manager()

    class Listener:
        calls = 0

        def on_theme_changed(self, theme_id: str) -> None:
            self.calls += 1

    listener = Listener()
    theme_mgr.add_listener(listener.on_theme_changed)
    assert any(item.matches(listener.on_theme_changed) for item in theme_mgr._listeners)

    del listener
    gc.collect()

    theme_mgr.set_theme(theme_mgr.current_theme_id())

    assert all(item.get() is not None for item in theme_mgr._listeners)
