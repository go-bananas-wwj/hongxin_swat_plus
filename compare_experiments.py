#!/usr/bin/env python3
"""Compare SWAT+ experiments with observed discharge at 镇西站."""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OBS_FILE = '/workspace/hongxin_swaw_plus/datasets/processed_hydro/镇西_discharge_2012_2022_daily.csv'
TXTINOUT = '/workspace/hongxin_swaw_plus/output/TxtInOut'
OUTLET_UNIT = 302  # cha0302

def read_observed():
    obs = pd.read_csv(OBS_FILE)
    obs['date'] = pd.to_datetime(obs['date'])
    obs = obs.set_index('date')
    obs.columns = ['observed']
    return obs

def read_model(channel_file):
    model = []
    with open(channel_file, 'r') as f:
        for i, line in enumerate(f):
            if i < 3:
                continue
            parts = line.split()
            if len(parts) < 9:
                continue
            unit = int(parts[4])
            if unit == OUTLET_UNIT:
                yr = int(parts[3])
                jday = int(parts[0])
                date = pd.Timestamp(f'{yr}-01-01') + pd.Timedelta(days=jday-1)
                flo_out = float(parts[8])  # ha-m/day
                flo_out_m3s = flo_out * 10000.0 / 86400.0
                model.append((date, flo_out_m3s))
    model_df = pd.DataFrame(model, columns=['date', 'modeled'])
    model_df = model_df.set_index('date')
    return model_df

def calc_metrics(obs, sim):
    obs_mean = obs.mean()
    ss_res = ((obs - sim) ** 2).sum()
    ss_tot = ((obs - obs_mean) ** 2).sum()
    nse = 1 - ss_res / ss_tot if ss_tot > 0 else float('nan')
    
    r = np.corrcoef(obs, sim)[0, 1]
    kge = 1 - np.sqrt((r - 1)**2 + (np.std(sim)/np.std(obs) - 1)**2 + (np.mean(sim)/np.mean(obs) - 1)**2)
    
    pbias = 100 * np.sum(sim - obs) / np.sum(obs)
    rmse = np.sqrt(np.mean((obs - sim)**2))
    
    return {'NSE': nse, 'KGE': kge, 'PBIAS': pbias, 'RMSE': rmse,
            'obs_mean': obs_mean, 'sim_mean': sim.mean(),
            'obs_max': obs.max(), 'sim_max': sim.max(),
            'zero_days': (sim == 0).sum()}

def analyze_experiment(name, channel_file, obs):
    print(f"\n=== {name} ===")
    sim = read_model(channel_file)
    merged = obs.join(sim, how='inner')
    print(f"Common days: {len(merged)}")
    
    metrics = calc_metrics(merged['observed'].values, merged['modeled'].values)
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.3f}")
        else:
            print(f"  {k}: {v}")
    
    return merged, metrics

obs = read_observed()
print(f"Observed data: {len(obs)} days, avg = {obs['observed'].mean():.2f} m³/s")

experiments = {
    'Base (alpha=0.05)': f'{TXTINOUT}/channel_day_base.txt',
    'Alpha=0.01': f'{TXTINOUT}/channel_day_alpha001.txt',
    'Alpha=0.005': f'{TXTINOUT}/channel_day_alpha005.txt',
}

results = {}
for name, fpath in experiments.items():
    if os.path.exists(fpath):
        merged, metrics = analyze_experiment(name, fpath, obs)
        results[name] = (merged, metrics)
    else:
        print(f"\n=== {name} ===")
        print(f"  File not found: {fpath}")

# Plot comparison
if len(results) >= 2:
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    # Full time series
    ax = axes[0]
    ax.plot(results['Base (alpha=0.05)'][0].index, results['Base (alpha=0.05)'][0]['observed'], 'k-', alpha=0.5, label='Observed', lw=0.8)
    for name, (merged, metrics) in results.items():
        if 'Base' in name:
            color = 'b'
        elif '0.01' in name:
            color = 'r'
        else:
            color = 'g'
        ax.plot(merged.index, merged['modeled'], color=color, alpha=0.6, label=name, lw=0.8)
    ax.set_ylabel('Flow (m³/s)')
    ax.legend()
    ax.set_title('SWAT+ Aquifer Parameter Experiments - 镇西站 (2012-2022)')
    ax.set_ylim(0, max(results['Base (alpha=0.05)'][0]['observed'].max(), 
                       results['Base (alpha=0.05)'][0]['modeled'].max()) * 1.1)
    
    # 2012 zoom
    ax = axes[1]
    for name, (merged, metrics) in results.items():
        sub = merged.loc['2012']
        color = 'b' if 'Base' in name else 'r'
        ax.plot(sub.index, sub['modeled'], color=color, alpha=0.7, label=name, lw=1)
    ax.plot(results['Base (alpha=0.05)'][0].loc['2012'].index, 
            results['Base (alpha=0.05)'][0].loc['2012']['observed'], 'k-', alpha=0.5, label='Observed', lw=1)
    ax.set_ylabel('Flow (m³/s)')
    ax.set_title('2012 Detail')
    ax.legend()
    
    # May 27 - June 7, 2012 spell
    ax = axes[2]
    spell = results['Base (alpha=0.05)'][0].loc['2012-05-27':'2012-06-07']
    ax.plot(spell.index, spell['observed'], 'k-o', label='Observed', markersize=4)
    for name, (merged, metrics) in results.items():
        sub = merged.loc['2012-05-27':'2012-06-07']
        color = 'b' if 'Base' in name else 'r'
        ax.plot(sub.index, sub['modeled'], color=color, alpha=0.7, label=name, marker='o', markersize=4)
    ax.set_ylabel('Flow (m³/s)')
    ax.set_title('May 27 - June 7, 2012 (Dry Spell)')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('/workspace/hongxin_swaw_plus/experiment_comparison.png', dpi=150)
    print("\nSaved plot to experiment_comparison.png")

# Print summary table
print("\n=== SUMMARY TABLE ===")
print(f"{'Experiment':<20} {'NSE':>8} {'KGE':>8} {'PBIAS':>8} {'RMSE':>8} {'SimAvg':>8} {'SimMax':>8} {'ZeroDays':>8}")
for name, (merged, metrics) in results.items():
    print(f"{name:<20} {metrics['NSE']:>8.3f} {metrics['KGE']:>8.3f} {metrics['PBIAS']:>8.1f} {metrics['RMSE']:>8.1f} {metrics['sim_mean']:>8.1f} {metrics['sim_max']:>8.1f} {metrics['zero_days']:>8d}")
