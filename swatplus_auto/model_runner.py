"""Run SWAT+ model and validate outputs."""

import subprocess
from pathlib import Path


class ModelRunner:
    """Execute SWAT+ simulation and check results."""

    def __init__(self, config):
        self.cfg = config
        self.executable = Path(config.get("model.swatplus_executable", "./swatplus"))
        self.txtinout = Path(config.get("project.workspace")) / "TxtInOut"

    def run(self) -> dict:
        """Run SWAT+ and validate outputs."""
        print("Step 1: Check TxtInOut exists")
        if not self.txtinout.exists():
            raise FileNotFoundError(f"TxtInOut not found: {self.txtinout}")

        print("Step 2: Run SWAT+")
        self._execute()

        print("Step 3: Check outputs")
        results = self._validate_outputs()

        print("Step 4: Water balance check")
        self._water_balance_check()

        return results

    def _execute(self):
        cmd = [str(self.executable)]
        subprocess.run(cmd, cwd=self.txtinout, check=True)

    def _validate_outputs(self) -> dict:
        print("  [TODO] Validate output files exist and are non-empty")
        return {}

    def _water_balance_check(self):
        print("  [TODO] Check precipitation = ET + runoff + recharge + delta_storage")
