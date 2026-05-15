#!/usr/bin/env python3
"""Process All-sky temperature GeoTIFFs (2019-2022) from zip archives.

Optimized approach:
  1. Extract each zip to /dev/shm (RAM disk) for fast disk I/O
  2. Read TIFFs directly from disk with rasterio
  3. Sample pixel values at virtual station locations
  4. Append to existing tmax/tmin CSV files (2012-2018 from CDAT)
  5. Generate SWAT+ tmp.cli file

Confirmed scale factor: 0.1 (raw Int16 * 0.1 = °C)
"""

import shutil
import subprocess
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

WORKSPACE = Path("/workspace/hongxin_swaw_plus")
DATASETS = WORKSPACE / "datasets"
STATIONS_DIR = WORKSPACE / "data/02_processed/weather_stations"
STATIONS_CSV = STATIONS_DIR / "stations.csv"
TEMP_DIR = Path("/dev/shm/allsky_temp")

YEARS = [2019, 2020, 2021, 2022]
SCALE_FACTOR = 0.10  # Confirmed by cross-check with CDAT


def read_stations():
    """Read virtual weather station coordinates."""
    df = pd.read_csv(STATIONS_CSV)
    return [
        {"id": row["id"], "lon": row["lon"], "lat": row["lat"]}
        for _, row in df.iterrows()
    ]


def extract_zip_to_temp(zip_path, temp_dir):
    """Extract zip archive to temp directory."""
    temp_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Extracting {zip_path.name} to {temp_dir} ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(temp_dir)
    print(f"  Extraction complete")


def process_year_from_disk(year, var, stations):
    """Process one year of All-sky data from extracted TIFFs on disk."""
    zip_path = DATASETS / f"Tem-{var}_{year}.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"{zip_path} not found")
    
    # Extract to temp
    extract_zip_to_temp(zip_path, TEMP_DIR)
    
    # Find all TIFF files
    year_dir = TEMP_DIR / str(year)
    tiff_files = sorted(year_dir.glob("*.tif"))
    
    if not tiff_files:
        raise FileNotFoundError(f"No TIFFs found in {year_dir}")
    
    # Prepare containers
    results = {s["id"]: [] for s in stations}
    coords = [(s["lon"], s["lat"]) for s in stations]
    
    print(f"  Processing {len(tiff_files)} TIFFs for {var} {year} ...")
    
    for i, tiff_path in enumerate(tiff_files):
        # Parse date from filename: YYYYDDD.tif
        basename = tiff_path.stem
        doy = int(basename[4:])
        date = datetime(year, 1, 1) + timedelta(days=doy - 1)
        date_str = date.strftime("%Y-%m-%d")
        
        with rasterio.open(tiff_path) as src:
            values = list(src.sample(coords))
            values = np.array([v[0] for v in values])
            
            # Handle NoData (-9999)
            values = np.where(values == -9999, np.nan, values)
            
            # Scale to actual temperature (Int16 * 0.1)
            values = values * SCALE_FACTOR
            
            for j, s in enumerate(stations):
                results[s["id"]].append((date_str, values[j]))
        
        if (i + 1) % 100 == 0 or (i + 1) == len(tiff_files):
            print(f"    {var} {year}: {i+1}/{len(tiff_files)} days done")
    
    # Clean up temp
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    
    return results


def append_to_csv(results, var):
    """Append All-sky data to existing station CSV files."""
    subdir = "tmax" if var == "MAX" else "tmin"
    colname = "tmax" if var == "MAX" else "tmin"
    out_dir = STATIONS_DIR / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for station_id, records in results.items():
        out_path = out_dir / f"{station_id}.csv"
        
        df_new = pd.DataFrame(records, columns=["time", colname])
        
        if out_path.exists():
            df_old = pd.read_csv(out_path)
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
            df_combined = df_combined.drop_duplicates(subset=["time"], keep="last")
            df_combined = df_combined.sort_values("time")
        else:
            df_combined = df_new
        
        df_combined.to_csv(out_path, index=False)
    
    print(f"  Appended {var} data to {len(results)} station CSVs")


def generate_tmp_cli():
    """Generate SWAT+ tmp.cli file from all station tmax/tmin CSVs."""
    tmax_dir = STATIONS_DIR / "tmax"
    tmin_dir = STATIONS_DIR / "tmin"
    
    stations = read_stations()
    
    # Read all station data
    all_dfs = []
    for s in stations:
        sid = s["id"]
        df_max = pd.read_csv(tmax_dir / f"{sid}.csv")
        df_min = pd.read_csv(tmin_dir / f"{sid}.csv")
        df = pd.merge(df_max, df_min, on="time", how="outer")
        df["station"] = sid
        all_dfs.append(df)
    
    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all["time"] = pd.to_datetime(df_all["time"])
    df_all = df_all.sort_values(["station", "time"])
    
    # Write tmp.cli in SWAT+ format
    tmp_cli_path = STATIONS_DIR / "tmp.cli"
    
    dates = sorted(df_all["time"].unique())
    
    with open(tmp_cli_path, "w") as f:
        # Header: number of stations
        f.write(f"{len(stations)}\n")
        # Station info: lat, lon, elevation
        for s in stations:
            f.write(f"{s['lat']:.6f} {s['lon']:.6f} 0.0\n")
        
        # Daily data
        for date in dates:
            df_day = df_all[df_all["time"] == date]
            year = date.year
            doy = date.dayofyear
            
            line_parts = [f"{year:4d}{doy:3d}"]
            for s in stations:
                row = df_day[df_day["station"] == s["id"]]
                if len(row) == 1:
                    tmax = row["tmax"].values[0]
                    tmin = row["tmin"].values[0]
                    tmax_str = f"{tmax:8.2f}" if not pd.isna(tmax) else "   -99.0"
                    tmin_str = f"{tmin:8.2f}" if not pd.isna(tmin) else "   -99.0"
                else:
                    tmax_str = "   -99.0"
                    tmin_str = "   -99.0"
                line_parts.append(tmax_str)
                line_parts.append(tmin_str)
            
            f.write(" ".join(line_parts) + "\n")
    
    print(f"  Generated {tmp_cli_path}")
    print(f"  Date range: {min(dates)} to {max(dates)}")
    print(f"  Total days: {len(dates)}")


def main():
    stations = read_stations()
    print(f"Loaded {len(stations)} virtual weather stations")
    
    for var in ["MAX", "MIN"]:
        print(f"\nProcessing All-sky {var} ...")
        for year in YEARS:
            results = process_year_from_disk(year, var, stations)
            append_to_csv(results, var)
    
    print("\nGenerating tmp.cli ...")
    generate_tmp_cli()
    
    print("\nAll-sky temperature processing complete!")


if __name__ == "__main__":
    main()
