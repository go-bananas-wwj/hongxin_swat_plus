#!/usr/bin/env python3
"""
SWAT+ Hydrological Validation Script
Compares simulated channel flow with observed flow data.
"""
import os
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ============================================================
# Configuration
# ============================================================
TXT_IN_OUT = '/workspace/hongxin_swaw_plus/data/02_processed/TxtInOut_v61'
OBS_DIR = '/workspace/hongxin_swaw_plus/datasets/new_extracted/new'
OUTPUT_DIR = '/workspace/hongxin_swaw_plus/results/validation'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Station mapping: (channel_gis_id, station_name_chinese)
STATIONS = [
    (2, '五岔沟'),
    (3, '索伦'),
    (4, '察尔森下'),
    (6, '镇西'),
    (7, '大石寨'),
    (8, '阿力得尔'),
    (9, '保隆'),
]

# ============================================================
# Helper functions
# ============================================================
def read_observed_data():
    """Read all observed flow data from xlsx files."""
    all_data = []
    
    for year_dir in sorted(glob.glob(os.path.join(OBS_DIR, '*'))):
        if not os.path.isdir(year_dir):
            continue
        year = int(os.path.basename(year_dir))
        
        for station_name_ch in [s[1] for s in STATIONS]:
            pattern = os.path.join(year_dir, f'{year}年{station_name_ch}逐日平均流量表.xlsx')
            files = glob.glob(pattern)
            if not files:
                continue
            
            df = pd.read_excel(files[0], header=0)
            # Format: rows=days (1-31), columns=months (一月-十二月)
            month_cols = ['一月', '二月', '三月', '四月', '五月', '六月',
                          '七月', '八月', '九月', '十月', '十一月', '十二月']
            
            for _, row in df.iterrows():
                try:
                    day = int(row.iloc[0])
                except (ValueError, TypeError):
                    continue
                if day < 1 or day > 31:
                    continue
                for month_idx, month_col in enumerate(month_cols, 1):
                    val = row.get(month_col)
                    if pd.isna(val):
                        continue
                    try:
                        date = datetime(year, month_idx, day)
                        all_data.append({
                            'date': date,
                            'station': station_name_ch,
                            'observed': float(val)
                        })
                    except ValueError:
                        continue
    
    obs_df = pd.DataFrame(all_data)
    obs_df = obs_df.drop_duplicates(subset=['date', 'station'])
    obs_df = obs_df.sort_values(['station', 'date']).reset_index(drop=True)
    return obs_df


def read_simulated_data():
    """Read channel_day.txt simulated flow data."""
    sim_data = []
    channel_day_path = os.path.join(TXT_IN_OUT, 'channel_day.txt')
    
    with open(channel_day_path, 'r') as f:
        lines = f.readlines()
    
    # Skip header lines
    data_lines = lines[3:]
    station_gis_ids = [s[0] for s in STATIONS]
    
    for line in data_lines:
        parts = line.strip().split()
        if len(parts) < 10:
            continue
        
        try:
            jday = int(parts[0])
            mon = int(parts[1])
            day = int(parts[2])
            year = int(parts[3])
            gis_id = int(parts[5])
            
            if gis_id not in station_gis_ids:
                continue
            
            # Flow is the 8th column (0-indexed: 7)
            flow = float(parts[7])
            
            date = datetime(year, mon, day)
            sim_data.append({
                'date': date,
                'gis_id': gis_id,
                'simulated': flow
            })
        except (ValueError, IndexError):
            continue
    
    sim_df = pd.DataFrame(sim_data)
    sim_df = sim_df.sort_values(['gis_id', 'date']).reset_index(drop=True)
    return sim_df


def calc_nse(obs, sim):
    """Nash-Sutcliffe Efficiency."""
    obs = np.array(obs)
    sim = np.array(sim)
    mask = ~(np.isnan(obs) | np.isnan(sim))
    obs, sim = obs[mask], sim[mask]
    if len(obs) == 0:
        return np.nan
    return 1 - np.sum((obs - sim)**2) / np.sum((obs - np.mean(obs))**2)


def calc_r2(obs, sim):
    """Coefficient of determination."""
    obs = np.array(obs)
    sim = np.array(sim)
    mask = ~(np.isnan(obs) | np.isnan(sim))
    obs, sim = obs[mask], sim[mask]
    if len(obs) == 0:
        return np.nan
    return np.corrcoef(obs, sim)[0, 1]**2


def calc_pbias(obs, sim):
    """Percent bias."""
    obs = np.array(obs)
    sim = np.array(sim)
    mask = ~(np.isnan(obs) | np.isnan(sim))
    obs, sim = obs[mask], sim[mask]
    if len(obs) == 0 or np.sum(obs) == 0:
        return np.nan
    return 100 * np.sum(sim - obs) / np.sum(obs)


