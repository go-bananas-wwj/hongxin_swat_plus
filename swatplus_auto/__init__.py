"""SWAT+ Auto: A config-driven, reusable framework for SWAT+ watershed modeling."""

from pathlib import Path

from .config import ConfigValidator

__version__ = "0.1.0"
__all__ = ["Workflow", "ConfigValidator"]


class Workflow:
    """Main workflow orchestrator for SWAT+ modeling."""

    STEPS = [
        "delineation",
        "hru",
        "weather",
        "txtinout",
        "run",
        "calibrate",
    ]

    def __init__(self, config):
        if isinstance(config, (str, Path)):
            self.config = ConfigValidator(config)
        else:
            self.config = config

    def run(self, step="all"):
        """Run a specific step or all steps."""
        if step == "all":
            for s in self.STEPS:
                self._run_step(s)
        elif step in self.STEPS:
            self._run_step(step)
        else:
            raise ValueError(f"Unknown step: {step}. Available: {', '.join(self.STEPS)}")

    def _run_step(self, step):
        print(f"\n{'='*60}")
        print(f"Running step: {step}")
        print(f"{'='*60}")

        if step == "delineation":
            from .delineation import Delineator
            d = Delineator(self.config)
            d.run()
        elif step == "hru":
            from .hru_generator import HRUGenerator
            h = HRUGenerator(self.config)
            h.run()
        elif step == "weather":
            from .weather_prep import WeatherPreparator
            w = WeatherPreparator(self.config)
            w.run()
        elif step == "txtinout":
            from .txtinout_writer import TxtInOutWriter
            t = TxtInOutWriter(self.config)
            t.run()
        elif step == "run":
            from .model_runner import ModelRunner
            m = ModelRunner(self.config)
            m.run()
        elif step == "calibrate":
            from .calibrator import Calibrator
            c = Calibrator(self.config)
            c.run()

    @classmethod
    def from_config(cls, config_path):
        return cls(config_path)
