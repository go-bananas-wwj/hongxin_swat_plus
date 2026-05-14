#!/usr/bin/env python3
"""Generate HRU data from subbasins, landuse, and soil rasters.

Steps:
  1. Align landuse and soil rasters to subbasin raster (25m)
  2. Compute zonal statistics: landuse and soil fractions per subbasin
  3. Generate SWAT+ TxtInOut files:
     - file.cio
     - basin.bsn
     - aquifer.aqu
     - channel.cha
     - hydrology.hyd
     - hru-data.hru
     - landuse.lum
     - soils.sol
     - topography.top
     - connect.con
     - time.sim
"""

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import reproject, Resampling
from tqdm import tqdm

# Paths
WORKSPACE = Path("/workspace/hongxin_swaw_plus")
PROCESSED = WORKSPACE / "data/02_processed"
RAW = WORKSPACE / "data/01_raw"
TXTOUT = PROCESSED / "TxtInOut"

SUBBASINS_TIF = WORKSPACE / "workspace" / "subbasins.tif"
LANDUSE_TIF = RAW / "landuse" / "CLCD_2018_clip_hongxin.tif"
SOIL_TIF = RAW / "soil" / "HWSD2_clip_utm51n_90m.tif"
LOOKUP_LU = WORKSPACE / "Datasets/swat_data/soil/landuse_lookup.csv"
LOOKUP_SOIL = WORKSPACE / "Datasets/swat_data/soil/soil_lookup.csv"
USERSOIL_CSV = WORKSPACE / "Datasets/swat_data/soil/usersoil.csv"

# Simulation settings
SIM_START = (2012, 1, 1)
SIM_END = (2022, 12, 31)
WARMUP_YEARS = 2
NBYR = SIM_END[0] - SIM_START[0] + 1


def align_raster(src_path, dst_path, template_path, resampling=Resampling.nearest):
    """Reproject/src raster to match template raster."""
    with rasterio.open(template_path) as tmpl:
        with rasterio.open(src_path) as src:
            kwargs = src.meta.copy()
            kwargs.update({
                "crs": tmpl.crs,
                "transform": tmpl.transform,
                "width": tmpl.width,
                "height": tmpl.height,
            })

            with rasterio.open(dst_path, "w", **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=tmpl.transform,
                        dst_crs=tmpl.crs,
                        resampling=resampling,
                    )
    return dst_path


def compute_zonal_stats(subbasins, zones, nodata_zones=None):
    """Compute fraction of each zone class within each subbasin.

    Returns DataFrame with columns: subbasin_id, zone_class, fraction
    """
    unique_subs = np.unique(subbasins[subbasins > 0])
    records = []

    for sub_id in unique_subs:
        mask = subbasins == sub_id
        sub_zones = zones[mask]

        if nodata_zones is not None:
            sub_zones = sub_zones[sub_zones != nodata_zones]

        if len(sub_zones) == 0:
            continue

        total = len(sub_zones)
        unique_zones, counts = np.unique(sub_zones, return_counts=True)
        for z, c in zip(unique_zones, counts):
            records.append({
                "subbasin_id": int(sub_id),
                "class": int(z),
                "fraction": c / total,
            })

    return pd.DataFrame(records)


def write_landuse_lum(landuse_classes, out_path):
    """Write landuse.lum file."""
    # Read lookup
    lu_lookup = pd.read_csv(LOOKUP_LU)
    lu_lookup = lu_lookup.set_index("LANDUSE_ID")["SWAT_CODE"].to_dict()

    with open(out_path, "w") as f:
        f.write("landuse.lum\n")
        f.write("name               cal_group       ov_mann         tile_dep        sep               \"sp_q\",\"sp_fcov\",\"sp_ov\",\"dist\",\"drain\",\"usle_p\",\"usle_ls\",\"nut_a\",\"sed_a\", \"pt_a\",\"p_q\",\"p_f\",\"p_dep\",\"p_wet\",\"n_upt\",\"n_min\",\"p_upt\",\"p_min\",\"ch_a\",\"ch_n\",\"ch_k\",\"tb_a\",\"tb_dep\",\"tb_slope\",\"tb_wet\",\"tb_len\",\"tb_width\"\n")

        for cls in sorted(landuse_classes):
            code = lu_lookup.get(cls, f"CL{cls}")
            f.write(f"{code:19s} 0               0.014000        0.000000        0.000000          0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000, 0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000,0.000000\n")


