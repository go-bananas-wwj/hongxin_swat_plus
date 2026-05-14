#!/usr/bin/env python3
"""Generate SWAT+ weather .cli files from processed CMFD and CDAT data.

Outputs:
  - pcp.cli, tmp.cli, slr.cli, hmd.cli, wnd.cli
  - weather-sta.cli
  - weather-wgn.cli
  - Individual .pcp, .tmp, .slr, .hmd, .wnd files per station
"""

from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

STATIONS_CSV = Path("/workspace/hongxin_swaw_plus/data/02_processed/weather_stations/stations.csv")
WEATHER_DIR = Path("/workspace/hongxin_swaw_plus/data/02_processed/weather_stations")
OUTPUT_DIR = Path("/workspace/hongxin_swaw_plus/data/02_processed/weather_cli")
SIM_PERIOD = (2012, 2022)


def load_station_data(station_id: str):
    """Load all weather variables for a single station."""
    data = {}

    for var in ["lrad", "prec", "rhum", "srad", "wind"]:
        f = WEATHER_DIR / var / f"{station_id}.csv"
        if f.exists():
            df = pd.read_csv(f, parse_dates=["time"])
            data[var] = df.set_index("time")[var]
        else:
            print(f"  Warning: missing {var} for {station_id}")
            data[var] = pd.Series(dtype=float)

    for var in ["tmax", "tmin"]:
        f = WEATHER_DIR / var / f"{station_id}.csv"
        if f.exists():
            df = pd.read_csv(f, parse_dates=["time"])
            data[var] = df.set_index("time")[var]
        else:
            print(f"  Warning: missing {var} for {station_id}")
            data[var] = pd.Series(dtype=float)

    return data


def write_pcp_file(station_id: str, station_info: pd.Series, prec: pd.Series, out_dir: Path):
    """Write .pcp file for a station."""
    outfile = out_dir / f"{station_id}.pcp"
    valid = prec.dropna()
    if len(valid) == 0:
        return None

    nbyr = valid.index.year.max() - valid.index.year.min() + 1
    lat = station_info["lat"]
    lon = station_info["lon"]
    elev = 200.0  # approximate elevation, can be refined with DEM

    with open(outfile, "w") as f:
        f.write(f"{station_id} daily precipitation\n")
        f.write("   NBYR tstep     LAT      LONG        ELEV\n")
        f.write(f"{nbyr:6d}{0:5d}{lat:10.4f}{lon:10.4f}{elev:12.3f}\n")

        for dt, val in valid.items():
            year = dt.year
            jday = dt.dayofyear
            f.write(f"{year:4d}{jday:5d}{val:10.2f}\n")

    return outfile.name


def write_tmp_file(station_id: str, station_info: pd.Series, tmax: pd.Series, tmin: pd.Series, out_dir: Path):
    """Write .tmp file for a station."""
    outfile = out_dir / f"{station_id}.tmp"

    # Align and drop NaNs
    df = pd.DataFrame({"tmax": tmax, "tmin": tmin}).dropna()
    if len(df) == 0:
        return None

    nbyr = df.index.year.max() - df.index.year.min() + 1
    lat = station_info["lat"]
    lon = station_info["lon"]
    elev = 200.0

    with open(outfile, "w") as f:
        f.write(f"{station_id} daily temperature\n")
        f.write("   NBYR tstep     LAT      LONG        ELEV\n")
        f.write(f"{nbyr:6d}{0:5d}{lat:10.4f}{lon:10.4f}{elev:12.3f}\n")

        for dt, row in df.iterrows():
            year = dt.year
            jday = dt.dayofyear
            f.write(f"{year:4d}{jday:5d}{row['tmax']:10.2f}{row['tmin']:10.2f}\n")

    return outfile.name


