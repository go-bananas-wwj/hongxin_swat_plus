#!/usr/bin/env python3
"""
Rebuild SWAT+ channel routing files from existing data.

This script:
1. Creates channel parameter files (hydrology.cha, initial.cha, sediment.cha, nutrients.cha)
2. Fixes channel.cha format
3. Creates channel.con with channel topology
4. Creates outlet.con
5. Modifies hru.con to add outflow connections
6. Updates object.cnt
7. Updates file.cio
"""

import os
import shutil
import csv
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

# Configuration
TXT_IN_OUT = "/workspace/hongxin_swaw_plus/data/02_processed/TxtInOut_v61"
OLD_STREAMS_SHP = "/workspace/hongxin_swaw_plus/workspace/streams.shp"
DRAINAGE_CSV = "/root/Desktop/qswat_data/hongxin_swat/Watershed/Shapes/hongxin_swatdrainage.csv"

# Read streams.shp using fiona
import fiona

def read_streams_topology() -> Dict[int, dict]:
    """Read old streams.shp and return dict of LINKNO -> properties."""
    streams = {}
    with fiona.open(OLD_STREAMS_SHP) as src:
        for f in src:
            props = f['properties']
            streams[props['LINKNO']] = props
    return streams


def read_drainage() -> Dict[int, int]:
    """Read drainage.csv and return dict of PolygonId -> DownId."""
    drainage = {}
    with open(DRAINAGE_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            drainage[int(row['PolygonId'])] = int(row['DownId'])
    return drainage


def read_channel_cha() -> Tuple[List[int], List[dict]]:
    """Read existing channel.cha and return (ids, records)."""
    cha_path = os.path.join(TXT_IN_OUT, "channel.cha")
    ids = []
    records = []
    with open(cha_path) as f:
        lines = f.readlines()
    
    # Header lines
    header = lines[:2]
    
    for line in lines[2:]:
        parts = line.strip().split()
        if not parts:
            continue
        try:
            cha_id = int(parts[0])
        except ValueError:
            continue
        ids.append(cha_id)
        # Parse the rest of the line
        # Format: id name order hyd init rel hyd_rad side_slp bot_wid dep len slope lat lon area a b c d e f g h i j k l m n o p q r s t u v w x y z
        record = {
            'id': cha_id,
            'name': parts[1] if len(parts) > 1 else f'cha{cha_id:04d}',
            'order': int(parts[2]) if len(parts) > 2 else 1,
            'hyd': parts[3] if len(parts) > 3 else '1',
            'init': parts[4] if len(parts) > 4 else '"null"',
            'rel': parts[5] if len(parts) > 5 else '"null"',
        }
        records.append(record)
    
    return ids, records, header


def read_hru_con() -> Tuple[List[str], List[dict]]:
    """Read existing hru.con and return (header_lines, records)."""
    hru_path = os.path.join(TXT_IN_OUT, "hru.con")
    with open(hru_path) as f:
        lines = f.readlines()
    
    header = lines[:2]
    records = []
    for line in lines[2:]:
        parts = line.strip().split()
        if not parts:
            continue
        try:
            hru_id = int(parts[0])
        except ValueError:
            continue
        record = {
            'line': line,
            'id': hru_id,
            'name': parts[1] if len(parts) > 1 else f'hru{hru_id:04d}',
            'gis_id': int(parts[2]) if len(parts) > 2 else 0,
            'area': float(parts[3]) if len(parts) > 3 else 0,
            'lat': float(parts[4]) if len(parts) > 4 else 0,
            'lon': float(parts[5]) if len(parts) > 5 else 0,
            'elev': float(parts[6]) if len(parts) > 6 else 0,
            'hru': int(parts[7]) if len(parts) > 7 else 0,
            'wst': parts[8] if len(parts) > 8 else 'null',
            'cst': int(parts[9]) if len(parts) > 9 else 0,
            'ovfl': int(parts[10]) if len(parts) > 10 else 0,
            'rule': int(parts[11]) if len(parts) > 11 else 0,
            'out_tot': int(parts[12]) if len(parts) > 12 else 0,
        }
        records.append(record)
    
    return header, records


def create_hydrology_cha():
    """Create hydrology.cha with default parameters."""
    content = """hydrology.cha
name             w              d              s              l              n              k              wdr            alpha_bnk      side
default          5.0            1.5            0.001          1.0            0.035          0.01           6.0            0.03           2.0
"""
    path = os.path.join(TXT_IN_OUT, "hydrology.cha")
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created {path}")


def create_initial_cha():
    """Create initial.cha with default parameters."""
    content = """initial.cha
name             org_min        pest           path           hmet           salt
default          null           null           null           null           null
"""
    path = os.path.join(TXT_IN_OUT, "initial.cha")
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created {path}")


def create_sediment_cha():
    """Create sediment.cha with default parameters."""
    content = """sediment.cha
name             eqn            cov1           cov2           bnk_bd         bed_bd         bnk_kd         bed_kd         bnk_d50        bed_d50        tc_bnk         tc_bed         erod1          erod2          erod3          erod4          erod5          erod6          erod7          erod8          erod9          erod10         erod11         erod12
default          0              0.1            0.1            1.3            1.3            0.0            0.0            0.05           0.05           0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0
"""
    path = os.path.join(TXT_IN_OUT, "sediment.cha")
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created {path}")


def create_nutrients_cha():
    """Create nutrients.cha with default parameters."""
    content = """nutrients.cha
name             onco           opco           rs1            rs2            rs3            rs4            rs5            rs6            rs7            rk1            rk2            rk3            rk4            rk5            rk6            bc1            bc2            bc3            bc4            lao            igropt         ai0            ai1            ai2            ai3            ai4            ai5            ai6            mumax          rhoq           tfact          k_l            k_n            k_p            lambda0        lambda1        lambda2        p_n
default          0.0            0.0            1.0            0.05           0.5            0.05           0.05           2.5            2.5            1.71           1.0            2.0            0.0            1.71           1.71           0.55           1.1            0.21           0.35           2              2              50.0           0.08           0.015          1.60           2.0            3.5            1.07           2.0            2.5            0.3            0.75           0.02           0.025          1.0            0.03           0.054          0.5
"""
    path = os.path.join(TXT_IN_OUT, "nutrients.cha")
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created {path}")


def fix_channel_cha(cha_ids: List[int], cha_records: List[dict], header: List[str]):
    """Fix channel.cha format to match SWAT+ v61 expectations."""
    path = os.path.join(TXT_IN_OUT, "channel.cha")
    
    lines = [header[0], header[1]]
    for rec in cha_records:
        # SWAT+ v61 reads: id name init hyd sed nut
        # We set all references to "default"
        line = f"{rec['id']:>5} {rec['name']:<12} default        default        default        default\n"
        lines.append(line)
    
    with open(path, 'w') as f:
        f.writelines(lines)
    print(f"Fixed {path} ({len(cha_records)} channels)")


def create_channel_con(cha_ids: List[int], drainage: Dict[int, int], streams: Dict[int, dict]):
    """Create channel.con defining channel topology."""
    path = os.path.join(TXT_IN_OUT, "channel.con")
    
    # Build channel ID to local index mapping
    cha_id_set = set(cha_ids)
    cha_id_to_local = {cid: i+1 for i, cid in enumerate(cha_ids)}
    
    # For each channel, find downstream channel
    # We use drainage.csv for subbasin-level topology
    # If a channel ID is not in drainage.csv, it may be a lake channel with no downstream
    
    lines = ["channel.con: Hongxin\n"]
    lines.append("      id  name                gis_id          area           lat           lon          elev       cha               wst       cst      ovfl      rule   out_tot  obtyp  obno   htyp       frac\n")
    
    for cid in cha_ids:
        # Get stream properties for lat/lon/elev
        stream = streams.get(cid, {})
        # For lat/lon, we'll use 0.0 since we don't have easy access from shapefile
        # In reality, we could compute centroid, but 0.0 is acceptable
        lat = 0.0
        lon = 0.0
        elev = 0.0
        area = 0.0
        name = f"cha{cid:04d}"
        
        # Find downstream channel
        down_id = drainage.get(cid, -1)
        
        if down_id in cha_id_set and down_id != -1:
            # Has downstream channel
            down_local = cha_id_to_local[down_id]
            out_tot = 1
            out_info = f"  cha    {down_local:>5} tot         1.0000"
        elif down_id == -1:
            # Watershed outlet - connect to outlet object
            # outlet object local ID is 1 (we'll create one outlet)
            out_tot = 1
            out_info = f"  out    {1:>5} tot         1.0000"
        else:
            # Downstream not in our channel set (possibly lake or removed)
            out_tot = 0
            out_info = ""
        
        line = f"{cid:>8}  {name:<16} {cid:>12} {area:>14.4f} {lat:>14.6f} {lon:>14.6f} {elev:>11.2f} {cid:>8} null          0         0         0         0{out_tot:>10}{out_info}\n"
        lines.append(line)
    
    with open(path, 'w') as f:
        f.writelines(lines)
    print(f"Created {path} ({len(cha_ids)} channels)")


def create_outlet_con():
    """Create outlet.con with one outlet."""
    path = os.path.join(TXT_IN_OUT, "outlet.con")
    content = """outlet.con: Hongxin
      id  name                gis_id          area           lat           lon          elev       out               wst       cst      ovfl      rule   out_tot
       1  outlet0001                   0       0.0000       0.000000       0.000000         0.00        1 null          0         0         0         0         0
"""
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created {path}")


def fix_hru_con(hru_header: List[str], hru_records: List[dict], cha_ids: List[int]):
    """Modify hru.con to add outflow connections to channels."""
    path = os.path.join(TXT_IN_OUT, "hru.con")
    
    cha_id_set = set(cha_ids)
    cha_id_to_local = {cid: i+1 for i, cid in enumerate(cha_ids)}
    
    lines = hru_header
    for rec in hru_records:
        gis_id = rec['gis_id']
        
        # Try to find matching channel
        # In old delineation, gis_id often corresponds to subbasin/channel ID
        # But not always - some gis_ids may not have corresponding channels
        if gis_id in cha_id_set:
            cha_local = cha_id_to_local[gis_id]
            out_tot = 1
            out_info = f"  cha    {cha_local:>5} tot         1.0000"
        else:
            # No matching channel - connect to outlet
            out_tot = 1
            out_info = f"  out    {1:>5} tot         1.0000"
        
        # Reconstruct the line with outflow info
        # Original format: id name gis_id area lat lon elev hru wst cst ovfl rule out_tot [...]
        line = f"{rec['id']:>8}  {rec['name']:<16} {rec['gis_id']:>12} {rec['area']:>14.4f} {rec['lat']:>14.6f} {rec['lon']:>14.6f} {rec['elev']:>11.2f} {rec['hru']:>8} {rec['wst']:<11} {rec['cst']:<9} {rec['ovfl']:<9} {rec['rule']:<9}{out_tot:>10}{out_info}\n"
        lines.append(line)
    
    with open(path, 'w') as f:
        f.writelines(lines)
    print(f"Fixed {path} ({len(hru_records)} HRUs)")


def update_object_cnt(num_hru: int, num_cha: int):
    """Update object.cnt with correct object counts."""
    path = os.path.join(TXT_IN_OUT, "object.cnt")
    
    # Object order: hru, hru_lte, ru, gwflow, aqu, chan, res, recall, exco, dr, canal, pump, outlet, chandeg
    # Currently only hru=2356
    # We'll set: hru=2356, cha=282, out=1
    # Total objects = 2356 + 282 + 1 = 2639
    
    total_objs = num_hru + num_cha + 1
    
    content = f"""object.cnt:
name                   ls_area      tot_area       obj       hru      lhru       rtu       mfl       aqu       cha       res       rec      exco       dlr       can       pmp       out      lcha     aqu2d       hrd       wro
hongxin                   1.          1         {total_objs:>6} {num_hru:>6}         0         0         0         0 {num_cha:>6}         0         0         0         0         0         0         1         0         0         0
"""
    with open(path, 'w') as f:
        f.write(content)
    print(f"Updated {path} (obj={total_objs}, hru={num_hru}, cha={num_cha}, out=1)")


def update_file_cio():
    """Update file.cio to reference channel files."""
    path = os.path.join(TXT_IN_OUT, "file.cio")
    
    with open(path) as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.startswith("connect"):
            new_lines.append("connect           hru.con           null              null              channel.con       null              null              null              null              null              null              null              null              null              null\n")
        elif line.startswith("channel"):
            new_lines.append("channel           initial.cha       channel.cha       hydrology.cha     sediment.cha      nutrients.cha     null              null              null\n")
        elif line.startswith("reservoir"):
            new_lines.append("reservoir         null       null       null        null         null        null        null        null\n")
        else:
            new_lines.append(line)
    
    with open(path, 'w') as f:
        f.writelines(new_lines)
    print(f"Updated {path}")


def backup_files():
    """Backup original files before modification."""
    files_to_backup = ['channel.cha', 'hru.con', 'object.cnt', 'file.cio']
    for fname in files_to_backup:
        src = os.path.join(TXT_IN_OUT, fname)
        dst = os.path.join(TXT_IN_OUT, fname + '.bak')
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"Backed up {fname}")


