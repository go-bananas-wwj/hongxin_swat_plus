#!/bin/bash
set -e
TOKEN="ms-399d1804-1cb3-446a-a3f7-dfc4dc70d977"
REPO="WeijieWu/hongxin_swat"

echo "=== Uploading remaining data to ModelScope ==="

# Upload CDAT (as original zip to avoid too many small files)
echo "Uploading CDAT original zip..."
modelscope upload --repo-type dataset --token "$TOKEN" \
    "$REPO" /workspace/hongxin_swaw_plus/datasets/cdat.zip 01_raw_data/cdat.zip \
    2>&1 | grep -E "(Upload Report|Uploaded|Failed)" | tail -3

# Upload watershed shapes
echo "Uploading watershed shapes..."
modelscope upload --repo-type dataset --token "$TOKEN" \
    "$REPO" /workspace/hongxin_swaw_plus/data/01_raw/watershed_shapes 01_raw_data/watershed_shapes \
    2>&1 | grep -E "(Upload Report|Uploaded|Failed)" | tail -3

# Upload CMFD (this will take a while)
echo "Uploading CMFD (this will take hours)..."
modelscope upload --repo-type dataset --token "$TOKEN" --max-workers 8 \
    "$REPO" /workspace/hongxin_swaw_plus/Datasets/CMFD_v2_2012-2024_daily 01_raw_data/cmfd_v2_daily \
    2>&1 | grep -E "(Upload Report|Uploaded|Failed)" | tail -3

echo "Done!"
