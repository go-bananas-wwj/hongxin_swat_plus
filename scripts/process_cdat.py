#!/usr/bin/env python3
"""Process CDAT temperature data: extract Tmax/Tmin at virtual stations.

CDAT resolution is 0.1°, which matches virtual station spacing exactly.
Optimized to batch-read entire directories.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from tqdm import tqdm

CDAT_DIR = Path("/workspace/hongxin_swaw_plus/data/01_raw/cdat/cdat")
STATIONS_CSV = Path("/workspace/hongxin_swaw_plus/data/02_processed/weather_stations/stations.csv")
OUTPUT_DIR = Path("/workspace/hongxin_swaw_plus/data/02_processed/weather_stations")
SIM_PERIOD = (2012, 2018)


def get_station_indices(stations: pd.DataFrame):
    """Compute row/col indices for each station in CDAT grid.

    CDAT grid: left=70.0, top=55.0, res=0.1°
    col = (lon - 70.0) / 0.1
    row = (55.0 - lat) / 0.1
    """
    lons = stations["lon"].values
    lats = stations["lat"].values
    cols = ((lons - 70.0) / 0.1).astype(int)
    rows = ((55.0 - lats) / 0.1).astype(int)
    return rows, cols


def process_directory(extract_dir: Path, station_rows, station_cols, station_ids):
    """Process all .tif files in a directory, return DataFrame."""
    tif_files = sorted(extract_dir.glob("*.tif"))
    if not tif_files:
        return None

    n_files = len(tif_files)
    n_stations = len(station_ids)

    # Pre-allocate array: (n_files, n_stations)
    values = np.full((n_files, n_stations), np.nan, dtype=np.float32)
    dates = []

    for i, tif_file in enumerate(tif_files):
        # Parse date: 20170319_max.tif → 2017-03-19
        date_str = tif_file.stem.split("_")[0]
        date = pd.to_datetime(date_str, format="%Y%m%d")
        dates.append(date)

        with rasterio.open(tif_file) as src:
            data = src.read(1)
            nodata = src.nodata
            # Extract at station locations
            vals = data[station_rows, station_cols]
            if nodata is not None:
                vals = np.where(vals == nodata, np.nan, vals)
            values[i] = vals

    # Build DataFrame
    df = pd.DataFrame(values, columns=station_ids)
    df["time"] = dates
    df = df[["time"] + list(station_ids)]
    return df


def main():
    print("=" * 60)
    print("CDAT Temperature Data Processing (Optimized)")
    print("=" * 60)

    # Load stations
    stations = pd.read_csv(STATIONS_CSV)
    print(f"Loaded {len(stations)} virtual stations")

    station_rows, station_cols = get_station_indices(stations)
    station_ids = stations["id"].values

    # Verify indices are within bounds
    n_rows, n_cols = 400, 700
    valid = (station_rows >= 0) & (station_rows < n_rows) & (station_cols >= 0) & (station_cols < n_cols)
    print(f"Stations within CDAT bounds: {valid.sum()}/{len(stations)}")
    if not valid.all():
        print("  Warning: some stations are outside CDAT coverage")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Process each year and variable
    for year in range(SIM_PERIOD[0], SIM_PERIOD[1] + 1):
        for var_type in ["max", "min"]:
            extract_dir = CDAT_DIR / f"extracted_{year}_{var_type}"
            print(f"\nProcessing {extract_dir.name}...")

            df = process_directory(extract_dir, station_rows, station_cols, station_ids)
            if df is not None:
                out_file = OUTPUT_DIR / f"cdat_{year}_{var_type}.csv"
                df.to_csv(out_file, index=False)
                print(f"  ✓ Saved {len(df)} days → {out_file}")
            else:
                print(f"  ⚠ No .tif files found")

    # Merge all years into continuous time series per station
    print("\n--- Merging years and saving per station ---")
    for var_type in ["max", "min"]:
        var_name = "tmax" if var_type == "max" else "tmin"
        var_dir = OUTPUT_DIR / var_name
        var_dir.mkdir(exist_ok=True)

        all_years = []
        for year in range(SIM_PERIOD[0], SIM_PERIOD[1] + 1):
            f = OUTPUT_DIR / f"cdat_{year}_{var_type}.csv"
            if f.exists():
                all_years.append(pd.read_csv(f, parse_dates=["time"]))

        if not all_years:
            continue

        merged = pd.concat(all_years, ignore_index=True)
        merged = merged.sort_values("time").reset_index(drop=True)

        # Save per station
        for station_id in tqdm(station_ids, desc=f"  {var_name}"):
            station_df = merged[["time", station_id]].copy()
            station_df.columns = ["time", var_name]
            station_df.to_csv(var_dir / f"{station_id}.csv", index=False)

        print(f"  ✓ Saved {len(station_ids)} {var_name} station files")

    print("\n" + "=" * 60)
    print("CDAT processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
