"""
Reservoir support module.
Identifies reservoir outlet points, finds their host channels,
and generates reservoir input files for SWAT+.
"""
import os
from osgeo import ogr
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class Reservoir:
    """Represents a single reservoir."""
    def __init__(self, res_id: int, point_ids: List[int], x: float, y: float,
                 subbasin_id: int, channel_linkno: int, ds_linkno: int):
        self.res_id = res_id
        self.point_ids = point_ids
        self.x = x
        self.y = y
        self.subbasin_id = subbasin_id
        self.channel_linkno = channel_linkno
        self.ds_linkno = ds_linkno  # downstream channel LINKNO


def identify_reservoirs(outlets_shp: str, subbasin_shp: str,
                        channel_shp: str) -> List[Reservoir]:
    """
    Read outlets shapefile, identify reservoir points (RES=1),
    find their host subbasin and nearest channel.
    Merge multiple reservoir points that map to the same nearest channel.
    """
    # Read outlets
    ds = ogr.GetDriverByName("ESRI Shapefile").Open(outlets_shp, 0)
    if ds is None:
        logger.warning(f"Cannot open outlets shapefile: {outlets_shp}")
        return []
    
    layer = ds.GetLayer()
    defn = layer.GetLayerDefn()
    field_names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
    
    res_field = "RES" if "RES" in field_names else None
    ptid_field = "PointId" if "PointId" in field_names else "ID"
    
    res_points = []
    for feat in layer:
        if res_field and feat.GetField(res_field) == 1:
            geom = feat.GetGeometryRef()
            res_points.append({
                "id": feat.GetField(ptid_field),
                "x": geom.GetX(),
                "y": geom.GetY(),
            })
    ds = None
    
    if not res_points:
        logger.info("No reservoir outlets found (RES=1)")
        return []
    
    logger.info(f"Found {len(res_points)} reservoir outlet point(s)")
    
    # Read subbasins for spatial query
    sb_ds = ogr.GetDriverByName("ESRI Shapefile").Open(subbasin_shp, 0)
    sb_layer = sb_ds.GetLayer()
    
    # Read channels for nearest search
    ch_ds = ogr.GetDriverByName("ESRI Shapefile").Open(channel_shp, 0)
    ch_layer = ch_ds.GetLayer()
    
    # Group reservoir points by nearest channel
    channel_groups = defaultdict(list)
    
    for rp in res_points:
        pt = ogr.Geometry(ogr.wkbPoint)
        pt.AddPoint(rp["x"], rp["y"])
        
        # Find nearest channel
        min_dist = 1e9
        nearest_linkno = None
        ch_layer.ResetReading()
        for feat in ch_layer:
            dist = feat.GetGeometryRef().Distance(pt)
            if dist < min_dist:
                min_dist = dist
                nearest_linkno = feat.GetField("LINKNO")
        
        if nearest_linkno is not None:
            channel_groups[nearest_linkno].append({
                **rp,
                "dist": min_dist,
            })
    
    sb_ds = None
    ch_ds = None
    
    # Build channel data for downstream lookup
    ch_ds = ogr.GetDriverByName("ESRI Shapefile").Open(channel_shp, 0)
    ch_layer = ch_ds.GetLayer()
    channels_data = {}
    for feat in ch_layer:
        linkno = feat.GetField("LINKNO")
        channels_data[linkno] = {
            "wsno": feat.GetField("WSNO") or 0,
            "dslinkno": feat.GetField("DSLINKNO") or -1,
        }
    ch_ds = None
    
    # Create Reservoir objects (merged by nearest channel)
    reservoirs = []
    for i, (linkno, points) in enumerate(sorted(channel_groups.items()), start=1):
        # Use centroid of all points for reservoir location
        avg_x = sum(p["x"] for p in points) / len(points)
        avg_y = sum(p["y"] for p in points) / len(points)
        point_ids = [p["id"] for p in points]
        
        # Find containing subbasin (use first point's subbasin)
        sb_ds = ogr.GetDriverByName("ESRI Shapefile").Open(subbasin_shp, 0)
        sb_layer = sb_ds.GetLayer()
        pt = ogr.Geometry(ogr.wkbPoint)
        pt.AddPoint(avg_x, avg_y)
        sb_id = None
        for feat in sb_layer:
            if feat.GetGeometryRef().Contains(pt):
                sb_id = feat.GetField("Subbasin")
                break
        sb_ds = None
        
        ds_linkno = channels_data.get(linkno, {}).get("dslinkno", -1)
        
        logger.info(f"  Reservoir {i}: merged {len(points)} point(s) -> PointIds={point_ids}, "
                    f"Subbasin={sb_id}, NearestChannel=LINKNO={linkno}, "
                    f"Downstream=LINKNO={ds_linkno}")
        
        reservoirs.append(Reservoir(
            res_id=i,
            point_ids=point_ids,
            x=avg_x,
            y=avg_y,
            subbasin_id=sb_id if sb_id else 0,
            channel_linkno=linkno,
            ds_linkno=ds_linkno,
        ))
    
    return reservoirs


