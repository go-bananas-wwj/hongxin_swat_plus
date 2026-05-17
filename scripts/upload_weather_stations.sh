#!/bin/bash
set -e
TOKEN="ms-399d1804-1cb3-446a-a3f7-dfc4dc70d977"
REPO="WeijieWu/hongxin_swat"

WORKSPACE="/workspace/hongxin_swaw_plus"
STATIONS_DIR="$WORKSPACE/data/02_processed/weather_stations"
UPLOAD_DIR="$WORKSPACE/modelscope_upload/02_processed_weather_stations"

echo "=== Packaging weather stations data ==="
mkdir -p "$UPLOAD_DIR"

# Create zip for each variable
for var in lrad prec rhum srad tmax tmin wind; do
    echo "  Zipping $var ..."
    zip -r -q "$UPLOAD_DIR/${var}_448stations_2012_2022_daily.zip" \
        "$STATIONS_DIR/$var/" \
        -x "*/.git*" -x "*/__pycache__*"
    size=$(du -h "$UPLOAD_DIR/${var}_448stations_2012_2022_daily.zip" | cut -f1)
    echo "    $size"
done

# Also zip stations.csv
cp "$STATIONS_DIR/stations.csv" "$UPLOAD_DIR/"

echo ""
echo "=== Uploading to ModelScope ==="
for f in "$UPLOAD_DIR"/*.zip; do
    fname=$(basename "$f")
    echo "  Uploading $fname ..."
    modelscope upload --repo-type dataset --token "$TOKEN" \
        "$REPO" "$f" "02_processed_weather_stations/$fname" \
        2>&1 | grep -E "(Upload Report|Uploaded|Failed)" | tail -3
done

echo ""
echo "=== Done ==="
