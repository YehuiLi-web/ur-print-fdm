from __future__ import annotations

from ur_print_fdm.plugins.registry import PluginRegistry


class _GoodEstimator:
    id = "good_estimator"
    title = "Good Estimator"

    def estimate(self, trajectory):  # pragma: no cover - not exercised in registry tests
        raise NotImplementedError


class _DuplicateEstimator:
    id = "dup_estimator"
    title = "Duplicate Estimator"

    def estimate(self, trajectory):  # pragma: no cover - not exercised in registry tests
        raise NotImplementedError


class _DuplicateEstimator2:
    id = "dup_estimator"
    title = "Duplicate Estimator (2)"

    def estimate(self, trajectory):  # pragma: no cover - not exercised in registry tests
        raise NotImplementedError


def test_load_entry_points_skips_failures(monkeypatch):
    import ur_print_fdm.plugins.registry as registry_module

    reg = PluginRegistry()

    class _BadEp:
        group = "ur_print_fdm.time_estimators"
        name = "bad"

        def load(self):
            raise RuntimeError("boom")

    class _GoodEp:
        group = "ur_print_fdm.time_estimators"
        name = "good"

        def load(self):
            return _GoodEstimator

    def _fake_iter(group: str):
        if group == "ur_print_fdm.time_estimators":
            return [_BadEp(), _GoodEp()]
        return []

    monkeypatch.setattr(registry_module, "_iter_entry_points", _fake_iter)

    failures = reg.load_entry_points()
    assert "good_estimator" in reg.estimators
    assert "ur_print_fdm.time_estimators:bad" in failures


def test_load_entry_points_does_not_override_existing_ids(monkeypatch):
    import ur_print_fdm.plugins.registry as registry_module

    reg = PluginRegistry()
    reg.register_estimator(_DuplicateEstimator())

    class _DupEp:
        group = "ur_print_fdm.time_estimators"
        name = "dup"

        def load(self):
            return _DuplicateEstimator2

    def _fake_iter(group: str):
        if group == "ur_print_fdm.time_estimators":
            return [_DupEp()]
        return []

    monkeypatch.setattr(registry_module, "_iter_entry_points", _fake_iter)

    failures = reg.load_entry_points()
    assert failures == []
    assert reg.estimators["dup_estimator"].title == _DuplicateEstimator.title

