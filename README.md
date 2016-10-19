# LOPoCS
Light OpenSource PointCloud Server

Lopocs is a point cloud server written in Python, allowing to load Point Cloud
from Postgis thanks to the pgpointcloud extension.

The current version of Lopocs provides a way to load Point Cloud from Postgis in:

* Potree viewer with LAZ compressed data
* iTowns2 on the side of other data type
* Cesium thanks to the 3DTiles format


## Install dependencies

```
cd lopocs
virtualenv -p /usr/bin/python3 venv
. venv/bin/activate
(venv) pip install -e .
```

## Run

```
cd lopocs
. venv/bin/activate
(venv) pip install uwsgi
(venv) uwsgi --yml conf/lopocs.uwsgi.yml
```
