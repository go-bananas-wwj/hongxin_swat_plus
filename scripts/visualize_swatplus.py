#!/usr/bin/env python3
"""SWAT+ simulation results visualization and evaluation toolkit.

Provides:
  - Hydrograph plotting (simulated vs observed discharge)
  - Water balance visualization
  - Performance metrics (NSE, R², PBIAS, RMSE)
  - Time series comparison
  - Flow duration curve
  - Scatter plot

Usage:
    python visualize_swatplus.py

Requirements:
    pip install matplotlib pandas numpy
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path("/workspace/hongxin_swaw_plus")
TXTOUT_DIR = PROJECT_ROOT / "data/02_processed/TxtInOut_v61"
OBS_DIR = PROJECT_ROOT / "datasets/processed_hydro"
OUTPUT_FIG_DIR = PROJECT_ROOT / "output/figures"

# Station name mapping (English -> Chinese file prefix)
STATION_MAP = {
    "ZhenXi": "镇西",
    "ChaErSen": "察尔森",
    "ChaErSenXia": "察尔森下",
    "WuChaGou": "五岔沟",
    "SuoLun": "索伦",
    "DaShiZhai": "大石寨",
    "BaoLong": "保隆",
    "ALiDeEr": "阿力得尔",
}

# Outlet subbasin mapping (to be configured based on project knowledge)
# Format: "StationName": subbasin_id
OUTLET_MAPPING = {
    # Example: "ZhenXi": 282,
}

# Colors
COLOR_SIM = "#2E86AB"
COLOR_OBS = "#A23B72"
COLOR_DIFF = "#F18F01"

# ---------------------------------------------------------------------------
# SWAT+ Output Readers
# ---------------------------------------------------------------------------

def read_channel_day(txtout_dir: Path) -> Optional[pd.DataFrame]:
    """Read channel_sd_day.txt or channel_day.txt (daily channel output)."""
    for fname in ["channel_sd_day.txt", "channel_day.txt"]:
        path = txtout_dir / fname
        if path.exists():
            df = pd.read_csv(path, sep=r"\s+", low_memory=False)
            df["date"] = pd.to_datetime(df[["yr", "mon", "day"]])
            return df
    return None


def read_basin_wb_day(txtout_dir: Path) -> Optional[pd.DataFrame]:
    """Read basin_wb_day.txt (daily water balance)."""
    path = txtout_dir / "basin_wb_day.txt"
    if not path.exists():
        return None
    df = pd.read_csv(path, sep=r"\s+", low_memory=False)
    df["date"] = pd.to_datetime(df[["yr", "mon", "day"]])
    return df


def read_observed_discharge(station_name: str) -> Optional[pd.DataFrame]:
    """Read observed daily discharge CSV for a station."""
    prefix = STATION_MAP.get(station_name, station_name)
    pattern = f"{prefix}_discharge_*_daily.csv"
    files = list(OBS_DIR.glob(pattern))
    if not files:
        return None
    df = pd.read_csv(files[0], parse_dates=["date"])
    df = df.rename(columns={"value": "observed"})
    return df


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def calculate_metrics(sim: np.ndarray, obs: np.ndarray) -> Dict[str, float]:
    """Calculate Nash-Sutcliffe Efficiency, R², PBIAS, RMSE."""
    mask = ~(np.isnan(sim) | np.isnan(obs))
    s, o = sim[mask], obs[mask]
    if len(s) == 0:
        return {"NSE": np.nan, "R2": np.nan, "PBIAS": np.nan, "RMSE": np.nan, "n": 0}

    ss_res = np.sum((o - s) ** 2)
    ss_tot = np.sum((o - np.mean(o)) ** 2)
    nse = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    corr = np.corrcoef(o, s)[0, 1]
    r2 = corr ** 2 if not np.isnan(corr) else np.nan

    pbias = 100 * np.sum(s - o) / np.sum(o) if np.sum(o) != 0 else np.nan
    rmse = np.sqrt(np.mean((s - o) ** 2))

    return {"NSE": nse, "R2": r2, "PBIAS": pbias, "RMSE": rmse, "n": len(s)}


# ---------------------------------------------------------------------------
# Plotting Functions
# ---------------------------------------------------------------------------

def plot_hydrograph(
    sim_df: pd.DataFrame,
    obs_df: pd.DataFrame,
    station_name: str,
    out_dir: Path,
    flow_col: str = "flo_out",
) -> Optional[Path]:
    """Plot simulated vs observed hydrograph with metrics."""
    out_dir.mkdir(parents=True, exist_ok=True)
    merged = pd.merge(sim_df, obs_df, on="date", how="inner")
    if len(merged) == 0:
        print(f"  ⚠ No overlapping dates for {station_name}")
        return None

    metrics = calculate_metrics(merged[flow_col].values, merged["observed"].values)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)

    ax = axes[0]
    ax.plot(merged["date"], merged["observed"], color=COLOR_OBS, label="Observed", lw=0.8, alpha=0.9)
    ax.plot(merged["date"], merged[flow_col], color=COLOR_SIM, label="Simulated", lw=0.8, alpha=0.9)
    ax.set_ylabel("Discharge (m³/s)")
    ax.set_title(
        f"{station_name} Daily Discharge\n"
        f"NSE={metrics['NSE']:.3f}  R²={metrics['R2']:.3f}  "
        f"PBIAS={metrics['PBIAS']:.1f}%  RMSE={metrics['RMSE']:.2f}  n={metrics['n']}"
    )
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    residual = merged[flow_col] - merged["observed"]
    ax2.fill_between(merged["date"], residual, 0, color=COLOR_DIFF, alpha=0.4)
    ax2.axhline(0, color="black", lw=0.5)
    ax2.set_ylabel("Sim - Obs (m³/s)")
    ax2.set_xlabel("Date")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = out_dir / f"hydrograph_{station_name}.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ Hydrograph: {out_path.name}")
    return out_path


def plot_scatter(
    sim_df: pd.DataFrame,
    obs_df: pd.DataFrame,
    station_name: str,
    out_dir: Path,
    flow_col: str = "flo_out",
) -> Optional[Path]:
    """Plot scatter plot of simulated vs observed with 1:1 line."""
    out_dir.mkdir(parents=True, exist_ok=True)
    merged = pd.merge(sim_df, obs_df, on="date", how="inner")
    if len(merged) == 0:
        return None

    metrics = calculate_metrics(merged[flow_col].values, merged["observed"].values)

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(merged["observed"], merged[flow_col], c=COLOR_SIM, alpha=0.4, s=8, edgecolors="none")

    # 1:1 line
    lims = [0, max(merged["observed"].max(), merged[flow_col].max()) * 1.05]
    ax.plot(lims, lims, "k--", lw=1, label="1:1")
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_aspect("equal")

    ax.set_xlabel("Observed Discharge (m³/s)")
    ax.set_ylabel("Simulated Discharge (m³/s)")
    ax.set_title(
        f"{station_name} Scatter Plot\n"
        f"NSE={metrics['NSE']:.3f}  R²={metrics['R2']:.3f}"
    )
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = out_dir / f"scatter_{station_name}.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ Scatter: {out_path.name}")
    return out_path


def plot_flow_duration_curve(
    sim_df: pd.DataFrame,
    obs_df: pd.DataFrame,
    station_name: str,
    out_dir: Path,
    flow_col: str = "flo_out",
) -> Optional[Path]:
    """Plot flow duration curve."""
    out_dir.mkdir(parents=True, exist_ok=True)
    merged = pd.merge(sim_df, obs_df, on="date", how="inner")
    if len(merged) == 0:
        return None

    sim_sorted = np.sort(merged[flow_col].values)[::-1]
    obs_sorted = np.sort(merged["observed"].values)[::-1]
    exceedance = np.arange(1, len(sim_sorted) + 1) / len(sim_sorted) * 100

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(exceedance, obs_sorted, color=COLOR_OBS, label="Observed", lw=1.5)
    ax.plot(exceedance, sim_sorted, color=COLOR_SIM, label="Simulated", lw=1.5)
    ax.set_xlabel("Exceedance Probability (%)")
    ax.set_ylabel("Discharge (m³/s)")
    ax.set_title(f"{station_name} Flow Duration Curve")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, alpha=0.3, which="both")

    plt.tight_layout()
    out_path = out_dir / f"fdc_{station_name}.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ FDC: {out_path.name}")
    return out_path


def plot_monthly_mean(
    sim_df: pd.DataFrame,
    obs_df: pd.DataFrame,
    station_name: str,
    out_dir: Path,
    flow_col: str = "flo_out",
) -> Optional[Path]:
    """Plot monthly mean discharge comparison."""
    out_dir.mkdir(parents=True, exist_ok=True)
    merged = pd.merge(sim_df, obs_df, on="date", how="inner")
    if len(merged) == 0:
        return None

    merged["month"] = merged["date"].dt.month
    monthly_sim = merged.groupby("month")[flow_col].mean()
    monthly_obs = merged.groupby("month")["observed"].mean()

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(1, 13)
    width = 0.35
    ax.bar(x - width / 2, monthly_obs, width, label="Observed", color=COLOR_OBS, alpha=0.8)
    ax.bar(x + width / 2, monthly_sim, width, label="Simulated", color=COLOR_SIM, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_ylabel("Mean Discharge (m³/s)")
    ax.set_title(f"{station_name} Monthly Mean Discharge")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    out_path = out_dir / f"monthly_mean_{station_name}.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ Monthly: {out_path.name}")
    return out_path


def plot_basin_water_balance(basin_df: pd.DataFrame, out_dir: Path) -> Path:
    """Plot basin-level water balance components."""
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    ax = axes[0]
    ax.plot(basin_df["date"], basin_df["precip"], color="#2E86AB", label="Precipitation", lw=0.6)
    ax.plot(basin_df["date"], basin_df["et"], color="#F18F01", label="ET", lw=0.6)
    ax.set_ylabel("mm/day")
    ax.set_title("Basin Water Balance: Precipitation & Evapotranspiration")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    ax.plot(basin_df["date"], basin_df["surq_gen"], color="#2E86AB", label="Surface Runoff", lw=0.6)
    ax.plot(basin_df["date"], basin_df["latq"], color="#A23B72", label="Lateral Flow", lw=0.6)
    ax.plot(basin_df["date"], basin_df["perc"], color="#F18F01", label="Percolation", lw=0.6)
    ax.set_ylabel("mm/day")
    ax.set_title("Runoff Components")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    ax.plot(basin_df["date"], basin_df["sw"], color="#2E86AB", label="Soil Water", lw=0.6)
    ax.set_ylabel("mm")
    ax.set_xlabel("Date")
    ax.set_title("Soil Water Storage")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = out_dir / "basin_water_balance.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ Water balance: {out_path.name}")
    return out_path


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main():
    OUTPUT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("SWAT+ Visualization Toolkit")
    print("=" * 60)

    # 1. Basin water balance
    basin_df = read_basin_wb_day(TXTOUT_DIR)
    if basin_df is not None:
        print("\n[1/4] Plotting basin water balance...")
        plot_basin_water_balance(basin_df, OUTPUT_FIG_DIR)
    else:
        print("\n[1/4] basin_wb_day.txt not found, skipping")

    # 2. Channel outputs
    channel_df = read_channel_day(TXTOUT_DIR)
    if channel_df is not None:
        print(f"\n[2/4] Channel data loaded: {len(channel_df)} rows, {channel_df['unit'].nunique()} units")

        # 2a. Plot for outlets with observations
        if OUTLET_MAPPING:
            print("\n[3/4] Plotting hydrographs for gauge stations...")
            for station_name, subbasin_id in OUTLET_MAPPING.items():
                sub = channel_df[channel_df["unit"] == subbasin_id].copy()
                if len(sub) == 0:
                    print(f"  ⚠ No data for {station_name} (unit={subbasin_id})")
                    continue

                obs = read_observed_discharge(station_name)
                if obs is None:
                    print(f"  ⚠ No observed data for {station_name}")
                    continue

                sub = sub.rename(columns={"flo_out": "simulated"})
                plot_hydrograph(sub, obs, station_name, OUTPUT_FIG_DIR)
                plot_scatter(sub, obs, station_name, OUTPUT_FIG_DIR)
                plot_flow_duration_curve(sub, obs, station_name, OUTPUT_FIG_DIR)
                plot_monthly_mean(sub, obs, station_name, OUTPUT_FIG_DIR)
        else:
            print("\n[3/4] OUTLET_MAPPING is empty. Skipping obs comparison.")
            print("      Edit OUTLET_MAPPING in visualize_swatplus.py to add station-unit links.")

        # 2b. Plot first few channels as preview
        print("\n[4/4] Plotting sample channel outputs...")
        for unit in sorted(channel_df["unit"].unique())[:3]:
            sub = channel_df[channel_df["unit"] == unit]
            fig, ax = plt.subplots(figsize=(14, 4))
            ax.plot(sub["date"], sub["flo_out"], color=COLOR_SIM, lw=0.6)
            ax.set_ylabel("Discharge (m³/s)")
            ax.set_title(f"Simulated Discharge - Channel Unit {unit}")
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            out_path = OUTPUT_FIG_DIR / f"channel_unit_{unit}.png"
            fig.savefig(out_path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            print(f"  ✅ Channel unit {unit}: {out_path.name}")
    else:
        print("\n[2/4] channel_day.txt not found. Run simulation with 'channel daily y' in print.prt")

    print(f"\n{'=' * 60}")
    print(f"Figures saved to: {OUTPUT_FIG_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
