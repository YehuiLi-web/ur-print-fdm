from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class SampleParameter:
    name: str  # Unique identifier for the parameter
    label: str # Display name
    default: Any
    param_type: type # float, int, bool, str
    min_val: float = 0.0
    max_val: float = 1000.0
    unit: str = ""
    decimals: int = 2
    description: str = ""

class SampleBase(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def title(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    def instructions(self) -> str:
        return ""

    @property
    def nozzle_recommendation(self) -> str:
        return ""

    @property
    def precautions(self) -> str:
        return ""

    @abstractmethod
    def get_parameters(self) -> List[SampleParameter]:
        pass

    @abstractmethod
    def generate_script(self, params: Dict[str, Any], context: Any = None) -> str:
        """
        Generate the URScript.
        params: dictionary of parameter values keyed by parameter name
        context: optional context object (e.g. print_lib instance)
        """
        pass

class SampleManager:
    _samples: Dict[str, SampleBase] = {}

    @classmethod
    def register(cls, sample: SampleBase):
        cls._samples[sample.id] = sample

    @classmethod
    def get_sample(cls, sample_id: str) -> Optional[SampleBase]:
        return cls._samples.get(sample_id)

    @classmethod
    def get_all_samples(cls) -> List[SampleBase]:
        return list(cls._samples.values())