def write_soils_sol(soil_classes, out_path):
    """Write soils.sol file referencing usersoil.csv."""
    soil_lookup = pd.read_csv(LOOKUP_SOIL)
    soil_lookup = soil_lookup.set_index("SOIL_ID")["NAME"].to_dict()

    with open(out_path, "w") as f:
        f.write("soils.sol\n")
        f.write("name          hydro_group   dp        porosity       awc            k              cbn           clay          sand          silt          rock          alb           usle_k        ec            cal           ph            \"soil_depth\"\n")

        for cls in sorted(soil_classes):
            name = soil_lookup.get(cls, f"SOIL_{cls}")
            f.write(f"{name:14s} D             2000.000  0.500000       0.150000       2.000000       1.500000      25.000000     35.000000     40.000000     10.000000     0.100000      0.280000      1.000000      0.000000      7.000000      \"2000\"\n")


def write_hru_data(hru_df, out_path):
    """Write hru-data.hru file."""
    with open(out_path, "w") as f:
        f.write("hru-data.hru\n")
        f.write("id  name  topo  hyd  lum  soil  \"snow\", \"field\", \"lnk\", \"init\", \"mgt\", \"soil_plant_init\", \"surf_stor\", \"sdr\", \"cmd\", \"plt\", \"irr\", \"fert\", \"graz\", \"harv\", \"burn\", \" Pest\", \"sw\", \"dgn\", \"pcp\", \"tmp\", \"slr\", \"hmd\", \"wnd\", \"pet\", \"atmo\", \"lai\", \"grww\", \"aorg\", \"conc\", \"flo\", \"sed\", \"nut\", \"chm\", \"salt\", \"path\", \"met\", \"test\"\n")

        for _, row in hru_df.iterrows():
            f.write(f"{row['hru_id']:4d} {row['name']:12s} {row['topo']:12s} {row['hyd']:12s} {row['lum']:12s} {row['soil']:12s} \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\"\n")


def write_connect_con(hru_df, out_path):
    """Write connect.con file (HRU → channel routing)."""
    with open(out_path, "w") as f:
        f.write("connect.con\n")
        f.write("id  name               order    area           len            slope          lat            lon            \"obj\", \"obj_num\", \"hyd_typ\", \"frac\", \"sr\", \"dr\", \"tot\", \"lk\", \"elem\", \"init\", \"out\", \"in\", \"rec\", \"dlr\", \"vol\", \"flo\", \"sed\", \"orgn\", \"sedp\", \"no3\", \"solp\", \"chla\", \"nh3\", \"no2\", \"cbod\", \"dox\", \"san\", \"sil\", \"cla\", \"sag\", \"lag\", \"grv\", \"temp\"\n")

        for _, row in hru_df.iterrows():
            f.write(f"{row['hru_id']:4d} {row['name']:19s} {row['subbasin_id']:8d} {row['area_ha']:14.4f} {row['len']:14.4f} {row['slope']:14.6f} {row['lat']:14.6f} {row['lon']:14.6f} \"hru\", {row['hru_id']:9d}, \"tot\", {1.0:8.4f}, {row['sr']:8.4f}, {row['dr']:8.4f}, {row['tot']:8.4f}, \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\"\n")


def write_time_sim(out_path):
    """Write time.sim file."""
    with open(out_path, "w") as f:
        f.write("time.sim\n")
        f.write("day_start  yrc_start  day_end  yrc_end  step\n")
        f.write(f"{SIM_START[1]:10d} {SIM_START[0]:10d} {SIM_END[1]:8d} {SIM_END[0]:8d} 0\n")


def write_file_cio(out_path):
    """Write file.cio (master control file)."""
    with open(out_path, "w") as f:
        f.write("file.cio\n")
        f.write("basin.bsn\n")
        f.write("aquifer.aqu\n")
        f.write("channel.cha\n")
        f.write("connect.con\n")
        f.write("hydrology.hyd\n")
        f.write("hru-data.hru\n")
        f.write("landuse.lum\n")
        f.write("soils.sol\n")
        f.write("topography.top\n")
        f.write("time.sim\n")
        f.write("weather-sta.cli\n")
        f.write("pcp.cli\n")
        f.write("tmp.cli\n")
        f.write("slr.cli\n")
        f.write("hmd.cli\n")
        f.write("wnd.cli\n")
        f.write("weather-wgn.cli\n")


