#!/usr/bin/env python3
"""Compare SWAT+ model channel flow with observed discharge at 镇西站."""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- Read observed data ---
obs = pd.read_csv('/workspace/hongxin_swaw_plus/datasets/processed_hydro/镇西_discharge_2012_2022_daily.csv')
obs['date'] = pd.to_datetime(obs['date'])
obs = obs.set_index('date')
obs.columns = ['observed']

# --- Read model channel data ---
# channel_day.txt columns: jday mon day yr unit gis_id name flo_in flo_out ...
# unit 303 = cha0302 = outlet
model = []
with open('/workspace/hongxin_swaw_plus/output/TxtInOut/channel_day.txt', 'r') as f:
    for i, line in enumerate(f):
        if i < 3:
            continue
        parts = line.split()
        if len(parts) < 9:
            continue
        unit = int(parts[4])
        if unit == 302:  # outlet (cha0302, gis_id=303)
            yr = int(parts[3])
            jday = int(parts[0])
            date = pd.Timestamp(f'{yr}-01-01') + pd.Timedelta(days=jday-1)
            flo_out = float(parts[8])  # ha-m/day
            # Convert ha-m/day to m3/s: 1 ha-m = 10000 m3, 1 day = 86400 s
            flo_out_m3s = flo_out * 10000.0 / 86400.0
            model.append((date, flo_out_m3s))

model_df = pd.DataFrame(model, columns=['date', 'modeled'])
model_df = model_df.set_index('date')

# --- Merge ---
merged = obs.join(model_df, how='inner')
print(f"Common days: {len(merged)}")
print(f"Observed avg: {merged['observed'].mean():.2f} m3/s")
print(f"Modeled avg:  {merged['modeled'].mean():.2f} m3/s")
print(f"Observed max: {merged['observed'].max():.2f} m3/s")
print(f"Modeled max:  {merged['modeled'].max():.2f} m3/s")

# Check for zero-flow spells in model
zero_days = (merged['modeled'] == 0).sum()
print(f"Model zero-flow days: {zero_days}")

# Check May 27 - June 7, 2012 spell
spell = merged.loc['2012-05-27':'2012-06-07']
print("\nMay 27 - June 7, 2012:")
print(spell)

# --- Plot ---
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

# Full time series
ax = axes[0]
ax.plot(merged.index, merged['observed'], 'b-', alpha=0.6, label='Observed (镇西)', lw=0.8)
ax.plot(merged.index, merged['modeled'], 'r-', alpha=0.6, label='Modeled (cha0302)', lw=0.8)
ax.set_ylabel('Flow (m³/s)')
ax.legend()
ax.set_title('SWAT+ Model vs Observed Discharge at 镇西站 (2012-2022)')
ax.set_ylim(0, max(merged['observed'].max(), merged['modeled'].max()) * 1.1)

# 2012 zoom
ax = axes[1]
sub = merged.loc['2012']
ax.plot(sub.index, sub['observed'], 'b-', alpha=0.7, label='Observed', lw=1)
ax.plot(sub.index, sub['modeled'], 'r-', alpha=0.7, label='Modeled', lw=1)
ax.set_ylabel('Flow (m³/s)')
ax.set_title('2012 Detail')
ax.legend()

plt.tight_layout()
plt.savefig('/workspace/hongxin_swaw_plus/flow_comparison.png', dpi=150)
print("\nSaved plot to flow_comparison.png")

# --- Nash-Sutcliffe ---
obs_mean = merged['observed'].mean()
ss_res = ((merged['observed'] - merged['modeled'])**2).sum()
ss_tot = ((merged['observed'] - obs_mean)**2).sum()
nse = 1 - ss_res / ss_tot
print(f"\nNSE: {nse:.3f}")

# --- Monthly means ---
merged['month'] = merged.index.month
merged['year'] = merged.index.year
monthly = merged.groupby(['year', 'month'])[['observed', 'modeled']].mean()
print("\nMonthly means (first 24 months):")
print(monthly.head(24))
