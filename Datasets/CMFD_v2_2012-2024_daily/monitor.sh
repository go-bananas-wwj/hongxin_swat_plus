#!/bin/bash
DIR="/workspace/hongxin_swaw_plus/Datasets/CMFD_v2_2012-2024_daily"
LOG="$DIR/download.log"
TOTAL=104
while true; do
    COUNT=$(ls $DIR/*.nc 2>/dev/null | wc -l)
    SIZE=$(du -sh $DIR 2>/dev/null | cut -f1)
    if [ "$COUNT" -ge "$TOTAL" ]; then
        echo "[COMPLETE] All $TOTAL files downloaded. Total size: $SIZE"
        break
    fi
    echo "[$(date '+%H:%M:%S')] Progress: $COUNT/$TOTAL files, $SIZE"
    sleep 120
done