def write_slr_file(station_id: str, station_info: pd.Series, srad: pd.Series, out_dir: Path):
    """Write .slr file for a station."""
    outfile = out_dir / f"{station_id}.slr"
    valid = srad.dropna()
    if len(valid) == 0:
        return None

    nbyr = valid.index.year.max() - valid.index.year.min() + 1
    lat = station_info["lat"]
    lon = station_info["lon"]
    elev = 200.0

    with open(outfile, "w") as f:
        f.write(f"{station_id} daily solar radiation\n")
        f.write("   NBYR tstep     LAT      LONG        ELEV\n")
        f.write(f"{nbyr:6d}{0:5d}{lat:10.4f}{lon:10.4f}{elev:12.3f}\n")

        for dt, val in valid.items():
            year = dt.year
            jday = dt.dayofyear
            f.write(f"{year:4d}{jday:5d}{val:10.2f}\n")

    return outfile.name


def write_hmd_file(station_id: str, station_info: pd.Series, rhum: pd.Series, out_dir: Path):
    """Write .hmd file for a station."""
    outfile = out_dir / f"{station_id}.hmd"
    valid = rhum.dropna()
    if len(valid) == 0:
        return None

    nbyr = valid.index.year.max() - valid.index.year.min() + 1
    lat = station_info["lat"]
    lon = station_info["lon"]
    elev = 200.0

    with open(outfile, "w") as f:
        f.write(f"{station_id} daily relative humidity\n")
        f.write("   NBYR tstep     LAT      LONG        ELEV\n")
        f.write(f"{nbyr:6d}{0:5d}{lat:10.4f}{lon:10.4f}{elev:12.3f}\n")

        for dt, val in valid.items():
            year = dt.year
            jday = dt.dayofyear
            f.write(f"{year:4d}{jday:5d}{val:10.4f}\n")

    return outfile.name


def write_wnd_file(station_id: str, station_info: pd.Series, wind: pd.Series, out_dir: Path):
    """Write .wnd file for a station."""
    outfile = out_dir / f"{station_id}.wnd"
    valid = wind.dropna()
    if len(valid) == 0:
        return None

    nbyr = valid.index.year.max() - valid.index.year.min() + 1
    lat = station_info["lat"]
    lon = station_info["lon"]
    elev = 200.0

    with open(outfile, "w") as f:
        f.write(f"{station_id} daily wind speed\n")
        f.write("   NBYR tstep     LAT      LONG        ELEV\n")
        f.write(f"{nbyr:6d}{0:5d}{lat:10.4f}{lon:10.4f}{elev:12.3f}\n")

        for dt, val in valid.items():
            year = dt.year
            jday = dt.dayofyear
            f.write(f"{year:4d}{jday:5d}{val:10.2f}\n")

    return outfile.name


