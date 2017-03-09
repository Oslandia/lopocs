 [![Build Status](https://secure.travis-ci.org/LI3DS/lopocs.png)]
 (https://travis-ci.org/LI3DS/lopocs)

<p align="center">
<img align="center" src="https://github.com/LI3DS/lopocs/blob/master/docs/lopocs.png" width="400">
</p>
<br>
<br>

LOPoCS (Light Opensource PointCloud Server) is a point cloud server written in
Python, allowing to load Point Cloud from Postgis thanks to the pgpointcloud
extension.

<br>
<p align="center">
<img align="center" src="https://github.com/LI3DS/lopocs/blob/dev/docs/itowns_montreal1_header.png" width="700">
</p>
<br>

The current version of LOPoCS provides a way to load Point Cloud from Postgis in:

* [Potree viewer](http://www.potree.org/ "Potree viewer") viewer with LAZ compressed data
* [iTowns2](https://github.com/iTowns/itowns2 "iTowns2") on the side of other data type
* [Cesium](https://github.com/AnalyticalGraphicsInc/cesium "Cesium") thanks to the [3DTiles](https://github.com/AnalyticalGraphicsInc/3d-tiles "3DTiles") format

Note that LOPoCS is currently the only 3DTiles server able to stream data from
[pgpointcloud](https://github.com/pgpointcloud/pointcloud "pgpointcloud"). This
is possible thanks to the python module
[py3dtiles](https://github.com/Oslandia/py3dtiles "py3dtiles").

Developments are still going on to improve state-of-the-art algorithms and
performances.

[Video](https://vimeo.com/189285883 "Video")

[Online demonstration](https://li3ds.github.io/lopocs/ "Online demonstration")


## Install

### From sources

To use LOPoCS from sources:

```
$ sudo apt-get install libgdal-dev
$ git clone https://github.com/LI3DS/lopocs
$ cd lopocs
$ virtualenv -p /usr/bin/python3 venv
$ . venv/bin/activate
(venv)$ pip install --upgrade pip
(venv)$ pip install -e .
```

If you want to run unit tests:

```
(venv)$ pip install nose
(venv)$ nosetests
...
```


## Fill the database with lopocs_builder

**lopocs_builder** is a powerful tool allowing to
- load and configure the database with extensions
- fill the database with points thanks to PDAL
- generate configuration file for uWSGI
- generate web page for several viewers (like Potree)

In other words, only one command line is standing between you and streaming
point clouds from Postgis!


### Dependancies

#### Vagrant VM

The easy way is to use the Vagrant VM which is fully configured! But you have
to build it first:

```
$ cd vagrant
$ vagrant up
```

Then you can connect to the VM with ssh:

```
$ vagrant ssh
> TODO
```

#### From sources

In order to have an efficient and a reactive streaming, we've made some
development in PDAL and pgpointcloud.

Some of these developments are not merged in upstream projects yet (but of
course, it's the intention). So you have to use some forks from the LI3DS
project to be able to use **lopocs_builder**:

- [LI3DS/pgpointcloud width dev branch](https://github.com/LI3DS/pointcloud/tree/dev)
- [LI3DS/PDAL with e57reader branch](https://github.com/LI3DS/PDAL/tree/e57reader)

Moreover, the [Morton Postgres extension](https://github.com/Oslandia/pgmorton)
is necessary.

Here are a few tips to compile everything:

```
TODO
```


### Usage

```
$ lopocs_builder --help
usage: lopocs_builder [-h] [-epsg epsg] [--confonly] [--potreeviewer]
                      [--force] [-pg_user pg_user] [-pg_table pg_table]
                      [-pg_host pg_host] [-pg_port pg_port] [-pg_pwd pg_pwd]
                      [-pdal_patchsize size] [-pdal_reader reader]
                      [-morton_size size] [-lod_max lod_max]
                      [-lopocs_cachedir dir] [-uwsgi_host uwsgi_host]
                      [-uwsgi_port uwsgi_port] [-uwsgi_log uwsgi_log]
                      [-uwsgi_venv uwsgi_venv]
                      files outdir pg_db

Prepare database for LOPoCS

positional arguments:
  files                 input files. A regex can be used: 'input/*.las'
  outdir                output directory
  pg_db                 postgres database

optional arguments:
  -h, --help            show this help message and exit
  -epsg epsg            EPSG code (default: 4326)
  --confonly            print current configuration only
  --potreeviewer        configure Potree viewer
  --force               remove database and output directory if they exist
  -pg_user pg_user      postgres user (default: USER)
  -pg_table pg_table    postgres table (default: patchs)
  -pg_host pg_host      postgres host (default: localhost)
  -pg_port pg_port      postgres port (default: 5432)
  -pg_pwd pg_pwd        postgres password (default: )
  -pdal_patchsize size  number of points per patch (default: 500)
  -pdal_reader reader   PDAL reader to use in the pipeline (default: las)
  -morton_size size     Grid size to compute the Morton Code (default: 64)
  -lod_max lod_max      Maximum Level Of Detail (default: 6)
  -lopocs_cachedir dir  LOPoCS cache directory (default:
                        '/home/USER/.cache/lopocs/')
  -uwsgi_host uwsgi_host
                        uWSGI host through which LOPoCS will be available
                        (default: 127.0.0.1)
  -uwsgi_port uwsgi_port
                        uWSGI port through which LOPoCS will be available
                        (default: 5000)
  -uwsgi_log uwsgi_log  uWSGI logfile (default: /tmp/lopocs.log)
  -uwsgi_venv uwsgi_venv
                        uWSGI virtualenv (default: /home/USER/devel/packa
                        ges/li3ds/lopocs/tools/../venv)
```


## API and Swagger

Each viewer has specific expectations and communication protocol. So, the API
is built to meet these specific needs.

Currently, 2 kinds of formats are supported:
- 3DTiles
- Greyhound format (LAZ data with a footer indicating the number of points)

LOPoCS is able to stream data up to 3 viewers:
- Potree viewer with the Greyhound format
- iTowns2 with the Greyhound format
- Cesium with the 3DTiles format

LOPoCS provides its RESTful API through a Swagger UI by default on
*http://localhost:5000*:

<p align="center">
<img align="center" src="https://github.com/LI3DS/lopocs/blob/master/docs/api.png" width="700">
</p>

There's three namespace:
- **infos**: to retrieve informations about LOPoCS (contact, ...)
- **greyhound**: to communicate with LOPoCS according to the Greyhound format
- **3dtiles**: to communicate with LOPoCS according to the 3DTiles format

### Infos Namespace

<p align="center">
<img align="center" src="https://github.com/LI3DS/lopocs/blob/master/docs/api_infos.png" width="700">
</p>

You can retrieve simple information about LOPoCS through this namespace. There
are no settings in this case, just simple query:

```
$ curl http://localhost:5000/infos/contact
"infos+li3ds@oslandia.com"
```

### Greyhound Namespace

<p align="center">
<img align="center" src="https://github.com/LI3DS/lopocs/blob/master/docs/api_greyhound.png" width="700">
</p>

The **greyhound** namespace provides 3 points of entry:
- info: returns information about the dataset served by the server in JSON
- hierarchy: returns the description of the dataset according to an octree in JSON
- read: returns points in LAZ format


### 3DTiles Namespace

<p align="center">
<img align="center" src="https://github.com/LI3DS/lopocs/blob/master/docs/api_3dtiles.png" width="700">
</p>

The **3dtiles** namespace provides 2 points of entry:
- info: returns information about the dataset in JSON
- read.pnts: returns points in 3DTiles Point Cloud format


## Full examples

Some examples with **las** and **e57** files are available in *examples*
directory.

### Saint Sulpice

An example with St Sulpice point cloud (e57 format) coming from [here](http://www.libe57.org/data.html):

```
(venv)$ cd examples/stsulpice
(venv)$ sh potree.sh
....
```

By running this command, the e57 file is downloaded and **lopocs_builder** is
called in this way:

```
lopocs_builder Trimble_StSulpice-Cloud-50mm.e57 outdir pc_stsulpice \
               -lod_max 4 -lopocs_cachedir outdir/cache -pdal_reader e57 \
               --force --potreeviewer
```

After a few minutes, **lopocs_builder** is done:

```
(venv)$ sh potree.sh
============================================================
LOPoCS configuration
============================================================

General
 - files: Trimble_StSulpice-Cloud-50mm.e57
 - output directory: lopocs/examples/stsulpice/outdir
 - epsg code: EPSG:4326
 - force: True

Postgres
 - host: localhost
 - database: pc_stsulpice
 - port: 5432
 - table: patchs
 - user: USER
 - password:

PDAL
 - reader: e57
 - patch size: 500

Morton
 - grid size: 64

Hierarchy
 - lod max: 4

LOPoCS
 - cache directory: lopocs/examples/stsulpice/outdir/cache

uWSGI
 - host: 127.0.0.1
 - port: 5000
 - logfile: /tmp/lopocs.log
 - virtualenv: lopocs/tools/../venv

Viewer(s)
 - PotreeViewer: True

============================================================
LOPoCS check environment
============================================================

dropdb...: /usr/local/bin/dropdb
createdb...: /usr/local/bin/createdb
pdal...: /usr/local/bin/pdal
pdal-config...: /usr/local/bin/pdal-config
pdal plugin midoc filter...: /usr/local/lib/libpdal_plugin_filter_midoc.so
pdal plugin pgpointcloud writer...: /usr/local/lib/libpdal_plugin_writer_pgpointcloud.so

============================================================
LOPoCS prepare
============================================================

Search input file(s)...: OK
Remove output directory...: OK
Drop database...: OK
Initialize output directory...: OK
Initialize cache directory...: OK

============================================================
LOPoCS initialize database
============================================================

Create the database...: OK
Initialize connection with database...: OK
Load postgis extension...: OK
Load pointcloud extension...: OK
Load pointcloud_postgis extension...: OK
Load morton extension...: OK

============================================================
LOPoCS fill database
============================================================

Build PDAL pipelines...: OK
Run PDAL pipelines...: OK

============================================================
LOPoCS preprocessing
============================================================

Extract bounding box...: OK

Insert Potree schema for scale=0.1...: OK
Insert Potree schema for scale=0.01...: OK

Compute Morton code...: OK

Generate a hierarchy file for Potree...: OK
Paste the Potree hierarchy in LOPoCS cache directory...: OK

Generate a configuration file for LOPoCS...: OK
Generate a configuration file for uWSGI...: OK

============================================================
LOPoCS configure viewer(s)
============================================================

Copy Potree project...: OK
Prepare Potree html file...: OK

Duration: 8484500 points processed in 374.0738787651062 seconds with LOD 4.
```

Then you can run LOPoCS with uWSGI and the configuration file generated by
**lopocs_builder**:

```
(venv)$ pip install uwsgi
(venv)$ uwsgi -y outdir/lopocs.uwsgi.yml
...
```

To test if LOPoCS is well online:

```
$ curl http://localhost:5000/infos/online
"Congratulation, LOPoCS is online!!!"
```

Then you can use Potree viewer to stream points from the database with your
favorite web browser tanks to the *potree.html* file generated by
**lopocs_builder**:

```
$ chromium outdir/potree.html
```

<br>
<p align="center">
<img align="center" src="https://github.com/LI3DS/lopocs/blob/dev/docs/stsulpice.png" width="700">
</p>
<br>


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

A simple Python script is provided by LOPoCS to build a hierarchy from a
pgpointcloud database:

```
$ python3 tools/build_hierarchy.py lopocs.yml . greyhound
```

Once the hierarchy file *potree.hcy* is created, you can paste it in the
cache directory and update the LOPoCS configuration file accordingly:

```
# LOPoCS configuration: lopocs.yml
flask:
    DEBUG: True
    ...
    ROOT_HCY: potree.hcy
    ...
```
