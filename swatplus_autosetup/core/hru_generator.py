"""
HRU generation module.
Reads watershed, landuse, soil, and slope rasters,
computes landuse/soil/slope combinations per subbasin,
and generates HRU list.
"""
import os
import numpy as np
from osgeo import gdal
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class HRU:
    """Represents a single Hydrologic Response Unit."""
    def __init__(self, hru_id: int, subbasin_id: int, landuse_id: int,
                 soil_id: int, slope_class: int, area_ha: float,
                 cell_count: int, percent: float):
        self.hru_id = hru_id
        self.subbasin_id = subbasin_id
        self.landuse_id = landuse_id
        self.soil_id = soil_id
        self.slope_class = slope_class
        self.area_ha = area_ha
        self.cell_count = cell_count
        self.percent = percent


def prepare_raster(
    src_path: str,
    ref_path: str,
    output_path: str,
    resample_alg: int = gdal.GRA_NearestNeighbour,
) -> Tuple[np.ndarray, dict]:
    """
    Reproject/resample a raster to match reference raster,
    then read as numpy array.
    """
    from utils.gdal_utils import reproject_raster_to_match, read_raster_as_array
    
    if not os.path.exists(output_path):
        logger.info(f"Reprojecting {src_path} -> {output_path}")
        reproject_raster_to_match(src_path, output_path, ref_path, resample_alg)
    else:
        logger.info(f"Using cached reprojected raster: {output_path}")
    
    data, meta = read_raster_as_array(output_path)
    return data, meta


def classify_slope(slope_percent: float, limits: List[float]) -> int:
    """
    Classify slope percent into slope class index.
    limits: e.g. [0, 2, 5, 999] -> classes 0, 1, 2
    Returns -1 for nodata.
    """
    if slope_percent < 0 or np.isnan(slope_percent):
        return -1
    for i in range(len(limits) - 1):
        if limits[i] <= slope_percent < limits[i + 1]:
            return i
    return len(limits) - 2  # last class


def compute_hrus(
    watershed_data: np.ndarray,
    watershed_nodata: float,
    landuse_data: np.ndarray,
    landuse_nodata: float,
    soil_data: np.ndarray,
    soil_nodata: float,
    slope_data: np.ndarray,
    slope_nodata: float,
    slope_limits: List[float],
    cell_area_ha: float,
) -> Dict[int, Dict[Tuple[int, int, int], dict]]:
    """
    Compute HRU composition for each subbasin.
    Returns: {subbasin_id: {(landuse, soil, slope): {"area_ha": ..., "cells": ...}}}
    """
    # Ensure all arrays have the same shape
    assert watershed_data.shape == landuse_data.shape == soil_data.shape == slope_data.shape, \
        f"Shape mismatch: ws={watershed_data.shape}, lu={landuse_data.shape}, soil={soil_data.shape}, slp={slope_data.shape}"
    
    h, w = watershed_data.shape
    logger.info(f"Processing {h}x{w} = {h*w} pixels, cell_area={cell_area_ha:.4f} ha")
    
    # Classify slope
    slope_class = np.vectorize(lambda x: classify_slope(x, slope_limits))(slope_data)
    
    subbasin_combos = defaultdict(lambda: defaultdict(lambda: {"area_ha": 0.0, "cells": 0}))
    
    valid_mask = (
        (watershed_data != watershed_nodata) &
        (landuse_data != landuse_nodata) &
        (soil_data != soil_nodata) &
        (slope_data != slope_nodata) &
        (slope_class >= 0)
    )
    
    valid_pixels = np.count_nonzero(valid_mask)
    logger.info(f"Valid pixels: {valid_pixels} / {h*w} ({100*valid_pixels/(h*w):.1f}%)")
    
    # Vectorized counting using unique combinations
    ws_valid = watershed_data[valid_mask]
    lu_valid = landuse_data[valid_mask].astype(int)
    soil_valid = soil_data[valid_mask].astype(int)
    slope_valid = slope_class[valid_mask].astype(int)
    
    # Stack into structured array for unique counting
    combos = np.core.records.fromarrays(
        [ws_valid, lu_valid, soil_valid, slope_valid],
        names="subbasin,landuse,soil,slope",
        formats="i4,i4,i4,i4"
    )
    
    unique_combos, counts = np.unique(combos, return_counts=True)
    
    for combo, count in zip(unique_combos, counts):
        sb = int(combo["subbasin"])
        lu = int(combo["landuse"])
        sl = int(combo["soil"])
        sp = int(combo["slope"])
        area_ha = count * cell_area_ha
        subbasin_combos[sb][(lu, sl, sp)]["area_ha"] += area_ha
        subbasin_combos[sb][(lu, sl, sp)]["cells"] += count
    
    return subbasin_combos


