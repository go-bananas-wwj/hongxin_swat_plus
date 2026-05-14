#!/usr/bin/env python3
"""Convert existing TxtInOut to SWAT+ v61.0.2 compatible format.

Strategy:
  1. Copy generic database files from Ames example
  2. Convert model-specific files to v61 format
  3. Create missing required files (object.cnt, hru.con, etc.)
"""

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform

WORKSPACE = Path("/workspace/hongxin_swaw_plus")
AMES_DIR = WORKSPACE / "swatplus-61.0.2/run_verify"
OLD_TXTOUT = WORKSPACE / "data/02_processed/TxtInOut"
NEW_TXTOUT = WORKSPACE / "data/02_processed/TxtInOut_v61"
SUBBASINS_TIF = WORKSPACE / "workspace/subbasins.tif"
STATIONS_CSV = WORKSPACE / "data/02_processed/weather_stations/stations.csv"

# Landuse name mapping: our codes -> Ames landuse.lum names
LU_MAP = {
    "AGRL": "agrl_lum",
    "FRST": "frst_lum",
    "PAST": "past_lum",
    "WATR": "upwn_lum",
    "BARR": "cosy_lum",
    "URBN": "urld_lum",
    "WETL": "wetw_lum",
}

# Soil name mapping: keep our names but ensure they match soils.sol
# We'll create a new soils.sol in v61 format


def copy_ames_databases():
    """Copy generic database files from Ames example."""
    files_to_copy = [
        "plants.plt", "fertilizer.frt", "tillage.til",
        "snow.sno", "cntable.lum", "cons_practice.lum",
        "ovn_table.lum", "tiledrain.str", "septic.str",
        "filterstrip.str", "grassedww.str", "plant.ini",
        "soil_plant.ini", "harv.ops", "graze.ops", "irr.ops",
        "fire.ops", "sweep.ops", "print.prt",
        "codes.bsn", "parameters.bsn",
    ]
    for fname in files_to_copy:
        src = AMES_DIR / fname
        dst = NEW_TXTOUT / fname
        if src.exists():
            shutil.copy(src, dst)
        else:
            print(f"  Warning: Ames file not found: {fname}")


def copy_weather_files():
    """Copy weather data and control files."""
    weather_files = [
        "pcp.cli", "tmp.cli", "slr.cli", "hmd.cli", "wnd.cli",
        "weather-sta.cli", "weather-wgn.cli",
    ]
    # Also copy all .pcp, .tmp, .slr, .hmd, .wnd, .wgn data files
    for f in OLD_TXTOUT.glob("wx*.*"):
        shutil.copy(f, NEW_TXTOUT / f.name)
    for f in weather_files:
        src = OLD_TXTOUT / f
        if src.exists():
            shutil.copy(src, NEW_TXTOUT / f)


