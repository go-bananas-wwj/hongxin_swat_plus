#!/usr/bin/env python3
"""
Validate generated TxtInOut folder for consistency and completeness.
"""
import argparse
import os
import sys


def count_data_lines(path: str, skip_header: int = 2) -> int:
    """Count non-empty data lines in a file."""
    if not os.path.exists(path):
        return -1
    with open(path) as f:
        lines = f.readlines()
    # Skip header lines, count remaining non-empty lines
    count = 0
    for line in lines[skip_header:]:
        if line.strip():
            count += 1
    return count


def parse_object_cnt(path: str) -> dict:
    """Parse object.cnt and return counts."""
    with open(path) as f:
        lines = f.readlines()
    # Find header and data line
    header_parts = lines[1].split()
    data_parts = lines[-1].split()
    
    def get_val(col_name):
        idx = header_parts.index(col_name)
        return int(data_parts[idx])
    
    result = {
        "obj": get_val("obj"),
        "hru": get_val("hru"),
        "cha": get_val("cha"),
        "out": get_val("out"),
    }
    # res may not exist in older object.cnt formats
    try:
        result["res"] = get_val("res")
    except ValueError:
        result["res"] = 0
    return result


def validate(txtinout_dir: str) -> bool:
    """Run all validation checks."""
    errors = []
    warnings = []
    
    print(f"Validating: {txtinout_dir}")
    print("=" * 60)
    
    # Check required files exist
    required_files = [
        "channel.con", "hru.con", "outlet.con", "object.cnt",
        "file.cio", "time.sim",
        "channel.cha", "hydrology.cha",
        "hru-data.hru",
    ]
    # Check reservoir files if reservoir.con exists
    has_reservoir = os.path.exists(os.path.join(txtinout_dir, "reservoir.con"))
    if has_reservoir:
        res_files = ["reservoir.con", "reservoir.res", "hydrology.res", "sediment.res", "nutrients.res", "initial.res"]
        for fname in res_files:
            fpath = os.path.join(txtinout_dir, fname)
            if not os.path.exists(fpath):
                errors.append(f"Missing reservoir file: {fname}")
    for fname in required_files:
        fpath = os.path.join(txtinout_dir, fname)
        if not os.path.exists(fpath):
            errors.append(f"Missing required file: {fname}")
    
    if errors:
        for e in errors:
            print(f"  [ERROR] {e}")
        return False
    
    # Count objects
    n_cha = count_data_lines(os.path.join(txtinout_dir, "channel.con"), skip_header=2)
    n_hru = count_data_lines(os.path.join(txtinout_dir, "hru.con"), skip_header=2)
    n_out = count_data_lines(os.path.join(txtinout_dir, "outlet.con"), skip_header=2)
    n_hyd = count_data_lines(os.path.join(txtinout_dir, "hydrology.cha"), skip_header=2)
    n_cha_idx = count_data_lines(os.path.join(txtinout_dir, "channel.cha"), skip_header=2)
    n_hru_dat = count_data_lines(os.path.join(txtinout_dir, "hru-data.hru"), skip_header=2)
    n_res = count_data_lines(os.path.join(txtinout_dir, "reservoir.con"), skip_header=2) if has_reservoir else 0
    
    obj = parse_object_cnt(os.path.join(txtinout_dir, "object.cnt"))
    
    print(f"  channel.con:    {n_cha} channels")
    print(f"  hru.con:        {n_hru} HRUs")
    print(f"  outlet.con:     {n_out} outlets")
    if has_reservoir:
        print(f"  reservoir.con:  {n_res} reservoirs")
    print(f"  hydrology.cha:  {n_hyd} entries")
    print(f"  channel.cha:    {n_cha_idx} entries")
    print(f"  hru-data.hru:   {n_hru_dat} entries")
    res_str = f", res={obj.get('res', 0)}" if has_reservoir else ""
    print(f"  object.cnt:     obj={obj['obj']}, hru={obj['hru']}, cha={obj['cha']}{res_str}, out={obj['out']}")
    
    # Validate counts
    expected_obj = n_hru + n_cha + n_out + n_res
    if obj["obj"] != expected_obj:
        errors.append(f"object.cnt obj={obj['obj']}, expected {expected_obj} (hru={n_hru} + cha={n_cha} + res={n_res} + out={n_out})")
    
    if obj["hru"] != n_hru:
        errors.append(f"object.cnt hru={obj['hru']}, expected {n_hru}")
    
    if obj["cha"] != n_cha:
        errors.append(f"object.cnt cha={obj['cha']}, expected {n_cha}")
    
    if obj["out"] != n_out:
        errors.append(f"object.cnt out={obj['out']}, expected {n_out}")
    
    if n_hyd != n_cha:
        errors.append(f"hydrology.cha has {n_hyd} entries, but channel.con has {n_cha} channels")
    
    if n_cha_idx != n_cha:
        errors.append(f"channel.cha has {n_cha_idx} entries, but channel.con has {n_cha} channels")
    
    if n_hru_dat != n_hru:
        errors.append(f"hru-data.hru has {n_hru_dat} entries, but hru.con has {n_hru} HRUs")
    
    # Check file.cio object count
    with open(os.path.join(txtinout_dir, "file.cio")) as f:
        for line in f:
            if line.strip().startswith("object"):
                parts = line.split()
                if len(parts) >= 2:
                    cio_obj = int(parts[1])
                    if cio_obj != expected_obj:
                        errors.append(f"file.cio object={cio_obj}, expected {expected_obj}")
                break
    
    # Check template files
    template_files = ["soils.sol", "plants.plt", "landuse.lum"]
    for fname in template_files:
        fpath = os.path.join(txtinout_dir, fname)
        if not os.path.exists(fpath):
            warnings.append(f"Missing template file: {fname} (may cause SWAT+ to fail)")
    
    print("=" * 60)
    if errors:
        print(f"Validation FAILED with {len(errors)} error(s):")
        for e in errors:
            print(f"  [ERROR] {e}")
    else:
        print("Validation PASSED. All counts are consistent.")
    
    if warnings:
        print(f"  {len(warnings)} warning(s):")
        for w in warnings:
            print(f"  [WARN] {w}")
    
    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(description="Validate SWAT+ TxtInOut folder")
    parser.add_argument("--dir", "-d", required=True, help="Path to TxtInOut directory")
    args = parser.parse_args()
    
    ok = validate(args.dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
