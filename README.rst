LOPoCS, a Light Opensource PointCloud Server
############################################

LOPoCS is a point cloud server written in
Python, allowing to load Point Cloud from a PostgreSQL database thanks to the ``pgpointcloud``
extension.

.. image:: docs/lopocs.png
    :align: center
    :width: 400px

|unix_build| |license|

The current version of LOPoCS provides a way to load Point Cloud from PostgreSQL to the following viewers:

* `Cesium <https://github.com/AnalyticalGraphicsInc/cesium>`_ thanks to the `3DTiles <https://github.com/AnalyticalGraphicsInc/3d-tiles>`_ format
* `Potree viewer <http://www.potree.org/>`_ : viewer with LAZ compressed data.

Note that LOPoCS is currently the only **3DTiles** server able to stream data from
`pgpointcloud <https://github.com/pgpointcloud/pointcloud>`_. This
is possible thanks to the python module
`py3dtiles <https://github.com/Oslandia/py3dtiles>`_.

Developments are still going on to improve state-of-the-art algorithms and
performances.

`Video <https://vimeo.com/189285883>`_

`Online demonstration <https://li3ds.github.io/lopocs>`_

.. contents::

.. section-numbering::


Main features
=============

* Command line tool to load data into PostgreSQL
* Stream patches stored in PostgreSQL
* Greyhound protocol support
* 3DTiles standard support (partial)
* Produce ready to use examples with Potree and Cesium

Installation
============

Dependencies
------------

  - python >= 3.4
  - gdal development headers (libgdal-dev)
  - pip (python3-pip)
  - virtualenv (python3-virtualenv)
  - `pgpointcloud <https://github.com/pgpointcloud/pointcloud>`_
  - `Morton Postgres extension <https://github.com/Oslandia/pgmorton>`_
  - `PDAL <https://github.com/pblottiere/PDAL/>`_ ( if using lopocs loader)

.. note:: The PDAL fork contains a new revert_morton plugin that orders points according to the revert Morton algorithm.

From sources
------------

.. code-block::bash

    $ git clone https://github.com/Oslandia/lopocs
    $ cd lopocs
    $ virtualenv -p /usr/bin/python3 venv
    $ source venv/bin/activate
    (venv)$ pip install -e .

Configuration
=============

You will find an example of a configuration file for lopocs in ``conf/lopocs.sample.yml``

You have to copy it to ``conf/lopocs.yml`` and fill with your values, lopocs will load it
if this file exists.
Another alternative is to set up the ``LOPOCS_SETTINGS`` environment variable to locate your configuration file.


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

Lopocs CLI
----------

You can invoke lopocs in your virtualenv to show help and list available subcommands

.. code-block::bash

    $ cd lopocs
    $ source venv/bin/activate
    (venv)$ lopocs


Demo data
---------

::

    (venv)$ mkdir demos
    (venv)$ lopocs demo --work-dir demos/ --sample sthelens --cesium
    (venv)$ lopocs serve


Run tests
=========

::

  (venv)$ pip install nose
  (venv)$ nosetests


.. |unix_build| image:: https://img.shields.io/travis/Oslandia/lopocs/master.svg?style=flat-square&label=unix%20build
    :target: http://travis-ci.org/Oslandia/lopocs
    :alt: Build status of the master branch

.. |license| image:: https://img.shields.io/badge/license-LGPL-blue.svg?style=flat-square
    :target: LICENSE
    :alt: Package license
