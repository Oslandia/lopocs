#! /bin/sh

# env vars
LOPOCS_ROOT=$(dirname $(readlink -f $0))/../..
FILE=Trimble_StSulpice-Cloud-50mm.e57
OUTDIR=outdir
DATABASE=pc_stsulpice
CACHEDIR=$OUTDIR/cache

# fix path
export PATH=$PATH:$LOPOCS_ROOT/tools

# download file if necessary
if [ ! -f $FILE ]
then
  wget https://freefr.dl.sourceforge.net/project/e57-3d-imgfmt/E57Example-data/$FILE
fi

# run lopocs builder
lopocs_builder $FILE $OUTDIR $DATABASE \
  -lod_max 4 -lopocs_cachedir $CACHEDIR -pdal_reader e57 \
  --force --potreeviewer
