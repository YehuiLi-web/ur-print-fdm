from ur_print_fdm.core.sample_library_manager import SampleManager
from .standard_samples import FlatPlateSample, CircularRingSample

# Automatically register standard samples
SampleManager.register(FlatPlateSample())
SampleManager.register(CircularRingSample())
