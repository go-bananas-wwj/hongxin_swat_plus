"""Weather data preparation: CMFD processing, CDAT/All-sky merging, .cli generation."""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from tqdm import tqdm


class WeatherPreparator:
    """Prepare weather data for SWAT+ from multiple sources."""

    # CMFD unit conversion factors: (target_unit, multiplier)
    CMFD_CONVERSIONS = {
        "lrad": ("MJ/m2/day", 0.0864),
        "prec": ("mm/day", 86400.0),
        "rhum": ("fraction", 0.01),
        "srad": ("MJ/m2/day", 0.0864),
        "wind": ("m/s", 1.0),
        "pres": ("hPa", 1.0),  # keep as-is, may not be used by SWAT+
        "shum": ("kg/kg", 1.0),  # keep as-is
    }

    def __init__(self, config):
        self.cfg = config
        self.cmfd_dir = Path(config.get("weather.cmfd_dir"))
        self.cdat_dir = Path(config.get("weather.cdat_dir"))
        self.allsky_dir = Path(config.get("weather.allsky_dir"))
        self.variables = config.get("weather.variables", ["prec", "tmp"])
        self.grid_spacing = config.get("weather.grid_spacing_deg", 0.1)
        self.sim_period = config.get("project.simulation_period")
        self.workspace = Path(config.get("project.workspace")) / "weather"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.station_prefix = config.get("weather.station_prefix", "wx")
        self.station_padding = config.get("weather.station_padding", 3)

    def run(self) -> dict:
        """Run full weather preparation pipeline."""
        print("Step 1: Generate virtual weather stations")
        stations = self._generate_stations()
        stations_file = self.workspace / "weather_stations.csv"
        stations.to_csv(stations_file, index=False)
        print(f"  Saved {len(stations)} stations to {stations_file}")

        print("Step 2: Process CMFD data")
        self._process_cmfd(stations)

        print("Step 3: Process CDAT temperature (2012-2018)")
        self._process_cdat(stations)

        print("Step 4: Process All-sky temperature (2019-2022)")
        self._process_allsky(stations)

        print("Step 5: Merge temperature data")
        self._merge_temperature(stations)

        print("Step 6: Generate SWAT+ .cli files")
        cli_dir = self._write_cli_files(stations)

        return {"stations": stations, "cli_dir": cli_dir}

    def _generate_stations(self) -> pd.DataFrame:
        """Generate virtual weather station grid within watershed bounds."""
        # For now, generate grid over the full DEM extent
        # TODO: clip to actual watershed boundary after delineation
        dem_path = Path(self.cfg.get("basin.dem_path"))
        with rasterio.open(dem_path) as src:
            bounds = src.bounds
            crs = src.crs

        # Convert bounds to WGS84 for grid generation
        if crs.to_epsg() != 4326:
            import pyproj
            transformer = pyproj.Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
            left, bottom = transformer.transform(bounds.left, bounds.bottom)
            right, top = transformer.transform(bounds.right, bounds.top)
        else:
            left, bottom, right, top = bounds.left, bounds.bottom, bounds.right, bounds.top

        # Generate grid
        lons = np.arange(left, right + self.grid_spacing, self.grid_spacing)
        lats = np.arange(bottom, top + self.grid_spacing, self.grid_spacing)

        stations = []
        station_id = 1
        for lat in lats:
            for lon in lons:
                stations.append({
                    "id": f"{self.station_prefix}{station_id:0{self.station_padding}d}",
                    "lon": round(lon, 4),
                    "lat": round(lat, 4),
                })
                station_id += 1

        df = pd.DataFrame(stations)
        print(f"  Generated {len(df)} virtual stations ({len(lons)} x {len(lats)} grid)")
        return df

    def _process_cmfd(self, stations: pd.DataFrame):
        """Process CMFD variables (excluding temp)."""
        print(f"  Processing CMFD from {self.cmfd_dir}")

        for var in self.variables:
            if var not in self.CMFD_CONVERSIONS:
                print(f"  ⚠ Unknown variable: {var}, skipping")
                continue

            target_unit, multiplier = self.CMFD_CONVERSIONS[var]
            print(f"    {var} → {target_unit} (x{multiplier})")

            # Find all .nc files for this variable
            nc_files = sorted(self.cmfd_dir.glob(f"{var}_*.nc"))
            if not nc_files:
                print(f"    ⚠ No files found for {var}")
                continue

            print(f"    Found {len(nc_files)} files")
            # TODO: Open with xarray, crop to simulation period, extract at station locations

    def _process_cdat(self, stations: pd.DataFrame):
        """Extract Tmax/Tmin from CDAT GeoTIFFs."""
        if not self.cdat_dir.exists():
            print(f"  ⚠ CDAT directory not found: {self.cdat_dir}")
            return
        print(f"  Processing CDAT from {self.cdat_dir}")
        # TODO: Read daily GeoTIFFs, extract values at station locations

    def _process_allsky(self, stations: pd.DataFrame):
        """Extract Tmax/Tmin from All-sky GeoTIFFs (resample to 0.1deg)."""
        if not self.allsky_dir.exists():
            print(f"  ⚠ All-sky directory not found: {self.allsky_dir}")
            return
        print(f"  Processing All-sky from {self.allsky_dir}")
        # TODO: Read daily GeoTIFFs, resample to 0.1deg, extract values

    def _merge_temperature(self, stations: pd.DataFrame):
        """Merge CDAT (2012-18) + All-sky (2019-22) into continuous Tmax/Tmin."""
        print("  Merging temperature data sources")
        # TODO: Concatenate time series, handle overlaps

    def _write_cli_files(self, stations: pd.DataFrame) -> Path:
        """Write SWAT+ .cli format weather files."""
        cli_dir = self.workspace / "cli"
        cli_dir.mkdir(exist_ok=True)
        print(f"  Writing .cli files to {cli_dir}")
        # TODO: Implement SWAT+ .cli format writer
        return cli_dir
