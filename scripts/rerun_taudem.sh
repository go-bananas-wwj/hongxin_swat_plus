#!/bin/bash
set -e

TAUDEM=/usr/local/share/SWATPlus/TauDEM5Bin
WORKSPACE=/workspace/hongxin_swaw_plus/workspace
DEM=/workspace/hongxin_swaw_plus/Datasets/swat_data/Watershed/Rasters/DEM/output_hh_utm51N_hongxinClip2.tif
OUTLETS=/root/Desktop/qswat_data/hongxin_swat/Watershed/Shapes/combined_inlets_outlets_snap.shp
OUTLETS_IO=/root/Desktop/qswat_data/hongxin_swat/Watershed/Shapes/combined_inlets_outlets_snapio.shp
SHAPES=/root/Desktop/qswat_data/hongxin_swat/Watershed/Shapes

cd $WORKSPACE

echo "Step 1: Reusing fel.tif and p.tif"
# fel.tif and p.tif already exist from previous run

echo "Step 2: AreaD8 with snapped outlets"
$TAUDEM/aread8 -p p.tif -ad8 ad8_new.tif -o "$OUTLETS" -nc

echo "Step 3: GridNet with snapped outlets"
$TAUDEM/gridnet -p p.tif -plen plen_new.tif -tlen tlen_new.tif -gord gord_new.tif -o "$OUTLETS"

echo "Step 4: Threshold for streams (64756)"
$TAUDEM/threshold -ssa ad8_new.tif -src srcStream_new.tif -thresh 64756

echo "Step 5: Threshold for channels (60967)"
$TAUDEM/threshold -ssa ad8_new.tif -src srcChannel_new.tif -thresh 60967

echo "Step 6: StreamNet for streams"
$TAUDEM/streamnet -fel fel.tif -p p.tif -ad8 ad8_new.tif -src srcStream_new.tif -ord ordStream_new.tif -tree treeStream_new.dat -coord coordStream_new.dat -net "$SHAPES/stream_new.shp" -w watershed_new.tif -o "$OUTLETS_IO" -sw

echo "Step 7: StreamNet for channels"
$TAUDEM/streamnet -fel fel.tif -p p.tif -ad8 ad8_new.tif -src srcChannel_new.tif -ord ordChannel_new.tif -tree treeChannel_new.dat -coord coordChannel_new.dat -net "$SHAPES/channel_new.shp" -w watershedChannel_new.tif -o "$OUTLETS" -sw

echo "Done!"
