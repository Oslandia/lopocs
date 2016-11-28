#! /bin/sh

DATABASE=pc_sthelens

dropdb $DATABASE > /dev/null 2>&1
createdb $DATABASE

psql -d $DATABASE -f extensions.sql
psql -d $DATABASE -f potree_schema_scale_01.sql
psql -d $DATABASE -f potree_schema_scale_001.sql
