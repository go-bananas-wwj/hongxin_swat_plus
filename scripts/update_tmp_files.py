#!/usr/bin/env python3
"""Update SWAT+ wx*.tmp files with 2019-2022 All-sky temperature data.

Reads existing wx*.tmp files in TxtInOut_v61, updates NBYR from 7 to 11,
and appends 2019-2022 daily tmax/tmin data.

Input:
  data/02_processed/weather_stations/tmax/wx###.csv
  data/02_processed/weather_stations/tmin/wx###.csv
  data/02_processed/TxtInOut_v61/wx###.tmp

Output:
  Updated wx###.tmp files with 2012-2022 data
"""

from pathlib import Path

import pandas as pd

WORKSPACE = Path("/workspace/hongxin_swaw_plus")
STATIONS_DIR = WORKSPACE / "data/02_processed/weather_stations"
TXTOUT_DIR = WORKSPACE / "data/02_processed/TxtInOut_v61"


def update_tmp_file(station_id):
    """Update a single wx*.tmp file."""
    tmp_path = TXTOUT_DIR / f"{station_id}.tmp"
    
    # Read existing header
    with open(tmp_path, "r") as f:
        lines = f.readlines()
    
    header = lines[0]  # Station name line
    header2 = lines[1]  # Column headers
    # NBYR line: "     7    0   45.7000  119.9000     200.000"
    nbyr_line = lines[2]
    # Update NBYR from 7 to 11
    nbyr_new = nbyr_line.replace("     7", "    11", 1)
    
    # Read new data for 2019-2022
    df_max = pd.read_csv(STATIONS_DIR / "tmax" / f"{station_id}.csv")
    df_min = pd.read_csv(STATIONS_DIR / "tmin" / f"{station_id}.csv")
    df = pd.merge(df_max, df_min, on="time")
    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.year
    df["doy"] = df["time"].dt.dayofyear
    
    # Filter 2019-2022
    df_new = df[(df["year"] >= 2019) & (df["year"] <= 2022)].copy()
    
    # Write updated file
    with open(tmp_path, "w") as f:
        f.write(header)
        f.write(header2)
        f.write(nbyr_new)
        
        # Write original data (lines[3:])
        for line in lines[3:]:
            f.write(line)
        
        # Append new data
        for _, row in df_new.iterrows():
            f.write(f"{int(row['year'])}  {int(row['doy']):3d}    {row['tmax']:7.2f}    {row['tmin']:7.2f}\n")


def main():
    # Get list of stations
    stations = sorted([p.stem for p in (STATIONS_DIR / "tmax").glob("wx*.csv")])
    print(f"Updating {len(stations)} station .tmp files ...")
    
    for i, sid in enumerate(stations):
        update_tmp_file(sid)
        if (i + 1) % 50 == 0 or (i + 1) == len(stations):
            print(f"  {i+1}/{len(stations)} done")
    
    print("All .tmp files updated!")
    
    # Verify one file
    sample = TXTOUT_DIR / "wx001.tmp"
    with open(sample, "r") as f:
        lines = f.readlines()
    print(f"\nVerification: {sample.name}")
    print(f"  Header: {lines[0].strip()}")
    print(f"  NBYR line: {lines[2].strip()}")
    print(f"  First data: {lines[3].strip()}")
    print(f"  Last 2018 data: {lines[-366].strip()}")
    print(f"  First 2019 data: {lines[-365].strip()}")
    print(f"  Last data: {lines[-1].strip()}")
    print(f"  Total lines: {len(lines)}")


if __name__ == "__main__":
    main()
