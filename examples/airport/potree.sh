#! /bin/sh

# env vars
LOPOCS_ROOT=$(dirname $(readlink -f $0))/../..
FILE=LAS12_Sample_withRGB_Quick_Terrain_Modeler_fixed.las
OUTDIR=outdir
DATABASE=pc_airport
CACHEDIR=$OUTDIR/cache

# fix path
export PATH=$PATH:$LOPOCS_ROOT/tools

# download file if necessary
if [ ! -f $FILE ]
then
  wget www.liblas.org/samples/$FILE
fi

# run lopocs builder
lopocs_builder $FILE $OUTDIR $DATABASE \
  -lod_max=5 -lopocs_cachedir $CACHEDIR -epsg 32616 \
  --force --potreeviewer
