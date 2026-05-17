#!/usr/bin/env python3
"""
可视化最佳校准结果 (alpha=0.02)
参考: /workspace/run_workflow_deli9.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date, timedelta

# ============ CONFIG ============
PROJECT_ROOT = '/workspace/hongxin_swaw_plus'
TXTINOUT = os.path.join(PROJECT_ROOT, 'output/TxtInOut')
OBS_CSV = os.path.join(PROJECT_ROOT, 'datasets/processed_hydro/镇西_discharge_2012_2022_daily.csv')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'visualization_best')
PLOT_DPI = 200
STATION_NAME = '镇西'

# 时期划分
WARMUP_YEARS = list(range(2012, 2015))
VALIDATION_YEARS = list(range(2015, 2018))
CALIBRATION_YEARS = list(range(2018, 2023))

# 字体配置
plt.rcParams['font.sans-serif'] = [
    'PingFang SC', 'PingFang HK', 'Hiragino Sans GB', 'STHeiti',
    'Heiti TC', 'Microsoft YaHei', 'SimHei', 'Lantinghei SC',
    'Noto Sans CJK JP',
    'DejaVu Sans'
]
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'


def read_simulated_channel(filepath):
    """读取 channel_day.txt 流量数据，返回 {date: flo_m3s}"""
    data = {}
    with open(filepath, 'r') as f:
        for _ in range(3):
            next(f)
        for line in f:
            parts = line.split()
            if len(parts) > 7:
                try:
                    gis_id = int(parts[5])
                    if gis_id == 303:  # 出口 channel
                        d = date(int(parts[3]), int(parts[1]), int(parts[2]))
                        flo_ham = float(parts[7])  # ha-m/day
                        flo_m3s = flo_ham * 10000.0 / 86400.0
                        data[d] = flo_m3s
                except (ValueError, IndexError):
                    continue
    return data


def read_precip(filepath):
    """从 basin_wb_day.txt 读取日降水 (mm)"""
    data = {}
    with open(filepath, 'r') as f:
        for _ in range(3):
            next(f)
        for line in f:
            parts = line.split()
            if len(parts) > 7:
                try:
                    d = date(int(parts[3]), int(parts[1]), int(parts[2]))
                    precip = float(parts[7])
                    data[d] = precip
                except (ValueError, IndexError):
                    continue
    return data


def read_observed(filepath):
    """读取观测流量 CSV"""
    data = {}
    df = pd.read_csv(filepath, parse_dates=['date'])
    for _, row in df.iterrows():
        d = row['date'].date()
        data[d] = float(row['discharge'])
    return data


def calc_nse(obs, sim):
    denom = np.sum((obs - np.mean(obs)) ** 2)
    return float('nan') if denom == 0 else 1.0 - np.sum((obs - sim) ** 2) / denom


def calc_kge(obs, sim):
    if len(obs) < 2 or np.std(obs) == 0:
        return float('nan')
    r = np.corrcoef(obs, sim)[0, 1]
    return 1.0 - np.sqrt((r - 1) ** 2 + (np.std(sim)/np.std(obs) - 1) ** 2 + (np.mean(sim)/np.mean(obs) - 1) ** 2)


def calc_pbias(obs, sim):
    s = np.sum(obs)
    return float('nan') if s == 0 else 100.0 * np.sum(sim - obs) / s


def calc_r2(obs, sim):
    if len(obs) < 2:
        return float('nan')
    r = np.corrcoef(obs, sim)[0, 1]
    return r ** 2


def calc_rmse(obs, sim):
    return np.sqrt(np.mean((obs - sim) ** 2))


def evaluate(obs, sim):
    return {
        'NSE': calc_nse(obs, sim),
        'KGE': calc_kge(obs, sim),
        'PBIAS(%)': calc_pbias(obs, sim),
        'R2': calc_r2(obs, sim),
        'RMSE': calc_rmse(obs, sim),
        'n': len(obs),
        'obs_mean': float(np.mean(obs)),
        'sim_mean': float(np.mean(sim)),
    }


def align_data(sim_data, obs_data, precip_data, years):
    dates, sim_vals, obs_vals, precip_vals = [], [], [], []
    for d in sorted(set(sim_data.keys()) & set(obs_data.keys())):
        if d.year in years:
            dates.append(d)
            sim_vals.append(sim_data[d])
            obs_vals.append(obs_data[d])
            precip_vals.append(precip_data.get(d, 0.0))
    return dates, np.array(sim_vals), np.array(obs_vals), np.array(precip_vals)


def plot_daily(dates, sim, obs, precip, period_name, metrics, output_dir):
    if len(dates) == 0:
        return
    fig, axes = plt.subplots(3, 1, figsize=(16, 9),
                             gridspec_kw={'height_ratios': [1, 3, 1]}, sharex=True)

    # 降水子图（倒置Y轴）
    ax0 = axes[0]
    ax0.bar(dates, precip, color="#2457ce", alpha=0.6, width=1.0, label='降水')
    ax0.set_ylabel('降水 (mm)', fontsize=10)
    if len(precip) > 0 and np.max(precip) > 0:
        ax0.set_ylim(np.max(precip) * 1.2, 0)
    ax0.legend(loc='upper right', fontsize=9)
    ax0.grid(True, linestyle='--', alpha=0.4)

    # 流量子图
    ax1 = axes[1]
    ax1.plot(dates, obs, color='#1f77b4', linewidth=0.9, label='实测', alpha=0.9)
    ax1.plot(dates, sim, color='#ff7f0e', linewidth=0.8, label='模拟', alpha=0.8)
    ax1.fill_between(dates, obs, alpha=0.1, color='#1f77b4')
    ax1.set_title(f'{STATION_NAME} {period_name} 日流量对比', fontsize=14, fontweight='bold')
    ax1.set_ylabel('流量 (m³/s)', fontsize=11)
    ax1.legend(loc='lower left', bbox_to_anchor=(0.02, 0.10), fontsize=10, framealpha=0.9)
    ax1.grid(True, linestyle='--', alpha=0.4)
    text = (f"NSE={metrics['NSE']:.3f}\nKGE={metrics['KGE']:.3f}\n"
            f"PBIAS={metrics['PBIAS(%)']:+.1f}%\nR²={metrics['R2']:.3f}\nRMSE={metrics['RMSE']:.2f}")
    props = dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.8)
    ax1.text(0.98, 0.97, text, transform=ax1.transAxes, fontsize=9,
             verticalalignment='top', horizontalalignment='right', bbox=props)

    # 残差子图
    ax2 = axes[2]
    residuals = sim - obs
    colors = ['#ff7f0e' if r > 0 else '#1f77b4' for r in residuals]
    ax2.bar(dates, residuals, color=colors, alpha=0.6, width=1.0)
    ax2.axhline(y=0, color='black', linewidth=0.5)
    ax2.set_ylabel('残差 (m³/s)', fontsize=10)
    ax2.set_xlabel('日期', fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.4)

    # X轴格式
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    safe = period_name.replace(' ', '_').replace('(', '').replace(')', '')
    path = os.path.join(output_dir, f'{STATION_NAME}_daily_{safe}.png')
    fig.savefig(path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Daily -> {path}")


def plot_combined_daily(cal_dates, cal_sim, cal_obs, cal_precip, cal_metrics,
                         val_dates, val_sim, val_obs, val_precip, val_metrics,
                         output_dir):
    if len(cal_dates) == 0 and len(val_dates) == 0:
        return

    all_dates = list(cal_dates) + list(val_dates)
    all_sim = np.concatenate([cal_sim, val_sim]) if len(cal_sim) > 0 and len(val_sim) > 0 else (
              cal_sim if len(cal_sim) > 0 else val_sim)
    all_obs = np.concatenate([cal_obs, val_obs]) if len(cal_obs) > 0 and len(val_obs) > 0 else (
              cal_obs if len(cal_obs) > 0 else val_obs)
    all_precip = np.concatenate([cal_precip, val_precip]) if len(cal_precip) > 0 and len(val_precip) > 0 else (
                 cal_precip if len(cal_precip) > 0 else val_precip)

    if len(all_dates) > 0:
        sort_idx = np.argsort([d.toordinal() for d in all_dates])
        all_dates = [all_dates[i] for i in sort_idx]
        all_sim = all_sim[sort_idx]
        all_obs = all_obs[sort_idx]
        all_precip = all_precip[sort_idx]

    split_date = date(2018, 1, 1)

    fig, axes = plt.subplots(3, 1, figsize=(18, 9),
                             gridspec_kw={'height_ratios': [1, 3, 1]}, sharex=True)

    # 降水子图
    ax0 = axes[0]
    ax0.bar(all_dates, all_precip, color="#2457ce", alpha=0.6, width=1.0, label='降水')
    ax0.set_ylabel('降水 (mm)', fontsize=10)
    if len(all_precip) > 0 and np.max(all_precip) > 0:
        ax0.set_ylim(np.max(all_precip) * 1.2, 0)
    ax0.legend(loc='upper right', fontsize=9)
    ax0.grid(True, linestyle='--', alpha=0.4)
    if split_date >= min(all_dates) and split_date <= max(all_dates):
        ax0.axvline(x=split_date, color='gray', linestyle='--', linewidth=1.2, alpha=0.8)

    # 流量子图
    ax1 = axes[1]
    ax1.plot(all_dates, all_obs, color='#1f77b4', linewidth=0.9, label='实测', alpha=0.9)
    ax1.plot(all_dates, all_sim, color='#ff7f0e', linewidth=0.8, label='模拟', alpha=0.8)
    ax1.fill_between(all_dates, all_obs, alpha=0.1, color='#1f77b4')
    ax1.set_title(f'{STATION_NAME} 全时段日流量对比（验证期 + 率定期）', fontsize=14, fontweight='bold')
    ax1.set_ylabel('流量 (m³/s)', fontsize=11)
    ax1.legend(loc='lower left', bbox_to_anchor=(0.02, 0.10), fontsize=10, framealpha=0.9)
    ax1.grid(True, linestyle='--', alpha=0.4)

    if split_date >= min(all_dates) and split_date <= max(all_dates):
        ax1.axvline(x=split_date, color='gray', linestyle='--', linewidth=1.2, alpha=0.8)
        ylim = ax1.get_ylim()
        label_y = ylim[1] - (ylim[1] - ylim[0]) * 0.05
        ax1.text(split_date - timedelta(days=60), label_y, '验证期',
                 fontsize=10, color='gray', ha='right', va='top', fontweight='bold')
        ax1.text(split_date + timedelta(days=60), label_y, '率定期',
                 fontsize=10, color='gray', ha='left', va='top', fontweight='bold')

    # 验证期指标框（左侧）
    if val_metrics:
        val_text = (f"验证期 ({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]})\n"
                    f"NSE={val_metrics['NSE']:.3f}\n"
                    f"KGE={val_metrics['KGE']:.3f}\n"
                    f"PBIAS={val_metrics['PBIAS(%)']:+.1f}%\n"
                    f"R²={val_metrics['R2']:.3f}\n"
                    f"RMSE={val_metrics['RMSE']:.2f}")
        props_val = dict(boxstyle='round,pad=0.5', facecolor='#e6f2ff', alpha=0.9)
        ax1.text(0.02, 0.97, val_text, transform=ax1.transAxes, fontsize=9,
                 verticalalignment='top', horizontalalignment='left', bbox=props_val)

    # 率定期指标框（右侧）
    if cal_metrics:
        cal_text = (f"率定期 ({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]})\n"
                    f"NSE={cal_metrics['NSE']:.3f}\n"
                    f"KGE={cal_metrics['KGE']:.3f}\n"
                    f"PBIAS={cal_metrics['PBIAS(%)']:+.1f}%\n"
                    f"R²={cal_metrics['R2']:.3f}\n"
                    f"RMSE={cal_metrics['RMSE']:.2f}")
        props_cal = dict(boxstyle='round,pad=0.5', facecolor='#fff2e6', alpha=0.9)
        ax1.text(0.98, 0.97, cal_text, transform=ax1.transAxes, fontsize=9,
                 verticalalignment='top', horizontalalignment='right', bbox=props_cal)

    # 残差子图
    ax2 = axes[2]
    residuals = all_sim - all_obs
    colors = ['#ff7f0e' if r > 0 else '#1f77b4' for r in residuals]
    ax2.bar(all_dates, residuals, color=colors, alpha=0.6, width=1.0)
    ax2.axhline(y=0, color='black', linewidth=0.5)
    ax2.set_ylabel('残差 (m³/s)', fontsize=10)
    ax2.set_xlabel('日期', fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.4)
    if split_date >= min(all_dates) and split_date <= max(all_dates):
        ax2.axvline(x=split_date, color='gray', linestyle='--', linewidth=1.2, alpha=0.8)

    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    path = os.path.join(output_dir, f'{STATION_NAME}_daily_全时段.png')
    fig.savefig(path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Combined Daily -> {path}")


def plot_scatter(obs, sim, period_name, metrics, output_dir):
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
    ax.text(0.05, 0.95, text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)
    plt.tight_layout()
    safe = period_name.replace(' ', '_').replace('(', '').replace(')', '')
    path = os.path.join(output_dir, f'{STATION_NAME}_scatter_{safe}.png')
    fig.savefig(path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Scatter -> {path}")


def plot_monthly(dates, sim, obs, period_name, metrics, output_dir):
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
    path = os.path.join(output_dir, f'{STATION_NAME}_monthly_{safe}.png')
    fig.savefig(path, dpi=PLOT_DPI)
    plt.close(fig)
    print(f"  [plot] Monthly -> {path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 使用 alpha=0.02 实验结果
    sim_file = os.path.join(TXTINOUT, 'channel_day_alpha002.txt')
    precip_file = os.path.join(TXTINOUT, 'basin_wb_day.txt')

    print("=" * 60)
    print(" 最佳参数可视化 (alpha=0.02)")
    print("=" * 60)

    print("\n[1/3] 读取数据...")
    sim_data = read_simulated_channel(sim_file)
    obs_data = read_observed(OBS_CSV)
    precip_data = read_precip(precip_file)
    print(f"  Simulated: {len(sim_data)} days")
    print(f"  Observed:  {len(obs_data)} days")
    print(f"  Precip:    {len(precip_data)} days")

    print("\n[2/3] 计算指标...")
    cal_dates, cal_sim, cal_obs, cal_precip = align_data(sim_data, obs_data, precip_data, CALIBRATION_YEARS)
    val_dates, val_sim, val_obs, val_precip = align_data(sim_data, obs_data, precip_data, VALIDATION_YEARS)

    cal_metrics = evaluate(cal_obs, cal_sim) if len(cal_dates) > 0 else {}
    val_metrics = evaluate(val_obs, val_sim) if len(val_dates) > 0 else {}

    print("-" * 50)
    if cal_metrics:
        print(f"率定期 ({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]}):")
        for k in ['NSE', 'KGE', 'PBIAS(%)', 'R2', 'RMSE']:
            print(f"  {k:>10} = {cal_metrics.get(k, float('nan')):.4f}")
    if val_metrics:
        print(f"\n验证期 ({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]}):")
        for k in ['NSE', 'KGE', 'PBIAS(%)', 'R2', 'RMSE']:
            print(f"  {k:>10} = {val_metrics.get(k, float('nan')):.4f}")
    print("-" * 50)

    print("\n[3/3] 生成图表...")
    if cal_metrics:
        plot_daily(cal_dates, cal_sim, cal_obs, cal_precip,
                   f'率定期({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]})', cal_metrics, OUTPUT_DIR)
        plot_scatter(cal_obs, cal_sim,
                     f'率定期({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]})', cal_metrics, OUTPUT_DIR)
        plot_monthly(cal_dates, cal_sim, cal_obs,
                     f'率定期({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]})', cal_metrics, OUTPUT_DIR)

    if val_metrics:
        plot_daily(val_dates, val_sim, val_obs, val_precip,
                   f'验证期({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]})', val_metrics, OUTPUT_DIR)
        plot_scatter(val_obs, val_sim,
                     f'验证期({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]})', val_metrics, OUTPUT_DIR)
        plot_monthly(val_dates, val_sim, val_obs,
                     f'验证期({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]})', val_metrics, OUTPUT_DIR)

    if cal_metrics or val_metrics:
        plot_combined_daily(cal_dates, cal_sim, cal_obs, cal_precip, cal_metrics,
                            val_dates, val_sim, val_obs, val_precip, val_metrics,
                            OUTPUT_DIR)

    print(f"\n输出目录: {OUTPUT_DIR}")
    print("=" * 60)
    print("Done!")


if __name__ == '__main__':
    main()
