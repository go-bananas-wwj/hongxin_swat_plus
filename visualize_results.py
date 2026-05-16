#!/usr/bin/env python3
"""
SWAT+ 结果可视化
参考 /workspace/run_workflow_deli9.py 的图表风格
"""

import os, sys, csv, math
from datetime import datetime, date, timedelta
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ============ CONFIG ============
PROJECT_ROOT = '/workspace/hongxin_swaw_plus'
TXTINOUT = os.path.join(PROJECT_ROOT, 'output', 'TxtInOut')
OBS_CSV = os.path.join(PROJECT_ROOT, 'datasets', 'processed_hydro', '镇西_discharge_2012_2022_daily.csv')
CHANNEL_NAME = 'cha0302'
STATION_NAME = '镇西'
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'visualization')
PLOT_DPI = 200

# 时期划分（参考 deli9）
CALIBRATION_YEARS = list(range(2018, 2023))   # 率定期 2018-2022
VALIDATION_YEARS = list(range(2015, 2018))    # 验证期 2015-2017
SPLIT_DATE = date(2018, 1, 1)

# ============ 指标计算 ============
def calc_nse(obs, sim):
    denom = np.sum((obs - np.mean(obs)) ** 2)
    return float('nan') if denom == 0 else 1.0 - np.sum((obs - sim) ** 2) / denom

def calc_kge(obs, sim):
    if len(obs) < 2 or np.std(obs) == 0:
        return float('nan')
    r = np.corrcoef(obs, sim)[0, 1]
    return 1.0 - math.sqrt((r - 1) ** 2 + (np.std(sim)/np.std(obs) - 1) ** 2 + (np.mean(sim)/np.mean(obs) - 1) ** 2)

def calc_pbias(obs, sim):
    s = np.sum(obs)
    return float('nan') if s == 0 else 100.0 * np.sum(sim - obs) / s

def calc_r2(obs, sim):
    if len(obs) < 2:
        return float('nan')
    r = np.corrcoef(obs, sim)[0, 1]
    return r ** 2

def calc_rmse(obs, sim):
    return math.sqrt(np.mean((obs - sim) ** 2))

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

# ============ 数据读取 ============
def read_simulated(filepath, channel_name):
    """读取 channel_day.txt，返回 {date: flow_m3s}, {date: precip_mm}"""
    flow_data = {}
    with open(filepath, 'r') as f:
        for _ in range(2):
            next(f)
        for line in f:
            parts = line.split()
            if len(parts) > 8 and parts[6] == channel_name:
                d = date(int(parts[3]), int(parts[1]), int(parts[2]))
                # ha-m/day -> m3/s
                flow_ham = float(parts[8])
                flow_data[d] = flow_ham * 10000.0 / 86400.0
    return flow_data

def read_precip(filepath):
    """读取 basin_wb_day.txt，返回 {date: precip_mm}"""
    precip_data = {}
    with open(filepath, 'r') as f:
        for _ in range(2):
            next(f)
        for line in f:
            parts = line.split()
            if len(parts) > 7:
                try:
                    d = date(int(parts[3]), int(parts[1]), int(parts[2]))
                    precip_data[d] = float(parts[7])
                except (ValueError, IndexError):
                    continue
    return precip_data

def read_observed(filepath):
    data = {}
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row.get('date') or row.get('Date')
            flow_str = row.get('discharge') or row.get('flow') or row.get('observed') or row.get('flow_m3s')
            if date_str and flow_str and flow_str.strip():
                data[datetime.strptime(date_str.strip(), '%Y-%m-%d').date()] = float(flow_str.strip())
    return data

def align_data(sim_data, obs_data, precip_data, years=None):
    dates, sim_vals, obs_vals, precip_vals = [], [], [], []
    common_dates = sorted(set(sim_data.keys()) & set(obs_data.keys()))
    for d in common_dates:
        if years is None or d.year in years:
            dates.append(d)
            sim_vals.append(sim_data[d])
            obs_vals.append(obs_data[d])
            precip_vals.append(precip_data.get(d, 0.0))
    return dates, np.array(sim_vals), np.array(obs_vals), np.array(precip_vals)

