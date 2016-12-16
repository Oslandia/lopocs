#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# -----------------------------------------------------------------------------
# imports
# -----------------------------------------------------------------------------
import shlex
import argparse
from flask import Flask
import shutil
import subprocess
import time
import json
import psycopg2
import os
import getpass
import glob
import sys
from distutils.dir_util import copy_tree

from lopocs.database import Session
from lopocs import greyhound


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
LOPOCS_MODULE_DIR = os.path.join(SCRIPT_DIR, "..")
sys.path.append(LOPOCS_MODULE_DIR)

# -----------------------------------------------------------------------------
# const
# -----------------------------------------------------------------------------
USER = getpass.getuser()
HOME = os.path.expanduser("~")


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def header(msg):
    print()
    print("============================================================")
    print(msg)
    print("============================================================")
    print()


def logger(msg='', res=False, valid=True, resmsg=''):
    if not res:
        print(msg + "...: ", end='')
    else:
        if valid:
            if resmsg:
                print(resmsg)
            else:
                print(bcolors.OKGREEN + "OK" + bcolors.ENDC)
        else:
            print(bcolors.FAIL + "FAIL" + bcolors.ENDC)

    sys.stdout.flush()


def config_summary(args):

    header("LOPoCS configuration")
    print("General")
    print(" - files: {}".format(args.files))
    print(" - output directory: {}".format(os.path.abspath(args.outdir)))
    print(" - epsg code: EPSG:{}".format(args.epsg))
    print(" - force: {}".format(args.force))
    print()
    print("Postgres")
    print(" - host: {}".format(args.pg_host))
    print(" - database: {}".format(args.pg_db))
    print(" - port: {}".format(args.pg_port))
    print(" - table: {}".format(args.pg_table))
    print(" - column: {}".format(args.pg_column))
    print(" - user: {}".format(args.pg_user))
    print(" - password: {}".format(args.pg_pwd))
    print(" - patch_compression: {}".format(args.pg_patchcompression))
    print()
    print("PDAL")
    print(" - reader: {}".format(args.pdal_reader))
    print(" - patch size: {}".format(args.pdal_patchsize))
    print()
    print("Morton")
    print(" - grid size: {0}".format(args.morton_size))
    print()
    print("Hierarchy")
    print(" - lod max: {0}".format(args.lod_max))
    print()
    print("LOPoCS")
    print(" - cache directory: {}".format(os.path.abspath(args.lopocs_cachedir)))
    print()
    print("UWSGI")
    print(" - host: {}".format(args.uwsgi_host))
    print(" - port: {}".format(args.uwsgi_port))
    print(" - logfile: {}".format(args.uwsgi_log))
    print(" - virtualenv: {}".format(args.uwsgi_venv))
    print()
    print("Viewer(s)")
    print(" - PotreeViewer: {}".format(args.potreeviewer))


def search_cmd(cmd):
    logger(cmd)

    cdb = shutil.which(cmd)
    if not cdb:
        logger(res=True, resmsg="not found")
        sys.exit()
    else:
        logger(res=True, resmsg=cdb)

    return cdb


def search_lib(libpath, libname):
    logger(libname)

    if os.path.isfile(libpath):
        logger(res=True, resmsg=libpath)
    else:
        logger(res=True, resmsg="not found")
        sys.exit()


def run_cmd(cmd):
    out = subprocess.check_output(cmd)
    if args.verbose:
        print(out)
    return out


def checkenv(args):
    env = {}

    # database
    cmd = "dropdb"
    env[cmd] = search_cmd(cmd)

    cmd = "createdb"
    env[cmd] = search_cmd(cmd)

    # pdal stuff
    cmd = "pdal"
    env[cmd] = search_cmd(cmd)

    cmd = "pdal-config"
    env[cmd] = search_cmd(cmd)

    out = run_cmd([env["pdal-config"], "--plugin-dir"])
    pdal_plugindir = str(out, 'utf-8').replace('\n', '')
    midoc = os.path.join(pdal_plugindir, "libpdal_plugin_filter_midoc.so")
    search_lib(midoc, "pdal plugin midoc filter")

    pgpointcloud_writer = os.path.join(pdal_plugindir, "libpdal_plugin_writer_pgpointcloud.so")
    search_lib(pgpointcloud_writer, "pdal plugin pgpointcloud writer")

    return env


