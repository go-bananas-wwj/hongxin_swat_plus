#!/bin/bash
set -e

cd /workspace/hongxin_swaw_plus/output/TxtInOut

# Backup original files
cp channel_day.txt channel_day_base.txt 2>/dev/null || true
cp basin_wb_day.txt basin_wb_day_base.txt 2>/dev/null || true
cp aquifer_day.txt aquifer_day_base.txt 2>/dev/null || true

# Helper: modify hydrology.hyd
modify_hyd() {
    local petco=$1 esco=$2 epco=$3 perco=$4
    sed -i "s/hyd1.*/hyd1                       0.50000       0.00000      10.00000       ${esco}       ${epco}       0.00000       0.00000       0.00000       0.20000       ${perco}       0.00000       0.00000       ${petco}       0.06000/" hydrology.hyd
}

# Helper: modify parameters.bsn (surq_lag)
modify_bsn() {
    local surq_lag=$1
    sed -i "s/\s*4.00000\s*1.00000\s*1.00000/  ${surq_lag}       1.00000       1.00000/" parameters.bsn
}

# Helper: modify cntable.lum (cn2 reduction)
modify_cn() {
    local pct=$1
    python3 << EOF
import re
with open('cntable.lum', 'r') as f:
    lines = f.readlines()
for i in range(2, len(lines)):
    parts = lines[i].split()
    if len(parts) >= 5:
        for j in range(1, 5):
            val = float(parts[j])
            val = val * (1 + $pct / 100.0)
            val = max(35.0, min(98.0, val))
            parts[j] = f"{val:.5f}"
        lines[i] = parts[0].ljust(24) + ''.join(f"{p:>14}" for p in parts[1:]) + '\n'
with open('cntable.lum', 'w') as f:
    f.writelines(lines)
EOF
}

# Helper: modify aquifer.aqu
modify_aqu() {
    local alpha=$1
    cat > aquifer.aqu <<EOF
aquifer.aqu
id  name  aqu_ini  flo  dep_bot  dep_wt  no3  minp  cbn  flo_dist  bf_max  alpha  revap_co  seep  spyld  hlife_n  flo_min  revap_min
1  aquifer1  null  0.05  20.0  10.0  0.0  0.0  0.5  1000.0  50.0  ${alpha}  0.0  0.0  0.1  30.0  20.0  0.0
EOF
}

# Helper: run experiment
run_exp() {
    local suffix=$1
    echo "=== Running experiment: $suffix ==="
    ./swatplus > swatplus_${suffix}.log 2>&1
    cp channel_day.txt channel_day_${suffix}.txt
    cp basin_wb_day.txt basin_wb_day_${suffix}.txt
    cp aquifer_day.txt aquifer_day_${suffix}.txt
    echo "=== Experiment $suffix complete ==="
}

# Experiment 1: alpha=0.02 (base hydro)
echo "Setting up alpha=0.02..."
modify_aqu 0.02
run_exp "alpha002"

# Experiment 2: alpha=0.03 (base hydro)
echo "Setting up alpha=0.03..."
modify_aqu 0.03
run_exp "alpha003"

# Experiment 3: alpha=0.01 + low ET (reduce evaporation, increase soil water)
echo "Setting up alpha=0.01 + low ET..."
modify_aqu 0.01
modify_hyd 0.50 0.20 0.20 0.65
run_exp "alpha001_lowet"

# Experiment 4: alpha=0.01 + high perco + lower CN + longer lag
echo "Setting up alpha=0.01 + high perco..."
modify_aqu 0.01
modify_hyd 0.88 0.75 0.75 0.90
modify_bsn 10.0
modify_cn -10
run_exp "alpha001_highperco"

# Restore base parameters
echo "Restoring base parameters..."
modify_aqu 0.05
modify_hyd 0.88 0.75 0.75 0.65
modify_bsn 4.0
# CN table: restore from original (we need to keep a backup)

# Since we modified cntable.lum in-place, restore from backup if exists
if [ -f "cntable.lum.orig" ]; then
    cp cntable.lum.orig cntable.lum
else
    # Revert CN changes: increase by 10%
    python3 << EOF
with open('cntable.lum', 'r') as f:
    lines = f.readlines()
for i in range(2, len(lines)):
    parts = lines[i].split()
    if len(parts) >= 5:
        for j in range(1, 5):
            val = float(parts[j])
            val = val / 0.90
            val = max(35.0, min(98.0, val))
            parts[j] = f"{val:.5f}"
        lines[i] = parts[0].ljust(24) + ''.join(f"{p:>14}" for p in parts[1:]) + '\n'
with open('cntable.lum', 'w') as f:
    f.writelines(lines)
EOF
fi

echo "All experiments complete."
