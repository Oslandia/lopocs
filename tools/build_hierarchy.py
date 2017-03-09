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

    baseurl_help = "Base URL of the lopocs instance to use"
    parser.add_argument('u', metavar='u', type=str, help=baseurl_help)

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
        h = greyhound.build_hierarchy_from_pg_mp(lod_max, bbox, lod_min)
        path = os.path.join(args.outdir, "potree.hcy")
        f = open(path, 'w')
        f.write(json.dumps(h))
        f.close()
    else:
        baseurl = args.u
        h = threedtiles.build_hierarchy_from_pg(baseurl, lod_max, bbox, lod_min)
        name = "tileset.json"

        path = os.path.join(args.outdir, name)
        f = open(path, 'w')
        f.write(h)
        f.close()

#    print(h)
