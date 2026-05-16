"""
Watershed delineation module.
Handles TauDEM execution OR reads existing shapefiles,
builds channel topology, and generates watershed raster.
"""
import os
import subprocess
import numpy as np
from osgeo import gdal, ogr, osr
from typing import Dict, List, Tuple, Optional, Set
import logging

logger = logging.getLogger(__name__)


class Channel:
    """Represents a single channel/reach."""
    def __init__(self, linkno: int, dslinkno: int, uslinkno1: int, uslinkno2: int,
                 length: float, area: float, order: int, wsno: int,
                 slope: float, geom=None):
        self.linkno = linkno
        self.dslinkno = dslinkno
        self.uslinkno1 = uslinkno1
        self.uslinkno2 = uslinkno2
        self.length = length
        self.area = area  # downstream contributing area
        self.order = order
        self.wsno = wsno  # subbasin/watershed number
        self.slope = slope
        self.geom = geom  # WKT or ogr geometry
        # SWAT internal IDs (assigned later)
        self.swat_channel_id: int = 0
        self.swat_basin_id: int = 0


class DelineationResult:
    """Holds all results from the delineation step."""
    def __init__(self):
        self.channels: Dict[int, Channel] = {}  # keyed by LINKNO
        self.subbasins: Dict[int, dict] = {}    # keyed by subbasin ID
        self.watershed_raster: Optional[str] = None
        self.channel_shp: Optional[str] = None
        self.subbasin_shp: Optional[str] = None
        self.outlet_linknos: List[int] = []
        self.channel_count: int = 0
        self.subbasin_count: int = 0


def run_taudem_delineation(config: dict, work_dir: str) -> DelineationResult:
    """
    Run full TauDEM D8 workflow based on config.
    This is a placeholder for full TauDEM automation.
    For now we focus on the 'use_existing' path.
    """
    raise NotImplementedError("Full TauDEM automation not yet implemented. Use use_existing_delineation=true.")


def read_channel_shapefile(path: str) -> Dict[int, Channel]:
    """Read channel shapefile and return dict of Channel objects keyed by LINKNO."""
    ds = ogr.GetDriverByName("ESRI Shapefile").Open(path, 0)
    layer = ds.GetLayer()
    channels = {}
    for feat in layer:
        linkno = feat.GetField("LINKNO")
        dslinkno = feat.GetField("DSLINKNO")
        uslinkno1 = feat.GetField("USLINKNO1")
        uslinkno2 = feat.GetField("USLINKNO2")
        length = feat.GetField("Length") or 0.0
        area = feat.GetField("DSContArea") or 0.0
        order = feat.GetField("strmOrder") or 0
        wsno = feat.GetField("WSNO") or 0
        slope = feat.GetField("Slope") or 0.0
        geom = feat.GetGeometryRef().Clone() if feat.GetGeometryRef() else None
        channels[linkno] = Channel(
            linkno=linkno,
            dslinkno=dslinkno,
            uslinkno1=uslinkno1,
            uslinkno2=uslinkno2,
            length=length,
            area=area,
            order=order,
            wsno=wsno,
            slope=slope,
            geom=geom,
        )
    ds = None
    logger.info(f"Read {len(channels)} channels from {path}")
    return channels


def read_subbasin_shapefile(path: str) -> Dict[int, dict]:
    """Read subbasin shapefile and return dict of subbasin info."""
    ds = ogr.GetDriverByName("ESRI Shapefile").Open(path, 0)
    layer = ds.GetLayer()
    subbasins = {}
    for feat in layer:
        sb_id = feat.GetField("Subbasin")
        area = feat.GetField("Area") or 0.0
        geom = feat.GetGeometryRef().Clone() if feat.GetGeometryRef() else None
        subbasins[sb_id] = {
            "id": sb_id,
            "area": area,
            "geom": geom,
        }
    ds = None
    logger.info(f"Read {len(subbasins)} subbasins from {path}")
    return subbasins


def assign_swat_channel_ids(channels: Dict[int, Channel]) -> None:
    """
    Assign sequential SWAT channel IDs (1-based) to channels.
    Skip channels with zero length or that are inside lakes (future).
    For simplicity, assign in ascending LINKNO order.
    """
    swat_id = 1
    for linkno in sorted(channels.keys()):
        ch = channels[linkno]
        # In real QSWATPlus, zero-length channels and channels inside lakes are skipped.
        # For now we include all channels with positive length.
        if ch.length > 0:
            ch.swat_channel_id = swat_id
            swat_id += 1
        else:
            ch.swat_channel_id = 0
    logger.info(f"Assigned {swat_id - 1} SWAT channel IDs")