# ============ 可视化设置 ============
def setup_plt():
    plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.family'] = 'sans-serif'

def plot_daily(dates, sim, obs, precip, period_name, metrics, output_dir):
    if len(dates) == 0:
        return
    fig, axes = plt.subplots(3, 1, figsize=(16, 9), gridspec_kw={'height_ratios': [1, 3, 1]}, sharex=True)

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
    text = f"NSE={metrics['NSE']:.3f}\nKGE={metrics['KGE']:.3f}\nPBIAS={metrics['PBIAS(%)']:+.1f}%\nR²={metrics['R2']:.3f}\nRMSE={metrics['RMSE']:.2f}"
    props = dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.8)
    ax1.text(0.98, 0.97, text, transform=ax1.transAxes, fontsize=9, verticalalignment='top', horizontalalignment='right', bbox=props)

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

def plot_combined_daily(all_dates, all_sim, all_obs, all_precip, cal_metrics, val_metrics, output_dir):
    if len(all_dates) == 0:
        return

    fig, axes = plt.subplots(3, 1, figsize=(18, 9), gridspec_kw={'height_ratios': [1, 3, 1]}, sharex=True)

    # 降水子图（倒置Y轴）
    ax0 = axes[0]
    ax0.bar(all_dates, all_precip, color="#2457ce", alpha=0.6, width=1.0, label='降水')
    ax0.set_ylabel('降水 (mm)', fontsize=10)
    if len(all_precip) > 0 and np.max(all_precip) > 0:
        ax0.set_ylim(np.max(all_precip) * 1.2, 0)
    ax0.legend(loc='upper right', fontsize=9)
    ax0.grid(True, linestyle='--', alpha=0.4)
    if SPLIT_DATE >= min(all_dates) and SPLIT_DATE <= max(all_dates):
        ax0.axvline(x=SPLIT_DATE, color='gray', linestyle='--', linewidth=1.2, alpha=0.8)

    # 流量子图
    ax1 = axes[1]
    ax1.plot(all_dates, all_obs, color='#1f77b4', linewidth=0.9, label='实测', alpha=0.9)
    ax1.plot(all_dates, all_sim, color='#ff7f0e', linewidth=0.8, label='模拟', alpha=0.8)
    ax1.fill_between(all_dates, all_obs, alpha=0.1, color='#1f77b4')
    ax1.set_title(f'{STATION_NAME} 全时段日流量对比（验证期 + 率定期）', fontsize=14, fontweight='bold')
    ax1.set_ylabel('流量 (m³/s)', fontsize=11)
    ax1.legend(loc='lower left', bbox_to_anchor=(0.02, 0.10), fontsize=10, framealpha=0.9)
    ax1.grid(True, linestyle='--', alpha=0.4)

    if SPLIT_DATE >= min(all_dates) and SPLIT_DATE <= max(all_dates):
        ax1.axvline(x=SPLIT_DATE, color='gray', linestyle='--', linewidth=1.2, alpha=0.8)
        ylim = ax1.get_ylim()
        label_y = ylim[1] - (ylim[1] - ylim[0]) * 0.05
        ax1.text(SPLIT_DATE - timedelta(days=60), label_y, '验证期',
                 fontsize=10, color='gray', ha='right', va='top', fontweight='bold')
        ax1.text(SPLIT_DATE + timedelta(days=60), label_y, '率定期',
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
    if SPLIT_DATE >= min(all_dates) and SPLIT_DATE <= max(all_dates):
        ax2.axvline(x=SPLIT_DATE, color='gray', linestyle='--', linewidth=1.2, alpha=0.8)

    # X轴格式
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
    ax.text(0.05, 0.95, text, transform=ax.transAxes, fontsize=10, verticalalignment='top', bbox=props)
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

# ============ 主流程 ============
def main():
    setup_plt()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("SWAT+ 结果可视化")
    print("=" * 60)

    print("\n[1/3] 读取模拟数据...")
    sim_data = read_simulated(os.path.join(TXTINOUT, 'channel_day.txt'), CHANNEL_NAME)
    precip_data = read_precip(os.path.join(TXTINOUT, 'basin_wb_day.txt'))
    print(f"  模拟流量: {len(sim_data)} days")
    print(f"  降水数据: {len(precip_data)} days")

    print("\n[2/3] 读取观测数据...")
    obs_data = read_observed(OBS_CSV)
    print(f"  观测流量: {len(obs_data)} days")

    print("\n[3/3] 对齐数据并绘图...")
    # 全时段
    all_dates, all_sim, all_obs, all_precip = align_data(sim_data, obs_data, precip_data)
    print(f"  全时段对齐: {len(all_dates)} days")

    # 率定期
    cal_dates, cal_sim, cal_obs, cal_precip = align_data(sim_data, obs_data, precip_data, CALIBRATION_YEARS)
    cal_metrics = evaluate(cal_obs, cal_sim) if len(cal_dates) > 0 else {}

    # 验证期
    val_dates, val_sim, val_obs, val_precip = align_data(sim_data, obs_data, precip_data, VALIDATION_YEARS)
    val_metrics = evaluate(val_obs, val_sim) if len(val_dates) > 0 else {}

    # 全时段指标
    all_metrics = evaluate(all_obs, all_sim) if len(all_dates) > 0 else {}

    print("\n" + "-" * 50)
    if val_metrics:
        print(f"验证期 ({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]}):")
        for k in ['NSE', 'KGE', 'PBIAS(%)', 'R2', 'RMSE']:
            print(f"  {k:>10} = {val_metrics.get(k, float('nan')):.4f}")
    if cal_metrics:
        print(f"\n率定期 ({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]}):")
        for k in ['NSE', 'KGE', 'PBIAS(%)', 'R2', 'RMSE']:
            print(f"  {k:>10} = {cal_metrics.get(k, float('nan')):.4f}")
    if all_metrics:
        print(f"\n全时段 ({all_dates[0].year}-{all_dates[-1].year}):")
        for k in ['NSE', 'KGE', 'PBIAS(%)', 'R2', 'RMSE']:
            print(f"  {k:>10} = {all_metrics.get(k, float('nan')):.4f}")
    print("-" * 50)

    # 绘图
    print("\n生成图表...")
    if cal_metrics:
        plot_daily(cal_dates, cal_sim, cal_obs, cal_precip,
                   f'率定期({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]})', cal_metrics, OUTPUT_DIR)
        plot_scatter(cal_obs, cal_sim, f'率定期({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]})', cal_metrics, OUTPUT_DIR)
        plot_monthly(cal_dates, cal_sim, cal_obs, f'率定期({CALIBRATION_YEARS[0]}-{CALIBRATION_YEARS[-1]})', cal_metrics, OUTPUT_DIR)

    if val_metrics:
        plot_daily(val_dates, val_sim, val_obs, val_precip,
                   f'验证期({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]})', val_metrics, OUTPUT_DIR)
        plot_scatter(val_obs, val_sim, f'验证期({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]})', val_metrics, OUTPUT_DIR)
        plot_monthly(val_dates, val_sim, val_obs, f'验证期({VALIDATION_YEARS[0]}-{VALIDATION_YEARS[-1]})', val_metrics, OUTPUT_DIR)

    # 全时段合并图
    if all_metrics:
        plot_combined_daily(all_dates, all_sim, all_obs, all_precip,
                            cal_metrics, val_metrics, OUTPUT_DIR)
        plot_scatter(all_obs, all_sim, '全时段', all_metrics, OUTPUT_DIR)
        plot_monthly(all_dates, all_sim, all_obs, '全时段', all_metrics, OUTPUT_DIR)

    print(f"\n输出目录: {OUTPUT_DIR}")
    print("=" * 60)
    print("Done!")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[Error] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
