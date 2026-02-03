from ur_print_fdm.config.manager import ConfigManager


def test_apply_dict_resets_to_defaults_and_merges(tmp_path):
    defaults = {"a": {"b": 1, "c": 2}, "ui": {"x": 10}}
    cm = ConfigManager(config_path=tmp_path / "config.json", defaults=defaults)
    cm.set("a.b", 999)

    cm.apply_dict({"a": {"b": 5}, "extra": {"k": "v"}})
    assert cm.get("a.b") == 5
    assert cm.get("a.c") == 2  # from defaults (reset)
    assert cm.get("ui.x") == 10  # from defaults (reset)
    assert cm.get("extra.k") == "v"  # unknown keys preserved

