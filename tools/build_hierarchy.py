# -*- coding: utf-8 -*-

import yaml
import argparse
import os
import sys
import json

from lopocs.database import Session
from lopocs import utils

if __name__ == '__main__':

    # arg parse
    descr = 'Process a database to build an octree hierarchy for potree'
    parser = argparse.ArgumentParser(description=descr)

    cfg_help = 'configuration file'
    parser.add_argument('cfg', metavar='cfg', type=str, help=cfg_help)

    output_dir_help = "output directory"
    parser.add_argument('outdir', metavar='outdir', type=str, help=cfg_help)

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

    # build the hierarchy
    fullbbox = Session.boundingbox2()
    bbox = [fullbbox['xmin'], fullbbox['ymin'], fullbbox['zmin'],
            fullbbox['xmax'], fullbbox['ymax'], fullbbox['zmax']]

    limit = ymlconf_db['LIMIT']
    lod_min = 0
    lod_max = ymlconf_db['DEPTH']-1
    bbox_str = '_'.join(str(e) for e in bbox)
    h = utils.build_hierarchy_from_pg(Session, lod_max, bbox, lod_min, limit)

    name = ("hierarchy_{0}.txt".format(ymlconf_db['PG_NAME']))
    path = os.path.join(args.outdir, name)
    f = open(path, 'w')
    f.write(json.dumps(h))
    f.close()
