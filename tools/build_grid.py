#! /bin/sh

import yaml
import sys
from binascii import hexlify
from struct import Struct, pack
import codecs
import io
from struct import pack
import numpy as np
import math
import argparse
import glob
import pymorton
import liblas

from lopocs.database import Session


def get_infos(files):
    infos = {}
    paths = glob.glob(files)
    npoints = 0

    xmin = float('inf')
    ymin = float('inf')
    zmin = float('inf')

    xmax = 0
    ymax = 0
    zmax = 0

    for path in paths:
        lasfile = liblas.file.File(path, mode='r')

        bbox_min = lasfile.header.get_min()
        bbox_max = lasfile.header.get_max()

        if bbox_min[0] < xmin:
            xmin = bbox_min[0]

        if bbox_min[1] < ymin:
            ymin = bbox_min[1]

        if bbox_min[2] < zmin:
            zmin = bbox_min[2]

        if bbox_max[0] > xmax:
            xmax = bbox_max[0]

        if bbox_max[1] > ymax:
            ymax = bbox_max[1]

        if bbox_max[2] > zmax:
            zmax = bbox_max[2]

        npoints += lasfile.header.get_count()

    infos['npoints'] = npoints
    infos['xmin'] = xmin
    infos['ymin'] = ymin
    infos['zmin'] = zmin
    infos['xmax'] = xmax
    infos['ymax'] = ymax
    infos['zmax'] = zmax
    infos['dx'] = xmax-xmin
    infos['dy'] = ymax-ymin
    infos['dz'] = zmax-zmin
    infos['volume'] = infos['dx']*infos['dy']*infos['dz']
    infos['density'] = npoints / infos['volume']

    return infos


def regular_grid(infos, pa_volume):

    # size of patch side in m
    pa_side = math.pow(pa_volume, 1/3)

    # number of cells for each dimensions
    nx = math.ceil(infos['dx'] / pa_side)
    ny = math.ceil(infos['dy'] / pa_side)
    nz = math.ceil(infos['dz'] / pa_side)

    # number of cells for a regular grid based on 4^x
    n = nx*ny
    n_regular = int(math.sqrt(math.pow(2, math.ceil(math.log(n)/math.log(2)))))
    pa_volume_regular = infos['volume'] / n_regular
    pa_side_regular = math.pow(pa_volume_regular, 1/3)

    # rest
    restx = (infos['dx'] - (n_regular-1)*pa_side_regular)/(n_regular-1)
    resty = (infos['dy'] - (n_regular-1)*pa_side_regular)/(n_regular-1)
    restz = (infos['dz'] - (n_regular-1)*pa_side_regular)/(n_regular-1)

    c = 0
    for i in range(0, n_regular):
        for j in range(0, n_regular):
            #for k in range(0, nz):
            pa_minx = infos['xmin'] + i*(pa_side_regular+restx)
            pa_miny = infos['ymin'] + j*(pa_side_regular+resty)
            #pa_minz = infos['zmin'] + k*(pa_side_regular+restz)
            pa_minz = infos['zmin'] #+ k*(pa_side_regular+restz)

            dx = pa_side_regular + restx
            dy = pa_side_regular + resty
            #dz = pa_side_regular + restz
            dz = infos['dz']

            c += 1
            print("{0}/{1}\r".format(c, n_regular*n_regular), end='')

            yield [pa_minx, pa_miny, pa_minz, dx, dy, dz, i, j]


def morton_revert_code(infos, cell):

    mcode = pymorton.interleave2(cell[6], cell[7])

    mcode_str = "{0:b}".format(mcode)
    nfill = 16-len(mcode_str)
    mcode_str = ("0"*nfill) + mcode_str

    mcode_str_revert = mcode_str[::-1]
    mcode_revert = int(mcode_str_revert, 2)

    return mcode_revert


def store_grid(infos, grid_gen):

    # create a table for the grid with a morton code for each cell
    sql = ("drop table if exists grid;"
           "create table grid("
           "id serial,"
           "points pcpatch(10),"
           "revert_morton integer,"
           "i integer, j integer)")
    Session.db.cursor().execute(sql)

    for cell in grid_gen:
        # store a cell
        p0b = np.array([cell[0], cell[1], cell[2]])
        p0u = np.array([cell[0], cell[1], cell[2]+cell[5]])

        p1b = np.array([cell[0]+cell[3], cell[1], cell[2]])
        p1u = np.array([cell[0]+cell[3], cell[1], cell[2]+cell[5]])

        p2b = np.array([cell[0]+cell[3], cell[1]+cell[4], cell[2]])
        p2u = np.array([cell[0]+cell[3], cell[1]+cell[4], cell[2]+cell[5]])

        p3b = np.array([cell[0], cell[1]+cell[4], cell[2]])
        p3u = np.array([cell[0], cell[1]+cell[4], cell[2]+cell[5]])

        p4 = np.array([cell[0]+cell[3]/2, cell[1]+cell[4]/2, cell[2]+cell[5]/2])

        patch = np.array([p0b, p0u, p1b, p1u, p2b, p2u, p3b, p3u, p4])

        pa_header = pack('<b3I', *[1, 10, 0, len(patch)])
        point_struct = Struct('<3d')
        pack_point = point_struct.pack

        points = []
        for pt in patch:
            points.append(pack_point(*pt))
        hexa = codecs.encode(pa_header + b''.join(points), 'hex').decode()

        morton_revert = morton_revert_code(infos, cell)

        rows = [str(morton_revert), hexa, str(cell[6]), str(cell[7])]
        Session.db.cursor().copy_from(
            io.StringIO('\t'.join(rows)), 'grid',
            columns=('revert_morton', 'points', 'i', 'j'))


if __name__ == '__main__':

    # arg parse
    descr = 'Build a regular grid with a revert morton code for each cell'
    parser = argparse.ArgumentParser(description=descr)

    cfg_help = 'configuration file for the database'
    parser.add_argument('cfg', metavar='cfg', type=str, help=cfg_help)

    pa_size_help = 'mean size of a patch to deduce the volume in m3'
    parser.add_argument('pa_size', metavar='pa_size', type=float, help=pa_size_help)

    files_help = 'list of files where we want to build the grid (regex)'
    parser.add_argument('files', metavar='files', type=str, help=files_help)

    args = parser.parse_args()

    # open config file
    ymlconf_db = None
    with open(args.cfg, 'r') as f:
        try:
            ymlconf_db = yaml.load(f)['flask']
        except:
            print("ERROR: ", sys.exc_info()[0])
            f.close()
            sys.exit()

    app = type('', (), {})()
    app.config = ymlconf_db

    # open database
    Session.init_app(app)

    # extract infos from files
    infos = get_infos(args.files)
    print(infos)

    # compute the volume patch in m3 according to the mean patch size
    pa_volume = args.pa_size/infos['density']

    # build the regular grid as a generator
    grid_gen = regular_grid(infos, pa_volume)

    # store the grid in database
    store_grid(infos, grid_gen)
