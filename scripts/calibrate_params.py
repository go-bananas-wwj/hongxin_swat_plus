#!/usr/bin/env python3
"""
Parameter calibration script for SWAT+ Hongxin project.
Reference: /workspace/run_workflow_deli9.py calibration experience.

Current issue after channel routing fix: simulated flow is ~79% higher than observed.
Strategy: increase ET, reduce surface runoff.
"""

import os
import shutil
from pathlib import Path

TXTINOUT = Path("/workspace/hongxin_swaw_plus/data/02_processed/TxtInOut_v61")

# Backup original files
FILES_TO_BACKUP = [
    "hydrology.hyd", "parameters.bsn", "cntable.lum", "soils.sol"
]


def backup_originals():
    for fname in FILES_TO_BACKUP:
        orig = TXTINOUT / f"{fname}.orig"
        target = TXTINOUT / fname
        if not orig.exists() and target.exists():
            shutil.copy2(target, orig)
            print(f"  Backed up {fname}")


def restore_originals():
    for fname in FILES_TO_BACKUP:
        orig = TXTINOUT / f"{fname}.orig"
        target = TXTINOUT / fname
        if orig.exists():
            shutil.copy2(orig, target)
            print(f"  Restored {fname}")


def _modify_generic(filepath, params_dict):
    """Generic file modifier."""
    if not filepath.exists():
        return 0
    with open(filepath, 'r') as f:
        lines = f.readlines()
    header = lines[1].strip().split()
    col_idx = {name: i for i, name in enumerate(header)}
    modified = 0
    for i, line in enumerate(lines):
        if i < 2:
            continue
        parts = line.strip().split()
        if len(parts) < len(header) - 1:
            continue
        changed = False
        for pname, cfg in params_dict.items():
            if pname in col_idx:
                idx = col_idx[pname]
                if idx < len(parts):
                    val = float(parts[idx])
                    if cfg['change_type'] == 'replace':
                        val = cfg['value']
                    elif cfg['change_type'] == 'percent':
                        val = val * (1 + cfg['value'] / 100)
                    parts[idx] = f"{val:.5f}"
                    changed = True
        if changed:
            lines[i] = parts[0].ljust(20) + ''.join(f"{p:>14}" for p in parts[1:]) + '\n'
            modified += 1
    with open(filepath, 'w') as f:
        f.writelines(lines)
    return modified


def modify_cntable(filepath, params_dict):
    """Modify cntable.lum: cn2 maps to cn_a/cn_b/cn_c/cn_d."""
    if not filepath.exists() or 'cn2' not in params_dict:
        return 0
    with open(filepath, 'r') as f:
        lines = f.readlines()
    header = lines[1].strip().split()
    col_idx = {name: i for i, name in enumerate(header)}
    cn_cols = ['cn_a', 'cn_b', 'cn_c', 'cn_d']
    cfg = params_dict['cn2']
    modified = 0
    for i, line in enumerate(lines):
        if i < 2:
            continue
        parts = line.strip().split()
        if len(parts) < len(header):
            continue
        changed = False
        for cn_col in cn_cols:
            if cn_col in col_idx:
                idx = col_idx[cn_col]
                if idx < len(parts):
                    val = float(parts[idx])
                    if cfg['change_type'] == 'replace':
                        val = cfg['value']
                    elif cfg['change_type'] == 'percent':
                        val = val * (1 + cfg['value'] / 100)
                    val = max(35.0, min(98.0, val))
                    parts[idx] = f"{val:.5f}"
                    changed = True
        if changed:
            lines[i] = parts[0].ljust(20) + ''.join(f"{p:>14}" for p in parts[1:]) + '\n'
            modified += 1
    with open(filepath, 'w') as f:
        f.writelines(lines)
    return modified


def modify_soils(filepath, params_dict):
    """Modify soils.sol: only modify soil layer data rows."""
    if not filepath.exists():
        return 0
    with open(filepath, 'r') as f:
        lines = f.readlines()
    header = lines[1].strip().split()
    col_idx = {name: i for i, name in enumerate(header)}
    offset = 7
    modified = 0
    for i, line in enumerate(lines):
        if i < 2:
            continue
        parts = line.strip().split()
        if len(parts) >= len(header) or len(parts) < 10:
            continue
        changed = False
        for pname, cfg in params_dict.items():
            if pname in col_idx:
                idx = col_idx[pname] - offset
                if 0 <= idx < len(parts):
                    val = float(parts[idx])
                    if cfg['change_type'] == 'replace':
                        val = cfg['value']
                    elif cfg['change_type'] == 'percent':
                        val = val * (1 + cfg['value'] / 100)
                    parts[idx] = f"{val:.5f}"
                    changed = True
        if changed:
            prefix_len = len(line) - len(line.lstrip())
            prefix = line[:prefix_len]
            lines[i] = prefix + '  '.join(parts) + '\n'
            modified += 1
    with open(filepath, 'w') as f:
        f.writelines(lines)
    return modified


