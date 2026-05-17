#!/usr/bin/env python3
import os, glob, numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

TXT_IN_OUT = '/workspace/hongxin_swaw_plus/data/02_processed/TxtInOut_v61'
OBS_DIR = '/workspace/hongxin_swaw_plus/datasets/new_extracted/new'
OUTPUT_DIR = '/workspace/hongxin_swaw_plus/results/validation'
os.makedirs(OUTPUT_DIR, exist_ok=True)

STATIONS = [
    (2, '五岔沟'), (3, '索伦'), (4, '察尔森下'),
    (6, '镇西'), (7, '大石寨'), (8, '阿力得尔'), (9, '保隆'),
]

HA_M_TO_M3S = 10000.0 / 86400.0  # ha-m/day -> m3/s

def read_obs():
    all_data = []
    for year_dir in sorted(glob.glob(os.path.join(OBS_DIR, '*'))):
        if not os.path.isdir(year_dir): continue
        year = int(os.path.basename(year_dir))
        for station_name_ch in [s[1] for s in STATIONS]:
            pattern = os.path.join(year_dir, f'{year}年{station_name_ch}逐日平均流量表.xlsx')
            files = glob.glob(pattern)
            if not files: continue
            df = pd.read_excel(files[0], header=0)
            month_cols = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月']
            for _, row in df.iterrows():
                try:
                    day = int(row.iloc[0])
                except: continue
                if day < 1 or day > 31: continue
                for mi, mc in enumerate(month_cols, 1):
                    val = row.get(mc)
                    if pd.isna(val): continue
                    try:
                        all_data.append({'date': datetime(year, mi, day), 'station': station_name_ch, 'observed': float(val)})
                    except: pass
    obs_df = pd.DataFrame(all_data).drop_duplicates(['date','station']).sort_values(['station','date']).reset_index(drop=True)
    return obs_df

def read_sim():
    sim_data = []
    station_gis_ids = [s[0] for s in STATIONS]
    with open(os.path.join(TXT_IN_OUT, 'channel_day.txt'), 'r') as f:
        for i, line in enumerate(f):
            if i < 3: continue
            parts = line.strip().split()
            if len(parts) < 10: continue
            try:
                gis_id = int(parts[5])
                if gis_id not in station_gis_ids: continue
                flo_in = float(parts[7]) * HA_M_TO_M3S
                flo_out = float(parts[8]) * HA_M_TO_M3S
                date = datetime(int(parts[3]), int(parts[1]), int(parts[2]))
                sim_data.append({'date': date, 'gis_id': gis_id, 'simulated': flo_out})
            except: pass
    return pd.DataFrame(sim_data).sort_values(['gis_id','date']).reset_index(drop=True)

def nse(o,s):
    o,s = np.array(o), np.array(s)
    mask = ~(np.isnan(o)|np.isnan(s))
    o,s = o[mask], s[mask]
    return 1 - np.sum((o-s)**2)/np.sum((o-np.mean(o))**2) if len(o)>0 and np.sum((o-np.mean(o))**2)>0 else np.nan

def r2(o,s):
    o,s = np.array(o), np.array(s)
    mask = ~(np.isnan(o)|np.isnan(s))
    o,s = o[mask], s[mask]
    return np.corrcoef(o,s)[0,1]**2 if len(o)>0 and np.std(o)>0 and np.std(s)>0 else np.nan

def pbias(o,s):
    o,s = np.array(o), np.array(s)
    mask = ~(np.isnan(o)|np.isnan(s))
    o,s = o[mask], s[mask]
    return 100*np.sum(s-o)/np.sum(o) if len(o)>0 and np.sum(o)>0 else np.nan

def kge(o,s):
    o,s = np.array(o), np.array(s)
    mask = ~(np.isnan(o)|np.isnan(s))
    o,s = o[mask], s[mask]
    if len(o)==0 or np.std(o)==0: return np.nan
    r = np.corrcoef(o,s)[0,1]
    alpha = np.std(s)/np.std(o)
    beta = np.mean(s)/np.mean(o)
    return 1 - np.sqrt((r-1)**2 + (alpha-1)**2 + (beta-1)**2)

obs_df = read_obs()
sim_df = read_sim()
print(f"Obs: {len(obs_df)} records, Sim: {len(sim_df)} records")

results = []
fig, axes = plt.subplots(len(STATIONS), 1, figsize=(16, 3*len(STATIONS)))
if len(STATIONS)==1: axes=[axes]

for idx, (gis_id, station_name) in enumerate(STATIONS):
    obs_sub = obs_df[obs_df['station']==station_name].copy()
    sim_sub = sim_df[sim_df['gis_id']==gis_id].copy()
    merged = pd.merge(obs_sub, sim_sub, on='date', how='inner').sort_values('date')
    
    if len(merged) < 30:
        print(f"{station_name}: too few data ({len(merged)})")
        continue
    
    o, s = merged['observed'].values, merged['simulated'].values
    results.append({
        'station': station_name, 'gis_id': gis_id, 'n_days': len(merged),
        'obs_mean': np.mean(o), 'sim_mean': np.mean(s),
        'NSE': nse(o,s), 'R2': r2(o,s), 'PBIAS': pbias(o,s), 'KGE': kge(o,s)
    })
    print(f"{station_name}: NSE={nse(o,s):.3f}, R2={r2(o,s):.3f}, PBIAS={pbias(o,s):.1f}%, KGE={kge(o,s):.3f}")
    
    ax = axes[idx]
    ax.plot(merged['date'], o, 'b-', label='Obs', alpha=0.7, lw=0.8)
    ax.plot(merged['date'], s, 'r-', label='Sim', alpha=0.7, lw=0.8)
    ax.set_ylabel('Flow (m3/s)', fontsize=9)
    ax.set_title(f'{station_name} (GIS{gis_id}) NSE={nse(o,s):.3f} R2={r2(o,s):.3f} PBIAS={pbias(o,s):.1f}% KGE={kge(o,s):.3f}', fontsize=10)
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)

plt.xlabel('Date', fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'hydro_comparison_v2.png'), dpi=150, bbox_inches='tight')
plt.close()

pd.DataFrame(results).to_csv(os.path.join(OUTPUT_DIR, 'metrics_v2.csv'), index=False, float_format='%.4f')
print(f"\n{'='*70}")
print(pd.DataFrame(results).to_string(index=False))
