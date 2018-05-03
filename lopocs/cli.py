#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import re
import sys
import shlex
import json
from zipfile import ZipFile
from datetime import datetime
from pathlib import Path
from subprocess import check_call, call, check_output, CalledProcessError, DEVNULL

import click
import requests
from flask_cors import CORS
from pyproj import Proj, transform

from lopocs import __version__
from lopocs import create_app, greyhound, threedtiles
from lopocs.database import Session
from lopocs.potreeschema import potree_schema
from lopocs.potreeschema import potree_page
from lopocs.cesium import cesium_page
from lopocs.utils import compute_scale_for_cesium


samples = {
    'airport': 'http://www.liblas.org/samples/LAS12_Sample_withRGB_Quick_Terrain_Modeler_fixed.las',
    'sthelens': 'http://www.liblas.org/samples/st-helens.las',
    'lyon': (3946, 'http://3d.oslandia.com/lyon.laz')
}

PDAL_PIPELINE = """
{{
"pipeline": [
    {{
        "type": "readers.{extension}",
        "filename":"{realfilename}"
    }},
    {{
        "type": "filters.chipper",
        "capacity": "{capacity}"
    }},
    {reproject}
    {{
        "type": "filters.mortonorder",
        "reverse": "true"
    }},
    {{
        "type":"writers.pgpointcloud",
        "connection":"dbname={pg_name} host={pg_host} port={pg_port} user={pg_user} password={pg_password}",
        "schema": "{schema}",
        "table":"{tab}",
        "compression":"none",
        "srid":"{srid}",
        "overwrite":"true",
        "column": "{column}",
        "scale_x": "{scale_x}",
        "scale_y": "{scale_y}",
        "scale_z": "{scale_z}",
        "offset_x": "{offset_x}",
        "offset_y": "{offset_y}",
        "offset_z": "{offset_z}"
    }}
]
}}"""


def fatal(message):
    '''print error and exit'''
    click.echo('\nFATAL: {}'.format(message), err=True)
    sys.exit(1)


def pending(msg, nl=False):
    click.echo('[{}] {} ... '.format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        msg
    ), nl=nl)


def green(message):
    click.secho(message.replace('\n', ''), fg='green')


def ok(mess=None):
    if mess:
        click.secho('{} : '.format(mess.replace('\n', '')), nl=False)
    click.secho('ok', fg='green')


def ko(mess=None):
    if mess:
        click.secho('{} : '.format(mess.replace('\n', '')), nl=False)
    click.secho('ko', fg='red')


def download(label, url, dest):
    '''
    download url using requests and a progressbar
    '''
    r = requests.get(url, stream=True)
    length = int(r.headers['content-length'])

    chunk_size = 512
    iter_size = 0
    with io.open(dest, 'wb') as fd:
        with click.progressbar(length=length, label=label) as bar:
            for chunk in r.iter_content(chunk_size):
                fd.write(chunk)
                iter_size += chunk_size
                bar.update(chunk_size)


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('LOPoCS version {}'.format(__version__))
    click.echo('')
    ctx.exit()


@click.group()
@click.option('--version', help='show version', is_flag=True, expose_value=False, callback=print_version)
def cli():
    '''lopocs command line tools'''
    pass


@click.option('--host', help='The hostname to listen on (default is 127.0.0.1)',
              default='127.0.0.1', type=str)
@click.option('--port', help='The port to listen on (default is 5000)',
              default=5000, type=int)
@cli.command()
def serve(host, port):
    '''run lopocs server (development usage)'''
    app = create_app()
    CORS(app)
    app.run(host=host, port=port)


def cmd_rt(message, command):
    '''wrapper around call function
    '''
    click.echo('{} ... '.format(message), nl=False)
    rt = call(command, shell=True)
    if rt != 0:
        ko()
        return
    ok()


def cmd_output(message, command):
    '''wrapper check_call function
    '''
    click.echo('{} ... '.format(message), nl=False)
    try:
        output = check_output(shlex.split(command)).decode()
        green(output)
    except Exception as exc:
        ko(str(exc))


def cmd_pg(message, request):
    '''wrapper around a session query
    '''
    click.echo('{} ... '.format(message), nl=False)
    try:
        result = Session.query(request)
        if not result:
            raise Exception('Not found')
        green(result[0][0])
    except Exception as exc:
        ko(str(exc))