def compute_wgn_params(station_id: str, data: dict) -> dict:
    """Compute weather generator parameters from observed data.

    Returns dict with monthly arrays (12 elements each).
    Based on 2012-2018 data (full temp coverage).
    """
    # Build DataFrame with all variables
    df = pd.DataFrame({
        "prec": data.get("prec", pd.Series(dtype=float)),
        "tmax": data.get("tmax", pd.Series(dtype=float)),
        "tmin": data.get("tmin", pd.Series(dtype=float)),
        "srad": data.get("srad", pd.Series(dtype=float)),
        "rhum": data.get("rhum", pd.Series(dtype=float)),
        "wind": data.get("wind", pd.Series(dtype=float)),
    })

    # Filter to 2012-2018 for consistent stats
    df = df[(df.index.year >= 2012) & (df.index.year <= 2018)]

    if len(df) == 0:
        return None

    df["month"] = df.index.month

    params = {}
    for mo in range(1, 13):
        mo_df = df[df["month"] == mo]

        # Temperature
        params.setdefault("tmpmx", []).append(mo_df["tmax"].mean() if "tmax" in mo_df else 0)
        params.setdefault("tmpmn", []).append(mo_df["tmin"].mean() if "tmin" in mo_df else 0)
        params.setdefault("tmpstdmx", []).append(mo_df["tmax"].std() if "tmax" in mo_df else 0)
        params.setdefault("tmpstdmn", []).append(mo_df["tmin"].std() if "tmin" in mo_df else 0)

        # Precipitation
        pcp = mo_df["prec"].dropna()
        params.setdefault("pcpmm", []).append(pcp.mean() if len(pcp) > 0 else 0)
        params.setdefault("pcpstd", []).append(pcp.std() if len(pcp) > 0 else 0)
        # Skewness
        if len(pcp) > 2 and pcp.std() > 0:
            skew = pcp.skew()
            params.setdefault("pcpskw", []).append(skew if not np.isnan(skew) else 0)
        else:
            params.setdefault("pcpskw", []).append(0)

        # Wet/dry probabilities
        wet = (pcp > 0.1).astype(int)
        if len(wet) > 1:
            ww = 0  # wet after wet
            wd = 0  # wet after dry
            dw = 0  # dry after wet
            dd = 0  # dry after dry
            for i in range(1, len(wet)):
                if wet.iloc[i-1] == 1 and wet.iloc[i] == 1:
                    ww += 1
                elif wet.iloc[i-1] == 1 and wet.iloc[i] == 0:
                    wd += 1
                elif wet.iloc[i-1] == 0 and wet.iloc[i] == 1:
                    dw += 1
                else:
                    dd += 1
            total_wet_after = ww + wd
            total_dry_after = dw + dd
            pr_ww = ww / total_wet_after if total_wet_after > 0 else 0
            pr_wd = wd / total_wet_after if total_wet_after > 0 else 0
        else:
            pr_ww = 0
            pr_wd = 0

        params.setdefault("pr_ww", []).append(pr_ww)
        params.setdefault("pr_wd", []).append(pr_wd)
        params.setdefault("pcpd", []).append(wet.sum() if len(wet) > 0 else 0)

        # Max half-hour rainfall (simplified: 2 * mean daily)
        params.setdefault("rainhmx", []).append(2 * pcp.mean() if len(pcp) > 0 else 0)

        # Solar radiation
        params.setdefault("solarav", []).append(mo_df["srad"].mean() if "srad" in mo_df else 0)

        # Dew point (approximate as tmin - 2)
        params.setdefault("dewpt", []).append(mo_df["tmin"].mean() - 2 if "tmin" in mo_df else 0)

        # Wind
        params.setdefault("windav", []).append(mo_df["wind"].mean() if "wind" in mo_df else 0)

    return params


def write_wgn_file(station_id: str, station_info: pd.Series, params: dict, out_dir: Path):
    """Write weather generator file for a station."""
    if params is None:
        return None

    outfile = out_dir / f"{station_id}.wgn"
    lat = station_info["lat"]
    lon = station_info["lon"]
    elev = 200.0
    rain_yrs = 7  # 2012-2018

    with open(outfile, "w") as f:
        f.write(f"{station_id} {lat:.4f} {lon:.4f} {elev:.1f} {rain_yrs}\n")
        f.write("   TMPMX   TMPMN TMPSTDMX TMPSTDMN   PCPMM   PCPSTD   PCPSKW   PR_WD   PR_WW   PCPD RAINHMX  SOLARAV    DEWPT   WINDAV\n")

        for mo in range(12):
            f.write(
                f"{params['tmpmx'][mo]:8.2f}{params['tmpmn'][mo]:8.2f}"
                f"{params['tmpstdmx'][mo]:9.2f}{params['tmpstdmn'][mo]:9.2f}"
                f"{params['pcpmm'][mo]:8.2f}{params['pcpstd'][mo]:9.2f}"
                f"{params['pcpskw'][mo]:9.2f}{params['pr_wd'][mo]:8.2f}"
                f"{params['pr_ww'][mo]:8.2f}{params['pcpd'][mo]:7.1f}"
                f"{params['rainhmx'][mo]:8.2f}{params['solarav'][mo]:9.2f}"
                f"{params['dewpt'][mo]:9.2f}{params['windav'][mo]:9.2f}\n"
            )

    return outfile.name