def create_file_cio():
    """Create proper file.cio for SWAT+ 61."""
    lines = [
        "file.cio: Hongxin SWAT+",
        "simulation        time.sim          print.prt         null              object.cnt        null              ",
        "basin             codes.bsn         parameters.bsn    ",
        "climate           weather-sta.cli   weather-wgn.cli   null              pcp.cli           tmp.cli           slr.cli           hmd.cli           wnd.cli           null              ",
        "connect           hru.con           null              null              null              null              null              null              null              null              null              null              null              null              null       ",
        "channel           null       null       null        null         null        null        null        null              ",
        "reservoir         null       null       null        null         null        null        null        null    ",
        "routing_unit      null       null       null       null              ",
        "hru               hru-data.hru      null              ",
        "exco              null              null              null              null              null              null              ",
        "recall            null              ",
        "dr                null              null              null              null              null              null              ",
        "aquifer           null              null       ",
        "herd              null              null              null              ",
        "water_rights      null              null              null              ",
        "link              null              null              ",
        "hydrology         hydrology.hyd     topography.hyd    null         ",
        "structural        tiledrain.str     septic.str        filterstrip.str   grassedww.str     bmpuser.str       ",
        "hru_parm_db       plants.plt        fertilizer.frt    tillage.til       pesticide.pes     null              null              null              urban.urb         septic.sep        snow.sno          ",
        "ops               harv.ops          graze.ops         irr.ops           chem_app.ops      fire.ops          sweep.ops         ",
        "lum               landuse.lum       management.sch    cntable.lum       cons_practice.lum ovn_table.lum     ",
        "chg               null     null              null              null              null              null              null              null              null              ",
        "init              plant.ini         soil_plant.ini    null     null              null              null              null              null              null              null              null              null              ",
        "soils             soils.sol         nutrients.sol              null              ",
        "decision_table    null              null              null              null              ",
        "regions           ls_unit.ele       null              null              null              null              null              null              null              null              aqu_catunit.ele   null              null              null              null              null              null              null              null              ",
        "pcp_path          null              ",
        "tmp_path          null              ",
        "slr_path          null              ",
        "hmd_path          null              ",
        "wnd_path          null              ",
    ]
    with open(NEW_TXTOUT / "file.cio", "w") as f:
        f.write("\n".join(lines) + "\n")


def create_object_cnt(n_hru):
    """Create object.cnt with HRU counts."""
    # Format: name ls_area tot_area obj hru lhru rtu mfl aqu cha res rec exco dlr can pmp out lcha aqu2d hrd wro
    header = "object.cnt:\n"
    header += "name                   ls_area      tot_area       obj       hru      lhru       rtu       mfl       aqu       cha       res       rec      exco       dlr       can       pmp       out      lcha     aqu2d       hrd       wro\n"
    data = f"hongxin                   1.          1          {n_hru:8d} {n_hru:8d}         0         0         0         0         0         0         0         0         0         0         0         0         0         0         0\n"
    with open(NEW_TXTOUT / "object.cnt", "w") as f:
        f.write(header + data)


def create_hru_con():
    """Create hru.con from connect.con data."""
    # Read connect.con
    with open(OLD_TXTOUT / "connect.con") as f:
        lines = f.readlines()

    # Parse header and data
    # Format: id name order area len slope lat lon "obj", obj_num, "hyd_typ", frac, ...
    data_lines = []
    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        hru_id = int(parts[0])
        name = parts[1]
        gis_id = int(parts[2])
        area = float(parts[3])
        # lat and lon are in UTM (large numbers), convert to lat/lon for hru.con
        # For now use placeholder - we'll fix with proper coordinates
        lat = float(parts[6])
        lon = float(parts[7])
        data_lines.append((hru_id, name, gis_id, area, lat, lon))

    # Read stations
    stations = pd.read_csv(STATIONS_CSV)

    # Convert UTM coordinates to lat/lon for proper weather station assignment
    with rasterio.open(SUBBASINS_TIF) as src:
        utm_x = np.array([d[5] for d in data_lines])
        utm_y = np.array([d[4] for d in data_lines])
        lons, lats = transform(src.crs, "EPSG:4326", utm_x, utm_y)

    # Find nearest weather station for each HRU
    stn_lon = stations["lon"].values
    stn_lat = stations["lat"].values
    stn_ids = stations["id"].values

    wst_names = []
    for lat, lon in zip(lats, lons):
        dist = np.sqrt((stn_lon - lon)**2 + (stn_lat - lat)**2)
        nearest = stn_ids[np.argmin(dist)]
        wst_names.append(nearest)

    # Write hru.con
    with open(NEW_TXTOUT / "hru.con", "w") as f:
        f.write("hru.con: Hongxin\n")
        f.write("      id  name                gis_id          area           lat           lon          elev       hru               wst       cst      ovfl      rule   out_tot\n")
        for i, (hru_id, name, gis_id, area, _, _) in enumerate(data_lines):
            lat = lats[i]
            lon = lons[i]
            wst = wst_names[i]
            # Default elev = 200
            elev = 200.0
            f.write(f"{hru_id:8d}  {name:19s} {gis_id:10d} {area:14.4f} {lat:14.6f} {lon:14.6f} {elev:12.2f} {hru_id:8d} {wst:>15s}         0         0         0         0\n")