@cli.command()
def check():
    '''check lopocs configuration and dependencies'''
    try:
        app = create_app()
    except Exception as exc:
        fatal(str(exc))

    if not app:
        fatal("it appears that you don't have any configuration file")

    # pdal
    cmd_output('Pdal', 'pdal-config --version')
    cmd_rt('Pdal plugin pgpointcloud', "test -e `pdal-config --plugin-dir`/libpdal_plugin_writer_pgpointcloud.so")

    # postgresql and extensions
    cmd_pg('PostgreSQL', 'show server_version')
    cmd_pg('PostGIS extension', "select default_version from pg_available_extensions where name = 'postgis'")
    cmd_pg('PgPointcloud extension', "select default_version from pg_available_extensions where name = 'pointcloud'")
    cmd_pg('PgPointcloud-PostGIS extension', "select default_version from pg_available_extensions where name = 'pointcloud_postgis'")


@click.option('--table', required=True, help='table name to store pointclouds, considered in public schema if no prefix provided')
@click.option('--column', help="column name to store patches", default="points", type=str)
@click.option('--work-dir', type=click.Path(exists=True), required=True, help="working directory where temporary files will be saved")
@click.option('--server-url', type=str, help="server url for lopocs", default="http://localhost:5000")
@click.option('--capacity', type=int, default=400, help="number of points in a pcpatch")
@click.option('--potree', 'usewith', help="load data for use with greyhound/potree", flag_value='potree')
@click.option('--cesium', 'usewith', help="load data for use with use 3dtiles/cesium ", default=True, flag_value='cesium')
@click.option('--srid', help="set Spatial Reference Identifier (EPSG code) for the source file", default=0, type=int)
@click.argument('filename', type=click.Path(exists=True))
@cli.command()
def load(filename, table, column, work_dir, server_url, capacity, usewith, srid):
    '''load pointclouds data using pdal and add metadata needed by lopocs'''
    _load(filename, table, column, work_dir, server_url, capacity, usewith, srid)


