import numpy as np
import rasterio
import fiona
from collections import defaultdict

# Read aligned rasters
with rasterio.open('/workspace/hongxin_swaw_plus/workspace/watershed_new3.tif') as src:
    watershed = src.read(1)
    ws_nodata = src.nodata

with rasterio.open('/tmp/landuse_aligned.tif') as src:
    landuse = src.read(1)
    lu_nodata = src.nodata

with rasterio.open('/tmp/soil_aligned.tif') as src:
    soil = src.read(1)
    soil_nodata = src.nodata

print(f"Watershed shape: {watershed.shape}, nodata: {ws_nodata}")
print(f"Landuse shape: {landuse.shape}, nodata: {lu_nodata}")
print(f"Soil shape: {soil.shape}, nodata: {soil_nodata}")

# Compute dominant landuse and soil per subbasin
subbasin_ids = np.unique(watershed)
subbasin_ids = subbasin_ids[subbasin_ids != ws_nodata]
print(f"Number of subbasins: {len(subbasin_ids)}")

subbasin_stats = {}
for sbid in subbasin_ids:
    mask = watershed == sbid
    lu_vals = landuse[mask]
    soil_vals = soil[mask]
    
    # Filter nodata
    lu_vals = lu_vals[lu_vals != lu_nodata]
    soil_vals = soil_vals[soil_vals != soil_nodata]
    
    if len(lu_vals) == 0:
        dom_lu = 0
    else:
        dom_lu = np.bincount(lu_vals).argmax()
    
    if len(soil_vals) == 0:
        dom_soil = 0
    else:
        dom_soil = np.bincount(soil_vals).argmax()
    
    subbasin_stats[int(sbid)] = {
        'pixels': int(mask.sum()),
        'dominant_landuse': int(dom_lu),
        'dominant_soil': int(dom_soil),
    }

print(f"Computed stats for {len(subbasin_stats)} subbasins")
print("Example subbasin 1:", subbasin_stats.get(1))
print("Example subbasin 100:", subbasin_stats.get(100))

# Save to JSON for later use
import json
with open('/workspace/hongxin_swaw_plus/subbasin_stats.json', 'w') as f:
    json.dump(subbasin_stats, f)
print("Saved to subbasin_stats.json")
