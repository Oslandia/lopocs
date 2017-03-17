
## Advanced usage

If you want to manually fill the database without **lopocs_builder** (or if it
doesn't work), you'll need some further explications.

### Download a LAS file

```
$ wget www.liblas.org/samples/LAS12_Sample_withRGB_Quick_Terrain_Modeler_fixed.las
$ mv LAS12_Sample_withRGB_Quick_Terrain_Modeler_fixed.las airport.las
```

### Initialize the database

The first step is to create the database and load extensions:

```
$ createdb pc_airport
$ psql pc_airport
psql (9.5.1)
Type "help" for help.

pc_airport=# create extension postgis;
CREATE EXTENSION
pc_airport=# create extension pointcloud;
CREATE EXTENSION
pc_airport=# create extension pointcloud_postgis;
CREATE EXTENSION
pc_airport=# create extension morton;
CREATE EXTENSION
```

### Using PDAL to fill the database

Firstly, you have to write a PDAL pipeline according to your format file, the
spatial reference, and so on... But the chipper and midoc filter as well as the
pgpointcloud writer are mandatory.

The pipeline for the *airport.las* file is named *pipe.json* and looks like:

```
{
  "pipeline":[
    {
      "type":"readers.las",
      "filename":"airport.las",
      "spatialreference":"EPSG:32616"
    }
    ,
    {
      "type":"filters.chipper",
      "capacity":500
    },
    {
      "type":"filters.midoc"
    },
    {
      "type":"writers.pgpointcloud",
      "connection":"dbname=pc_airport",
      "table":"patchs",
      "compression":"lazperf",
      "srid":"32616",
      "overwrite":"false"
    }
  ]
}
```

Then you can run PDAL:

```
$ pdal pipeline -i pipe.json
```

### Morton indexing

Once you have patchs of points in database thanks to PDAL, you have to
compute a Morton code for each one of them:

```
$ psql pc_airport
psql (9.5.1)
Type "help" for help.

pc_airport=# ALTER TABLE patchs add column morton bigint;
ALTER TABLE
pc_airport=# SELECT Morton_Update('patchs', 'pa::geometry', 'morton', 64, TRUE)
SELECT
pc_airport=# CREATE INDEX ON patchs(morton);
CREATE INDEX
```

### Configuration file for uWSGI and LOPoCS

For LOPoCS running with uWSGI only (without web server such as Nginx), the
configuration file looks like:

```
# uWSGI configuration: lopocs.uwsgi.yml
uwsgi:
    virtualenv: lopocs/venv
    master: true
    socket: 127.0.0.1:5000
    protocol: http
    module: lopocs.wsgi:app
    processes: 4
    enable-threads: true
    lazy-apps: true
    need-app: true
    catch: exceptions=true
    env: LOPOCS_SETTINGS=lopocs.yml
```

```
# LOPoCS configuration: lopocs.yml
flask:
    DEBUG: True
    LOG_LEVEL: debug
    PG_HOST: localhost
    PG_USER: USER
    PG_NAME: pc_airport
    PG_PORT: 5432
    PG_COLUMN: pa
    PG_TABLE: patchs
    PG_PASSWORD:
    DEPTH: 6
    USE_MORTON: True
    CACHE_DIR: ~/.cache/lopocs
    STATS: False
```

So, if you want to run LOPoCS:

```
$ uwsgi -y lopocs.uwsgi.yml
```


### [For Potree] Schemas in pgpointcloud

Potree waits from the streaming server a specific point structure:

```
X: int32 scaled and offsetted
Y: int32 scaled and offsetted
Z: int32 scaled and offsetted
Intensity: uint16
Classification: uint8
Red: uint16
Green: uint16
Blue: uint16
```

The offset is the center of the bounding box of your data. Note that it should
be the same box sent by the */info* response coming from LOPoCS. To retrieve
the boundaries:

```
$ pdal info --summary airport.las
...
    "bounds":
    {
      "X":
      {
        "max": 728998.1352,
        "min": 728262.8032
      },
      "Y":
      {
        "max": 4677014.685,
        "min": 4676439.353
      },
      "Z":
      {
        "max": 327.0779649,
        "min": 292.6479649
      }
}
...
```

Thus:

```
OFFSET_X = 728262.803 + (728998.135 - 728262.803) / 2 = 728630.469
OFFSET_Y = 4676439.353 + (4677014.685 - 4676439.353) / 2 = 4676727.019
OFFSET_Z = 292.6479649 + (327.0779649 - 292.6479649) / 2 = 309.8629649
```

Then we have to build pointcloud schemas with these offsets and two different
scales (0.1 and 0.01):

```
$ cp docs/potree_schema_scale_01.sql airport_schema_scale_01.sql
$ sed -i -e "s@!XOFFSET!@728630.469@g" airport_schema_scale_01.sql
$ sed -i -e "s@!YOFFSET!@4676727.019@g" airport_schema_scale_01.sql
$ sed -i -e "s@!ZOFFSET!@309.8629649@g" airport_schema_scale_01.sql
$ sed -i -e "s@!SRID!@32616@g" airport_schema_scale_01.sql
$ cp docs/potree_schema_scale_001.sql airport_schema_scale_001.sql
$ sed -i -e "s@!XOFFSET!@728630.469@g" airport_schema_scale_001.sql
$ sed -i -e "s@!YOFFSET!@4676727.019@g" airport_schema_scale_001.sql
$ sed -i -e "s@!ZOFFSET!@309.8629649@g" airport_schema_scale_001.sql
$ sed -i -e "s@!SRID!@32616@g" airport_schema_scale_001.sql
```

These schemas have to be inserted in the database:

```
$ psql pc_airport -f airport_schema_scale_01.sql
$ psql pc_airport -f airport_schema_scale_001.sql
```

### [For Potree] Hierarchy computation

A hierarchy, described in Json, is necessary for the Potree loader.

If you want a full description of what a Greyhound hierarchy is, you can take
a look [here](https://github.com/hobu/greyhound/blob/master/doc/clientDevelopment.rst).