def calc_rmse(obs, sim):
    """Root mean square error."""
    obs = np.array(obs)
    sim = np.array(sim)
    mask = ~(np.isnan(obs) | np.isnan(sim))
    obs, sim = obs[mask], sim[mask]
    if len(obs) == 0:
        return np.nan
    return np.sqrt(np.mean((obs - sim)**2))


def calc_kge(obs, sim):
    """Kling-Gupta Efficiency."""
    obs = np.array(obs)
    sim = np.array(sim)
    mask = ~(np.isnan(obs) | np.isnan(sim))
    obs, sim = obs[mask], sim[mask]
    if len(obs) == 0:
        return np.nan
    r = np.corrcoef(obs, sim)[0, 1]
    alpha = np.std(sim) / np.std(obs) if np.std(obs) > 0 else 0
    beta = np.mean(sim) / np.mean(obs) if np.mean(obs) > 0 else 0
    return 1 - np.sqrt((r - 1)**2 + (alpha - 1)**2 + (beta - 1)**2)


# ============================================================
# Main
# ============================================================
if __name__ == '__main__':
    print("Reading observed data...")
    obs_df = read_observed_data()
    print(f"  -> {len(obs_df)} observed records")
    print(f"  -> Stations: {obs_df['station'].unique().tolist()}")
    print(f"  -> Year range: {obs_df['date'].min()} to {obs_df['date'].max()}")
    
    print("\nReading simulated data...")
    sim_df = read_simulated_data()
    print(f"  -> {len(sim_df)} simulated records")
    print(f"  -> GIS IDs: {sorted(sim_df['gis_id'].unique().tolist())}")
    print(f"  -> Year range: {sim_df['date'].min()} to {sim_df['date'].max()}")
    
    # Build station name mapping
    gis_to_name = {gid: name for gid, name in STATIONS}
    
    results = []
    fig, axes = plt.subplots(len(STATIONS), 1, figsize=(16, 3*len(STATIONS)))
    if len(STATIONS) == 1:
        axes = [axes]
    
    for idx, (gis_id, station_name) in enumerate(STATIONS):
        print(f"\nAnalyzing {station_name} (GIS ID {gis_id})...")
        
        obs_sub = obs_df[obs_df['station'] == station_name].copy()
        sim_sub = sim_df[sim_df['gis_id'] == gis_id].copy()
        
        print(f"  Observed: {len(obs_sub)} days, Simulated: {len(sim_sub)} days")
        
        if len(obs_sub) == 0:
            print(f"  WARNING: No observed data for {station_name}")
            continue
        if len(sim_sub) == 0:
            print(f"  WARNING: No simulated data for {station_name}")
            continue
        
        # Merge on date
        merged = pd.merge(obs_sub, sim_sub, on='date', how='inner')
        merged = merged.sort_values('date')
        
        print(f"  -> {len(merged)} matching days")
        
        if len(merged) < 30:
            print(f"  WARNING: Too few matching days for {station_name}")
            continue
        
        # Calculate metrics
        obs_vals = merged['observed'].values
        sim_vals = merged['simulated'].values
        
        nse = calc_nse(obs_vals, sim_vals)
        r2 = calc_r2(obs_vals, sim_vals)
        pbias = calc_pbias(obs_vals, sim_vals)
        rmse = calc_rmse(obs_vals, sim_vals)
        kge = calc_kge(obs_vals, sim_vals)
        
        results.append({
            'station': station_name,
            'gis_id': gis_id,
            'n_days': len(merged),
            'obs_mean': np.mean(obs_vals),
            'sim_mean': np.mean(sim_vals),
            'NSE': nse,
            'R2': r2,
            'PBIAS': pbias,
            'RMSE': rmse,
            'KGE': kge
        })
        
        print(f"  NSE={nse:.3f}, R²={r2:.3f}, PBIAS={pbias:.1f}%, KGE={kge:.3f}")
        
        # Plot
        ax = axes[idx]
        ax.plot(merged['date'], obs_vals, 'b-', label='Observed', alpha=0.7, linewidth=0.8)
        ax.plot(merged['date'], sim_vals, 'r-', label='Simulated', alpha=0.7, linewidth=0.8)
        ax.set_ylabel('Flow (m³/s)', fontsize=9)
        ax.set_title(f'{station_name} (GIS {gis_id}) | NSE={nse:.3f} R²={r2:.3f} PBIAS={pbias:.1f}% KGE={kge:.3f}', fontsize=10)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)
    
    plt.xlabel('Date', fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'hydro_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    
    # Save results table
    results_df = pd.DataFrame(results)
    results_df.to_csv(os.path.join(OUTPUT_DIR, 'metrics.csv'), index=False, float_format='%.4f')
    print(f"\n{'='*70}")
    print("VALIDATION RESULTS:")
    print(results_df.to_string(index=False))
    print(f"{'='*70}")
    print(f"\nPlots saved to: {OUTPUT_DIR}/hydro_comparison.png")
    print(f"Metrics saved to: {OUTPUT_DIR}/metrics.csv")
