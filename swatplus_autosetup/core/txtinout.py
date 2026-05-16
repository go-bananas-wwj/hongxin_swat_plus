"""
TxtInOut generation module.
Generates SWAT+ input files based on delineation and HRU results.
"""
import os
import shutil
import numpy as np
from osgeo import ogr
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging
from .reservoir import (
    identify_reservoirs, Reservoir,
    write_reservoir_con, write_reservoir_res,
    write_reservoir_hydrology, write_reservoir_sediment,
    write_reservoir_nutrients, write_reservoir_initial,
)

logger = logging.getLogger(__name__)


class TxtInOutGenerator:
    """Generates SWAT+ TxtInOut folder from template + new topology."""
    
    def __init__(self, config: dict, delineation_result, hrus: List):
        self.config = config
        self.delin = delineation_result
        self.hrus = hrus
        self.out_dir = os.path.join(config["project"]["output_dir"], "TxtInOut")
        self.template_dir = config["project"]["template_txtinout"]
        
        # Internal mappings
        self.linkno_to_cha: Dict[int, int] = {}
        self.cha_to_linkno: Dict[int, int] = {}
        self.subbasin_to_cha: Dict[int, int] = {}  # subbasin_id -> main channel cha
        self.channel_to_hrus: Dict[int, List[int]] = defaultdict(list)  # cha -> [hru_ids]
        
        # Reservoir data
        self.reservoirs: List[Reservoir] = []
        self.reservoir_subbasins: set = set()  # subbasin IDs that have reservoirs
        self.reservoir_by_linkno: Dict[int, Reservoir] = {}  # channel LINKNO -> Reservoir
        
        os.makedirs(self.out_dir, exist_ok=True)
    
    def _build_channel_mappings(self):
        """Build mappings from LINKNO to cha and from subbasin to main cha."""
        # All channels from shapefile
        all_channels = list(self.delin.channels.values())
        all_channels.sort(key=lambda c: c.linkno)
        
        # Assign cha sequentially (1-based) in LINKNO order to channels with positive length
        cha = 1
        for ch in all_channels:
            if ch.length > 0:
                ch.swat_channel_id = cha
                self.linkno_to_cha[ch.linkno] = cha
                self.cha_to_linkno[cha] = ch.linkno
                cha += 1
            else:
                ch.swat_channel_id = 0
        
        # Map subbasin to its main channel (the channel with matching WSNO)
        # Consider ALL channels for subbasin mapping, but prefer positive-length ones
        subbasin_channels = defaultdict(list)
        for ch in all_channels:
            if ch.wsno in self.delin.subbasins:
                subbasin_channels[ch.wsno].append(ch)
        
        for sb_id, ch_list in subbasin_channels.items():
            # Separate positive-length and zero-length channels
            pos_chs = [c for c in ch_list if c.length > 0]
            if pos_chs:
                main_ch = max(pos_chs, key=lambda c: c.area)
            else:
                # All zero-length: pick largest area
                main_ch = max(ch_list, key=lambda c: c.area)
                # Force-assign a cha ID if not already assigned
                if main_ch.swat_channel_id == 0:
                    main_ch.swat_channel_id = cha
                    self.linkno_to_cha[main_ch.linkno] = cha
                    self.cha_to_linkno[cha] = main_ch.linkno
                    cha += 1
            
            self.subbasin_to_cha[sb_id] = main_ch.swat_channel_id
            # Also update all channels in this subbasin to point to same basin ID
            for ch in ch_list:
                ch.swat_basin_id = sb_id
        
        logger.info(f"Channel mappings: {len(self.linkno_to_cha)} channels, {len(self.subbasin_to_cha)} subbasins with main channels")
    
    def _compute_channel_centroids(self) -> Dict[int, Tuple[float, float, float]]:
        """Compute centroid (lat, lon, elev) for each channel from shapefile geometry."""
        centroids = {}
        ds = ogr.GetDriverByName("ESRI Shapefile").Open(self.delin.channel_shp, 0)
        layer = ds.GetLayer()
        
        # Get DEM for elevation sampling
        from utils.gdal_utils import read_raster_as_array
        dem_path = self.config["inputs"]["dem"]["path"]
        dem_data, dem_meta = read_raster_as_array(dem_path)
        dem_gt = dem_meta["geotransform"]
        dem_nodata = dem_meta["nodata"] if dem_meta["nodata"] is not None else -9999
        
        for feat in layer:
            linkno = feat.GetField("LINKNO")
            if linkno not in self.linkno_to_cha:
                continue
            geom = feat.GetGeometryRef()
            if geom:
                centroid = geom.Centroid()
                x, y = centroid.GetX(), centroid.GetY()
                
                # Sample elevation from DEM
                col = int((x - dem_gt[0]) / dem_gt[1])
                row = int((y - dem_gt[3]) / dem_gt[5])
                elev = 0.0
                if 0 <= row < dem_data.shape[0] and 0 <= col < dem_data.shape[1]:
                    val = dem_data[row, col]
                    if val != dem_nodata:
                        elev = float(val) * self.config["inputs"]["dem"].get("vertical_factor", 1.0)
                
                centroids[linkno] = (y, x, elev)  # lat=y, lon=x in projected coords
            else:
                centroids[linkno] = (0.0, 0.0, 0.0)
        ds = None
        return centroids
    
    def _compute_hru_centroids(self) -> Dict[int, Tuple[float, float, float]]:
        """Compute approximate centroid for each HRU from subbasin shapefile."""
        centroids = {}
        ds = ogr.GetDriverByName("ESRI Shapefile").Open(self.delin.subbasin_shp, 0)
        layer = ds.GetLayer()
        
        # Get DEM for elevation sampling
        from utils.gdal_utils import read_raster_as_array
        dem_path = self.config["inputs"]["dem"]["path"]
        dem_data, dem_meta = read_raster_as_array(dem_path)
        dem_gt = dem_meta["geotransform"]
        dem_nodata = dem_meta["nodata"] if dem_meta["nodata"] is not None else -9999
        
        # Build subbasin -> HRU mapping
        sb_hrus = defaultdict(list)
        for hru in self.hrus:
            sb_hrus[hru.subbasin_id].append(hru)
        
        for feat in layer:
            sb_id = feat.GetField("Subbasin")
            if sb_id not in sb_hrus:
                continue
            geom = feat.GetGeometryRef()
            if geom:
                centroid = geom.Centroid()
                x, y = centroid.GetX(), centroid.GetY()
                col = int((x - dem_gt[0]) / dem_gt[1])
                row = int((y - dem_gt[3]) / dem_gt[5])
                elev = 0.0
                if 0 <= row < dem_data.shape[0] and 0 <= col < dem_data.shape[1]:
                    val = dem_data[row, col]
                    if val != dem_nodata:
                        elev = float(val) * self.config["inputs"]["dem"].get("vertical_factor", 1.0)
                
                for hru in sb_hrus[sb_id]:
                    centroids[hru.hru_id] = (y, x, elev)
            else:
                for hru in sb_hrus[sb_id]:
                    centroids[hru.hru_id] = (0.0, 0.0, 0.0)
        ds = None
        return centroids
    
    def _identify_reservoirs(self):
        """Identify reservoirs from outlets shapefile."""
        outlets_shp = self.config["inputs"]["outlets"].get("path")
        if not outlets_shp or not os.path.exists(outlets_shp):
            logger.info("No outlets shapefile provided, skipping reservoir detection")
            return
        
        self.reservoirs = identify_reservoirs(
            outlets_shp=outlets_shp,
            subbasin_shp=self.delin.subbasin_shp,
            channel_shp=self.delin.channel_shp,
        )
        
        # Build lookup maps
        for res in self.reservoirs:
            self.reservoir_by_linkno[res.channel_linkno] = res
            # The subbasin associated with the reservoir is the WSNO of its channel
            ch = self.delin.channels.get(res.channel_linkno)
            if ch:
                self.reservoir_subbasins.add(ch.wsno)
        
        if self.reservoirs:
            logger.info(f"Reservoirs control subbasins: {sorted(self.reservoir_subbasins)}")
    
    def _copy_template_files(self):
        """Copy non-topology files from template TxtInOut."""
        skip_files = {
            "channel.con", "hru.con", "outlet.con", "object.cnt",
            "file.cio", "time.sim",
            "channel.cha", "hydrology.cha", "sediment.cha", "nutrients.cha",
            "initial.cha", "hru-data.hru",
            "reservoir.con", "reservoir.res", "hydrology.res",
            "sediment.res", "nutrients.res", "initial.res",
            # Also skip output files
            "channel_day.txt", "hru_wb_aa.txt", "simulation.out",
            "run.log", "success.fin", "diagnostics.out",
            # Skip backup files
        }
        skip_extensions = {".bak", ".bak2", ".orig"}
        
        if not self.template_dir or not os.path.exists(self.template_dir):
            logger.warning("No template TxtInOut provided. Only topology files will be generated.")
            return
        
        for fname in os.listdir(self.template_dir):
            if fname in skip_files:
                continue
            if any(fname.endswith(ext) for ext in skip_extensions):
                continue
            src = os.path.join(self.template_dir, fname)
            dst = os.path.join(self.out_dir, fname)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
        
        logger.info(f"Copied template files from {self.template_dir}")
    
    def _write_channel_con(self):
        """Generate channel.con with correct topology.
        If a channel's downstream is a reservoir-controlled channel,
        route to the reservoir instead.
        """
        centroids = self._compute_channel_centroids()
        
        lines = []
        lines.append(f"channel.con: {self.config['project']['name']}")
        lines.append(
            "id  name                gis_id          area           lat           lon          elev       cha               wst       cst      ovfl      rule   out_tot  obtyp  obno   htyp       frac"
        )
        
        # Sort by cha for consistent output
        for cha_id in sorted(self.cha_to_linkno.keys()):
            linkno = self.cha_to_linkno[cha_id]
            ch = self.delin.channels[linkno]
            
            lat, lon, elev = centroids.get(linkno, (0.0, 0.0, 0.0))
            gis_id = linkno + 1  # QSWATPlus uses LINKNO + 1 as gis_id
            
            # Determine downstream
            if ch.dslinkno == -1 or ch.dslinkno not in self.linkno_to_cha:
                # Outlet
                obtyp = "out"
                obno = 1
            elif ch.dslinkno in self.reservoir_by_linkno:
                # Downstream is a reservoir-controlled channel -> route to reservoir
                res = self.reservoir_by_linkno[ch.dslinkno]
                obtyp = "res"
                obno = res.res_id
            else:
                # Downstream channel
                obtyp = "cha"
                obno = self.linkno_to_cha[ch.dslinkno]
            
            lines.append(
                f"{cha_id:4d}  cha{cha_id:04d}  {gis_id:22d} {ch.area:14.4f} {lat:14.6f} {lon:14.6f} {elev:10.2f} "
                f"{cha_id:8d} null        0         0         0                 1  {obtyp:4s} {obno:5d} tot      1.0000"
            )
        
        path = os.path.join(self.out_dir, "channel.con")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Wrote {path} ({len(lines)-2} channels)")
    
    def _write_channel_cha(self):
        """Generate channel.cha (channel parameter index file)."""
        lines = []
        lines.append("channel.cha")
        lines.append("id  name          init         hyd          sed          nut")
        
        for cha_id in sorted(self.cha_to_linkno.keys()):
            lines.append(
                f"{cha_id:5d} cha{cha_id:04d}       default      cha{cha_id:04d}      default      default"
            )
        
        path = os.path.join(self.out_dir, "channel.cha")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Wrote {path} ({len(lines)-2} entries)")
    
    def _write_hydrology_cha(self):
        """Generate hydrology.cha with channel physical parameters."""
        # Read shapefile to get slope and length for each LINKNO
        ds = ogr.GetDriverByName("ESRI Shapefile").Open(self.delin.channel_shp, 0)
        layer = ds.GetLayer()
        linkno_props = {}
        for feat in layer:
            linkno = feat.GetField("LINKNO")
            slope = feat.GetField("Slope") or 0.001
            length = feat.GetField("Length") or 1000.0
            if slope <= 0:
                slope = 0.001
            linkno_props[linkno] = (slope, length)
        ds = None
        
        lines = []
        lines.append("hydrology.cha")
        lines.append(
            "name             w              d              s              l              n              k              wdr            alpha_bnk      side"
        )
        
        for cha_id in sorted(self.cha_to_linkno.keys()):
            linkno = self.cha_to_linkno[cha_id]
            slope, length = linkno_props.get(linkno, (0.001, 1000.0))
            # Convert length from map units (meters for UTM) to km if needed
            # SWAT+ uses km for channel length in some versions, m in others
            # Looking at old file: l=1.0000 for very short channels, likely in km
            length_km = length / 1000.0
            
            lines.append(
                f"cha{cha_id:04d}                 5.0000         1.5000       {slope:10.6f}     {length_km:10.4f}         0.0350         0.0100         6.0000         0.0300         2.0000"
            )
        
        path = os.path.join(self.out_dir, "hydrology.cha")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Wrote {path} ({len(lines)-2} entries)")
    
    def _write_sediment_cha(self):
        """Generate sediment.cha with default parameters."""
        lines = [
            "sediment.cha",
            "name             eqn            cov1           cov2           bnk_bd         bed_bd         bnk_kd         bed_kd         bnk_d50        bed_d50        tc_bnk         tc_bed         erod1          erod2          erod3          erod4          erod5          erod6          erod7          erod8          erod9          erod10         erod11         erod12",
            "default          0              0.1            0.1            1.3            1.3            0.0            0.0            0.05           0.05           0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0            0.0",
        ]
        path = os.path.join(self.out_dir, "sediment.cha")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
    
    def _write_nutrients_cha(self):
        """Generate nutrients.cha with default parameters."""
        lines = [
            "nutrients.cha",
            "name             onco           opco           rs1            rs2            rs3            rs4            rs5            rs6            rs7            rk1            rk2            rk3            rk4            rk5            rk6            bc1            bc2            bc3            bc4            lao            igropt         ai0            ai1            ai2            ai3            ai4            ai5            ai6            mumax          rhoq           tfact          k_l            k_n            k_p            lambda0        lambda1        lambda2        p_n",
            "default          0.0            0.0            1.0            0.05           0.5            0.05           0.05           2.5            2.5            1.71           1.0            2.0            0.0            1.71           1.71           0.55           1.1            0.21           0.35           2              2              50.0           0.08           0.015          1.60           2.0            3.5            1.07           2.0            2.5            0.3            0.75           0.02           0.025          1.0            0.03           0.054          0.5",
        ]
        path = os.path.join(self.out_dir, "nutrients.cha")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
    
    def _write_initial_cha(self):
        """Generate initial.cha with default parameters."""
        lines = [
            "initial.cha",
            "name             org_min        pest           path           hmet           salt",
            "default          null           null           null           null           null",
        ]
        path = os.path.join(self.out_dir, "initial.cha")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
    
    def _write_hru_con(self):
        """Generate hru.con with HRU routing to subbasin channels.
        If a subbasin is controlled by a reservoir, HRUs route to the reservoir.
        """
        centroids = self._compute_hru_centroids()
        
        # Build subbasin -> reservoir mapping
        sb_to_res = {}
        for res in self.reservoirs:
            ch = self.delin.channels.get(res.channel_linkno)
            if ch:
                sb_to_res[ch.wsno] = res
        
        lines = []
        lines.append(f"hru.con: {self.config['project']['name']}")
        lines.append(
            "  id  name                gis_id          area           lat           lon          elev       hru               wst       cst      ovfl      rule   out_tot  obtyp  obno   htyp       frac"
        )
        
        # Group HRUs by subbasin for sequential numbering within subbasin
        # But SWAT+ uses global hru numbering
        for hru in self.hrus:
            hru_id = hru.hru_id
            sb_id = hru.subbasin_id
            
            # Check if this subbasin is controlled by a reservoir
            if sb_id in sb_to_res:
                res = sb_to_res[sb_id]
                obtyp = "res"
                obno = res.res_id
            else:
                # Route to subbasin's main channel
                cha_id = self.subbasin_to_cha.get(sb_id, 0)
                if cha_id == 0:
                    logger.warning(f"No main channel for subbasin {sb_id}, HRU {hru_id} will route to outlet")
                    cha_id = 1  # fallback
                obtyp = "cha"
                obno = cha_id
            
            lat, lon, elev = centroids.get(hru_id, (0.0, 0.0, 0.0))
            
            lines.append(
                f"{hru_id:4d}  hru{hru_id:04d}  {sb_id:22d} {hru.area_ha:14.4f} {lat:14.6f} {lon:14.6f} {elev:10.2f} "
                f"{hru_id:8d} null        0         0         0                 1  {obtyp:4s} {obno:5d} tot      1.0000"
            )
        
        path = os.path.join(self.out_dir, "hru.con")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Wrote {path} ({len(self.hrus)} HRUs)")
    
    def _write_hru_data(self):
        """Generate hru-data.hru with soil and landuse mappings."""
        # Load lookup tables
        import sqlite3
        sqlite_path = self.config["inputs"]["landuse"].get("lookup_sqlite")
        
        landuse_map = {}
        soil_map = {}
        
        if sqlite_path and os.path.exists(sqlite_path):
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Landuse lookup
            lu_table = self.config["inputs"]["landuse"].get("lookup_table", "landuse_lookup")
            try:
                cursor.execute(f"SELECT LANDUSE_ID, SWAT_CODE FROM {lu_table}")
                for row in cursor.fetchall():
                    landuse_map[row[0]] = row[1]
            except Exception as e:
                logger.warning(f"Could not read landuse lookup from {lu_table}: {e}")
            
            # Soil lookup
            soil_table = self.config["inputs"]["soil"].get("lookup_table", "soil_lookup")
            try:
                cursor.execute(f"SELECT SOIL_ID, NAME FROM {soil_table}")
                for row in cursor.fetchall():
                    soil_map[row[0]] = row[1]
            except Exception as e:
                logger.warning(f"Could not read soil lookup from {soil_table}: {e}")
            
            conn.close()
        
        # Build landuse -> lum mapping (simple: lowercase + "_lum")
        # In old TxtInOut: AGRL -> agrl_lum, FRST -> frst_lum, etc.
        def to_lum(name):
            return name.lower() + "_lum"
        
        lines = []
        lines.append("hru-data.hru:")
        lines.append(
            "      id  name                          topo             hydro              soil            lu_mgt   soil_plant_init         surf_stor              snow             field"
        )
        
        for hru in self.hrus:
            hru_id = hru.hru_id
            lu_name = landuse_map.get(hru.landuse_id, f"LU{hru.landuse_id}")
            soil_name = soil_map.get(hru.soil_id, f"SOIL{hru.soil_id}")
            lum_name = to_lum(lu_name)
            
            lines.append(
                f"{hru_id:8d}  hru{hru_id:04d}                       top{hru_id:04d}          hyd1              {soil_name:<16s} {lum_name:<8s}        null                  null              snow001              null"
            )
        
        path = os.path.join(self.out_dir, "hru-data.hru")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Wrote {path} ({len(self.hrus)} HRUs)")
    
    def _write_outlet_con(self):
        """Generate outlet.con."""
        lines = []
        lines.append(f"outlet.con: {self.config['project']['name']}")
        lines.append(
            "  id  name                gis_id          area           lat           lon          elev       out               wst       cst      ovfl      rule   out_tot"
        )
        lines.append(
            "  1  outlet0001                   0       0.0000       0.000000       0.000000         0.00        1 null          0         0         0         0         0"
        )
        
        path = os.path.join(self.out_dir, "outlet.con")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Wrote {path}")
    
    def _write_reservoir_files(self):
        """Generate all reservoir input files."""
        if not self.reservoirs:
            return
        
        write_reservoir_con(
            self.reservoirs,
            self.linkno_to_cha,
            os.path.join(self.out_dir, "reservoir.con")
        )
        write_reservoir_res(
            self.reservoirs,
            os.path.join(self.out_dir, "reservoir.res")
        )
        write_reservoir_hydrology(
            self.reservoirs,
            os.path.join(self.out_dir, "hydrology.res")
        )
        write_reservoir_sediment(
            self.reservoirs,
            os.path.join(self.out_dir, "sediment.res")
        )
        write_reservoir_nutrients(
            self.reservoirs,
            os.path.join(self.out_dir, "nutrients.res")
        )
        write_reservoir_initial(
            self.reservoirs,
            os.path.join(self.out_dir, "initial.res")
        )
    
    def _write_object_cnt(self):
        """Generate object.cnt."""
        n_hru = len(self.hrus)
        n_cha = len(self.linkno_to_cha)
        n_res = len(self.reservoirs)
        n_out = 1
        n_obj = n_hru + n_cha + n_res + n_out
        
        lines = []
        lines.append("object.cnt:")
        lines.append(
            "  name                   ls_area      tot_area       obj       hru      lhru       rtu       mfl       aqu       cha       res       rec      exco       dlr       can       pmp       out      lcha     aqu2d       hrd       wro"
        )
        lines.append(
            f"  {self.config['project']['name']:<22s} 1.          1           {n_obj:5d}   {n_hru:5d}         0         0         0         0    {n_cha:5d}    {n_res:5d}         0         0         0         0         0         {n_out:5d}         0         0         0"
        )
        
        path = os.path.join(self.out_dir, "object.cnt")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Wrote {path} (obj={n_obj}, hru={n_hru}, cha={n_cha}, res={n_res}, out={n_out})")
    
    def _write_file_cio(self):
        """Generate file.cio based on template or default."""
        # Try to read template file.cio
        template_path = os.path.join(self.template_dir, "file.cio")
        if os.path.exists(template_path):
            with open(template_path) as f:
                lines = f.readlines()
            
            # Update object count line
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("object") and "null" in stripped:
                    parts = stripped.split()
                    if len(parts) >= 2:
                        n_obj = len(self.hrus) + len(self.linkno_to_cha) + len(self.reservoirs) + 1
                        lines[i] = f"  object       {n_obj}    null\n"
            
            # Update reservoir line if reservoirs exist
            if self.reservoirs:
                for i, line in enumerate(lines):
                    if line.strip().startswith("reservoir"):
                        lines[i] = "reservoir         initial.res       reservoir.res     hydrology.res     sediment.res      nutrients.res     null              null\n"
                        break
            
            with open(os.path.join(self.out_dir, "file.cio"), "w") as f:
                f.writelines(lines)
            logger.info("Wrote file.cio (from template)")
        else:
            # Write minimal file.cio
            n_obj = len(self.hrus) + len(self.linkno_to_cha) + len(self.reservoirs) + 1
            lines = [
                "file.cio: project configuration",
                "  nbyr     tstep   styro  stmon  stday  edyr   edmon  eddy",
                "  3        0       2018   1      1      2020   12     31",
                "  objects  name",
                f"  object   {n_obj}    null",
            ]
            with open(os.path.join(self.out_dir, "file.cio"), "w") as f:
                f.write("\n".join(lines) + "\n")
            logger.info("Wrote file.cio (minimal default)")
    
    def _write_time_sim(self):
        """Generate time.sim."""
        swat = self.config.get("swatplus", {})
        start = swat.get("start_date", "2018-01-01")
        end = swat.get("end_date", "2020-12-31")
        tstep = swat.get("time_step", "0")
        
        sy, sm, sd = start.split("-")
        ey, em, ed = end.split("-")
        
        lines = [
            "time.sim: simulation time configuration",
            "  day_start  yrc_start   day_end   yrc_end   step",
            f"  {int(sd):3d}        {int(sy):4d}       {int(ed):3d}       {int(ey):4d}       {tstep}",
        ]
        
        path = os.path.join(self.out_dir, "time.sim")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Wrote {path}")
    
    def generate(self):
        """Run full TxtInOut generation."""
        logger.info("=" * 60)
        logger.info("Starting TxtInOut generation")
        logger.info("=" * 60)
        
        self._build_channel_mappings()
        self._identify_reservoirs()
        self._copy_template_files()
        self._write_channel_con()
        self._write_channel_cha()
        self._write_hydrology_cha()
        self._write_sediment_cha()
        self._write_nutrients_cha()
        self._write_initial_cha()
        self._write_hru_con()
        self._write_hru_data()
        self._write_outlet_con()
        self._write_reservoir_files()
        self._write_object_cnt()
        self._write_file_cio()
        self._write_time_sim()
        
        logger.info(f"TxtInOut generation complete. Output: {self.out_dir}")
        return self.out_dir


def run_txtinout_generation(config: dict, delineation_result, hrus: List) -> str:
    """Main entry point for TxtInOut generation."""
    gen = TxtInOutGenerator(config, delineation_result, hrus)
    return gen.generate()
