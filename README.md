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

In order to have an efficient and a reactive streaming, we've made some
development in PDAL, pgpointcloud and Potree.

Some of these developments are not merged in upstream projects yet (but of
course, it's the intention). So you have to use these forks to correctly configure the
database for LOPoCS:
- https://github.com/LI3DS/pointcloud
- https://github.com/LI3DS/PDAL
- https://github.com/LI3DS/potree


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
(venv)$ pip install -e "git+https://github.com/hobu/laz-perf#egg=lazperf&subdirectory=python"
```

If you want to run unit tests:

```
(venv)$ pip install nose
(venv)$ nosetests
...
```

## How to run

LOPoCS has been tested with uWSGI and Nginx.

Once files *lopocs.uwsgi.yml* and *lopocs.yml* are well configurated for your
environment, you can run LOPoCS:

```
(venv)$ pip install uwsgi
(venv)$ uwsgi --yml conf/lopocs.uwsgi.yml
spawned uWSGI worker 1 (pid: 5984, cores: 1)

```

In case of the next error:

```
(venv)$ uwsgi --yml conf/lopocs.uwsgi.yml
ImportError: No module named site
(venv)$ deactivate
$ . venv/bin/activate
(venv)$ uwsgi --yml conf/lopocs.uwsgi.yml
spawned uWSGI worker 1 (pid: 5984, cores: 1)

```

To test your installation:

```
$ curl http://localhost:5000/infos/online
"Congratulation, LOPoCS is online!!!"
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


## lopocs_builder

The aim of **lopocs_builder** is to prepare the database for LOPoCS, fill the
database thanks to PDAL and make some processing computation in a single
command line.


### Usage

```
(venv)$ ./tools/lopocs_builder --help
usage: lopocs_builder [-h] [--confonly] [--potreeviewer] [-pg_user pg_user]
                      [-pg_table pg_table] [-pg_host pg_host]
                      [-pg_port pg_port] [-pg_pwd pg_pwd]
                      [-pdal_patchsize size] [-pdal_reader reader]
                      [-morton_size size] [-lod_max lod_max]
                      [-lopocs_cachedir dir] [-uwsgi_host uwsgi_host]
                      [-uwsgi_port uwsgi_port] [-uwsgi_log uwsgi_log]
                      [-uwsgi_venv uwsgi_venv]
                      files outdir epsg pg_db

Prepare database for LOPoCS

positional arguments:
  files                 input files. A regex can be used: 'input/*.las'
  outdir                output directory
  epsg                  EPSG code
  pg_db                 postgres database

optional arguments:
  -h, --help            show this help message and exit
  --confonly            print current configuration only
  --potreeviewer        Download and configure Potree viewer
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
                        '/home/USER/.cache/lopocs/'))
  -uwsgi_host uwsgi_host
                        UWSGI host through which LOPoCS will be available
                        (default: 127.0.0.1)
  -uwsgi_port uwsgi_port
                        UWSGI port through which LOPoCS will be available
                        (default: 5000)
  -uwsgi_log uwsgi_log  UWSGI logfile (default: /tmp/lopocs.log)
  -uwsgi_venv uwsgi_venv
                        UWSGI virtualenv (default: lopocs/tools/../venv)
```

### Examples

#### Airport

Download the LAS file:

```
$ . venv/bin/activate
(venv)$ wget www.liblas.org/samples/LAS12_Sample_withRGB_Quick_Terrain_Modeler_fixed.las
Resolving www.liblas.org (www.liblas.org)... 52.216.225.130
Connecting to www.liblas.org (www.liblas.org)|52.216.225.130|:80... connected.
HTTP request sent, awaiting response... 200 OK
Length: 99099473 (95M) [binary/octet-stream]
Saving to: ‘LAS12_Sample_withRGB_Quick_Terrain_Modeler_fixed.las’
```

Run **lopocs_builder**:

```
(venv)$ rm -rf airport
(venv)$ dropdb pc_airport
(venv)$ ./tools/lopocs_builder \
    LAS12_Sample_withRGB_Quick_Terrain_Modeler_fixed.las \
    airport \
    32616 \
    pc_airport \
    -lopocs_cachedir airport/cache \
    --potreeviewer
...
```

Launch LOPoCS with UWSGI:

```
(venv)$ uwsgi -y airport/lopocs.uwsgi.yml
```

Finally, open Potree viewer with your favorite web browser:

```
(venv)$ chromium airport/potree.html
```

## License

LOPoCS is distributed under LPGL2 or later.