def write_basin_bsn(out_path):
    """Write basin.bsn file."""
    with open(out_path, "w") as f:
        f.write("basin.bsn\n")
        f.write("name              \"lat\", \"lon\", \"elev\", \"area\", \"slope\", \"dep\", \"dep_bot\", \"dep_wt\", \"pr\", \"eq\", \"pc\", \"surf_stor\", \"aeration\", \"snow\", \"sw\", \"gw\", \"aqu\", \"dgn\", \"ch\", \"res\", \"rec\", \"exc\", \"salt\", \"path\", \"met\", \"test\"\n")
        f.write("basin1             45.800000, 120.000000, 200.000000, 1843000.000000, 0.020000, 2000.000000, 2000.000000, 2000.000000, 0, 0, 0, \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\"\n")


def write_aquifer_aqu(out_path):
    """Write aquifer.aqu file."""
    with open(out_path, "w") as f:
        f.write("aquifer.aqu\n")
        f.write("id  name          \"gw_flo\", \"gw_sed\", \"gw_no3\", \"gw_solp\", \"gw_chla\", \"gw_nh3\", \"gw_no2\", \"gw_cbod\", \"gw_dox\", \"gw_san\", \"gw_sil\", \"gw_cla\", \"gw_sag\", \"gw_lag\", \"gw_grv\", \"gw_tmp\"\n")
        f.write("1   aquifer1      \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\"\n")


def write_channel_cha(n_channels, out_path):
    """Write channel.cha file."""
    with open(out_path, "w") as f:
        f.write("channel.cha\n")
        f.write("id  name          order  \"hyd\", \"init\", \"rel\", \"hyd_rad\", \"side_slp\", \"bot_wid\", \"dep\", \"len\", \"slope\", \"lat\", \"lon\", \"area\", \"a\", \"b\", \"c\", \"d\", \"e\", \"f\", \"g\", \"h\", \"i\", \"j\", \"k\", \"l\", \"m\", \"n\", \"o\", \"p\", \"q\", \"r\", \"s\", \"t\", \"u\", \"v\", \"w\", \"x\", \"y\", \"z\"\n")
        for i in range(1, n_channels + 1):
            f.write(f"{i:4d} channel{i:6d} {i:6d} \"null\", \"null\", \"null\", 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000\n")


def write_hydrology_hyd(out_path):
    """Write hydrology.hyd file."""
    with open(out_path, "w") as f:
        f.write("hydrology.hyd\n")
        f.write("name          lat_ttime  lat_sed  can_max  esco  epco  orgn  orgp  cns  cn_swf  \"sw_init\", \"sno_init\", \"pet\", \"latq\", \"surlag\", \"lyr1\", \"lyr2\", \"lyr3\", \"lyr4\", \"lyr5\", \"lyr6\", \"lyr7\", \"lyr8\", \"lyr9\", \"lyr10\"\n")
        f.write("hyd1          0.500000   0.000000 10.000000 0.950000 1.000000 0.000000 0.000000 0.000000 0.500000 \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\"\n")


def write_topography_top(hru_df, out_path):
    """Write topography.top file."""
    with open(out_path, "w") as f:
        f.write("topography.top\n")
        f.write("name          lat_len   ch_l       ch_s     ch_w   fp_fract  \"slp\", \"slp_len\", \"slp_w\", \"slp_len_fr\", \"slp_w_fr\", \"lat_slp\", \"lat_slp_len\", \"lat_slp_w\", \"lat_slp_len_fr\", \"lat_slp_w_fr\"\n")
        for _, row in hru_df.iterrows():
            f.write(f"{row['name']:14s} {row['lat_len']:9.2f} {row['ch_l']:10.2f} {row['ch_s']:8.4f} {row['ch_w']:8.2f} {row['fp_fract']:9.4f} \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\", \"null\"\n")


