LOPoCS, a Light Opensource PointCloud Server
############################################

LOPoCS is a point cloud server written in
Python, allowing to load Point Cloud from a PostgreSQL database thanks to the ``pgpointcloud``
extension.

.. image:: docs/lopocs.png
    :align: center
    :width: 400px

.. image:: docs/itowns_montreal1_header.png
    :align: center
    :width: 700px

|unix_build| |license|

The current version of LOPoCS provides a way to load Point Cloud from PostgreSQL to the following viewers:

* `Potree viewer <http://www.potree.org/>`_ : viewer with LAZ compressed data.
* `iTowns2 <https://github.com/iTowns/itowns2>`_ : on the side of other data type
* `Cesium <https://github.com/AnalyticalGraphicsInc/cesium>`_ thanks to the `3DTiles <https://github.com/AnalyticalGraphicsInc/3d-tiles>`_ format

Note that LOPoCS is currently the only **3DTiles** server able to stream data from
`pgpointcloud <https://github.com/pgpointcloud/pointcloud>`_. This
is possible thanks to the python module
`py3dtiles <https://github.com/Oslandia/py3dtiles>`_.

Developments are still going on to improve state-of-the-art algorithms and
performances.

`Video <https://vimeo.com/189285883>`_
`Online demonstration <https://li3ds.github.io/lopocs>`_)

.. contents::

.. section-numbering::


Main features
=============

* Command line tool to load data into PostgreSQL
* Stream patches stored in PostgreSQL
* Greyhound protocol support
* 3DTiles standard support (partial)
* Produce ready to use examples with Potree, Cesium and itowns2

Installation
============

Dependencies
------------

  - python >= 3.4
  - gdal development headers (libgdal-dev)
  - pip (python3-pip)
  - virtualenv (python3-virtualenv)
  - numpy (python3-numpy)
  - `pgpointcloud fork <https://github.com/LI3DS/pointcloud>`_
  - `Morton Postgres extension <https://github.com/Oslandia/pgmorton>`_
  - `PDAL <https://github.com/pblottiere/PDAL/>`_ (optional)

If you want to use the lopocs loader, you must have PDAL installed with extra features.
These features are currently maintained in `this fork <https://github.com/pblottiere/PDAL>`_,
but the goal is to contribute most of them in the official PDAL repository.

From sources
------------

::

  $ git clone https://github.com/Oslandia/lopocs
  $ cd lopocs
  $ virtualenv -p /usr/bin/python3 --system-site-packages venv
  $ source venv/bin/activate
  (venv)$ pip install -e .

Configuration
=============

You will find an example of a configuration file for lopocs in ``conf/lopocs.sample.yml``

You can copy it to ``conf/lopocs.yml`` and fill with your values, lopocs will load it
if this file exists.

Usage
=====

Prepare database
----------------

::

  $ createdb lopocs_test
  $ psql lopocs_test
  lopocs_test=# create extension postgis;
  CREATE EXTENSION
  lopocs_test=# create extension pointcloud;
  CREATE EXTENSION
  lopocs_test=# create extension pointcloud_postgis;
  CREATE EXTENSION
  lopocs_test=# create extension morton;
  CREATE EXTENSION

Fill the database with lopocs command line
------------------------------------------

Ensure you are inside the virtualenv created above and launch the lopocs command
without arguments to see what subcommands are available

::

  $ source venv/bin/activate
  (venv)$ lopocs

Download a sample data and view it potree in a few minutes:

::

  (venv)$ lopocs demo --work-dir .


Test lopocs with docker
=======================

If you are a little bit lazy or you don't want to compile the world right now,
you can test lopocs with a one line command. You will need ansible for that and docker
(respectively an IT provisioner and the well known container engine)

::

  $ ./docker.sh


Run tests
========

::

  (venv)$ pip install nose
  (venv)$ nosetests


.. |unix_build| image:: https://img.shields.io/travis/Oslandia/lopocs/master.svg?style=flat-square&label=unix%20build
    :target: http://travis-ci.org/Oslandia/lopocs
    :alt: Build status of the master branch

.. |license| image:: https://img.shields.io/badge/license-LGPL-blue.svg?style=flat-square
    :target: LICENSE
    :alt: Package license