def getfiles(args):
    logger("Search input file(s)")

    files = []
    pattern = args.files
    for filename in glob.glob(pattern):
        files.append(os.path.abspath(filename))

    if not files:
        logger(res=True, valid=False)
        print("No input files found.")
        sys.exit()
    else:
        logger(res=True, valid=True)

    return files


def clean(args):
    logger("Remove output directory")
    if os.path.exists(args.outdir):
        shutil.rmtree(args.outdir)
    logger(res=True, valid=True)

    logger("Drop database")
    run_cmd(shlex.split('{} {} {} {} {} {}'.format(
        env['dropdb'],
        '--if-exists',
        '-p {}'.format(args.pg_port) if args.pg_port else '',
        '-U {}'.format(args.pg_user) if args.pg_user else '',
        '-h {}'.format(args.pg_host) if args.pg_host else '',
        args.pg_db
    )))


def init_outdir(args):
    logger("Initialize output directory")
    if not os.path.exists(args.outdir):
        os.makedirs(args.outdir)

    args.pdal_dir = os.path.join(args.outdir, "pdal")
    if not os.path.exists(args.pdal_dir):
        os.makedirs(args.pdal_dir)
    logger(res=True, valid=True)

    logger("Initialize cache directory")
    if not os.path.exists(args.lopocs_cachedir):
        os.makedirs(args.lopocs_cachedir)
    logger(res=True, valid=True)


def initdb(args, env):
    logger("Create the database")
    print(args.pg_port, args.pg_user, args.pg_host, args.pg_db)
    run_cmd(shlex.split('{} {} {} {} {}'.format(
        env['createdb'],
        '-p {}'.format(args.pg_port) if args.pg_port else '',
        '-U {}'.format(args.pg_user) if args.pg_user else '',
        '-h {}'.format(args.pg_host) if args.pg_host else '',
        args.pg_db
    )))

    logger("Initialize connection with database")
    app.config['PG_USER'] = args.pg_user
    app.config['PG_HOST'] = args.pg_host
    app.config['PG_PASSWORD'] = args.pg_pwd
    app.config['PG_PORT'] = args.pg_port
    app.config['PG_NAME'] = args.pg_db
    app.config['LOGGER_NAME'] = 'scan'
    Session.init_app(app)
    logger(res=True, valid=True)

    logger("Load postgis extension")
    query = "create extension if not exists postgis"
    try:
        Session.execute(query)
        logger(res=True, valid=True)
    except psycopg2.OperationalError as err:
        logger(res=True, valid=False)
        print(err)
        sys.exit()

    logger("Load pointcloud extension")
    query = "create extension if not exists pointcloud"
    try:
        Session.execute(query)
        logger(res=True, valid=True)
    except psycopg2.OperationalError as err:
        logger(res=True, valid=False)
        print(err)
        sys.exit()

    logger("Load pointcloud_postgis extension")
    query = "create extension if not exists pointcloud_postgis"
    try:
        Session.execute(query)
        logger(res=True, valid=True)
    except psycopg2.OperationalError as err:
        logger(res=True, valid=False)
        print(err)
        sys.exit()

    Session.create_pointcloud_streaming_table()

    logger("Load morton extension")
    query = "create extension if not exists morton"
    try:
        Session.execute(query)
        logger(res=True, valid=True)
    except psycopg2.OperationalError as err:
        logger(res=True, valid=False)
        print(err)
        sys.exit()


def pdal_reader_las(epsg, filename):
    json = ('{{\n'
            '"type":"readers.las",\n'
            '"filename":"{0}",\n'
            '"spatialreference":"EPSG:{1}"\n'
            '}}\n').format(filename, epsg)
    return json


def pdal_reader_e57(filename):
    json = ('{{\n'
            '"type":"readers.e57",\n'
            '"filename":"{0}"\n'
            '}}\n').format(filename)
    return json


