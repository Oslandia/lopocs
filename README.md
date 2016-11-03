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
(venv)$ . venv/bin/activate
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
