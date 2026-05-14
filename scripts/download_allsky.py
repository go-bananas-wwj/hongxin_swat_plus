#!/usr/bin/env python3
"""Download All-sky temperature data from Zenodo (2019-2022)."""
import os
import sys
import time
from pathlib import Path

# Zenodo download links
FILES = {
    "tmax": {
        "base_url": "https://zenodo.org/record/10983207/files",
        "years": [2019, 2020, 2021, 2022],
        "prefix": "Tem-MAX",
    },
    "tmin": {
        "base_url": "https://zenodo.org/record/10983199/files",
        "years": [2019, 2020, 2021, 2022],
        "prefix": "Tem-MIN",
    },
}

OUTPUT_DIR = Path("/workspace/hongxin_swaw_plus/data/01_raw/allsky_temp")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def download_file(url: str, output_path: Path, max_retries: int = 3) -> bool:
    """Download a file with retry."""
    for attempt in range(max_retries):
        cmd = f'curl -L -o "{output_path}" "{url}" --max-time 7200 --connect-timeout 60'
        print(f"  [{attempt+1}/{max_retries}] Downloading: {url}")
        ret = os.system(cmd)
        if ret == 0 and output_path.exists() and output_path.stat().st_size > 1000000:
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"  ✓ Saved ({size_mb:.1f} MB)")
            return True
        print(f"  ✗ Failed, retrying...")
        time.sleep(5)
    return False

def main():
    print("=" * 60)
    print("All-sky Temperature Data Downloader")
    print("=" * 60)
    
    for var_type, info in FILES.items():
        print(f"\n--- {var_type.upper()} ---")
        for year in info["years"]:
            filename = f"{info['prefix']}_{year}.zip"
            url = f"{info['base_url']}/{filename}"
            output_path = OUTPUT_DIR / filename
            
            if output_path.exists() and output_path.stat().st_size > 1000000:
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"  ✓ {filename} already exists ({size_mb:.1f} MB)")
                continue
            
            success = download_file(url, output_path)
            if not success:
                print(f"  ✗ FAILED: {filename}")
                sys.exit(1)
    
    print("\n" + "=" * 60)
    print("All downloads complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
