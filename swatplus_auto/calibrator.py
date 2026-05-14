"""Model calibration interface (placeholder)."""

from pathlib import Path


class Calibrator:
    """Calibrate SWAT+ model parameters against observed data."""

    def __init__(self, config):
        self.cfg = config
        self.enabled = config.get("calibration.enabled", False)
        self.method = config.get("calibration.method", "sufi2")
        self.observed_dir = Path(config.get("calibration.observed_flow_dir", "./data/hydrology"))

    def run(self) -> dict:
        """Run calibration if enabled and data is available."""
        if not self.enabled:
            print("Calibration is disabled in config.")
            return {}

        if not self.observed_dir.exists():
            print(f"Observed flow data not found: {self.observed_dir}")
            print("Skipping calibration.")
            return {}

        print(f"Running calibration with method: {self.method}")
        print("  [TODO] Implement calibration algorithm")
        return {}
