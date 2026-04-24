from ur_print_fdm.ui.services.file_service import file_service


def test_file_service_write_and_read_roundtrip(tmp_path):
    target = tmp_path / "nested" / "demo.script"

    write_result = file_service.write_text(target, "hello")
    read_result = file_service.read_text(target)

    assert write_result.success is True
    assert read_result.success is True
    assert read_result.payload == "hello"


def test_file_service_read_missing_file_returns_failure(tmp_path):
    target = tmp_path / "missing.script"

    result = file_service.read_text(target)

    assert result.success is False
    assert str(target) in result.detail