def main():
    print("=" * 60)
    print("HRU & TxtInOut Generator")
    print("=" * 60)

    TXTOUT.mkdir(parents=True, exist_ok=True)

    # Step 1: Align rasters
    print("\nAligning landuse raster to subbasin grid...")
    lu_aligned = PROCESSED / "CLCD_2018_aligned.tif"
    if not lu_aligned.exists():
        align_raster(LANDUSE_TIF, lu_aligned, SUBBASINS_TIF)

    print("Aligning soil raster to subbasin grid...")
    soil_aligned = PROCESSED / "HWSD2_aligned.tif"
    if not soil_aligned.exists():
        align_raster(SOIL_TIF, soil_aligned, SUBBASINS_TIF)

    # Step 2: Read aligned rasters
    print("Reading rasters...")
    with rasterio.open(SUBBASINS_TIF) as src:
        subbasins = src.read(1)
        sub_transform = src.transform
        sub_crs = src.crs
        pixel_area_ha = (src.res[0] * src.res[1]) / 10000.0

    with rasterio.open(lu_aligned) as src:
        landuse = src.read(1)
        lu_nodata = src.nodata

    with rasterio.open(soil_aligned) as src:
        soil = src.read(1)
        soil_nodata = src.nodata

    # Step 3: Compute zonal statistics
    print("Computing landuse fractions per subbasin...")
    lu_stats = compute_zonal_stats(subbasins, landuse, lu_nodata)

    print("Computing soil fractions per subbasin...")
    soil_stats = compute_zonal_stats(subbasins, soil, soil_nodata)

    # Step 4: Generate HRUs (landuse × soil combinations)
    print("Generating HRUs...")
    lu_lookup = pd.read_csv(LOOKUP_LU)
    lu_lookup = lu_lookup.set_index("LANDUSE_ID")["SWAT_CODE"].to_dict()

    soil_lookup = pd.read_csv(LOOKUP_SOIL)
    soil_lookup = soil_lookup.set_index("SOIL_ID")["NAME"].to_dict()

    hru_records = []
    hru_id = 1

    unique_subs = sorted(lu_stats["subbasin_id"].unique())

    for sub_id in tqdm(unique_subs, desc="Subbasins"):
        sub_lu = lu_stats[lu_stats["subbasin_id"] == sub_id]
        sub_soil = soil_stats[soil_stats["subbasin_id"] == sub_id]

        for _, lu_row in sub_lu.iterrows():
            for _, soil_row in sub_soil.iterrows():
                frac = lu_row["fraction"] * soil_row["fraction"]
                if frac < 0.001:  # Skip very small combinations (<0.1%)
                    continue

                lu_code = lu_lookup.get(lu_row["class"], f"CL{lu_row['class']}")
                soil_code = soil_lookup.get(soil_row["class"], f"SOIL_{soil_row['class']}")

                # Get subbasin centroid
                mask = subbasins == sub_id
                rows, cols = np.where(mask)
                if len(rows) == 0:
                    continue
                centroid_row = int(rows.mean())
                centroid_col = int(cols.mean())
                lon, lat = rasterio.transform.xy(sub_transform, centroid_row, centroid_col)

                area_ha = frac * mask.sum() * pixel_area_ha

                hru_records.append({
                    "hru_id": hru_id,
                    "subbasin_id": sub_id,
                    "name": f"hru{hru_id:04d}",
                    "topo": f"top{hru_id:04d}",
                    "hyd": "hyd1",
                    "lum": lu_code,
                    "soil": soil_code,
                    "area_ha": area_ha,
                    "lat": lat,
                    "lon": lon,
                    "len": 100.0,
                    "slope": 0.02,
                    "sr": 0.0,
                    "dr": 0.0,
                    "tot": 1.0,
                    "lat_len": 100.0,
                    "ch_l": 1000.0,
                    "ch_s": 0.001,
                    "ch_w": 10.0,
                    "fp_fract": 0.0,
                })
                hru_id += 1

    hru_df = pd.DataFrame(hru_records)
    print(f"Generated {len(hru_df)} HRUs")

    # Step 5: Write TxtInOut files
    print("\nWriting TxtInOut files...")

    write_file_cio(TXTOUT / "file.cio")
    write_time_sim(TXTOUT / "time.sim")
    write_basin_bsn(TXTOUT / "basin.bsn")
    write_aquifer_aqu(TXTOUT / "aquifer.aqu")
    write_channel_cha(len(unique_subs), TXTOUT / "channel.cha")
    write_hydrology_hyd(TXTOUT / "hydrology.hyd")
    write_hru_data(hru_df, TXTOUT / "hru-data.hru")
    write_connect_con(hru_df, TXTOUT / "connect.con")
    write_topography_top(hru_df, TXTOUT / "topography.top")

    lu_classes = sorted(lu_stats["class"].unique())
    write_landuse_lum(lu_classes, TXTOUT / "landuse.lum")

    soil_classes = sorted(soil_stats["class"].unique())
    write_soils_sol(soil_classes, TXTOUT / "soils.sol")

    # Copy weather files
    print("Copying weather files...")
    weather_cli = PROCESSED / "weather_cli"
    for f in weather_cli.glob("*"):
        import shutil
        shutil.copy(f, TXTOUT / f.name)

    print(f"\n{'=' * 60}")
    print(f"TxtInOut directory: {TXTOUT}")
    print(f"Files generated: {len(list(TXTOUT.glob('*')))}")
    print("=" * 60)


if __name__ == "__main__":
    main()
