import json
import threading

from ur_print_fdm.config.manager import ConfigManager

def test_default_config():
    defaults = {"robot": {"ip": "127.0.0.1", "port": 50004}}
    cm = ConfigManager(defaults=defaults)
    assert cm.get("robot.ip") == "127.0.0.1"
    assert cm.get("robot.port") == 50004
    assert cm.get("nonexistent", "fallback") == "fallback"

def test_load_config(tmp_path):
    config_file = tmp_path / "config.json"
    data = {"robot": {"ip": "192.168.1.100"}}
    config_file.write_text(json.dumps(data))

    defaults = {"robot": {"ip": "127.0.0.1", "port": 50004}, "ui": {"theme": "dark"}}
    cm = ConfigManager(config_path=config_file, defaults=defaults)

    # Merged value
    assert cm.get("robot.ip") == "192.168.1.100"
    # Default value (missing in file)
    assert cm.get("robot.port") == 50004
    assert cm.get("ui.theme") == "dark"

def test_save_config(tmp_path):
    config_file = tmp_path / "config.json"
    cm = ConfigManager(config_path=config_file, defaults={"a": 1})
    cm.set("b.c", 2)
    cm.save()

    with open(config_file, "r") as f:
        data = json.load(f)
    assert data["a"] == 1
    assert data["b"]["c"] == 2

def test_recursive_merge():
    defaults = {"a": {"b": 1, "c": 2}}
    cm = ConfigManager(defaults=defaults)
    cm._merge_config({"a": {"b": 10}})
    assert cm.get("a.b") == 10
    assert cm.get("a.c") == 2

def test_thread_safety():
    cm = ConfigManager(defaults={"counter": 0})
    def increment():
        for _ in range(100):
            val = cm.get("counter")
            cm.set("counter", val + 1)

    threads = [threading.Thread(target=increment) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert isinstance(cm.get("counter"), int)
