from ur_print_fdm.shared.net import is_valid_ip


def test_is_valid_ip():
    assert is_valid_ip("127.0.0.1") is True
    assert is_valid_ip("192.168.1.10") is True
    assert is_valid_ip("999.1.1.1") is False
    assert is_valid_ip("not_an_ip") is False