def convert_hru_data_hru():
    """Convert hru-data.hru to SWAT+ 61 format."""
    with open(OLD_TXTOUT / "hru-data.hru") as f:
        lines = f.readlines()

    # Parse old format: id name topo hyd lum soil "snow", "field", ...
    # New format: id name topo hydro soil lu_mgt soil_plant_init surf_stor snow field
    new_lines = ["hru-data.hru:\n"]
    new_lines.append("      id  name                          topo             hydro              soil            lu_mgt   soil_plant_init         surf_stor              snow             field\n")

    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        # Extract fields - old format is space-separated but some values may have quotes
        parts = line.split()
        hru_id = int(parts[0])
        name = parts[1]
        topo = parts[2]
        hyd = parts[3]
        lum = parts[4]
        soil = parts[5]

        # Map landuse name
        lum_mapped = LU_MAP.get(lum, lum.lower() + "_lum")

        new_lines.append(
            f"{hru_id:8d}  {name:29s} {topo:16s} {hyd:17s} {soil:15s} {lum_mapped:15s} null                  null              snow001              null\n"
        )

    with open(NEW_TXTOUT / "hru-data.hru", "w") as f:
        f.write("".join(new_lines))


def convert_topography():
    """Convert topography.top to topography.hyd (SWAT+ 61 format)."""
    with open(OLD_TXTOUT / "topography.top") as f:
        lines = f.readlines()

    # New format: name slope slope_len lat_len dis_stream dep_co
    new_lines = ["topography.hyd:\n"]
    new_lines.append("name          slope   slope_len   lat_len   dis_stream   dep_co\n")

    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        name = parts[0]
        # Extract values if available, else use defaults
        try:
            lat_len = float(parts[1])
            ch_l = float(parts[2])
            ch_s = float(parts[3])
            ch_w = float(parts[4])
        except (IndexError, ValueError):
            lat_len = 50.0
            ch_l = 100.0
            ch_s = 0.02
            ch_w = 10.0

        slope = ch_s
        slope_len = ch_l
        dis_stream = ch_w
        dep_co = 1.0

        new_lines.append(f"{name:14s} {slope:7.4f} {slope_len:11.2f} {lat_len:9.2f} {dis_stream:12.2f} {dep_co:8.2f}\n")

    with open(NEW_TXTOUT / "topography.hyd", "w") as f:
        f.write("".join(new_lines))


def convert_hydrology_hyd():
    """Convert hydrology.hyd to SWAT+ 61 format."""
    # Ames format: name lat_ttime lat_sed can_max esco epco orgn_enrich orgp_enrich cn3_swf bio_mix perco lat_orgn lat_orgp pet_co latq_co
    with open(OLD_TXTOUT / "hydrology.hyd") as f:
        lines = f.readlines()

    new_lines = ["hydrology.hyd:\n"]
    new_lines.append("name                 lat_ttime       lat_sed       can_max          esco          epco   orgn_enrich   orgp_enrich       cn3_swf       bio_mix         perco      lat_orgn      lat_orgp        pet_co       latq_co\n")

    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        name = parts[0]
        # Extract values, use defaults for missing
        try:
            lat_ttime = float(parts[1]) if len(parts) > 1 else 0.5
            lat_sed = float(parts[2]) if len(parts) > 2 else 0.0
            can_max = float(parts[3]) if len(parts) > 3 else 0.0
            esco = float(parts[4]) if len(parts) > 4 else 0.95
            epco = float(parts[5]) if len(parts) > 5 else 1.0
        except (IndexError, ValueError):
            lat_ttime, lat_sed, can_max, esco, epco = 0.5, 0.0, 0.0, 0.95, 1.0

        new_lines.append(
            f"{name:20s} {lat_ttime:13.5f} {lat_sed:13.5f} {can_max:13.5f} {esco:13.5f} {epco:13.5f} "
            f"{0.0:13.5f} {0.0:13.5f} {0.0:13.5f} {0.2:13.5f} {0.5:13.5f} {0.0:13.5f} {0.0:13.5f} {1.0:13.5f} {0.01:13.5f}\n"
        )

    with open(NEW_TXTOUT / "hydrology.hyd", "w") as f:
        f.write("".join(new_lines))


