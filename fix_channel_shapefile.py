"""Add BasinNo and other required fields to channel shapefile."""
import fiona
import rasterio
from shapely.geometry import shape, LineString, Point
import numpy as np
import os

# Paths
channel_shp = '/root/Desktop/qswat_data/hongxin_swat/Watershed/Shapes/channel_new3.shp'
watershed_tif = '/workspace/hongxin_swaw_plus/workspace/watershed_new3.tif'
out_shp = '/root/Desktop/qswat_data/hongxin_swat/Watershed/Shapes/output_hh_utm51N_hongxinClip2channel.shp'

# Read watershed raster
with rasterio.open(watershed_tif) as src:
    watershed = src.read(1)
    transform = src.transform
    nodata = src.nodata

def get_basin_at_point(pt):
    row, col = rasterio.transform.rowcol(transform, pt.x, pt.y)
    if 0 <= row < watershed.shape[0] and 0 <= col < watershed.shape[1]:
        val = watershed[row, col]
        if val != nodata and not np.isnan(val):
            return int(val)
    return -1

# Process channel shapefile
with fiona.open(channel_shp) as src:
    schema = src.schema.copy()
    # Add missing fields
    for field_name, field_type in [
        ('BasinNo', 'int'),
        ('LakeIn', 'int'),
        ('LakeOut', 'int'),
        ('LakeWithin', 'int'),
        ('LakeMain', 'int'),
    ]:
        if field_name not in schema['properties']:
            schema['properties'][field_name] = field_type
    
    with fiona.open(out_shp, 'w', driver='ESRI Shapefile', crs=src.crs, schema=schema) as dst:
        for feat in src:
            geom = shape(feat['geometry'])
            if isinstance(geom, LineString):
                # Get midpoint
                coords = list(geom.coords)
                mid_idx = len(coords) // 2
                pt = Point(coords[mid_idx])
            else:
                pt = geom.centroid
            
            basin = get_basin_at_point(pt)
            feat['properties']['BasinNo'] = basin
            feat['properties']['LakeIn'] = 0
            feat['properties']['LakeOut'] = 0
            feat['properties']['LakeWithin'] = 0
            feat['properties']['LakeMain'] = 0
            dst.write(feat)

print(f"Written {out_shp} with BasinNo field")
