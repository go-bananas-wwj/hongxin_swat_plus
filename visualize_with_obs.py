#!/usr/bin/env python3
"""
Hongxin SWAT+ Visualization with Observed Data (Zhenxi Station)
===============================================================
对比 SWAT+ 模拟出口流量 (cha0302) 与镇西站实测流量。
"""

import os
import subprocess
from datetime import datetime, date
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ============ CONFIG ============
TXTINOUT = '/workspace/hongxin_swaw_plus/output/TxtInOut'
OUTPUT_DIR = '/workspace/hongxin_swaw_plus/figures'
OBS_FILE = '/workspace/hongxin_swaw_plus/datasets/processed_hydro/镇西_discharge_2012_2022_daily.csv'
PLOT_DPI = 200

WATERSHED_AREA_HA = 783181.0
MM_DAY_TO_M3S = WATERSHED_AREA_HA * 10.0 / 86400.0


def read_observed_data(filepath):
    """读取镇西站实测流量 (m³/s)"""
    data = {}
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                d = datetime.strptime(parts[0], '%Y-%m-%d').date()
                q = float(parts[1])
                data[d] = q
    return data


def read_basin_wb():
    """读取 basin_wb_day.txt"""
    filepath = os.path.join(TXTINOUT, 'basin_wb_day.txt')
    data = []
    with open(filepath, 'r') as f:
        next(f); next(f)
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 28 and parts[4] == '1':
                d = date(int(parts[3]), int(parts[1]), int(parts[2]))
                data.append({
                    'date': d,
                    'precip': float(parts[7]),
                    'et': float(parts[14]),
                    'wateryld': float(parts[12]),
                })
    return data


def extract_channel_data(channel_name, outfile):
    infile = os.path.join(TXTINOUT, 'channel_day.txt')
    cmd = f"awk '$7==\"{channel_name}\" {{print $1,$2,$3,$4,$8,$9}}' {infile} > {outfile}"
    subprocess.run(cmd, shell=True, check=True)