def convert_soils_sol():
    """Convert soils.sol to SWAT+ 61 multi-layer format."""
    with open(OLD_TXTOUT / "soils.sol") as f:
        lines = f.readlines()

    new_lines = ["soils.sol Hongxin\n"]
    new_lines.append("   name               NLY  HYD_GRP        ZMX    ANION_EXCL     CRK       TEXTURE        DEPTH        BD       AWC        K        CBN      CLAY      SILT      SAND      ROCK       ALB     USLE_K       EC       CAL        PH\n")

    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        name = parts[0]
        hydro_group = parts[1] if len(parts) > 1 else "D"
        dp = float(parts[2]) if len(parts) > 2 else 2000.0
        porosity = float(parts[3]) if len(parts) > 3 else 0.5
        awc = float(parts[4]) if len(parts) > 4 else 0.15
        k = float(parts[5]) if len(parts) > 5 else 2.0
        cbn = float(parts[6]) if len(parts) > 6 else 1.5
        clay = float(parts[7]) if len(parts) > 7 else 25.0
        sand = float(parts[8]) if len(parts) > 8 else 35.0
        silt = float(parts[9]) if len(parts) > 9 else 40.0
        rock = float(parts[10]) if len(parts) > 10 else 10.0
        alb = float(parts[11]) if len(parts) > 11 else 0.1
        usle_k = float(parts[12]) if len(parts) > 12 else 0.28
        ec = float(parts[13]) if len(parts) > 13 else 1.0
        cal = float(parts[14]) if len(parts) > 14 else 0.0
        ph = float(parts[15]) if len(parts) > 15 else 7.0

        # Compute bulk density from porosity (approximate)
        bd = 2.65 * (1 - porosity)

        # Single layer
        new_lines.append(f"{name:15s}        1  {hydro_group:>9s} {dp:10.3f}        0.500     0.500       L-           \n")
        new_lines.append(f"{'':15s}                                                                                  {dp:10.2f} {bd:9.3f} {awc:9.3f} {k:9.3f} {cbn:9.3f} {clay:9.3f} {silt:9.3f} {sand:9.3f} {rock:9.3f} {alb:9.3f} {usle_k:9.3f} {ec:9.3f} {cal:9.3f} {ph:9.3f}\n")

    with open(NEW_TXTOUT / "soils.sol", "w") as f:
        f.write("".join(new_lines))


