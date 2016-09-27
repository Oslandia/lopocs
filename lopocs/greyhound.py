# -*- coding: utf-8 -*-
import json
from flask import Response

from .database import Session
from . import utils
from .utils import Dimension, Schema, decimal_default, list_from_str
from .utils import GreyhoundReadSchema, GreyhoundInfoSchema
from .conf import Config

class GreyhoundInfo(object):

    def run(self):
        # a little faster than boundingbox()
        # box = Session.boundingbox()
        box = Session.boundingbox2()

        # approximate but far faster than Session.numpoints()
        # npoints = Session.numpoints()
        npoints = Session.approx_row_count() * Session.patch_size()

        srs = Session.srs()
        schema_json = GreyhoundInfoSchema().json()

        info = json.dumps( {
            "baseDepth" : 0,
            "bounds" : [box['xmin'], box['ymin'], box['zmin'],
                box['xmax'], box['ymax'], box['zmax']],
            "boundsConforming" : [box['xmin'], box['ymin'], box['zmin'],
                box['xmax'], box['ymax'], box['zmax']],
            "numPoints" : npoints,
            "schema" : schema_json,
            "srs" : srs,
            "type" : "octree"}, default = decimal_default )

        resp = Response(info)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Content-Type'] = 'text/plain'
        return resp

class GreyhoundRead(object):

    def run(self, args):

        read = ""

        offset = list_from_str(args['offset'])
        box = list_from_str(args['bounds'])

        read = Session.get_points(box, GreyhoundReadSchema().dims, offset,
            args['scale'], args['depthEnd'] - 8 - 1)

        resp = Response(read)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Content-Type'] = 'application/octet-stream'
        return resp

class GreyhoundHierarchy(object):

    def run(self, args):
        lod_min = args['depthBegin'] - 8  # greyhound start to 8

        lod_max = args['depthEnd'] - 8 - 1  # greyhound start to 8 and non inclusive
        if lod_max > (Config.DEPTH-1):
            lod_max = Config.DEPTH-1

        bbox = list_from_str(args['bounds'])

        filename = ("{0}_{1}_{2}_{3}.hcy"
                    .format(Session.dbname, lod_min, lod_max,
                            '_'.join(str(e) for e in bbox)))
        cached_hcy = utils.read_hierarchy_in_cache(filename)

        if cached_hcy:
            resp = Response(json.dumps(cached_hcy))
        else:
            new_hcy = utils.build_hierarchy_from_pg(Session, lod_max, bbox,
                                                    lod_min, Config.LIMIT)
            utils.write_hierarchy_in_cache(new_hcy, filename)
            resp = Response(json.dumps(new_hcy))

        #resp = Response(json.dumps(self.fake_hierarchy(0, 6, 10000)))

        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Content-Type'] = 'text/plain'

        return resp

    def fake_hierarchy(self, begin, end, npatchs):
        p = {}
        begin = begin + 1

        if begin != end:
            p['n'] = npatchs
            #p['n'] = 500*1000

            if begin != (end-1):
                p['nwu'] = self.fake_hierarchy(begin, end, npatchs)
                p['nwd'] = self.fake_hierarchy(begin, end, npatchs)
                p['neu'] = self.fake_hierarchy(begin, end, npatchs)
                p['ned'] = self.fake_hierarchy(begin, end, npatchs)
                p['swu'] = self.fake_hierarchy(begin, end, npatchs)
                p['swd'] = self.fake_hierarchy(begin, end, npatchs)
                p['seu'] = self.fake_hierarchy(begin, end, npatchs)
                p['sed'] = self.fake_hierarchy(begin, end, npatchs)

        return p
