"""
State management for saving/loading intermediate results between steps.
"""
import json
import os
from typing import Dict, List, Optional
from core.delineation import DelineationResult, Channel


def save_delineation_result(result: DelineationResult, path: str):
    """Save delineation result to JSON (excluding geometry objects)."""
    data = {
        "channel_shp": result.channel_shp,
        "subbasin_shp": result.subbasin_shp,
        "watershed_raster": result.watershed_raster,
        "outlet_linknos": result.outlet_linknos,
        "channel_count": result.channel_count,
        "subbasin_count": result.subbasin_count,
        "channels": {},
        "subbasins": {},
    }
    
    for linkno, ch in result.channels.items():
        data["channels"][str(linkno)] = {
            "linkno": ch.linkno,
            "dslinkno": ch.dslinkno,
            "uslinkno1": ch.uslinkno1,
            "uslinkno2": ch.uslinkno2,
            "length": ch.length,
            "area": ch.area,
            "order": ch.order,
            "wsno": ch.wsno,
            "slope": ch.slope,
            "swat_channel_id": ch.swat_channel_id,
            "swat_basin_id": ch.swat_basin_id,
        }
    
    for sb_id, sb in result.subbasins.items():
        data["subbasins"][str(sb_id)] = {
            "id": sb["id"],
            "area": sb["area"],
            "swat_basin_id": sb.get("swat_basin_id", 0),
        }
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_delineation_result(path: str) -> Optional[DelineationResult]:
    """Load delineation result from JSON."""
    if not os.path.exists(path):
        return None
    
    with open(path) as f:
        data = json.load(f)
    
    result = DelineationResult()
    result.channel_shp = data.get("channel_shp")
    result.subbasin_shp = data.get("subbasin_shp")
    result.watershed_raster = data.get("watershed_raster")
    result.outlet_linknos = data.get("outlet_linknos", [])
    result.channel_count = data.get("channel_count", 0)
    result.subbasin_count = data.get("subbasin_count", 0)
    
    for linkno_str, ch_data in data.get("channels", {}).items():
        ch = Channel(
            linkno=ch_data["linkno"],
            dslinkno=ch_data["dslinkno"],
            uslinkno1=ch_data["uslinkno1"],
            uslinkno2=ch_data["uslinkno2"],
            length=ch_data["length"],
            area=ch_data["area"],
            order=ch_data["order"],
            wsno=ch_data["wsno"],
            slope=ch_data["slope"],
        )
        ch.swat_channel_id = ch_data.get("swat_channel_id", 0)
        ch.swat_basin_id = ch_data.get("swat_basin_id", 0)
        result.channels[ch.linkno] = ch
    
    for sb_id_str, sb_data in data.get("subbasins", {}).items():
        result.subbasins[sb_data["id"]] = {
            "id": sb_data["id"],
            "area": sb_data["area"],
            "swat_basin_id": sb_data.get("swat_basin_id", 0),
        }
    
    return result
