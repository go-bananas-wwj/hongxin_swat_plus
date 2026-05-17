#!/usr/bin/env python3
"""Detailed analysis of SWAT+ aquifer experiment."""

import pandas as pd
import numpy as np

OBS_FILE = '/workspace/hongxin_swaw_plus/datasets/processed_hydro/镇西_discharge_2012_2022_daily.csv'
TXTINOUT = '/workspace/hongxin_swaw_plus/output/TxtInOut'
OUTLET_UNIT = 302

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
                flo_out = float(parts[8])
                flo_out_m3s = flo_out * 10000.0 / 86400.0
                model.append((date, flo_out_m3s))
    return pd.DataFrame(model, columns=['date', 'flow']).set_index('date')

obs = pd.read_csv(OBS_FILE)
obs['date'] = pd.to_datetime(obs['date'])
obs = obs.set_index('date')
obs.columns = ['observed']

base = read_model(f'{TXTINOUT}/channel_day_base.txt')
alpha001 = read_model(f'{TXTINOUT}/channel_day_alpha001.txt')
alpha005 = read_model(f'{TXTINOUT}/channel_day_alpha005.txt')

# Merge
merged = obs.join(base, how='inner', rsuffix='_base').join(alpha001, how='inner', rsuffix='_alpha001').join(alpha005, how='inner', rsuffix='_alpha005')
merged.columns = ['observed', 'base', 'alpha001', 'alpha005']

print("=== Monthly Means ===")
merged['month'] = merged.index.month
merged['year'] = merged.index.year
monthly = merged.groupby(['year', 'month'])[['observed', 'base', 'alpha001']].mean()
print(monthly.head(24))

print("\n=== Low Flow Period: May 27 - June 7, 2012 ===")
spell = merged.loc['2012-05-27':'2012-06-07']
print(spell)

print("\n=== Peak Flow Days (Top 10 Observed) ===")
peaks = merged.nlargest(10, 'observed')[['observed', 'base', 'alpha001']]
print(peaks)

print("\n=== Flow Duration Curve (Percentiles) ===")
for col in ['observed', 'base', 'alpha001', 'alpha005']:
    data = merged[col].values
    print(f"\n{col}:")
    for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        print(f"  P{p}: {np.percentile(data, p):.2f}")

print("\n=== Low Flow Spell Analysis ===")
# Count continuous zero-flow spells in model
for col in ['base', 'alpha001', 'alpha005']:
    is_zero = (merged[col] == 0).astype(int)
    spells = []
    current = 0
    for v in is_zero:
        if v == 1:
            current += 1
        else:
            if current > 0:
                spells.append(current)
            current = 0
    if current > 0:
        spells.append(current)
    
    print(f"\n{col}:")
    print(f"  Total zero spells: {len(spells)}")
    print(f"  Max spell length: {max(spells) if spells else 0} days")
    print(f"  Spell lengths: {sorted(spells, reverse=True)[:10]}")