def read_channel_csv(filepath):
    data = {}
    with open(filepath, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 6:
                d = date(int(parts[3]), int(parts[1]), int(parts[2]))
                flo_out = float(parts[5]) * 10000.0 / 86400.0  # ha-m/day -> m3/s
                data[d] = flo_out
    return data


def calc_metrics(obs, sim):
    mask = (~np.isnan(obs)) & (~np.isnan(sim))
    o = obs[mask]
    s = sim[mask]
    if len(o) == 0:
        return {'NSE': np.nan, 'KGE': np.nan, 'PBIAS(%)': np.nan,
                'R2': np.nan, 'RMSE': np.nan, 'n': 0}
    obs_mean = np.mean(o)
    ss_tot = np.sum((o - obs_mean) ** 2)
    ss_res = np.sum((o - s) ** 2)
    nse = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    rmse = np.sqrt(np.mean((o - s) ** 2))
    pbias = (np.mean(s) - obs_mean) / obs_mean * 100 if obs_mean > 0 else 0
    r = np.corrcoef(o, s)[0, 1] if len(o) > 1 else 0
    r2 = r ** 2
    beta = np.mean(s) / obs_mean if obs_mean > 0 else 0
    gamma = (np.std(s) / np.mean(s)) / (np.std(o) / obs_mean) if obs_mean > 0 and np.std(o) > 0 else 0
    kge = 1 - np.sqrt((r - 1) ** 2 + (beta - 1) ** 2 + (gamma - 1) ** 2)
    return {'NSE': nse, 'KGE': kge, 'PBIAS(%)': pbias, 'R2': r2, 'RMSE': rmse, 'n': len(o)}


def setup_plt():
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False


def plot_daily_combined(dates, obs, sim, proxy, precip, metrics, output_path):
    fig, axes = plt.subplots(3, 1, figsize=(18, 10),
                             gridspec_kw={'height_ratios': [1, 3, 1]}, sharex=True)

    # 降水
    ax0 = axes[0]
    ax0.bar(dates, precip, color="#2457ce", alpha=0.6, width=1.0, label='Precipitation')
    ax0.set_ylabel('Precip (mm)', fontsize=10)
    if len(precip) > 0 and np.max(precip) > 0:
        ax0.set_ylim(np.max(precip) * 1.2, 0)
    ax0.legend(loc='upper right', fontsize=9)
    ax0.grid(True, linestyle='--', alpha=0.4)

    # 流量对比
    ax1 = axes[1]
    ax1.plot(dates, obs, color='#2ca02c', linewidth=0.9, label='Observed (Zhenxi)', alpha=0.9)
    ax1.plot(dates, sim, color='#ff7f0e', linewidth=0.8, label='Simulated (cha0302)', alpha=0.8)
    ax1.plot(dates, proxy, color='#1f77b4', linewidth=0.6, label='Basin Proxy', alpha=0.5)
    ax1.fill_between(dates, obs, alpha=0.05, color='#2ca02c')
    ax1.set_title('Hongxin Daily Streamflow: Observed vs Simulated (2012-2022)',
                  fontsize=14, fontweight='bold')
    ax1.set_ylabel('Discharge (m³/s)', fontsize=11)
    ax1.legend(loc='upper right', fontsize=10, framealpha=0.9)
    ax1.grid(True, linestyle='--', alpha=0.4)

    text = (f"NSE={metrics['NSE']:.3f}\n"
            f"KGE={metrics['KGE']:.3f}\n"
            f"PBIAS={metrics['PBIAS(%)']:+.1f}%\n"
            f"R²={metrics['R2']:.3f}\n"
            f"RMSE={metrics['RMSE']:.2f}")
    props = dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.8)
    ax1.text(0.98, 0.97, text, transform=ax1.transAxes, fontsize=9,
             verticalalignment='top', horizontalalignment='right', bbox=props)

    # 残差
    ax2 = axes[2]
    residuals = sim - obs
    colors = ['#ff7f0e' if r > 0 else '#2ca02c' for r in residuals]
    ax2.bar(dates, residuals, color=colors, alpha=0.6, width=1.0)
    ax2.axhline(y=0, color='black', linewidth=0.5)
    ax2.set_ylabel('Residual (Sim - Obs, m³/s)', fontsize=10)
    ax2.set_xlabel('Date', fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.4)

    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    fig.savefig(output_path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Daily Combined -> {output_path}")


def plot_monthly(dates, obs, sim, output_path):
    monthly = {}
    for d, o, s in zip(dates, obs, sim):
        key = (d.year, d.month)
        monthly.setdefault(key, {'obs': [], 'sim': []})
        monthly[key]['obs'].append(o)
        monthly[key]['sim'].append(s)

    keys = sorted(monthly.keys())
    labels = [f'{y}-{m:02d}' for y, m in keys]
    obs_m = [np.mean(monthly[k]['obs']) for k in keys]
    sim_m = [np.mean(monthly[k]['sim']) for k in keys]

    fig, ax = plt.subplots(figsize=(16, 5))
    x = np.arange(len(keys))
    width = 0.35
    ax.bar(x - width / 2, obs_m, width, label='Observed', color='#2ca02c', alpha=0.8)
    ax.bar(x + width / 2, sim_m, width, label='Simulated', color='#ff7f0e', alpha=0.8)
    ax.set_xlabel('Month', fontsize=11)
    ax.set_ylabel('Monthly Avg. Discharge (m³/s)', fontsize=11)
    ax.set_title('Hongxin Monthly Streamflow: Observed vs Simulated', fontsize=14, fontweight='bold')
    ax.set_xticks(x[::3])
    ax.set_xticklabels([labels[i] for i in range(0, len(labels), 3)], rotation=45, ha='right')
    ax.legend(fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.4, axis='y')
    plt.tight_layout()
    fig.savefig(output_path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Monthly -> {output_path}")


def plot_scatter(obs, sim, output_path):
    mask = (~np.isnan(obs)) & (~np.isnan(sim)) & (obs >= 0) & (sim >= 0)
    o = obs[mask]
    s = sim[mask]
    if len(o) == 0:
        print("  [skip] Scatter -> no valid data")
        return
    metrics = calc_metrics(o, s)
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(o, s, s=8, alpha=0.4, color='#1f77b4', edgecolors='none')
    max_val = max(np.max(o), np.max(s)) * 1.1
    ax.plot([0, max_val], [0, max_val], 'k--', linewidth=1, alpha=0.6, label='1:1')
    ax.set_xlim(0, max_val)
    ax.set_ylim(0, max_val)
    ax.set_xlabel('Observed (m³/s)', fontsize=12)
    ax.set_ylabel('Simulated (m³/s)', fontsize=12)
    ax.set_title('Hongxin Scatter (2012-2022)', fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(loc='lower right')
    text = f"R²={metrics['R2']:.3f}\nNSE={metrics['NSE']:.3f}\nn={metrics['n']}"
    props = dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.8)
    ax.text(0.05, 0.95, text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)
    plt.tight_layout()
    fig.savefig(output_path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Scatter -> {output_path}")


def plot_flow_duration(obs, sim, output_path):
    o_sorted = np.sort(obs[~np.isnan(obs)])[::-1]
    s_sorted = np.sort(sim[~np.isnan(sim)])[::-1]
    if len(o_sorted) == 0 or len(s_sorted) == 0:
        print("  [skip] Flow Duration -> no valid data")
        return
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(np.arange(1, len(o_sorted)+1) / len(o_sorted) * 100, o_sorted,
            color='#2ca02c', linewidth=1.5, label='Observed')
    ax.plot(np.arange(1, len(s_sorted)+1) / len(s_sorted) * 100, s_sorted,
            color='#ff7f0e', linewidth=1.5, label='Simulated')
    ax.set_xlabel('Exceedance Probability (%)', fontsize=12)
    ax.set_ylabel('Discharge (m³/s)', fontsize=12)
    ax.set_title('Flow Duration Curve', fontsize=14, fontweight='bold')
    ax.set_yscale('log')
    ax.legend(fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()
    fig.savefig(output_path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Flow Duration -> {output_path}")


def main():
    setup_plt()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 60)
    print("Hongxin SWAT+ Visualization with Zhenxi Observed Data")
    print("=" * 60)

    # 1. 读取观测数据
    print("\n[1/4] Reading observed data...")
    obs_data = read_observed_data(OBS_FILE)
    print(f"  Observed records: {len(obs_data)}")

    # 2. 读取 basin 数据
    print("\n[2/4] Reading basin data...")
    basin_data = read_basin_wb()
    print(f"  Basin records: {len(basin_data)}")

    # 3. 读取模拟出口流量
    print("\n[3/4] Reading simulated outlet data...")
    tmp = os.path.join(OUTPUT_DIR, 'cha0302.csv')
    extract_channel_data('cha0302', tmp)
    sim_data = read_channel_csv(tmp)
    os.remove(tmp)
    print(f"  Simulated records: {len(sim_data)}")

    # 4. 对齐数据
    print("\n[4/4] Aligning and plotting...")
    dates = [d['date'] for d in basin_data]
    precip = np.array([d['precip'] for d in basin_data])
    proxy = np.array([d['wateryld'] for d in basin_data]) * MM_DAY_TO_M3S

    obs_arr = np.array([obs_data.get(d, np.nan) for d in dates])
    sim_arr = np.array([sim_data.get(d, np.nan) for d in dates])

    metrics = calc_metrics(obs_arr, sim_arr)
    print(f"  Metrics (Sim vs Obs): NSE={metrics['NSE']:.3f}, KGE={metrics['KGE']:.3f}, "
          f"PBIAS={metrics['PBIAS(%)']:+.1f}%, R²={metrics['R2']:.3f}")

    plot_daily_combined(
        dates, obs_arr, sim_arr, proxy, precip, metrics,
        os.path.join(OUTPUT_DIR, 'hongxin_daily_obs_vs_sim.png')
    )
    plot_monthly(
        dates, obs_arr, sim_arr,
        os.path.join(OUTPUT_DIR, 'hongxin_monthly_obs_vs_sim.png')
    )
    plot_scatter(
        obs_arr, sim_arr,
        os.path.join(OUTPUT_DIR, 'hongxin_scatter_obs_vs_sim.png')
    )
    plot_flow_duration(
        obs_arr, sim_arr,
        os.path.join(OUTPUT_DIR, 'hongxin_flow_duration.png')
    )

    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("=" * 60)
    print("Done!")


if __name__ == '__main__':
    main()
