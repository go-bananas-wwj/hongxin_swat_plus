#!/usr/bin/env python3
"""
Visualize SWAT+ basin_wb_day.txt vs observed discharge.
Style reference: /workspace/run_workflow_deli9.py

Uses wateryld as proxy for runoff, converts mm/day -> m3/s.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Chinese font support
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
from pathlib import Path
from datetime import date

# ============ CONFIG ============
TXTINOUT = Path("/workspace/hongxin_swaw_plus/data/02_processed/TxtInOut_v61")
OBS_DIR = Path("/workspace/hongxin_swaw_plus/datasets/processed_hydro")
OUT_DIR = Path("/workspace/hongxin_swaw_plus/figures")
OUT_DIR.mkdir(exist_ok=True)

STATION_NAME = "镇西"
OUTLET_GIS_ID = 282  # outlet channel
PLOT_DPI = 200

# Periods
WARMUP_YEARS = list(range(2012, 2015))  # warmup 2012-2014
VALIDATION_YEARS = list(range(2015, 2018))
CALIBRATION_YEARS = list(range(2018, 2023))

# SWAT+ basin_wb_day.txt columns (v61)
WB_COLS = [
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "precip", "snofall", "snomlt", "surq_gen", "latq", "wateryld",
    "perc", "et", "ecanopy", "eplant", "esoil", "surq_cont", "cn",
    "sw_init", "sw_final", "sw_ave", "sw_300", "sno_init", "sno_final",
    "snopack", "pet", "qtile", "irr", "surq_runon", "latq_runon",
    "overbank", "surq_cha", "surq_res", "surq_ls", "latq_cha",
    "latq_res", "latq_ls", "gwsoilq", "satex", "satex_chan",
    "sw_change", "lagsurf", "laglatq", "lagsatex", "wet_evap",
    "wet_oflo", "wet_stor"
]


def read_channel_outlet():
    """Read channel_day.txt for outlet channel (gis_id=282)."""
    df = pd.read_csv(TXTINOUT / "channel_day.txt", sep=r"\s+", skiprows=[0, 2], header=0, low_memory=False)
    df = df.rename(columns={"yr": "year", "mon": "month", "day": "day"})
    df["date"] = pd.to_datetime(df[["year", "month", "day"]])
    # Convert flo_out from ha-m/day to m3/s
    df["sim_q"] = df["flo_out"] * 10000.0 / 86400.0
    # Filter to outlet channel
    df = df[df["gis_id"] == OUTLET_GIS_ID].copy()
    return df.sort_values("date").reset_index(drop=True)


def read_basin_wb():
    """Read basin_wb_day.txt for precipitation only"""
    df = pd.read_csv(TXTINOUT / "basin_wb_day.txt", sep=r"\s+", skiprows=3, header=None, names=WB_COLS)
    df = df.rename(columns={"yr": "year", "mon": "month", "day": "day"})
    df["date"] = pd.to_datetime(df[["year", "month", "day"]])
    return df.sort_values("date").reset_index(drop=True)


def read_obs(station):
    path = OBS_DIR / f"{station}_discharge_2012_2022_daily.csv"
    df = pd.read_csv(path, parse_dates=["date"])
    df.columns = ["date", "discharge"]
    return df


def calc_metrics(sim, obs):
    """Calculate NSE, KGE, PBIAS, R2, RMSE"""
    mask = np.isfinite(sim) & np.isfinite(obs)
    s, o = sim[mask], obs[mask]
    if len(s) == 0:
        return {}
    
    # NSE
    nse = 1 - np.sum((s - o) ** 2) / np.sum((o - np.mean(o)) ** 2)
    
    # R2
    r = np.corrcoef(s, o)[0, 1]
    r2 = r ** 2
    
    # PBIAS
    pbias = 100 * np.sum(s - o) / np.sum(o)
    
    # RMSE
    rmse = np.sqrt(np.mean((s - o) ** 2))
    
    # KGE
    alpha = np.std(s) / np.std(o) if np.std(o) > 0 else 0
    beta = np.mean(s) / np.mean(o) if np.mean(o) > 0 else 0
    kge = 1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)
    
    return {
        "NSE": nse, "KGE": kge, "R2": r2,
        "PBIAS(%)": pbias, "RMSE": rmse, "n": len(s)
    }


def split_periods(df_sim, df_wb, df_obs):
    """Split into warmup, validation, calibration"""
    merged = pd.merge(df_sim[["date", "sim_q"]], df_wb[["date", "precip"]], on="date", how="inner")
    merged = pd.merge(merged, df_obs, on="date", how="inner")
    
    def _filter(years):
        if not years:
            return merged.iloc[0:0]
        return merged[merged["date"].dt.year.isin(years)].copy()
    
    return _filter(WARMUP_YEARS), _filter(VALIDATION_YEARS), _filter(CALIBRATION_YEARS)


def plot_daily(dates, sim, obs, precip, period_name, metrics, suffix=""):
    if len(dates) == 0:
        return
    fig, axes = plt.subplots(3, 1, figsize=(16, 9), gridspec_kw={'height_ratios': [1, 3, 1]}, sharex=True)
    
    # Precip (inverted Y)
    ax0 = axes[0]
    ax0.bar(dates, precip, color="#2457ce", alpha=0.6, width=1.0, label='降水')
    ax0.set_ylabel('降水 (mm)', fontsize=10)
    if len(precip) > 0 and np.max(precip) > 0:
        ax0.set_ylim(np.max(precip) * 1.2, 0)
    ax0.legend(loc='upper right', fontsize=9)
    ax0.grid(True, linestyle='--', alpha=0.4)
    
    # Flow
    ax1 = axes[1]
    ax1.plot(dates, obs, color='#1f77b4', linewidth=0.9, label='实测', alpha=0.9)
    ax1.plot(dates, sim, color='#ff7f0e', linewidth=0.8, label='模拟', alpha=0.8)
    ax1.fill_between(dates, obs, alpha=0.1, color='#1f77b4')
    title = f'{STATION_NAME} {period_name} 日流量对比 (basin wateryld proxy)'
    ax1.set_title(title, fontsize=14, fontweight='bold')
    ax1.set_ylabel('流量 (m³/s)', fontsize=11)
    ax1.legend(loc='lower left', bbox_to_anchor=(0.02, 0.10), fontsize=10, framealpha=0.9)
    ax1.grid(True, linestyle='--', alpha=0.4)
    text = (f"NSE={metrics['NSE']:.3f}\n"
            f"KGE={metrics['KGE']:.3f}\n"
            f"PBIAS={metrics['PBIAS(%)']:+.1f}%\n"
            f"R²={metrics['R2']:.3f}\n"
            f"RMSE={metrics['RMSE']:.2f}")
    props = dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.8)
    ax1.text(0.98, 0.97, text, transform=ax1.transAxes, fontsize=9,
             verticalalignment='top', horizontalalignment='right', bbox=props)
    
    # Residuals
    ax2 = axes[2]
    residuals = sim - obs
    colors = ['#ff7f0e' if r > 0 else '#1f77b4' for r in residuals]
    ax2.bar(dates, residuals, color=colors, alpha=0.6, width=1.0)
    ax2.axhline(y=0, color='black', linewidth=0.5)
    ax2.set_ylabel('残差 (m³/s)', fontsize=10)
    ax2.set_xlabel('日期', fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.4)
    
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    safe = period_name.replace(' ', '_').replace('(', '').replace(')', '')
    path = OUT_DIR / f'{STATION_NAME}_daily_{safe}{suffix}.png'
    fig.savefig(path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Daily -> {path}")


def plot_combined_daily(val_df, cal_df, val_metrics, cal_metrics):
    """Combined validation + calibration plot"""
    if len(val_df) == 0 and len(cal_df) == 0:
        return
    
    merged = pd.concat([val_df, cal_df]).sort_values("date").reset_index(drop=True)
    dates = merged["date"].tolist()
    sim = merged["sim_q"].values
    obs = merged["discharge"].values
    precip = merged["precip"].values
    split_date = date(2018, 1, 1)
    
    fig, axes = plt.subplots(3, 1, figsize=(18, 9), gridspec_kw={'height_ratios': [1, 3, 1]}, sharex=True)
    
    # Precip
    ax0 = axes[0]
    ax0.bar(dates, precip, color="#2457ce", alpha=0.6, width=1.0, label='降水')
    ax0.set_ylabel('降水 (mm)', fontsize=10)
    if len(precip) > 0 and np.max(precip) > 0:
        ax0.set_ylim(np.max(precip) * 1.2, 0)
    ax0.legend(loc='upper right', fontsize=9)
    ax0.grid(True, linestyle='--', alpha=0.4)
    ax0.axvline(x=split_date, color='gray', linestyle='--', linewidth=1.2, alpha=0.8)
    
    # Flow
    ax1 = axes[1]
    ax1.plot(dates, obs, color='#1f77b4', linewidth=0.9, label='实测', alpha=0.9)
    ax1.plot(dates, sim, color='#ff7f0e', linewidth=0.8, label='模拟', alpha=0.8)
    ax1.fill_between(dates, obs, alpha=0.1, color='#1f77b4')
    ax1.set_title(f'{STATION_NAME} 全时段日流量对比（验证期 + 率定期）\n(basin wateryld proxy)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('流量 (m³/s)', fontsize=11)
    ax1.legend(loc='lower left', bbox_to_anchor=(0.02, 0.10), fontsize=10, framealpha=0.9)
    ax1.grid(True, linestyle='--', alpha=0.4)
    ax1.axvline(x=split_date, color='gray', linestyle='--', linewidth=1.2, alpha=0.8)
    ylim = ax1.get_ylim()
    label_y = ylim[1] - (ylim[1] - ylim[0]) * 0.05
    ax1.text(split_date - pd.Timedelta(days=60), label_y, '验证期', fontsize=10, color='gray', ha='right', va='top', fontweight='bold')
    ax1.text(split_date + pd.Timedelta(days=60), label_y, '率定期', fontsize=10, color='gray', ha='left', va='top', fontweight='bold')
    
    # Validation metrics (left)
    if val_metrics:
        val_text = (f"验证期 ({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]})\n"
                    f"NSE={val_metrics['NSE']:.3f}\n"
                    f"KGE={val_metrics['KGE']:.3f}\n"
                    f"PBIAS={val_metrics['PBIAS(%)']:+.1f}%\n"
                    f"R²={val_metrics['R2']:.3f}\n"
                    f"RMSE={val_metrics['RMSE']:.2f}")
        ax1.text(0.02, 0.97, val_text, transform=ax1.transAxes, fontsize=9,
                 verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.7))
    
    # Calibration metrics (right)
    if cal_metrics:
        cal_text = (f"率定期 ({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]})\n"
                    f"NSE={cal_metrics['NSE']:.3f}\n"
                    f"KGE={cal_metrics['KGE']:.3f}\n"
                    f"PBIAS={cal_metrics['PBIAS(%)']:+.1f}%\n"
                    f"R²={cal_metrics['R2']:.3f}\n"
                    f"RMSE={cal_metrics['RMSE']:.2f}")
        ax1.text(0.98, 0.97, cal_text, transform=ax1.transAxes, fontsize=9,
                 verticalalignment='top', horizontalalignment='right',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.7))
    
    # Residuals
    ax2 = axes[2]
    residuals = sim - obs
    colors = ['#ff7f0e' if r > 0 else '#1f77b4' for r in residuals]
    ax2.bar(dates, residuals, color=colors, alpha=0.6, width=1.0)
    ax2.axhline(y=0, color='black', linewidth=0.5)
    ax2.set_ylabel('残差 (m³/s)', fontsize=10)
    ax2.set_xlabel('日期', fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.4)
    ax2.axvline(x=split_date, color='gray', linestyle='--', linewidth=1.2, alpha=0.8)
    
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    path = OUT_DIR / f'{STATION_NAME}_daily_combined.png'
    fig.savefig(path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Combined -> {path}")


def plot_scatter(obs, sim, period_name, metrics):
    if len(obs) == 0:
        return
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(obs, sim, s=8, alpha=0.4, color='#1f77b4', edgecolors='none')
    max_val = max(np.max(obs), np.max(sim)) * 1.1
    ax.plot([0, max_val], [0, max_val], 'k--', linewidth=1, alpha=0.6, label='1:1')
    ax.set_xlim(0, max_val)
    ax.set_ylim(0, max_val)
    ax.set_xlabel('实测 (m³/s)', fontsize=12)
    ax.set_ylabel('模拟 (m³/s)', fontsize=12)
    ax.set_title(f'{STATION_NAME} {period_name} 散点图', fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(loc='lower right')
    text = f"R²={metrics['R2']:.3f}\nNSE={metrics['NSE']:.3f}\nn={metrics['n']}"
    props = dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.8)
    ax.text(0.05, 0.95, text, transform=ax.transAxes, fontsize=10, verticalalignment='top', bbox=props)
    plt.tight_layout()
    safe = period_name.replace(' ', '_').replace('(', '').replace(')', '')
    path = OUT_DIR / f'{STATION_NAME}_scatter_{safe}.png'
    fig.savefig(path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Scatter -> {path}")


def plot_monthly(dates, sim, obs, period_name):
    if len(dates) == 0:
        return
    monthly = {}
    for d, s, o in zip(dates, sim, obs):
        key = (d.year, d.month)
        monthly.setdefault(key, {'sim': [], 'obs': []})
        monthly[key]['sim'].append(s)
        monthly[key]['obs'].append(o)
    keys = sorted(monthly.keys())
    labels = [f'{y}-{m:02d}' for y, m in keys]
    sim_m = [np.mean(monthly[k]['sim']) for k in keys]
    obs_m = [np.mean(monthly[k]['obs']) for k in keys]
    
    fig, ax = plt.subplots(figsize=(16, 5))
    x = np.arange(len(keys))
    width = 0.35
    ax.bar(x - width / 2, obs_m, width, label='实测', color='#1f77b4', alpha=0.8)
    ax.bar(x + width / 2, sim_m, width, label='模拟', color='#ff7f0e', alpha=0.8)
    ax.set_xlabel('月份', fontsize=11)
    ax.set_ylabel('月均流量 (m³/s)', fontsize=11)
    ax.set_title(f'{STATION_NAME} {period_name} 月均流量', fontsize=14, fontweight='bold')
    ax.set_xticks(x[::3])
    ax.set_xticklabels([labels[i] for i in range(0, len(labels), 3)], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.4, axis='y')
    plt.tight_layout()
    safe = period_name.replace(' ', '_').replace('(', '').replace(')', '')
    path = OUT_DIR / f'{STATION_NAME}_monthly_{safe}.png'
    fig.savefig(path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Monthly -> {path}")


def plot_water_balance(sim_df):
    """Annual water balance components"""
    sim_df["year"] = sim_df["date"].dt.year
    annual = sim_df.groupby("year").agg({
        "precip": "sum", "et": "sum", "wateryld": "sum",
        "perc": "sum", "snofall": "sum", "snomlt": "sum"
    })
    
    fig, ax = plt.subplots(figsize=(10, 5))
    x = annual.index
    ax.bar(x - 0.2, annual["precip"], 0.4, label="Precipitation", alpha=0.8)
    ax.bar(x + 0.2, annual["et"], 0.4, label="ET", alpha=0.8)
    ax.plot(x, annual["wateryld"], 'o-', color='red', label="Water Yield", linewidth=1.5)
    ax.set_xlabel("Year")
    ax.set_ylabel("Annual total (mm)")
    ax.set_title("Basin Water Balance (2012–2022)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path = OUT_DIR / "water_balance.png"
    fig.savefig(path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Water balance -> {path}")


def main():
    print("Reading channel_day.txt for outlet...")
    sim = read_channel_outlet()
    print(f"  Simulated days (outlet {OUTLET_GIS_ID}): {len(sim)}")
    
    print("Reading basin_wb_day.txt for precip...")
    wb = read_basin_wb()
    print(f"  Basin wb days: {len(wb)}")
    
    print(f"Reading observed: {STATION_NAME}...")
    obs = read_obs(STATION_NAME)
    print(f"  Observed days: {len(obs)}")
    
    # Water balance
    print("\nPlotting water balance...")
    plot_water_balance(wb)
    
    # Split periods
    warmup, val, cal = split_periods(sim, wb, obs)
    print(f"\nPeriod sizes: warmup={len(warmup)}, validation={len(val)}, calibration={len(cal)}")
    
    # Metrics
    val_m = calc_metrics(val["sim_q"].values, val["discharge"].values) if len(val) > 0 else {}
    cal_m = calc_metrics(cal["sim_q"].values, cal["discharge"].values) if len(cal) > 0 else {}
    
    # Daily plots
    print("\nPlotting daily hydrographs...")
    if len(val) > 0:
        plot_daily(val["date"].tolist(), val["sim_q"].values, val["discharge"].values,
                   val["precip"].values, "验证期", val_m)
        plot_scatter(val["discharge"].values, val["sim_q"].values, "验证期", val_m)
        plot_monthly(val["date"].tolist(), val["sim_q"].values, val["discharge"].values, "验证期")
    
    if len(cal) > 0:
        plot_daily(cal["date"].tolist(), cal["sim_q"].values, cal["discharge"].values,
                   cal["precip"].values, "率定期", cal_m)
        plot_scatter(cal["discharge"].values, cal["sim_q"].values, "率定期", cal_m)
        plot_monthly(cal["date"].tolist(), cal["sim_q"].values, cal["discharge"].values, "率定期")
    
    # Combined
    if len(val) > 0 or len(cal) > 0:
        plot_combined_daily(val, cal, val_m, cal_m)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"METRICS SUMMARY (outlet channel {OUTLET_GIS_ID})")
    print(f"{'='*50}")
    if val_m:
        print(f"Validation ({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]}):")
        print(f"  NSE={val_m['NSE']:.3f}  KGE={val_m['KGE']:.3f}  PBIAS={val_m['PBIAS(%)']:+.1f}%  R²={val_m['R2']:.3f}  RMSE={val_m['RMSE']:.2f}")
    if cal_m:
        print(f"Calibration ({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]}):")
        print(f"  NSE={cal_m['NSE']:.3f}  KGE={cal_m['KGE']:.3f}  PBIAS={cal_m['PBIAS(%)']:+.1f}%  R²={cal_m['R2']:.3f}  RMSE={cal_m['RMSE']:.2f}")
    print(f"\nAll figures saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