def _load(filename, table, column, work_dir, server_url, capacity, usewith, srid=0):
    '''load pointclouds data using pdal and add metadata needed by lopocs'''
    # intialize flask application
    app = create_app()

    filename = Path(filename)
    work_dir = Path(work_dir)
    extension = filename.suffix[1:].lower()
    # laz uses las reader in PDAL
    extension = extension if extension != 'laz' else 'las'
    basename = filename.stem
    basedir = filename.parent

    pending('Creating metadata table')
    Session.create_pointcloud_lopocs_table()
    ok()

    pending('Reading summary with PDAL')
    json_path = os.path.join(
        str(work_dir.resolve()),
        '{basename}_{table}_pipeline.json'.format(**locals()))

    # tablename should be always prefixed
    if '.' not in table:
        table = 'public.{}'.format(table)

    cmd = "pdal info --summary {}".format(filename)
    try:
        output = check_output(shlex.split(cmd))
    except CalledProcessError as e:
        fatal(e)

    summary = json.loads(output.decode())['summary']
    ok()

    if 'srs' not in summary and not srid:
        fatal('Unable to find the spatial reference system, please provide a SRID with option --srid')

    if not srid:
        # find authority code in wkt string
        srid = re.findall('EPSG","(\d+)"', summary['srs']['wkt'])[-1]

    p = Proj(init='epsg:{}'.format(srid))

    if p.is_latlong():
        # geographic
        scale_x, scale_y, scale_z = (1e-6, 1e-6, 1e-2)
    else:
        # projection or geocentric
        scale_x, scale_y, scale_z = (0.01, 0.01, 0.01)

    offset_x = summary['bounds']['X']['min'] + (summary['bounds']['X']['max'] - summary['bounds']['X']['min']) / 2
    offset_y = summary['bounds']['Y']['min'] + (summary['bounds']['Y']['max'] - summary['bounds']['Y']['min']) / 2
    offset_z = summary['bounds']['Z']['min'] + (summary['bounds']['Z']['max'] - summary['bounds']['Z']['min']) / 2

    reproject = ""

    if usewith == 'cesium':
        from_srid = srid
        # cesium only use epsg:4978, so we must reproject before loading into pg
        srid = 4978

        reproject = """
        {{
           "type":"filters.reprojection",
           "in_srs":"EPSG:{from_srid}",
           "out_srs":"EPSG:{srid}"
        }},""".format(**locals())
        # transform bounds in new coordinate system
        pini = Proj(init='epsg:{}'.format(from_srid))
        pout = Proj(init='epsg:{}'.format(srid))
        # recompute offset in new space and start at 0
        pending('Reprojected bounds', nl=True)
        # xmin, ymin, zmin = transform(pini, pout, offset_x, offset_y, offset_z)
        xmin, ymin, zmin = transform(pini, pout, summary['bounds']['X']['min'], summary['bounds']['Y']['min'], summary['bounds']['Z']['min'])
        xmax, ymax, zmax = transform(pini, pout, summary['bounds']['X']['max'], summary['bounds']['Y']['max'], summary['bounds']['Z']['max'])
        offset_x, offset_y, offset_z = xmin, ymin, zmin
        click.echo('{} < x < {}'.format(xmin, xmax))
        click.echo('{} < y < {}'.format(ymin, ymax))
        click.echo('{} < z < {}  '.format(zmin, zmax), nl=False)
        ok()
        pending('Computing best scales for cesium')
        # override scales for cesium if possible we try to use quantized positions
        scale_x = min(compute_scale_for_cesium(xmin, xmax), 1)
        scale_y = min(compute_scale_for_cesium(ymin, ymax), 1)
        scale_z = min(compute_scale_for_cesium(zmin, zmax), 1)
        ok('[{}, {}, {}]'.format(scale_x, scale_y, scale_z))

    pg_host = app.config['PG_HOST']
    pg_name = app.config['PG_NAME']
    pg_port = app.config['PG_PORT']
    pg_user = app.config['PG_USER']
    pg_password = app.config['PG_PASSWORD']
    realfilename = str(filename.resolve())
    schema, tab = table.split('.')

    pending('Loading point clouds into database')

    with io.open(json_path, 'w') as json_file:
        json_file.write(PDAL_PIPELINE.format(**locals()))

    cmd = "pdal pipeline {}".format(json_path)

    try:
        check_call(shlex.split(cmd), stderr=DEVNULL, stdout=DEVNULL)
    except CalledProcessError as e:
        fatal(e)
    ok()

    pending("Creating indexes")
    Session.execute("""
        create index on {table} using gist(pc_envelopegeometry(points));
        alter table {table} add column morton bigint;
        select Morton_Update('{table}', 'points', 'morton', 128, TRUE);
        create index on {table}(morton);
    """.format(**locals()))
    ok()

    pending("Adding metadata for lopocs")
    Session.update_metadata(
        table, column, srid, scale_x, scale_y, scale_z,
        offset_x, offset_y, offset_z
    )
    lpsession = Session(table, column)
    ok()

    # retrieve boundingbox
    fullbbox = lpsession.boundingbox
    bbox = [
        fullbbox['xmin'], fullbbox['ymin'], fullbbox['zmin'],
        fullbbox['xmax'], fullbbox['ymax'], fullbbox['zmax']
    ]

    if usewith == 'potree':
        lod_min = 0
        lod_max = 5
        # add schema currently used by potree (version 1.5RC)
        Session.add_output_schema(
            table, column, 0.01, 0.01, 0.01,
            offset_x, offset_y, offset_z, srid, potree_schema
        )
        cache_file = (
            "{0}_{1}_{2}_{3}_{4}.hcy".format(
                lpsession.table,
                lpsession.column,
                lod_min,
                lod_max,
                '_'.join(str(e) for e in bbox)
            )
        )
        pending("Building greyhound hierarchy")
        new_hcy = greyhound.build_hierarchy_from_pg(
            lpsession, lod_min, lod_max, bbox
        )
        greyhound.write_in_cache(new_hcy, cache_file)
        ok()
        create_potree_page(str(work_dir.resolve()), server_url, table, column)

    if usewith == 'cesium':
        pending("Building 3Dtiles tileset")
        hcy = threedtiles.build_hierarchy_from_pg(
            lpsession, server_url, bbox
        )

        tileset = os.path.join(str(work_dir.resolve()), 'tileset-{}.{}.json'.format(table, column))

        with io.open(tileset, 'wb') as out:
            out.write(hcy.encode())
        ok()
        create_cesium_page(str(work_dir.resolve()), table, column)