def write_reservoir_con(reservoirs: List[Reservoir], linkno_to_cha: Dict[int, int],
                        output_path: str):
    """
    Generate reservoir.con file.
    Reservoir outflows to the channel it replaces (not the downstream channel).
    This way the replaced channel still carries the reservoir outflow.
    """
    lines = []
    lines.append("reservoir.con: reservoirs")
    lines.append(
        "id  name                gis_id          area           lat           lon          elev       res               wst       cst      ovfl      rule   out_tot  obtyp  obno   htyp       frac"
    )
    
    for res in reservoirs:
        # Outflow to the replaced channel itself (not downstream)
        # This ensures the replaced channel still receives reservoir outflow
        if res.channel_linkno >= 0 and res.channel_linkno in linkno_to_cha:
            obtyp = "cha"
            obno = linkno_to_cha[res.channel_linkno]
        elif res.ds_linkno >= 0 and res.ds_linkno in linkno_to_cha:
            obtyp = "cha"
            obno = linkno_to_cha[res.ds_linkno]
        else:
            obtyp = "out"
            obno = 1
        
        lines.append(
            f"{res.res_id:4d}  res{res.res_id:04d}  {res.point_ids[0]:22d}       0.0000 {res.y:14.6f} {res.x:14.6f}       0.00 "
            f"{res.res_id:8d} null        0         0         0                 1  {obtyp:4s} {obno:5d} tot      1.0000"
        )
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"Wrote {output_path} ({len(reservoirs)} reservoirs)")


def write_reservoir_res(reservoirs: List[Reservoir], output_path: str):
    """Generate reservoir.res (reservoir parameter index file)."""
    lines = []
    lines.append("reservoir.res")
    lines.append("id  name          init         hyd          rel          sed          nut")
    
    for res in reservoirs:
        lines.append(
            f"{res.res_id:4d}  res{res.res_id:04d}       default      res{res.res_id:04d}      ctbl_sim     default      default"
        )
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"Wrote {output_path} ({len(reservoirs)} entries)")


def write_reservoir_hydrology(reservoirs: List[Reservoir], output_path: str):
    """Generate hydrology.res with default reservoir parameters."""
    lines = []
    lines.append("hydrology.res")
    lines.append(
        "name             iyres        mores        psa          pvol         esa          evol         k            evrsv        br1          br2"
    )
    
    for res in reservoirs:
        # Default values for a generic reservoir
        lines.append(
            f"res{res.res_id:04d}                 0            0      100.0000     500.0000     150.0000     750.0000       0.0100       0.7000       0.0000       0.0000"
        )
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"Wrote {output_path} ({len(reservoirs)} entries)")


def write_reservoir_sediment(reservoirs: List[Reservoir], output_path: str):
    """Generate sediment.res with default parameters."""
    lines = [
        "sediment.res",
        "name             nsed         d50          carbon       bd           sed_stlr     velsetlr",
        "default          0.0001       0.05         0.0          1.3          0.0          0.0",
    ]
    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def write_reservoir_nutrients(reservoirs: List[Reservoir], output_path: str):
    """Generate nutrients.res with default parameters."""
    lines = [
        "nutrients.res",
        "name             onco           opco           rs1            rs2            rs3            rs4            rs5            rs6            rs7            rk1            rk2            rk3            rk4            rk5            rk6            bc1            bc2            bc3            bc4            lao            igropt         ai0            ai1            ai2            ai3            ai4            ai5            ai6            mumax          rhoq           tfact          k_l            k_n            k_p            lambda0        lambda1        lambda2        p_n",
        "default          0.0            0.0            1.0            0.05           0.5            0.05           0.05           2.5            2.5            1.71           1.0            2.0            0.0            1.71           1.71           0.55           1.1            0.21           0.35           2              2              50.0           0.08           0.015          1.60           2.0            3.5            1.07           2.0            2.5            0.3            0.75           0.02           0.025          1.0            0.03           0.054          0.5",
    ]
    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def write_reservoir_initial(reservoirs: List[Reservoir], output_path: str):
    """Generate initial.res with default parameters."""
    lines = [
        "initial.res",
        "name             org_min        pest           path           hmet           salt",
        "default          null           null           null           null           null",
    ]
    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")
