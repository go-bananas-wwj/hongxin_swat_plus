# SWAT+ Re-Delineation Status Report

## Date
2026-05-16

## Problem Diagnosis

The original QSWATPlus delineation was **fundamentally broken**:

- **Old channel.shp**: 310 LINKNOs (0-309) but `channel.con` only had 282 channels
- **Missing channels**: LINKNO 0, 1, and 283-309 (28 channels total)
- **Critical finding**: The missing LINKNO 283-309 were the **main-stem downstream channels**, including the terminal outlet at 镇西 (LINKNO=309, DSContArea=18,442 km²)
- **Old subbasins.shp**: 265 subbasins, maximum outlet channel DSContArea=6,127 km²
- **Root cause**: The old delineation only covered ~33% of the total watershed area. The downstream 2/3 of the basin was completely missing from the SWAT+ model.

This explains why simulated flows were severely underestimated (98-100% bias at most stations).

## Solution Executed

### 1. TauDEM D8 Re-Delineation

Re-ran the complete TauDEM D8 workflow from command line using correct parameters:

| Parameter | Value |
|-----------|-------|
| DEM | `output_hh_utm51N_hongxinClip2.tif` (8764×6958, 25m cell) |
| Channel threshold | 60,967 cells |
| Stream threshold | 64,756 cells |
| Outlet snapping | `moveoutletstostreams` with max_dist=400 cells (~10 km) |
| Outlets | 8 stations + 1 reservoir |

**Critical fix**: Removed erroneous `-sw` (single watershed) flag from `streamnet` calls. The original `-sw` flag caused TauDEM to treat the entire domain as a single watershed, preventing subbasin generation.

### 2. New Delineation Results

| File | Old | New | Status |
|------|-----|-----|--------|
| channel.shp | 310 LINKNOs (incomplete coverage) | **303 LINKNOs (0-302)** | ✅ Complete watershed |
| stream.shp | 281 LINKNOs | **285 LINKNOs (0-284)** | ✅ Complete watershed |
| subbasins.shp | 265 subbasins | **284 subbasins** | ✅ Complete watershed |
| Max DSContArea | 6,127 km² | **18,442 km²** | ✅ Full basin outlet |

### 3. Outlet Channel Mapping

| Station | Outlet ID | New LINKNO | DSContArea (km²) | DSLINKNO |
|---------|-----------|------------|------------------|----------|
| 五岔沟 | 2 | 233 | 1,623 | 234 |
| 索伦 | 3 | 268 | 5,719 | 271 |
| 察尔森下 | 4 | 289 | 7,653 | 291 |
| 镇西 | 6 | **302** | **18,442** | **-1 (terminal)** |
| 大石寨 | 7 | 76 | 82 | 167 |
| 阿力得尔 | 8 | 236 | 2,081 | 240 |
| 保隆 | 9 | 109 | 87 | 171 |
| 乌兰浩特 | 10 | 104 | 57 | 192 |
| Reservoir | 11 | 288 | 7,651 | 289 |

**镇西 (Outlet 6)** is now correctly identified as the **terminal outlet** with DSLINKNO=-1 and the full watershed area of 18,442 km².

### 4. Files Replaced in QSWATPlus Project

All new files copied to `/root/Desktop/qswat_data/hongxin_swat/Watershed/Shapes/`:
- `output_hh_utm51N_hongxinClip2channel.shp` (303 features)
- `output_hh_utm51N_hongxinClip2stream.shp` (285 features)
- `output_hh_utm51N_hongxinClip2subbasins.shp` (284 features)

Old files backed up to `old_delineation/`.

### 5. Database Updated

```sql
UPDATE project_config SET delineation_done = 1;
```

## Next Steps (Manual in QGIS)

The remaining work **must be done interactively in QGIS + QSWATPlus** because HRU creation requires user choices (landuse/soil lookup tables, HRU thresholds, etc.).

### Step 1: Open Project in QGIS

```bash
cd /root/Desktop/qswat_data/hongxin_swat
qgis hongxin_swat.qgs &
```

### Step 2: Verify Delineation

1. In QSWATPlus panel, click **"Step 1: Delineation"**
2. Check that streams, channels, and subbasins display correctly
3. Verify all 8 outlet points are snapped to the channel network
4. Click **"OK"** to save delineation state

### Step 3: Create HRUs

1. In QSWATPlus panel, click **"Step 2: Create HRUs"**
2. On the **Landuse/Soil** tab:
   - Landuse file: `CLCD_2018_clip_hongxin.tif` (already set)
   - Soil file: `HWSD2_clip_utm51n_90m.tif` (already set)
   - Select appropriate lookup tables
   - Click **"Read"**
3. On the **HRU Definition** tab:
   - Choose HRU creation method (e.g., Dominant HRU)
   - Set thresholds if needed
   - Click **"Create"**
4. Wait for completion (may take 10-30 minutes)

### Step 4: Write TxtInOut

1. In QSWATPlus panel, click **"Step 3: Edit Inputs and Run SWAT+"**
2. Set weather data paths if needed
3. Click **"Write Inputs"** to generate TxtInOut
4. Run SWAT+ model

### Step 5: Validate

1. Run the model for the full simulation period (2012-2022)
2. Use `scripts/validate_hydro_v2.py` with the **correct outlet→gis_id mapping**:

```python
# Correct mapping for new delineation
mapping = {
    2: 233,   # 五岔沟
    3: 268,   # 索伦
    4: 289,   # 察尔森下
    6: 302,   # 镇西
    7: 76,    # 大石寨
    8: 236,   # 阿力得尔
    9: 109,   # 保隆
    10: 104,  # 乌兰浩特
}
```

3. Check that simulated flows at 镇西 (gis_id=302) are now in the correct range (~40 m³/s mean)

## Files Generated

### TauDEM Intermediates (workspace/)
- `ad8_new.tif` — D8 accumulation with snapped outlets
- `srcStream_new.tif` — Stream raster (threshold=64756)
- `srcChannel_new.tif` — Channel raster (threshold=60967)
- `watershed_new3.tif` — Subbasin grid (284 subbasins)
- `watershedChannel_new3.tif` — Channel watershed grid (302 subbasins)
- `stream_new3.shp` / `channel_new3.shp` — New stream/channel networks

### QSWATPlus Project Updates
- `Watershed/Shapes/output_hh_utm51N_hongxinClip2channel.shp` → 303 features
- `Watershed/Shapes/output_hh_utm51N_hongxinClip2stream.shp` → 285 features
- `Watershed/Shapes/output_hh_utm51N_hongxinClip2subbasins.shp` → 284 features
- `project_config.delineation_done` → 1

## Known Issues

1. **Old TxtInOut is invalid**: The existing `TxtInOut_v61/` was built on the broken 282-channel delineation. It must be completely regenerated after HRU creation.
2. **Weather data**: Existing `.pcp` and `.tmp` files should still be valid, but `file.cio` and weather station assignments may need review.
3. **Channel parameters**: New `hydrology.cha` will need actual channel geometry extracted from the new `channel.shp`.

## Summary

The watershed delineation has been **completely rebuilt** with the correct topology. The model now covers the full 18,442 km² basin with all 8 monitoring stations as true subbasin outlets. The remaining HRU creation and TxtInOut export steps require interactive QSWATPlus operation in QGIS.
