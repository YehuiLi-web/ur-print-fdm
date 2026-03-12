from ur_print_fdm.ui.workers.loader_binding import build_loader_binding_note


def test_loader_binding_note_mentions_urp_and_remote_loader_name():
    note = build_loader_binding_note("/programs/custom_loader.urp", "custom_remote.script")

    assert "/programs/custom_loader.urp" in note
    assert "custom_remote.script" in note
    assert "Dashboard 实际加载的是" in note