def assign_swat_basin_ids(channels: Dict[int, Channel], subbasins: Dict[int, dict]) -> None:
    """
    Assign SWAT basin IDs to subbasins.
    In QSWATPlus, SWATBasin is sequential and some subbasins may be removed (e.g., inside lakes).
    For simplicity, assign 1-based sequential IDs to all subbasins that have a channel.
    """
    # Map WSNO to subbasin ID
    wsno_to_subbasin = {sb["id"]: sb_id for sb_id, sb in subbasins.items()}
    
    # Find which subbasins have channels
    subbasins_with_channels = set()
    for ch in channels.values():
        if ch.swat_channel_id > 0 and ch.wsno in wsno_to_subbasin:
            subbasins_with_channels.add(ch.wsno)
    
    swat_id = 1
    for wsno in sorted(subbasins_with_channels):
        # Find channels in this subbasin
        for ch in channels.values():
            if ch.wsno == wsno and ch.swat_channel_id > 0:
                ch.swat_basin_id = swat_id
        # Also mark the subbasin
        if wsno in subbasins:
            subbasins[wsno]["swat_basin_id"] = swat_id
        swat_id += 1
    
    logger.info(f"Assigned {swat_id - 1} SWAT basin IDs")


def find_outlet_linknos(channels: Dict[int, Channel]) -> List[int]:
    """Find channels that are outlets (DSLINKNO == -1)."""
    outlets = [ch.linkno for ch in channels.values() if ch.dslinkno == -1]
    logger.info(f"Found {len(outlets)} outlet channels: {sorted(outlets)}")
    return outlets


def build_downstream_map(channels: Dict[int, Channel]) -> Dict[int, int]:
    """Build mapping from LINKNO to downstream LINKNO. -1 for outlets."""
    return {ch.linkno: ch.dslinkno for ch in channels.values()}


def build_upstream_map(channels: Dict[int, Channel]) -> Dict[int, List[int]]:
    """Build mapping from LINKNO to list of upstream LINKNOs."""
    upstream = {linkno: [] for linkno in channels}
    for ch in channels.values():
        if ch.uslinkno1 >= 0 and ch.uslinkno1 in upstream:
            upstream[ch.linkno].append(ch.uslinkno1)
        if ch.uslinkno2 >= 0 and ch.uslinkno2 in upstream:
            upstream[ch.linkno].append(ch.uslinkno2)
    return upstream


def generate_watershed_raster(
    subbasin_shp: str,
    reference_raster: str,
    output_path: str,
    burn_field: str = "Subbasin",
) -> str:
    """
    Rasterize subbasin shapefile to create watershed raster.
    Uses reference raster for extent/resolution/projection.
    """
    from utils.gdal_utils import rasterize_shapefile
    
    logger.info(f"Rasterizing {subbasin_shp} -> {output_path}")
    rasterize_shapefile(
        shapefile_path=subbasin_shp,
        output_raster_path=output_path,
        reference_raster_path=reference_raster,
        burn_field=burn_field,
        dtype=gdal.GDT_Int32,
        nodata=-9999,
        all_touched=True,
    )
    logger.info(f"Watershed raster created: {output_path}")
    return output_path


def run_delineation(config: dict) -> DelineationResult:
    """Main entry point for delineation."""
    result = DelineationResult()
    
    if config["project"]["use_existing_delineation"]:
        existing = config["delineation"]["existing"]
        result.channel_shp = existing["channel_shp"]
        result.subbasin_shp = existing["subbasin_shp"]
        result.channels = read_channel_shapefile(result.channel_shp)
        result.subbasins = read_subbasin_shapefile(result.subbasin_shp)
        
        # Assign SWAT IDs
        assign_swat_channel_ids(result.channels)
        assign_swat_basin_ids(result.channels, result.subbasins)
        
        # Find outlets
        result.outlet_linknos = find_outlet_linknos(result.channels)
        
        # Generate or use existing watershed raster
        if existing.get("watershed_raster") and os.path.exists(existing["watershed_raster"]):
            result.watershed_raster = existing["watershed_raster"]
        else:
            dem_path = config["inputs"]["dem"]["path"]
            out_dir = os.path.join(config["project"]["output_dir"], "delineation")
            os.makedirs(out_dir, exist_ok=True)
            result.watershed_raster = generate_watershed_raster(
                subbasin_shp=result.subbasin_shp,
                reference_raster=dem_path,
                output_path=os.path.join(out_dir, "watershed.tif"),
            )
        
        result.channel_count = sum(1 for ch in result.channels.values() if ch.swat_channel_id > 0)
        result.subbasin_count = sum(1 for sb in result.subbasins.values() if sb.get("swat_basin_id", 0) > 0)
    else:
        # TODO: Implement full TauDEM workflow
        raise NotImplementedError("TauDEM workflow not yet implemented.")
    
    return result