def main():
    print("=" * 60)
    print("SWAT+ Weather .cli File Generator")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    stations = pd.read_csv(STATIONS_CSV)
    print(f"Loaded {len(stations)} virtual stations")

    pcp_files = []
    tmp_files = []
    slr_files = []
    hmd_files = []
    wnd_files = []
    wgn_files = []
    sta_records = []

    for _, row in tqdm(stations.iterrows(), total=len(stations), desc="Processing stations"):
        station_id = row["id"]
        data = load_station_data(station_id)

        pcp_name = write_pcp_file(station_id, row, data.get("prec"), OUTPUT_DIR)
        tmp_name = write_tmp_file(station_id, row, data.get("tmax"), data.get("tmin"), OUTPUT_DIR)
        slr_name = write_slr_file(station_id, row, data.get("srad"), OUTPUT_DIR)
        hmd_name = write_hmd_file(station_id, row, data.get("rhum"), OUTPUT_DIR)
        wnd_name = write_wnd_file(station_id, row, data.get("wind"), OUTPUT_DIR)

        # Compute wgn params
        wgn_params = compute_wgn_params(station_id, data)
        wgn_name = write_wgn_file(station_id, row, wgn_params, OUTPUT_DIR)

        if pcp_name:
            pcp_files.append(pcp_name)
        if tmp_name:
            tmp_files.append(tmp_name)
        if slr_name:
            slr_files.append(slr_name)
        if hmd_name:
            hmd_files.append(hmd_name)
        if wnd_name:
            wnd_files.append(wnd_name)
        if wgn_name:
            wgn_files.append(wgn_name)

        # weather-sta.cli record
        sta_records.append({
            "name": station_id,
            "wgn": wgn_name.replace(".wgn", "") if wgn_name else "null",
            "pgage": pcp_name.replace(".pcp", "") if pcp_name else "sim",
            "tgage": tmp_name.replace(".tmp", "") if tmp_name else "sim",
            "sgage": slr_name.replace(".slr", "") if slr_name else "sim",
            "hgage": hmd_name.replace(".hmd", "") if hmd_name else "sim",
            "wgage": wnd_name.replace(".wnd", "") if wnd_name else "sim",
            "petgage": "null",
            "atmodep": "null",
        })

    # Write .cli list files
    def write_cli_list(filename: str, files: list):
        with open(OUTPUT_DIR / filename, "w") as f:
            f.write(f"{filename} - list of weather data files\n")
            f.write("filename\n")
            for fname in files:
                f.write(f"{fname}\n")

    write_cli_list("pcp.cli", pcp_files)
    write_cli_list("tmp.cli", tmp_files)
    write_cli_list("slr.cli", slr_files)
    write_cli_list("hmd.cli", hmd_files)
    write_cli_list("wnd.cli", wnd_files)
    write_cli_list("weather-wgn.cli", wgn_files)

    # Write weather-sta.cli
    with open(OUTPUT_DIR / "weather-sta.cli", "w") as f:
        f.write("weather-sta.cli - weather station data\n")
        f.write("name          wgn                pcp                tmp                slr                hmd                wnd                pet                atmo\n")
        for rec in sta_records:
            f.write(
                f"{rec['name']:14s}{rec['wgn']:19s}{rec['pgage']:19s}"
                f"{rec['tgage']:19s}{rec['sgage']:19s}"
                f"{rec['hgage']:19s}{rec['wgage']:19s}"
                f"{rec['petgage']:19s}{rec['atmodep']:19s}\n"
            )

    print(f"\n{'=' * 60}")
    print(f"Generated {len(pcp_files)} .pcp files")
    print(f"Generated {len(tmp_files)} .tmp files")
    print(f"Generated {len(slr_files)} .slr files")
    print(f"Generated {len(hmd_files)} .hmd files")
    print(f"Generated {len(wnd_files)} .wnd files")
    print(f"Generated {len(wgn_files)} .wgn files")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
