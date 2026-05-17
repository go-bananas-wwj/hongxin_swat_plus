#!/bin/bash
set -e

cd /workspace/hongxin_swaw_plus/output/TxtInOut

# Backup base output
cp channel_day.txt channel_day_base.txt 2>/dev/null || true
cp basin_wb_day.txt basin_wb_day_base.txt 2>/dev/null || true

# Experiments to run
# Format: suffix alpha flo_min spyld flo dep_wt
declare -a experiments=(
    "alpha001 0.01 20.0 0.1 0.05 10.0"
    "alpha005 0.005 20.0 0.1 0.05 10.0"
)

for exp in "${experiments[@]}"; do
    read -r suffix alpha flo_min spyld flo dep_wt <<< "$exp"
    echo "=== Running experiment: $suffix ==="
    
    # Modify aquifer parameters
    cat > aquifer.aqu <<EOF
aquifer.aqu
id  name  aqu_ini  flo  dep_bot  dep_wt  no3  minp  cbn  flo_dist  bf_max  alpha  revap_co  seep  spyld  hlife_n  flo_min  revap_min
1  aquifer1  null  $flo  20.0  $dep_wt  0.0  0.0  0.5  1000.0  50.0  $alpha  0.0  0.0  $spyld  30.0  $flo_min  0.0
EOF
    
    # Run SWAT+
    ./swatplus > swatplus_${suffix}.log 2>&1
    
    # Save key outputs
    cp channel_day.txt channel_day_${suffix}.txt
    cp basin_wb_day.txt basin_wb_day_${suffix}.txt
    cp aquifer_day.txt aquifer_day_${suffix}.txt
    
    echo "=== Experiment $suffix complete ==="
done

# Restore base parameters
cat > aquifer.aqu <<EOF
aquifer.aqu
id  name  aqu_ini  flo  dep_bot  dep_wt  no3  minp  cbn  flo_dist  bf_max  alpha  revap_co  seep  spyld  hlife_n  flo_min  revap_min
1  aquifer1  null  0.05  20.0  10.0  0.0  0.0  0.5  1000.0  50.0  0.05  0.0  0.0  0.1  30.0  20.0  0.0
EOF

echo "All experiments complete."
