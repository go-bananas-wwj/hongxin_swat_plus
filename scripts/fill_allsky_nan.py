#!/usr/bin/env python3
"""Fill NaN values in All-sky temperature data using nearest valid station.

Stations wx281, wx309, wx337 have all-NaN for 2019-2022 (outside All-sky coverage).
Fill by copying from nearest valid neighbor on each day.
"""

from pathlib import Path

import pandas as pd

WORKSPACE = Path("/workspace/hongxin_swaw_plus")
STATIONS_DIR = WORKSPACE / "data/02_processed/weather_stations"
TXTOUT_DIR = WORKSPACE / "data/02_processed/TxtInOut_v61"

# Mapping: station with NaN -> nearest valid neighbor
FILL_MAP = {
    "wx281": "wx282",  # (119.9, 46.7) -> (120.0, 46.7)
    "wx309": "wx310",  # (119.9, 46.8) -> (120.0, 46.8)
    "wx337": "wx338",  # (119.9, 46.9) -> (120.0, 46.9)
}


def fill_station(sid, neighbor_id):
    """Fill NaN values for one station from its neighbor."""
    for var, col in [("tmax", "tmax"), ("tmin", "tmin")]:
        df = pd.read_csv(STATIONS_DIR / var / f"{sid}.csv")
        df_nbr = pd.read_csv(STATIONS_DIR / var / f"{neighbor_id}.csv")
        
        nan_count = df[col].isna().sum()
        if nan_count > 0:
            df = pd.merge(df, df_nbr[["time", col]], on="time", suffixes=("", "_nbr"))
            df[col] = df[col].fillna(df[f"{col}_nbr"])
            df = df[["time", col]]
            df.to_csv(STATIONS_DIR / var / f"{sid}.csv", index=False)
            print(f"  {sid}: filled {nan_count} NaN in {var} from {neighbor_id}")


def update_tmp_file(sid):
    """Update a single wx*.tmp file after filling NaN."""
    tmp_path = TXTOUT_DIR / f"{sid}.tmp"
    
    with open(tmp_path, "r") as f:
        lines = f.readlines()
    
    header = lines[0]
    header2 = lines[1]
    nbyr_line = lines[2]
    
    df_max = pd.read_csv(STATIONS_DIR / "tmax" / f"{sid}.csv")
    df_min = pd.read_csv(STATIONS_DIR / "tmin" / f"{sid}.csv")
    df = pd.merge(df_max, df_min, on="time")
    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.year
    df["doy"] = df["time"].dt.dayofyear
    
    df_new = df[(df["year"] >= 2019) & (df["year"] <= 2022)].copy()
    
    with open(tmp_path, "w") as f:
        f.write(header)
        f.write(header2)
        f.write(nbyr_line)
        for line in lines[3:]:
            f.write(line)
        for _, row in df_new.iterrows():
            f.write(f"{int(row['year'])}  {int(row['doy']):3d}    {row['tmax']:7.2f}    {row['tmin']:7.2f}\n")


def main():
    print("Filling NaN values in All-sky temperature data...")
    
    for sid, neighbor_id in FILL_MAP.items():
        fill_station(sid, neighbor_id)
        update_tmp_file(sid)
    
    print("\nNaN filling complete!")
    
    # Verify no NaN remains
    total_nan = 0
    for i in range(1, 449):
        sid = f"wx{i:03d}"
        df_max = pd.read_csv(STATIONS_DIR / "tmax" / f"{sid}.csv")
        df_min = pd.read_csv(STATIONS_DIR / "tmin" / f"{sid}.csv")
        total_nan += df_max.tmax.isna().sum()
        total_nan += df_min.tmin.isna().sum()
    
    print(f"Total NaN remaining: {total_nan}")


if __name__ == "__main__":
    main()
