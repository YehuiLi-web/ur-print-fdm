from ur_print_fdm.core.sample_library_manager import SampleManager
from ur_print_fdm.plugins.bootstrap import bootstrap_plugins
from ur_print_fdm.samples.loader import load_samples


def test_load_samples_registers_legacy_samples():
    bootstrap_plugins()
    load_samples()
    assert len(SampleManager.get_all_samples()) >= 1
