#!/bin/bash
set -e
OUTPUT_DIR="/workspace/hongxin_swaw_plus/data/01_raw/allsky_temp"
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Function to download a single file
download_file() {
    local url="$1"
    local output="$2"
    if [ -f "$output" ] && [ $(stat -c%s "$output") -gt 1000000 ]; then
        echo "✓ $output already exists"
        return 0
    fi
    echo "↓ Downloading $output ..."
    curl -L -o "$output" "$url" --max-time 7200 --connect-timeout 60 || true
    if [ -f "$output" ] && [ $(stat -c%s "$output") -gt 1000000 ]; then
        echo "✓ $output done"
    else
        echo "✗ $output failed"
    fi
}

# Download all files in parallel
export -f download_file

urls=(
    "https://zenodo.org/record/10983207/files/Tem-MAX_2019.zip"
    "https://zenodo.org/record/10983207/files/Tem-MAX_2020.zip"
    "https://zenodo.org/record/10983207/files/Tem-MAX_2021.zip"
    "https://zenodo.org/record/10983207/files/Tem-MAX_2022.zip"
    "https://zenodo.org/record/10983199/files/Tem-MIN_2019.zip"
    "https://zenodo.org/record/10983199/files/Tem-MIN_2020.zip"
    "https://zenodo.org/record/10983199/files/Tem-MIN_2021.zip"
    "https://zenodo.org/record/10983199/files/Tem-MIN_2022.zip"
)

for url in "${urls[@]}"; do
    filename=$(basename "$url")
    download_file "$url" "$filename" &
done

wait
echo "All downloads complete!"
ls -lh *.zip