@click.option('--table', required=True, help='table name to store pointclouds, considered in public schema if no prefix provided')
@click.option('--column', help="column name to store patches", default="points", type=str)
@click.option('--work-dir', type=click.Path(exists=True), required=True, help="working directory where temporary files will be saved")
@click.option('--server-url', type=str, help="server url for lopocs", default="http://localhost:5000")
@cli.command()
def tileset(table, column, server_url, work_dir):
    """
    (Re)build a tileset.json for a given table
    """
    # intialize flask application
    create_app()

    work_dir = Path(work_dir)

    if '.' not in table:
        table = 'public.{}'.format(table)

    lpsession = Session(table, column)
    # initialize range for level of details
    fullbbox = lpsession.boundingbox
    bbox = [
        fullbbox['xmin'], fullbbox['ymin'], fullbbox['zmin'],
        fullbbox['xmax'], fullbbox['ymax'], fullbbox['zmax']
    ]
    pending('Building tileset from database')
    hcy = threedtiles.build_hierarchy_from_pg(
        lpsession, server_url, bbox
    )
    ok()
    tileset = os.path.join(str(work_dir.resolve()), 'tileset-{}.{}.json'.format(table, column))
    pending('Writing tileset to disk')
    with io.open(tileset, 'wb') as out:
        out.write(hcy.encode())
    ok()


def create_potree_page(work_dir, server_url, tablename, column):
    '''Create an html demo page with potree viewer
    '''
    # get potree build
    potree = os.path.join(work_dir, 'potree')
    potreezip = os.path.join(work_dir, 'potree.zip')
    if not os.path.exists(potree):
        download('Getting potree code', 'http://3d.oslandia.com/potree.zip', potreezip)
        # unzipping content
        with ZipFile(potreezip) as myzip:
            myzip.extractall(path=work_dir)
    tablewschema = tablename.split('.')[-1]
    sample_page = os.path.join(work_dir, 'potree-{}.html'.format(tablewschema))
    abs_sample_page = str(Path(sample_page).absolute())
    pending('Creating a potree demo page : file://{}'.format(abs_sample_page))
    resource = '{}.{}'.format(tablename, column)
    server_url = server_url.replace('http://', '')
    with io.open(sample_page, 'wb') as html:
        html.write(potree_page.format(resource=resource, server_url=server_url).encode())
    ok()


def create_cesium_page(work_dir, tablename, column):
    '''Create an html demo page with cesium viewer
    '''
    cesium = os.path.join(work_dir, 'cesium')
    cesiumzip = os.path.join(work_dir, 'cesium.zip')
    if not os.path.exists(cesium):
        download('Getting cesium code', 'http://3d.oslandia.com/cesium.zip', cesiumzip)
        # unzipping content
        with ZipFile(cesiumzip) as myzip:
            myzip.extractall(path=work_dir)
    tablewschema = tablename.split('.')[-1]
    sample_page = os.path.join(work_dir, 'cesium-{}.html'.format(tablewschema))
    abs_sample_page = str(Path(sample_page).absolute())
    pending('Creating a cesium demo page : file://{}'.format(abs_sample_page))
    resource = '{}.{}'.format(tablename, column)
    with io.open(sample_page, 'wb') as html:
        html.write(cesium_page.format(resource=resource).encode())
    ok()


@cli.command()
@click.option('--sample', help="sample data available", default="airport", type=click.Choice(samples.keys()))
@click.option('--work-dir', type=click.Path(exists=True), required=True, help="working directory where sample files will be saved")
@click.option('--server-url', type=str, help="server url for lopocs", default="http://localhost:5000")
@click.option('--potree', 'usewith', help="load data for using with greyhound/potree", flag_value='potree')
@click.option('--cesium', 'usewith', help="load data for using with 3dtiles/cesium ", default=True, flag_value='cesium')
def demo(sample, work_dir, server_url, usewith):
    '''
    download sample lidar data, load it into pgpointcloud
    '''
    srid = None
    if isinstance(samples[sample], (list, tuple)):
        # srid given
        srid = samples[sample][0]
        download_link = samples[sample][1]
    else:
        download_link = samples[sample]
    filepath = Path(download_link)
    pending('Using sample data {}: {}'.format(sample, filepath.name))
    dest = os.path.join(work_dir, filepath.name)
    ok()

    if not os.path.exists(dest):
        download('Downloading sample', download_link, dest)

    # now load data
    if srid:
        _load(dest, sample, 'points', work_dir, server_url, 400, usewith, srid=srid)
    else:
        _load(dest, sample, 'points', work_dir, server_url, 400, usewith)

    click.echo(
        'Now you can test lopocs server by executing "lopocs serve"'
        .format(sample)
    )