def main():
    print("=" * 60)
    print("Rebuilding SWAT+ Channel Routing Files")
    print("=" * 60)
    
    # Backup original files
    backup_files()
    
    # Read existing data
    print("\nReading existing data...")
    streams = read_streams_topology()
    print(f"  Old streams: {len(streams)} reaches")
    
    drainage = read_drainage()
    print(f"  Drainage: {len(drainage)} subbasin connections")
    
    cha_ids, cha_records, cha_header = read_channel_cha()
    print(f"  channel.cha: {len(cha_ids)} channels")
    
    hru_header, hru_records = read_hru_con()
    print(f"  hru.con: {len(hru_records)} HRUs")
    
    # Create parameter files
    print("\nCreating channel parameter files...")
    create_hydrology_cha()
    create_initial_cha()
    create_sediment_cha()
    create_nutrients_cha()
    
    # Fix channel.cha
    print("\nFixing channel.cha...")
    fix_channel_cha(cha_ids, cha_records, cha_header)
    
    # Create connection files
    print("\nCreating connection files...")
    create_channel_con(cha_ids, drainage, streams)
    create_outlet_con()
    
    # Fix hru.con
    print("\nFixing hru.con...")
    fix_hru_con(hru_header, hru_records, cha_ids)
    
    # Update object.cnt
    print("\nUpdating object.cnt...")
    update_object_cnt(len(hru_records), len(cha_ids))
    
    # Update file.cio
    print("\nUpdating file.cio...")
    update_file_cio()
    
    print("\n" + "=" * 60)
    print("Done! Channel routing files have been rebuilt.")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the generated files in TxtInOut_v61/")
    print("2. Run SWAT+ to verify channel_day.txt is generated")
    print("3. Check for any errors in the model output")


if __name__ == "__main__":
    main()