def remove_small_hrus(
    subbasin_combos: Dict[int, Dict[Tuple[int, int, int], dict]],
    min_area_ha: float,
    min_percent: float,
) -> Dict[int, Dict[Tuple[int, int, int], dict]]:
    """
    Remove HRUs below area or percent threshold by redistributing their area
    to the largest HRU in the same subbasin.
    """
    cleaned = {}
    for sb_id, combos in subbasin_combos.items():
        total_area = sum(info["area_ha"] for info in combos.values())
        if total_area == 0:
            continue
        
        # Filter by thresholds
        kept = {}
        removed_area = 0.0
        removed_cells = 0
        for key, info in combos.items():
            pct = 100.0 * info["area_ha"] / total_area
            if info["area_ha"] >= min_area_ha and pct >= min_percent:
                kept[key] = dict(info)
            else:
                removed_area += info["area_ha"]
                removed_cells += info["cells"]
        
        if not kept:
            # If all would be removed, keep the largest one
            largest_key = max(combos.keys(), key=lambda k: combos[k]["area_ha"])
            kept[largest_key] = dict(combos[largest_key])
            removed_area -= combos[largest_key]["area_ha"]
            removed_cells -= combos[largest_key]["cells"]
        
        # Redistribute removed area to largest kept HRU
        if removed_area > 0 and kept:
            largest_key = max(kept.keys(), key=lambda k: kept[k]["area_ha"])
            kept[largest_key]["area_ha"] += removed_area
            kept[largest_key]["cells"] += removed_cells
        
        # Recalculate percentages
        total_area = sum(info["area_ha"] for info in kept.values())
        for info in kept.values():
            info["percent"] = 100.0 * info["area_ha"] / total_area if total_area > 0 else 0.0
        
        cleaned[sb_id] = kept
    
    return cleaned


def generate_hru_list(
    subbasin_combos: Dict[int, Dict[Tuple[int, int, int], dict]],
) -> List[HRU]:
    """Generate sequential HRU list from subbasin combos."""
    hrus = []
    hru_id = 1
    for sb_id in sorted(subbasin_combos.keys()):
        combos = subbasin_combos[sb_id]
        for (lu, soil, slope), info in sorted(combos.items()):
            hrus.append(HRU(
                hru_id=hru_id,
                subbasin_id=sb_id,
                landuse_id=lu,
                soil_id=soil,
                slope_class=slope,
                area_ha=info["area_ha"],
                cell_count=info["cells"],
                percent=info.get("percent", 0.0),
            ))
            hru_id += 1
    
    logger.info(f"Generated {len(hrus)} HRUs")
    return hrus


def run_hru_generation(config: dict, delineation_result) -> List[HRU]:
    """Main entry point for HRU generation."""
    out_dir = os.path.join(config["project"]["output_dir"], "hrus")
    os.makedirs(out_dir, exist_ok=True)
    
    # Read watershed raster
    from utils.gdal_utils import read_raster_as_array
    ws_data, ws_meta = read_raster_as_array(delineation_result.watershed_raster)
    ws_nodata = ws_meta["nodata"] if ws_meta["nodata"] is not None else -9999
    
    # Compute cell area in hectares from geotransform
    gt = ws_meta["geotransform"]
    cell_area_m2 = abs(gt[1] * gt[5])
    cell_area_ha = cell_area_m2 / 10000.0
    logger.info(f"Cell area: {cell_area_m2:.1f} m2 = {cell_area_ha:.4f} ha")
    
    # Prepare landuse raster
    lu_data, lu_meta = prepare_raster(
        config["inputs"]["landuse"]["raster"],
        delineation_result.watershed_raster,
        os.path.join(out_dir, "landuse_aligned.tif"),
        resample_alg=gdal.GRA_NearestNeighbour,
    )
    lu_nodata = lu_meta["nodata"] if lu_meta["nodata"] is not None else -9999
    
    # Prepare soil raster
    soil_data, soil_meta = prepare_raster(
        config["inputs"]["soil"]["raster"],
        delineation_result.watershed_raster,
        os.path.join(out_dir, "soil_aligned.tif"),
        resample_alg=gdal.GRA_NearestNeighbour,
    )
    soil_nodata = soil_meta["nodata"] if soil_meta["nodata"] is not None else -9999
    
    # Prepare slope raster
    slope_data, slope_meta = prepare_raster(
        config["inputs"]["slope"]["raster"],
        delineation_result.watershed_raster,
        os.path.join(out_dir, "slope_aligned.tif"),
        resample_alg=gdal.GRA_Bilinear,
    )
    slope_nodata = slope_meta["nodata"] if slope_meta["nodata"] is not None else -9999
    
    # Compute HRU combos
    slope_limits = config["inputs"]["slope"]["limits"]
    subbasin_combos = compute_hrus(
        watershed_data=ws_data,
        watershed_nodata=ws_nodata,
        landuse_data=lu_data,
        landuse_nodata=lu_nodata,
        soil_data=soil_data,
        soil_nodata=soil_nodata,
        slope_data=slope_data,
        slope_nodata=slope_nodata,
        slope_limits=slope_limits,
        cell_area_ha=cell_area_ha,
    )
    
    # Apply thresholds if configured
    hru_config = config["hru"]
    if hru_config.get("min_area_ha", 0) > 0 or hru_config.get("min_percent", 0) > 0:
        subbasin_combos = remove_small_hrus(
            subbasin_combos,
            min_area_ha=hru_config.get("min_area_ha", 0),
            min_percent=hru_config.get("min_percent", 0),
        )
    
    # Generate HRU list
    hrus = generate_hru_list(subbasin_combos)
    
    # Write HRU report
    report_path = os.path.join(out_dir, "hru_report.txt")
    with open(report_path, "w") as f:
        f.write("HRU Report\n")
        f.write("=" * 80 + "\n")
        f.write(f"{'HRU_ID':>8} {'Subbasin':>10} {'Landuse':>10} {'Soil':>10} {'Slope':>8} {'Area_ha':>12} {'Cells':>10} {'Percent':>10}\n")
        f.write("-" * 80 + "\n")
        for hru in hrus:
            f.write(f"{hru.hru_id:>8} {hru.subbasin_id:>10} {hru.landuse_id:>10} {hru.soil_id:>10} {hru.slope_class:>8} {hru.area_ha:>12.2f} {hru.cell_count:>10} {hru.percent:>10.2f}\n")
    
    logger.info(f"HRU report written to {report_path}")
    return hrus