def convert_landuse_lum():
    """Create landuse.lum referencing Ames databases."""
    # Read old landuse classes
    with open(OLD_TXTOUT / "landuse.lum") as f:
        lines = f.readlines()

    old_classes = []
    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        old_classes.append(parts[0])

    # Write new landuse.lum in v61 format
    # Format: name cal_group plnt_com mgt cn2 cons_prac urban urb_ro ov_mann tile sep vfs grww bmp
    new_lines = ["landuse.lum: Hongxin\n"]
    new_lines.append("name                         cal_group          plnt_com                                        mgt               cn2         cons_prac             urban            urb_ro           ov_mann              tile               sep               vfs              grww               bmp\n")

    for cls in old_classes:
        mapped = LU_MAP.get(cls, cls.lower() + "_lum")
        # Use generic references from Ames
        plnt_com = "agrl_comm"  # generic agricultural community
        mgt = "null"
        cn2 = "rc_strow_g"
        cons_prac = "up_down_slope"
        urban = "null"
        urb_ro = "null"
        ov_mann = "convtill_nores"
        tile = "null"
        sep = "null"
        vfs = "null"
        grww = "null"
        bmp = "null"

        if mapped in ["frst_lum", "frsd_lum", "frse_lum"]:
            plnt_com = "frst_comm"
            ov_mann = "forest"
        elif mapped in ["past_lum", "rnge_lum", "rngb_lum"]:
            plnt_com = "past_comm"
            ov_mann = "pasture"
        elif mapped in ["wetw_lum"]:
            plnt_com = "wetw_comm"
            ov_mann = "wetland"
        elif mapped in ["urld_lum", "upwn_lum"]:
            plnt_com = "urld_comm"
            ov_mann = "urban"

        new_lines.append(
            f"{mapped:29s} null         {plnt_com:47s} {mgt:17s} {cn2:14s} {cons_prac:17s} {urban:17s} {urb_ro:17s} {ov_mann:16s} {tile:17s} {sep:17s} {vfs:17s} {grww:17s} {bmp:17s}\n"
        )

    with open(NEW_TXTOUT / "landuse.lum", "w") as f:
        f.write("".join(new_lines))


def create_time_sim():
    """Copy time.sim."""
    shutil.copy(OLD_TXTOUT / "time.sim", NEW_TXTOUT / "time.sim")


def create_aquifer_aqu():
    """Copy aquifer.aqu."""
    shutil.copy(OLD_TXTOUT / "aquifer.aqu", NEW_TXTOUT / "aquifer.aqu")


def create_channel_cha():
    """Copy channel.cha."""
    shutil.copy(OLD_TXTOUT / "channel.cha", NEW_TXTOUT / "channel.cha")


def create_nutrients_sol():
    """Create empty nutrients.sol."""
    with open(NEW_TXTOUT / "nutrients.sol", "w") as f:
        f.write("nutrients.sol\n")


def create_empty_files():
    """Create empty files referenced by file.cio to avoid errors."""
    empty_files = [
        "management.sch", "pesticide.pes", "urban.urb", "septic.sep",
        "chem_app.ops", "bmpuser.str", "ls_unit.ele", "aqu_catunit.ele",
    ]
    for fname in empty_files:
        with open(NEW_TXTOUT / fname, "w") as f:
            f.write(f"{fname}\n")


def main():
    print("Converting TxtInOut to SWAT+ v61 format...")
    NEW_TXTOUT.mkdir(parents=True, exist_ok=True)

    print("1. Copying Ames database files...")
    copy_ames_databases()

    print("2. Copying weather files...")
    copy_weather_files()

    print("3. Creating file.cio...")
    create_file_cio()

    print("4. Creating object.cnt...")
    # Count HRUs from old hru-data.hru
    with open(OLD_TXTOUT / "hru-data.hru") as f:
        n_hru = len(f.readlines()) - 2
    create_object_cnt(n_hru)

    print("5. Creating hru.con...")
    create_hru_con()

    print("6. Converting hru-data.hru...")
    convert_hru_data_hru()

    print("7. Converting topography.top -> topography.hyd...")
    convert_topography()

    print("8. Converting hydrology.hyd...")
    convert_hydrology_hyd()

    print("9. Converting soils.sol...")
    convert_soils_sol()

    print("10. Converting landuse.lum...")
    convert_landuse_lum()

    print("11. Copying time.sim, aquifer.aqu, channel.cha...")
    create_time_sim()
    create_aquifer_aqu()
    create_channel_cha()

    print("12. Creating empty placeholder files...")
    create_nutrients_sol()
    create_empty_files()

    # Count files
    n_files = len(list(NEW_TXTOUT.glob("*")))
    print(f"\nDone! Created {n_files} files in {NEW_TXTOUT}")


if __name__ == "__main__":
    main()
