"""Configuration validation and defaults for SWAT+ Auto."""

from pathlib import Path
from typing import Any, Optional

import yaml


DEFAULTS = {
    "project": {
        "name": "swatplus_project",
        "workspace": "./workspace",
        "simulation_period": [2000, 2020],
        "warmup_years": 2,
    },
    "basin": {
        "threshold_area_km2": 50,
        "projection": "EPSG:4326",
    },
    "weather": {
        "grid_spacing_deg": 0.1,
        "variables": ["prec", "tmp"],
    },
    "model": {
        "output_variables": ["flo_out"],
    },
}


class ConfigValidator:
    """Validates and fills defaults for SWAT+ configuration."""

    REQUIRED_SECTIONS = ["project", "basin", "weather"]
    REQUIRED_BASIN_KEYS = ["dem_path", "landuse_path", "soil_path", "outlet_coords"]

    def __init__(self, config_path: str | Path):
        self.path = Path(config_path)
        self.raw = self._load_raw()
        self.validated = self._validate()

    def _load_raw(self) -> dict:
        with open(self.path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _validate(self) -> dict:
        cfg = self._deep_merge(DEFAULTS.copy(), self.raw)

        # Check required sections
        for section in self.REQUIRED_SECTIONS:
            if section not in cfg:
                raise ValueError(f"Missing required section: '{section}'")

        # Check required basin keys
        basin = cfg.get("basin", {})
        for key in self.REQUIRED_BASIN_KEYS:
            if key not in basin:
                raise ValueError(f"Missing required basin key: '{key}'")

        # Validate paths exist
        for key in ["dem_path", "landuse_path", "soil_path"]:
            path = Path(basin[key])
            if not path.exists():
                # Try relative to config file
                rel_path = self.path.parent / path
                if rel_path.exists():
                    basin[key] = str(rel_path)
                else:
                    raise FileNotFoundError(f"Basin file not found: {path}")

        # Validate simulation period
        sim_period = cfg["project"]["simulation_period"]
        if len(sim_period) != 2 or sim_period[0] >= sim_period[1]:
            raise ValueError("simulation_period must be [start_year, end_year] with start < end")

        # Validate outlet_coords
        coords = basin["outlet_coords"]
        if len(coords) != 2:
            raise ValueError("outlet_coords must be [lon, lat]")

        return cfg

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Recursively merge override into base."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigValidator._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def save(self, output_path: Optional[str | Path] = None) -> Path:
        """Save validated config to YAML."""
        path = Path(output_path or self.path)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.validated, f, default_flow_style=False, allow_unicode=True)
        return path

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self.validated
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
