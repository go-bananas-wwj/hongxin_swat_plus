"""
GDAL utility functions for raster and vector operations.
"""
import os
import numpy as np
from osgeo import gdal, ogr, osr
from typing import Optional, Tuple, Dict, List


def get_raster_info(path: str) -> dict:
    """Return basic info about a raster."""
    ds = gdal.Open(path, gdal.GA_ReadOnly)
    if ds is None:
        raise FileNotFoundError(f"Cannot open raster: {path}")
    band = ds.GetRasterBand(1)
    info = {
        "path": path,
        "width": ds.RasterXSize,
        "height": ds.RasterYSize,
        "geotransform": ds.GetGeoTransform(),
        "projection": ds.GetProjection(),
        "nodata": band.GetNoDataValue(),
        "dtype": band.DataType,
    }
    ds = None
    return info


def reproject_raster_to_match(
    src_path: str,
    dst_path: str,
    reference_path: str,
    resample_alg: int = gdal.GRA_NearestNeighbour,
    dtype: Optional[int] = None,
) -> str:
    """
    Reproject a raster to match the extent, resolution and projection of a reference raster.
    Uses gdal.Warp under the hood.
    """
    ref_ds = gdal.Open(reference_path, gdal.GA_ReadOnly)
    ref_proj = ref_ds.GetProjection()
    ref_gt = ref_ds.GetGeoTransform()
    ref_w = ref_ds.RasterXSize
    ref_h = ref_ds.RasterYSize
    ref_ds = None

    src_ds = gdal.Open(src_path, gdal.GA_ReadOnly)
    src_band = src_ds.GetRasterBand(1)
    src_nodata = src_band.GetNoDataValue()
    if dtype is None:
        dtype = src_band.DataType

    kwargs = {
        "format": "GTiff",
        "width": ref_w,
        "height": ref_h,
        "dstSRS": ref_proj,
        "outputBounds": (
            ref_gt[0],
            ref_gt[3] + ref_h * ref_gt[5],
            ref_gt[0] + ref_w * ref_gt[1],
            ref_gt[3],
        ),
        "resampleAlg": resample_alg,
        "dstNodata": src_nodata if src_nodata is not None else -9999,
    }

    gdal.Warp(dst_path, src_ds, **kwargs)
    src_ds = None

    # Ensure output has the requested dtype
    out_ds = gdal.Open(dst_path, gdal.GA_Update)
    out_band = out_ds.GetRasterBand(1)
    if out_band.DataType != dtype:
        # Re-create with correct dtype
        driver = gdal.GetDriverByName("GTiff")
        temp_path = dst_path + ".tmp.tif"
        temp_ds = driver.Create(temp_path, ref_w, ref_h, 1, dtype)
        temp_ds.SetGeoTransform(out_ds.GetGeoTransform())
        temp_ds.SetProjection(out_ds.GetProjection())
        temp_band = temp_ds.GetRasterBand(1)
        data = out_band.ReadAsArray()
        temp_band.WriteArray(data)
        temp_band.SetNoDataValue(kwargs["dstNodata"])
        temp_ds = None
        out_ds = None
        os.replace(temp_path, dst_path)

    return dst_path


def rasterize_shapefile(
    shapefile_path: str,
    output_raster_path: str,
    reference_raster_path: str,
    burn_field: str,
    dtype: int = gdal.GDT_Int32,
    nodata: int = -9999,
    all_touched: bool = False,
) -> str:
    """
    Rasterize a shapefile field to a raster matching a reference raster's extent and resolution.
    """
    ref_ds = gdal.Open(reference_raster_path, gdal.GA_ReadOnly)
    ref_gt = ref_ds.GetGeoTransform()
    ref_w = ref_ds.RasterXSize
    ref_h = ref_ds.RasterYSize
    ref_proj = ref_ds.GetProjection()
    ref_ds = None

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(output_raster_path, ref_w, ref_h, 1, dtype)
    out_ds.SetGeoTransform(ref_gt)
    out_ds.SetProjection(ref_proj)
    out_band = out_ds.GetRasterBand(1)
    out_band.SetNoDataValue(nodata)
    out_band.Fill(nodata)
    out_ds = None

    shp_ds = ogr.Open(shapefile_path)
    shp_layer = shp_ds.GetLayer()

    options = [f"ATTRIBUTE={burn_field}"]
    if all_touched:
        options.append("ALL_TOUCHED=TRUE")

    target_ds = gdal.Open(output_raster_path, gdal.GA_Update)
    gdal.RasterizeLayer(target_ds, [1], shp_layer, options=options)
    target_ds = None
    shp_ds = None

    return output_raster_path


def read_raster_as_array(path: str) -> Tuple[np.ndarray, dict]:
    """Read a raster band into a numpy array and return metadata."""
    ds = gdal.Open(path, gdal.GA_ReadOnly)
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray()
    nodata = band.GetNoDataValue()
    meta = {
        "geotransform": ds.GetGeoTransform(),
        "projection": ds.GetProjection(),
        "nodata": nodata,
        "width": ds.RasterXSize,
        "height": ds.RasterYSize,
    }
    ds = None
    return data, meta


def write_raster(
    path: str,
    data: np.ndarray,
    geotransform: Tuple,
    projection: str,
    dtype: Optional[int] = None,
    nodata: Optional[float] = None,
) -> str:
    """Write a numpy array to a GeoTIFF."""
    if dtype is None:
        dtype = gdal_array.NumericTypeCodeToGDALTypeCode(data.dtype)
        if dtype is None:
            dtype = gdal.GDT_Float32
    h, w = data.shape
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, w, h, 1, dtype)
    ds.SetGeoTransform(geotransform)
    ds.SetProjection(projection)
    band = ds.GetRasterBand(1)
    band.WriteArray(data)
    if nodata is not None:
        band.SetNoDataValue(nodata)
    ds = None
    return path


def coords_to_pixel(gt, x, y):
    """Convert geo coordinates to pixel (col, row)."""
    col = int((x - gt[0]) / gt[1])
    row = int((y - gt[3]) / gt[5])
    return col, row


def pixel_to_coords(gt, col, row):
    """Convert pixel (col, row) to geo coordinates."""
    x = gt[0] + col * gt[1] + row * gt[2]
    y = gt[3] + col * gt[4] + row * gt[5]
    return x, y


from osgeo import gdal_array
