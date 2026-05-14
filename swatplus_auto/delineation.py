"""Watershed delineation using TauDEM."""

import subprocess
from pathlib import Path

import rasterio


class Delineator:
    """Run TauDEM watershed delineation pipeline."""

    def __init__(self, config):
        self.cfg = config
        self.dem_path = Path(config.get("basin.dem_path"))
        self.workspace = Path(config.get("project.workspace"))
        self.outlet = config.get("basin.outlet_coords")
        self.threshold_km2 = config.get("basin.threshold_area_km2", 50)
        self._ensure_workspace()

    def _ensure_workspace(self):
        self.workspace.mkdir(parents=True, exist_ok=True)

    def run(self) -> dict:
        """Run full delineation pipeline."""
        print("Step 1: Pit removal")
        self._pitremove()

        print("Step 2: D8 flow direction")
        self._d8flowdir()

        print("Step 3: D8 flow accumulation")
        self._aread8()

        print("Step 4: Create outlet shapefile")
        self._create_outlet_shp()

        print("Step 5: Threshold and stream network")
        self._threshold()
        self._streamnet()

        print("Step 6: Watershed delineation")
        self._gagewatershed()

        return {
            "subbasins": self.workspace / "subbasins.tif",
            "streams": self.workspace / "streams.shp",
        }

    def _pitremove(self):
        cmd = [
            "pitremove",
            "-z", str(self.dem_path),
            "-fel", str(self.workspace / "fel.tif"),
        ]
        subprocess.run(cmd, check=True)

    def _d8flowdir(self):
        cmd = [
            "d8flowdir",
            "-fel", str(self.workspace / "fel.tif"),
            "-p", str(self.workspace / "p.tif"),
            "-sd8", str(self.workspace / "sd8.tif"),
        ]
        subprocess.run(cmd, check=True)

    def _aread8(self):
        cmd = [
            "aread8",
            "-p", str(self.workspace / "p.tif"),
            "-ad8", str(self.workspace / "ad8.tif"),
        ]
        subprocess.run(cmd, check=True)

    def _create_outlet_shp(self):
        """Create outlet shapefile from coordinates."""
        from osgeo import ogr, osr

        driver = ogr.GetDriverByName("ESRI Shapefile")
        out_path = self.workspace / "outlet.shp"
        if out_path.exists():
            driver.DeleteDataSource(str(out_path))
        ds = driver.CreateDataSource(str(out_path))
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)  # WGS84
        layer = ds.CreateLayer("outlet", srs, ogr.wkbPoint)
        layer.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))

        feat = ogr.Feature(layer.GetLayerDefn())
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(self.outlet[0], self.outlet[1])
        feat.SetGeometry(point)
        feat.SetField("id", 1)
        layer.CreateFeature(feat)
        feat = None
        ds = None
        print(f"  Created outlet: {out_path}")

    def _threshold(self):
        # Get DEM resolution to compute pixel threshold
        with rasterio.open(self.dem_path) as src:
            res = src.res[0]  # meters
            pixel_threshold = int((self.threshold_km2 * 1e6) / (res * res))

        cmd = [
            "threshold",
            "-ssa", str(self.workspace / "ad8.tif"),
            "-src", str(self.workspace / "src.tif"),
            "-thresh", str(pixel_threshold),
        ]
        subprocess.run(cmd, check=True)
        print(f"  Threshold: {self.threshold_km2} km2 = {pixel_threshold} pixels")

    def _streamnet(self):
        cmd = [
            "streamnet",
            "-fel", str(self.workspace / "fel.tif"),
            "-p", str(self.workspace / "p.tif"),
            "-ad8", str(self.workspace / "ad8.tif"),
            "-src", str(self.workspace / "src.tif"),
            "-ord", str(self.workspace / "ord.tif"),
            "-tree", str(self.workspace / "tree.dat"),
            "-coord", str(self.workspace / "coord.dat"),
            "-net", str(self.workspace / "streams.shp"),
            "-w", str(self.workspace / "subbasins.tif"),
        ]
        subprocess.run(cmd, check=True)

    def _gagewatershed(self):
        """Delineate watershed above outlet."""
        cmd = [
            "gagewatershed",
            "-p", str(self.workspace / "p.tif"),
            "-o", str(self.workspace / "outlet.shp"),
            "-gw", str(self.workspace / "watershed.tif"),
        ]
        subprocess.run(cmd, check=True)
