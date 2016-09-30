# -*- coding: utf-8 -*-

import yaml
import sys
from struct import Struct, pack
import codecs
import io
from struct import pack
import numpy as np
import math
import argparse

from lopocs.database import Session


def get_infos():
    infos = {}
    infos.update(Session.boundingbox2d())

    sql = "select count(*) from {0}".format(Session.column)
    infos['npatchs'] = Session.query_aslist(sql)[0]

    infos['dx'] = infos['xmax'] - infos['xmin']
    infos['dy'] = infos['ymax'] - infos['ymin']
    #infos['dz'] = infos['zmax'] - infos['zmin']

    return infos


def compute_cell_parameters(infos):

    # number of cells for a regular grid based on 4^x
    n = infos['npatchs']
    n_side_regular = int(math.sqrt(math.pow(2, math.ceil(math.log(n)/math.log(2)))))

    #restx = (infos['dx'] - (n_side_regular-1)*pa_side_regular)/(n_regular-1)
    #resty = (infos['dy'] - (n_regular-1)*pa_side_regular)/(n_regular-1)
    #restz = (infos['dz'] - (n_regular-1)*pa_side_regular)/(n_regular-1)

    side_x_regular = infos['dx'] / n_side_regular
    side_y_regular = infos['dy'] / n_side_regular

    return [n_side_regular, side_x_regular, side_y_regular]


def regular_grid(infos, cell_params):

    # number of cells for a regular grid based on 4^x
    #n = infos['npatchs']
    #n_regular = int(math.sqrt(math.pow(2, math.ceil(math.log(n)/math.log(2)))))
    #pa_side_regular = math.sqrt(n_regular)

    ## rest
    #restx = (infos['dx'] - (n_regular-1)*pa_side_regular)/(n_regular-1)
    #resty = (infos['dy'] - (n_regular-1)*pa_side_regular)/(n_regular-1)
    #restz = (infos['dz'] - (n_regular-1)*pa_side_regular)/(n_regular-1)

    side_x = cell_params[1]
    side_y = cell_params[2]
    n_regular = cell_params[0]

    c = 0
    for i in range(0, n_regular):
        for j in range(0, n_regular):
            #for k in range(0, nz):
            pa_minx = infos['xmin'] + i*side_x
            pa_miny = infos['ymin'] + j*side_y
            ##pa_minz = infos['zmin'] + k*(pa_side_regular+restz)
            #pa_minz = infos['zmin'] #+ k*(pa_side_regular+restz)

            #dx = pa_side_regular + restx
            #dy = pa_side_regular + resty
            ##dz = pa_side_regular + restz
            #dz = infos['dz']

            c += 1
            print("{0}/{1}\r".format(c, n_regular*n_regular), end='')

            yield [pa_minx, pa_miny, 0.0, side_x, side_y, 1.0, i, j]


def interleave(n):
    n &= 0x0000ffff
    n = (n | (n << 8)) & 0x00FF00FF
    n = (n | (n << 4)) & 0x0F0F0F0F
    n = (n | (n << 2)) & 0x33333333
    n = (n | (n << 1)) & 0x55555555
    return n


def morton_revert_code(x, y):

    mcode = interleave(x) | (interleave(y) << 1)

    mcode_str = "{0:b}".format(mcode)
    nfill = 16-len(mcode_str)
    mcode_str = ("0"*nfill) + mcode_str

    mcode_str_revert = mcode_str[::-1]
    mcode_revert = int(mcode_str_revert, 2)

    return mcode_revert


def store_grid(grid_gen):

    pcid_schema = 3

    # create a table for the grid with a morton code for each cell
    sql = ("drop table if exists grid;"
           "create table grid("
           "id serial,"
           "cells pcpatch({0}),"
           "revert_morton integer,"
           "patchs_ids integer[],"
           "col integer, row integer)".format(pcid_schema))
    Session.db.cursor().execute(sql)

    for cell in grid_gen:
        # build a cell (cube with a center)
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

        pa_header = pack('<b3I', *[1, pcid_schema, 0, len(patch)])
        point_struct = Struct('<3d')
        pack_point = point_struct.pack

        points = []
        for pt in patch:
            points.append(pack_point(*pt))
        hexa = codecs.encode(pa_header + b''.join(points), 'hex').decode()

        # compute a morton code for the cell
        morton_revert = morton_revert_code(cell[6], cell[7])

        # fill the database
        rows = [str(morton_revert), hexa, str(cell[6]), str(cell[7])]
        Session.db.cursor().copy_from(
            io.StringIO('\t'.join(rows)), 'grid',
            columns=('revert_morton', 'cells', 'col', 'row'))


def build_index_by_morton(infos, side_x, side_y):
    # add an index column
    sql = ("ALTER TABLE {0} drop column if exists morton;"
           "ALTER TABLE {0} add column morton integer"
           .format(Session.column)
           )
    Session.db.cursor().execute(sql)

    for n in range(0, infos['npatchs']):
        print("{0}/{1}\r".format(n, infos['npatchs']), end='')

        sql = ("select pc_patchmin({0}, 'x') as xmin, "
               "pc_patchmax({0}, 'x') as xmax, "
               "pc_patchmin({0}, 'y') as ymin, "
               "pc_patchmax({0}, 'y') as ymax "
               "from {1} where id = {2}"
               .format(Session.column, Session.table, n+1))
        res = Session.query_asdict(sql)[0]

        center_x = float(res['xmin']) + side_x/2
        center_y = float(res['ymin']) + side_y/2

        #col = math.floor((float(res['xmin']) - infos['xmin']) / side)
        #row = math.floor((float(res['ymin']) - infos['ymin']) / side)
        col = math.floor((center_x - infos['xmin']) / side_x)
        row = math.floor((center_y - infos['ymin']) / side_y)

        morton = morton_revert_code(col, row)

        sql = ("update pa set morton = {0}"
               " where id = {1}".format(morton, n+1))
        Session.db.cursor().execute(sql)


if __name__ == '__main__':

    # arg parse
    descr = 'Build a regular grid with a revert morton code for each cell'
    parser = argparse.ArgumentParser(description=descr)

    cfg_help = 'configuration file for the database'
    parser.add_argument('cfg', metavar='cfg', type=str, help=cfg_help)

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
    infos = get_infos()
    #print(infos)

    # compute cell parameters
    cell_params = compute_cell_parameters(infos)
    #print(cell_params)

    # build the regular grid as a generator
    save_grid = False
    if save_grid:
        grid_gen = regular_grid(infos, cell_params)
        store_grid(grid_gen)

    # associate a patch of data with a cell
    build_index_by_morton(infos, cell_params[1], cell_params[2])
