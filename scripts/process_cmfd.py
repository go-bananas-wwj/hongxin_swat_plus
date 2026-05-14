#!/usr/bin/env python3
"""Process CMFD data: crop to basin, unit conversion, extract to stations, write .cli."""

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from tqdm import tqdm

# Configuration
CMFD_DIR = Path("/workspace/hongxin_swaw_plus/data/01_raw/cmfd_v2_daily/nc_files")
WATERSHED_TIF = Path("/workspace/hongxin_swaw_plus/workspace/watershed.tif")
OUTPUT_DIR = Path("/workspace/hongxin_swaw_plus/data/02_processed/weather_stations")
SIM_PERIOD = (2012, 2022)
GRID_SPACING = 0.1

CONVERSIONS = {
    "lrad": ("MJ/m2/day", 0.0864),
    "prec": ("mm/day", 86400.0),
    "rhum": ("fraction", 0.01),
    "srad": ("MJ/m2/day", 0.0864),
    "wind": ("m/s", 1.0),
    "pres": ("hPa", 1.0),
    "shum": ("kg/kg", 1.0),
}

VARIABLES = ["lrad", "prec", "rhum", "srad", "wind"]


def get_watershed_bounds():
    with rasterio.open(WATERSHED_TIF) as src:
        bounds = src.bounds
        import pyproj
        transformer = pyproj.Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
        left, bottom = transformer.transform(bounds.left, bounds.bottom)
        right, top = transformer.transform(bounds.right, bounds.top)
    return left, bottom, right, top


def generate_stations():
    left, bottom, right, top = get_watershed_bounds()
    lons = np.arange(np.floor(left / GRID_SPACING) * GRID_SPACING,
                     np.ceil(right / GRID_SPACING) * GRID_SPACING + GRID_SPACING,
                     GRID_SPACING)
    lats = np.arange(np.floor(bottom / GRID_SPACING) * GRID_SPACING,
                     np.ceil(top / GRID_SPACING) * GRID_SPACING + GRID_SPACING,
                     GRID_SPACING)

    stations = []
    sid = 1
    for lat in lats:
        for lon in lons:
            if left <= lon <= right and bottom <= lat <= top:
                stations.append({"id": f"wx{sid:03d}", "lon": round(lon, 4), "lat": round(lat, 4)})
                sid += 1

    df = pd.DataFrame(stations)
    print(f"Generated {len(df)} virtual stations")
    return df


def process_variable(var: str, stations: pd.DataFrame):
    if var not in CONVERSIONS:
        return

    target_unit, multiplier = CONVERSIONS[var]
    print(f"\nProcessing {var} → {target_unit} (x{multiplier})")

    # Find files within simulation period
    nc_files = sorted(CMFD_DIR.glob(f"{var}_*.nc"))
    filtered = []
    for f in nc_files:
        year_range = f.stem.split("_")[-1]
        start_year, end_year = int(year_range[:4]), int(year_range[7:11])
        if end_year >= SIM_PERIOD[0] and start_year <= SIM_PERIOD[1]:
            filtered.append(str(f))

    if not filtered:
        print(f"  ⚠ No files found")
        return

    print(f"  Opening {len(filtered)} files...")

    # Open all files at once with xarray
    ds = xr.open_mfdataset(filtered, combine="nested", concat_dim="time", parallel=False)

    # Find the actual variable name
    data_var = None
    for v in ds.data_vars:
        if v.lower() == var.lower() or v.startswith(var):
            data_var = v
            break

    if data_var is None:
        print(f"  ⚠ Variable not found in dataset")
        ds.close()
        return

    # Crop to simulation period
    ds = ds.sel(time=slice(f"{SIM_PERIOD[0]}-01-01", f"{SIM_PERIOD[1]}-12-31"))

    # Vectorized extraction at all stations
    lons = xr.DataArray(stations["lon"].values, dims="station")
    lats = xr.DataArray(stations["lat"].values, dims="station")

    print(f"  Extracting at {len(stations)} stations...")
    extracted = ds[data_var].sel(lon=lons, lat=lats, method="nearest")

    # Apply unit conversion
    extracted = extracted * multiplier

    # Convert to DataFrame
    print(f"  Converting to DataFrame...")
    df = extracted.to_dataframe(name=var).reset_index()
    df = df[["time", "station", var]]
    df["station_id"] = stations.iloc[df["station"].values]["id"].values
    df = df[["time", "station_id", var]]

    ds.close()

    # Save per station
    var_dir = OUTPUT_DIR / var
    var_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Saving station files...")
    for station_id, group in tqdm(df.groupby("station_id"), desc=f"  {var}", total=len(stations)):
        group = group.sort_values("time")
        outfile = var_dir / f"{station_id}.csv"
        group[["time", var]].to_csv(outfile, index=False)

    print(f"  ✓ Saved {len(stations)} station files to {var_dir}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("CMFD Weather Data Processing (Optimized)")
    print("=" * 60)

    stations = generate_stations()
    stations.to_csv(OUTPUT_DIR / "stations.csv", index=False)

    for var in VARIABLES:
        process_variable(var, stations)

    print("\n" + "=" * 60)
    print("CMFD processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