def pdal_pipeline(files, args, env):
    logger("Build PDAL pipelines")
    pipelines = []
    for f in files:
        basename = os.path.splitext(os.path.basename(f))[0]
        json_path = os.path.join(args.pdal_dir,
                                 '{0}.pipeline'.format(basename))
        fh = open(json_path, 'w')

        if args.pdal_reader == 'e57':
            reader_pipe = pdal_reader_e57(f)
        elif args.pdal_reader == 'las':
            reader_pipe = pdal_reader_las(args.epsg, f)

        json = ('{{\n'
                '"pipeline":[\n'
                '{0}'
                ',\n'
                '{{\n'
                '"type":"filters.chipper",\n'
                '"capacity":{1}\n'
                '}},\n'
                '{{\n'
                '"type":"filters.midoc"\n'
                '}},\n'
                '{{\n'
                '"type":"writers.pgpointcloud",\n'
                '"connection":"dbname={2} port={5} user={6} password={7}",\n'
                '"table":"{3}",\n'
                '"compression":"{8}",\n'
                '"srid":"{4}",\n'
                '"overwrite":"true"\n'
                '}}\n'
                ']\n'
                '}}\n'.format(
                  reader_pipe, args.pdal_patchsize,
                  args.pg_db, args.pg_table, args.epsg,
                  args.pg_port, args.pg_user, args.pg_pwd,
                  args.pg_patchcompression))

        fh.write(json)
        fh.close()

        pipelines.append(os.path.abspath(json_path))
    logger(res=True, valid=True)

    n = len(pipelines)
    for i in range(0, n):
        print("Run PDAL pipelines...: {0}/{1}".format(i, n), end='\r')
        sys.stdout.flush()
        pipe = pipelines[i]
        run_cmd([env['pdal'], 'pipeline', '-i', '{0}'.format(pipe)])
    print("                                                     ", end='\r')
    logger("Run PDAL pipelines")
    logger(res=True, valid=True)


def getbbox(session):
    logger("Extract bounding box")
    fullbbox = session.boundingbox
    bbox = [fullbbox['xmin'], fullbbox['ymin'], fullbbox['zmin'],
            fullbbox['xmax'], fullbbox['ymax'], fullbbox['zmax']]
    logger(res=True, valid=True)

    return bbox


def morton_code(args, session):
    logger("Compute Morton code")

    sql = ("ALTER TABLE {0} add column morton bigint".format(args.pg_table))
    session.execute(sql)

    sql = ("SELECT Morton_Update('{0}', '{2}', 'morton', {1}, TRUE)"
           .format(args.pg_table, args.morton_size, args.pg_column))
    session.execute(sql)

    sql = ("CREATE index ON {0}(morton)".format(args.pg_table))
    session.execute(sql)

    logger(res=True, valid=True)


def create_patch_index(args, session):
    logger("Create geo index on patch")
    session.execute(
        "create index if not exists {0}_{1}_idx on {0} using gist(geometry({1}))"
        .format(args.pg_table, args.pg_column)
    )
    logger(res=True, valid=True)


def hierarchy(app, args, bbox, session):
    logger("Generate a hierarchy file for Potree")

    # save hierarchy in file
    hierarchy = greyhound.build_hierarchy_from_pg_mp(session, args.lod_max, bbox, 0)
    path = os.path.join(args.lopocs_cachedir, 'potree.hcy')
    f = open(path, 'w')
    json.dump(hierarchy, f)
    f.close()
    logger(res=True, valid=True)

    logger("Paste the Potree hierarchy in LOPoCS cache directory")
    logger(res=True, valid=True)

    # logger("Generate a hierarchy file for Cesium")
    # h = threedtiles.build_hierarchy_from_pg(baseurl, lod_max, bbox, lod_min)
    # logger(res=True, valid=True)


