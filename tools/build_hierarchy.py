# -*- coding: utf-8 -*-

import yaml
import argparse
import os
import sys
import json

from lopocs.database import Session
from lopocs import greyhound
from lopocs import threedtiles

if __name__ == '__main__':

    # arg parse
    descr = 'Process a database to build an octree hierarchy for potree'
    parser = argparse.ArgumentParser(description=descr)

    cfg_help = 'configuration file'
    parser.add_argument('cfg', metavar='cfg', type=str, help=cfg_help)

    output_dir_help = "output directory"
    parser.add_argument('outdir', metavar='outdir', type=str, help=cfg_help)

    target_help = "Target for the hierarchy (greyhound or 3dtiles)"
    parser.add_argument('t', metavar='t', type=str, help=target_help)

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
    fullbbox = Session.boundingbox()
    bbox = [fullbbox['xmin'], fullbbox['ymin'], fullbbox['zmin'],
            fullbbox['xmax'], fullbbox['ymax'], fullbbox['zmax']]

    print(fullbbox)

    lod_min = 0
    lod_max = ymlconf_db['DEPTH']-1
    bbox_str = '_'.join(str(e) for e in bbox)

    if args.t == "greyhound":
        h = greyhound.build_hierarchy_from_pg(lod_max, bbox, lod_min)

        name = ("{0}_{1}_{2}_{3:.3f}_{4:.3f}_{5:.3f}_{6:.3f}_{7:.3f}_"
                "{8:.3f}.hcy"
                .format(ymlconf_db['PG_NAME'], lod_min, lod_max, bbox[0],
                        bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]))

        path = os.path.join(args.outdir, name)
        f = open(path, 'w')
        f.write(json.dumps(h))
        f.close()
    else:
        h = threedtiles.build_hierarchy_from_pg(lod_max, bbox, lod_min)
        name = "tileset.json"

        path = os.path.join(args.outdir, name)
        f = open(path, 'w')
        f.write(h)
        f.close()

#    print(h)
