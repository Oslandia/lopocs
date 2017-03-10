#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import sys
import shlex
from datetime import datetime
from pathlib import Path
from subprocess import check_call, CalledProcessError, DEVNULL

import click
from lopocs import __version__
from lopocs import create_app, greyhound, threedtiles
from lopocs.database import Session

# intialize flask application
app = create_app()


def fatal(message):
    '''print error and exit'''
    click.echo('\nFATAL: {}'.format(message), err=True)
    sys.exit(1)


def pending(msg, nl=False):
    click.echo('[{}] {} ... '.format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        msg
    ), nl=nl)


def ok(mess=None):
    click.secho('ok: {}'.format(mess) if mess else 'ok', fg='green')


def ko():
    click.secho('ko', fg='red')


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


@cli.command()
def serve():
    '''run lopocs server (development usage)'''
    app.run()


@click.option('--table', required=True, help='table name to store pointclouds, considered in public schema if no prefix provided')
@click.option('--column', help="column name to store patches", default="points", type=str)
@click.option('--work-dir', type=click.Path(exists=True), help="working directory where temporary files will be saved")
@click.option('--server-url', type=str, help="server url for lopocs", default="http://localhost:5000")
@click.argument('filename', type=click.Path(exists=True))
@cli.command()
def load(filename, table, column, work_dir, server_url):
    '''load pointclouds data using pdal and add metadata needed by lopocs'''
    filename = Path(filename)
    work_dir = Path(work_dir)
    extension = filename.suffix[1:].lower()
    basename = filename.stem
    basedir = filename.parent

    pending('Creating metadata table')
    Session.create_pointcloud_lopocs_table()
    ok()

    pending('Loading point clouds into database')
    json_path = os.path.join(
        str(work_dir.resolve()),
        '{basename}_{table}_pipeline.json'.format(**locals()))

    schema, table = table.split('.') if '.' in table else 'public', table

    json_pipeline = """
{{
    "pipeline": [
        {{
            "type": "readers.{7}",
            "filename":"{0}"
        }},
        {{
            "type": "filters.chipper",
            "capacity":400
        }},
        {{
            "type": "filters.revertmorton"
        }},
        {{
            "type":"writers.pgpointcloud",
            "connection":"dbname={1} port={2} user={3} password={4}",
            "schema": "{5}",
            "table":"{6}",
            "compression":"none",
            "srid":"0",
            "overwrite":"true",
            "column": "points"
        }}
    ]
}}""".format(
        str(filename.resolve()),
        app.config['PG_NAME'],
        app.config['PG_PORT'],
        app.config['PG_USER'],
        app.config['PG_PASSWORD'],
        schema,
        table,
        extension
    )

    with io.open(json_path, 'w') as json_file:
        json_file.write(json_pipeline)

    cmd = "pdal pipeline {}".format(json_path)

    try:
        check_call(shlex.split(cmd), stderr=DEVNULL, stdout=DEVNULL)
    except CalledProcessError as e:
        fatal(e)
    ok()

    pending("Creating indexes")
    Session.execute("""
        create index on {table} using gist(geometry(points));
        alter table {table} add column morton bigint;
        select Morton_Update('{table}', 'points', 'morton', 64, TRUE);
        create index on {table}(morton);
    """.format(**locals()))
    ok()

    # create a session dedicated to given table and column
    lpsession = Session(table, column)

    pending("Loading metadata for lopocs")
    lpsession.load_lopocs_metadata(table, 0.01, 0)
    lpsession.load_lopocs_metadata(table, 0.1, 0)
    ok()

    # initialize range for level of details
    lod_min = 0
    lod_max = 5

    # retrieve boundingbox
    fullbbox = lpsession.boundingbox
    bbox = [
        fullbbox['xmin'], fullbbox['ymin'], fullbbox['zmin'],
        fullbbox['xmax'], fullbbox['ymax'], fullbbox['zmax']
    ]
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

    pending("Building 3Dtiles tileset")
    hcy = threedtiles.build_hierarchy_from_pg(
        lpsession, table, column, server_url, lod_max, bbox, lod_min
    )

    tileset = os.path.join(str(work_dir.resolve()), 'tileset.json')

    with io.open(tileset, 'wb') as out:
        out.write(hcy.encode())
    ok()