# Calibration schemes reference from run_workflow_deli9.py
SCHEMES = {
    'baseline': [],
    # Moderate reduction: increase ET, reduce surface runoff
    'moderate': [
        {'name': 'pet_co', 'change_type': 'replace', 'value': 0.88, 'group': 'hru'},
        {'name': 'esco', 'change_type': 'replace', 'value': 0.75, 'group': 'hru'},
        {'name': 'epco', 'change_type': 'replace', 'value': 0.75, 'group': 'hru'},
        {'name': 'perco', 'change_type': 'replace', 'value': 0.65, 'group': 'hru'},
        {'name': 'cn2', 'change_type': 'percent', 'value': -12.0, 'group': 'cnt'},
        {'name': 'soil_k', 'change_type': 'percent', 'value': 80.0, 'group': 'sol'},
        {'name': 'latq_co', 'change_type': 'replace', 'value': 0.06, 'group': 'hru'},
    ],
    # Aggressive reduction: high PET, high evaporation
    'aggressive': [
        {'name': 'pet_co', 'change_type': 'replace', 'value': 1.00, 'group': 'hru'},
        {'name': 'esco', 'change_type': 'replace', 'value': 0.95, 'group': 'hru'},
        {'name': 'epco', 'change_type': 'replace', 'value': 0.95, 'group': 'hru'},
        {'name': 'perco', 'change_type': 'replace', 'value': 0.90, 'group': 'hru'},
        {'name': 'cn2', 'change_type': 'percent', 'value': -15.0, 'group': 'cnt'},
        {'name': 'soil_k', 'change_type': 'percent', 'value': 100.0, 'group': 'sol'},
        {'name': 'latq_co', 'change_type': 'replace', 'value': 0.10, 'group': 'hru'},
    ],
    # Conservative: small adjustments
    'conservative': [
        {'name': 'pet_co', 'change_type': 'replace', 'value': 0.70, 'group': 'hru'},
        {'name': 'esco', 'change_type': 'replace', 'value': 0.50, 'group': 'hru'},
        {'name': 'epco', 'change_type': 'replace', 'value': 0.50, 'group': 'hru'},
        {'name': 'perco', 'change_type': 'replace', 'value': 0.30, 'group': 'hru'},
        {'name': 'cn2', 'change_type': 'percent', 'value': -5.0, 'group': 'cnt'},
        {'name': 'soil_k', 'change_type': 'percent', 'value': 30.0, 'group': 'sol'},
        {'name': 'latq_co', 'change_type': 'replace', 'value': 0.03, 'group': 'hru'},
    ],
}


def apply_scheme(scheme_name):
    if scheme_name not in SCHEMES:
        print(f"Unknown scheme: {scheme_name}")
        print(f"Available: {list(SCHEMES.keys())}")
        return

    params = SCHEMES[scheme_name]
    if not params:
        restore_originals()
        print(f"Applied baseline (restored originals)")
        return

    hru_params = {p['name']: p for p in params if p['group'] == 'hru'}
    bsn_params = {p['name']: p for p in params if p['group'] == 'bsn'}
    cnt_params = {p['name']: p for p in params if p['group'] == 'cnt'}
    sol_params = {p['name']: p for p in params if p['group'] == 'sol'}

    print(f"Applying scheme: {scheme_name}")
    if hru_params:
        n = _modify_generic(TXTINOUT / 'hydrology.hyd', hru_params)
        print(f"  hydrology.hyd: {n} rows modified")
    if bsn_params:
        n = _modify_generic(TXTINOUT / 'parameters.bsn', bsn_params)
        print(f"  parameters.bsn: {n} rows modified")
    if cnt_params:
        n = modify_cntable(TXTINOUT / 'cntable.lum', cnt_params)
        print(f"  cntable.lum: {n} rows modified")
    if sol_params:
        n = modify_soils(TXTINOUT / 'soils.sol', sol_params)
        print(f"  soils.sol: {n} rows modified")
    print(f"Done.")


if __name__ == "__main__":
    import sys
    backup_originals()
    if len(sys.argv) > 1:
        apply_scheme(sys.argv[1])
    else:
        print("Usage: python calibrate_params.py <scheme_name>")
        print(f"Available schemes: {list(SCHEMES.keys())}")
