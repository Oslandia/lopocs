<p align="center">
<img align="center" src="https://github.com/LI3DS/lopocs/blob/master/docs/lopocs.png" width="400">
</p>
<br>
<br>

LOPoCS (Light Opensource PointCloud Server) is a point cloud server written in
Python, allowing to load Point Cloud from Postgis thanks to the pgpointcloud
extension.

The current version of LOPoCS provides a way to load Point Cloud from Postgis in:

* [Potree viewer](http://www.potree.org/ "Potree viewer") viewer with LAZ compressed data
* [iTowns2](https://github.com/iTowns/itowns2 "iTowns2") on the side of other data type
* [Cesium](https://github.com/AnalyticalGraphicsInc/cesium "Cesium") thanks to the [3DTiles](https://github.com/AnalyticalGraphicsInc/3d-tiles "3DTiles") format

Note that LOPoCS is currently the only 3DTiles server able to stream data from
[pgpointcloud](https://github.com/pgpointcloud/pointcloud "pgpointcloud"). This
is possible thanks to the python module
[py3dtiles](https://github.com/pblottiere/py3dtiles "py3dtiles").

Developments are still going on to improve state-of-the-art algorithms and
performances.


## Install

### From source

To install LOPoCS from source:

```
$ git clone https://github.com/LI3DS/lopocs
$ cd lopocs
$ virtualenv -p /usr/bin/python3 venv
$ . venv/bin/activate
(venv)$ pip install -e .
(venv)$ python setup.py install
```

If you want to run unit tests:

```
(venv)$ python setup.py test
```

## How to run

LOPoCS has been tested with uWSGI and Nginx:

```
(venv) pip install uwsgi
(venv) uwsgi --yml conf/lopocs.uwsgi.yml
```

## Swagger

LOPoCS provides its RESTful API through a Swagger UI:

TODO: screenshot

### Default Namespace

TODO

### Greyhound Namespace

TODO

### 3DTiles Namespace

TODO
