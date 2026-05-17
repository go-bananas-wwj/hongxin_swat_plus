#!/usr/bin/env python3
"""Analyze all calibration experiments automatically."""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OBS_FILE = '/workspace/hongxin_swaw_plus/datasets/processed_hydro/镇西_discharge_2012_2022_daily.csv'
TXTINOUT = '/workspace/hongxin_swaw_plus/output/TxtInOut'
OUTLET_UNIT = 302

def read_observed():
    obs = pd.read_csv(OBS_FILE)
    obs['date'] = pd.to_datetime(obs['date'])
    obs = obs.set_index('date')
    obs.columns = ['observed']
    return obs

def read_model(channel_file):
    if not os.path.exists(channel_file):
        return None
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
                flo_out = float(parts[8])
                flo_out_m3s = flo_out * 10000.0 / 86400.0
                model.append((date, flo_out_m3s))
    model_df = pd.DataFrame(model, columns=['date', 'flow'])
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
            'zero_days': (sim == 0).sum(), 'sim_min': sim.min()}

obs = read_observed()

experiments = {
    'Base (α=0.05)': 'channel_day_base.txt',
    'α=0.01': 'channel_day_alpha001.txt',
    'α=0.005': 'channel_day_alpha005.txt',
    'α=0.02': 'channel_day_alpha002.txt',
    'α=0.03': 'channel_day_alpha003.txt',
    'α=0.01_lowET': 'channel_day_alpha001_lowet.txt',
    'α=0.01_highperco': 'channel_day_alpha001_highperco.txt',
}

results = {}
for name, fname in experiments.items():
    fpath = os.path.join(TXTINOUT, fname)
    sim = read_model(fpath)
    if sim is None:
        continue
    merged = obs.join(sim, how='inner')
    metrics = calc_metrics(merged['observed'].values, merged['flow'].values)
    results[name] = metrics

# Print summary table
print("\n" + "="*110)
print(f"{'Experiment':<22} {'NSE':>8} {'KGE':>8} {'PBIAS':>8} {'RMSE':>8} {'SimAvg':>8} {'SimMax':>8} {'SimMin':>8} {'ZeroDays':>8}")
print("="*110)
for name, m in results.items():
    print(f"{name:<22} {m['NSE']:>8.3f} {m['KGE']:>8.3f} {m['PBIAS']:>8.1f} {m['RMSE']:>8.1f} {m['sim_mean']:>8.1f} {m['sim_max']:>8.1f} {m['sim_min']:>8.2f} {m['zero_days']:>8d}")
print("="*110)

# Find best by NSE, KGE, lowest RMSE
best_nse = max(results.items(), key=lambda x: x[1]['NSE'])
best_kge = max(results.items(), key=lambda x: x[1]['KGE'])
best_rmse = min(results.items(), key=lambda x: x[1]['RMSE'])
print(f"\nBest by NSE:  {best_nse[0]} (NSE={best_nse[1]['NSE']:.3f})")
print(f"Best by KGE:  {best_kge[0]} (KGE={best_kge[1]['KGE']:.3f})")
print(f"Best by RMSE: {best_rmse[0]} (RMSE={best_rmse[1]['RMSE']:.1f})")

# Save results to CSV
if results:
    df = pd.DataFrame(results).T
    df.to_csv('/workspace/hongxin_swaw_plus/calibration_results.csv')
    print("\nSaved results to calibration_results.csv")