def configfile(args, bbox):
    print()

    logger("Generate a configuration file for LOPoCS")
    cfg = ("flask:\n"
           "    DEBUG: True\n"
           "    LOG_LEVEL: debug\n"
           "    PG_HOST: {11}\n"
           "    PG_USER: {12}\n"
           "    PG_NAME: {0}\n"
           "    PG_PORT: {1}\n"
           "    PG_PASSWORD: {13}\n"
           "    ROOT_HCY: {14}\n"
           "    DEPTH: {3}\n"
           "    BB: [{4}, {5}, {6}, {7}, {8}, {9}]\n"
           "    USE_MORTON: True\n"
           "    CACHE_DIR: {10}\n"
           "    STATS: False\n"
           .format(args.pg_db, args.pg_port, args.pg_table, args.lod_max + 1, bbox[0],
                   bbox[1], bbox[2], bbox[3], bbox[4], bbox[5],
                   os.path.abspath(args.lopocs_cachedir),
                   args.pg_host, args.pg_user, args.pg_pwd,
                   "potree.hcy"))
    path = os.path.join(args.outdir, 'lopocs.yml')
    f = open(path, 'w')
    f.write(cfg)
    f.close()
    logger(res=True, valid=True)

    logger("Generate a configuration file for UWSGI")
    cfg = """
uwsgi:
    virtualenv: {0}
    master: true
    socket: {1}:{2}
    protocol: http
    module: lopocs.wsgi:app
    processes: 4
    enable-threads: true
    lazy-apps: true
    need-app: true
    catch: exceptions=true
    #    logto2: {4}
    #    log-maxsize: 10000000
    env: LOPOCS_SETTINGS={3}/lopocs.yml
""".format(args.uwsgi_venv, args.uwsgi_host, args.uwsgi_port,
           os.path.abspath(args.outdir), args.uwsgi_log)

    path = os.path.join(args.outdir, 'lopocs.uwsgi.yml')
    f = open(path, 'w')
    f.write(cfg)
    f.close()
    logger(res=True, valid=True)


def potreeviewer(args):
    potree_dir = os.path.join(LOPOCS_MODULE_DIR, "vendor/potree")

    logger("Copy Potree project")
    copy_tree(potree_dir, os.path.join(args.outdir, "potree"))
    logger(res=True, valid=True)

    logger("Prepare Potree html file")
    src = os.path.join(potree_dir, "examples/greyhound_helens.html")
    dst = os.path.abspath(os.path.join(args.outdir, "potree/examples/potree.html"))

    replacements = {'192.168.1.12': args.uwsgi_host, '5000': str(args.uwsgi_port)}
    with open(src) as infile, open(dst, 'w') as outfile:
        for line in infile:
            for src, target in replacements.items():
                line = line.replace(src, target)
            outfile.write(line)

    os.symlink(dst, os.path.join(args.outdir, "potree.html"))

    logger(res=True, valid=True)

# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    descr = 'Prepare database for LOPoCS'
    parser = argparse.ArgumentParser(description=descr)

    # general
    files_help = "input files. A regex can be used: 'input/*.las'"
    parser.add_argument('files', metavar='files', type=str, help=files_help)

    outdir_help = "output directory"
    parser.add_argument('outdir', metavar='outdir', type=str, help=outdir_help)

    epsg_help = "EPSG code (default: 4326)"
    parser.add_argument('-epsg', metavar='epsg', type=int, help=epsg_help,
                        default=4326)

    # flags
    conf_help = "print current configuration only"
    parser.add_argument('--confonly', help=conf_help, action="store_true")

    potreeviewer_help = "configure Potree viewer"
    parser.add_argument('--potreeviewer', help=potreeviewer_help, action="store_true")

    force_help = "remove database and output directory if they exist"
    parser.add_argument('--force', help=force_help, action="store_true")

    # postgres parameters
    pg_db_help = 'postgres database'
    parser.add_argument('pg_db', metavar='pg_db', type=str, help=pg_db_help)

    pg_user_help = 'postgres user (default: {})'.format(USER)
    parser.add_argument('-pg_user', metavar='pg_user', type=str,
                        help=pg_user_help, default=USER)

    pg_table_default = 'patchs'
    pg_table_help = 'postgres table (default: {})'.format(pg_table_default)
    parser.add_argument('-pg_table', metavar='pg_table', type=str,
                        help=pg_table_help, default=pg_table_default)

    parser.add_argument('-pg_column', metavar='pg_column', type=str,
                        help='patch column name', default='pa')

    pg_host_help = 'postgres host (default: localhost)'
    parser.add_argument('-pg_host', metavar='pg_host', type=str,
                        help=pg_host_help, default='localhost')

    pg_port_default = 5432
    pg_host_help = 'postgres port (default: {})'.format(pg_port_default)
    parser.add_argument('-pg_port', metavar='pg_port', type=str,
                        help=pg_host_help, default=pg_port_default)

    pg_pwd_help = 'postgres password (default: )'
    parser.add_argument('-pg_pwd', metavar='pg_pwd', type=str,
                        help=pg_pwd_help, default='')

    parser.add_argument('-pg_patchcompression', metavar='pg_patchcompression', type=str,
                        help='patch compression', default='none')

    # pdal pipeline
    pdal_patchsize_help = "number of points per patch (default: 400)"
    parser.add_argument('-pdal_patchsize', metavar='size', type=int,
                        help=pdal_patchsize_help, default=400)

    pdal_reader_help = "PDAL reader to use in the pipeline (default: las)"
    parser.add_argument('-pdal_reader', metavar='reader', type=str,
                        help=pdal_reader_help, default='las')

    # morton
    morton_grid_help = "Grid size to compute the Morton Code (default: 64)"
    parser.add_argument('-morton_size', metavar='size', type=int,
                        help=morton_grid_help, default=64)

    # hierarchy
    lod_max_help = "Maximum Level Of Detail (default: 6)"
    parser.add_argument('-lod_max', metavar='lod_max', type=int,
                        help=lod_max_help, default=6)

    # lopocs
    lp_cachedir_default = os.path.join(HOME, '.cache', 'lopocs')
    lp_cachedir_help = ("LOPoCS cache directory (default: {})"
                        .format(lp_cachedir_default))
    parser.add_argument('-lopocs_cachedir', metavar='dir', type=str,
                        help=lp_cachedir_help, default=lp_cachedir_default)

    # uwsgi
    uwsgi_host_help = ("UWSGI host through which LOPoCS will be available (default: 127.0.0.1)")
    parser.add_argument('-uwsgi_host', metavar='uwsgi_host', type=str,
                        help=uwsgi_host_help, default='127.0.0.1')

    uwsgi_port_help = ("UWSGI port through which LOPoCS will be available (default: 5000)")
    parser.add_argument('-uwsgi_port', metavar='uwsgi_port', type=int,
                        help=uwsgi_port_help, default=5000)

    uwsgi_log_help = ("UWSGI logfile (default: /tmp/lopocs.log)")
    parser.add_argument('-uwsgi_log', metavar='uwsgi_log', type=str,
                        help=uwsgi_log_help, default='/tmp/lopocs.log')

    uwsgi_venv_default = os.path.join(SCRIPT_DIR, '../venv')
    uwsgi_venv_help = ("UWSGI virtualenv (default: {0})".format(uwsgi_venv_default))
    parser.add_argument('-uwsgi_venv', metavar='uwsgi_venv', type=str,
                        help=uwsgi_venv_help, default=uwsgi_venv_default)

    parser.add_argument('--verbose', action="store_true", help='Be more verbose')

    args = parser.parse_args()

    # print configuration
    config_summary(args)

    if (not args.confonly):
        # time
        start_time = time.time()

        header("LOPoCS check environment")
        env = checkenv(args)

        app = Flask(__name__)
        with app.app_context():
            header("LOPoCS prepare")
            files = getfiles(args)
            if args.force:
                clean(args)
            init_outdir(args)
            header("LOPoCS initialize database")
            initdb(args, env)
            header("LOPoCS fill database")
            pdal_pipeline(files, args, env)
            session = Session(args.pg_table, args.pg_column)
            create_patch_index(args, session)
            header("LOPoCS preprocessing")
            session.load_lopocs_metadata(
                args.pg_table, 0.1, args.epsg
            )
            session.load_lopocs_metadata(
                args.pg_table, 0.01, args.epsg
            )
            bbox = getbbox(session)
            morton_code(args, session)
            hierarchy(app, args, bbox, session)
            configfile(args, bbox)

            if args.potreeviewer:
                header("LOPoCS configure viewer(s)")
                potreeviewer(args)

        # summary
        print()
        session = Session(args.pg_table, args.pg_column)
        elapsed = time.time() - start_time
        npoints = session.patch_size * session.approx_row_count
        print("Duration: {} points processed in {} seconds with LOD {}."
              .format(npoints, elapsed, args.lod_max))
