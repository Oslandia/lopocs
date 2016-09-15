# -*- coding: utf-8 -*-
import json
from flask import Response

from .database import Session
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
            args['scale'], args['depthEnd'] - Config.DEPTH - 3)

        resp = Response(read)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Content-Type'] = 'application/octet-stream'
        return resp

class GreyhoundHierarchy(object):

    def run(self, args):
        if args['depthBegin'] == 8:
            npatchs = Session.approx_row_count()
            resp = Response(json.dumps(self.fake_hierarchy(0, Config.DEPTH+1, npatchs)))
        else:
            resp = Response(json.dumps(self.fake_hierarchy(0, 2, 0)))

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
