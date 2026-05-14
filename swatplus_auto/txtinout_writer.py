"""Generate SWAT+ TxtInOut configuration files."""

from pathlib import Path


class TxtInOutWriter:
    """Write all SWAT+ input files in TxtInOut format."""

    def __init__(self, config):
        self.cfg = config
        self.workspace = Path(config.get("project.workspace"))
        self.txtinout = self.workspace / "TxtInOut"
        self.txtinout.mkdir(parents=True, exist_ok=True)

    def run(self) -> Path:
        """Generate complete TxtInOut directory."""
        print("Step 1: Write file.cio")
        self._write_file_cio()

        print("Step 2: Write subbasin files")
        self._write_subbasin_files()

        print("Step 3: Write HRU files")
        self._write_hru_files()

        print("Step 4: Write channel/aquifer files")
        self._write_channel_files()

        print("Step 5: Write reservoir files")
        self._write_reservoir_files()

        print("Step 6: Copy weather .cli files")
        self._copy_weather_files()

        return self.txtinout

    def _write_file_cio(self):
        print("  [TODO] Implement file.cio writer")

    def _write_subbasin_files(self):
        print("  [TODO] Implement .sub file writer")

    def _write_hru_files(self):
        print("  [TODO] Implement .hru/.mgt/.sol/.gw writers")

    def _write_channel_files(self):
        print("  [TODO] Implement .cha/.aqu writers")

    def _write_reservoir_files(self):
        print("  [TODO] Implement reservoir file writer")

    def _copy_weather_files(self):
        print("  [TODO] Copy weather .cli files to TxtInOut")
