# -*- coding: utf-8 -*-
from flask_restplus import Api, Resource, reqparse

from . import greyhound
from . import threedtiles

api = Api(version='0.1', title='LOPoCS API',
          description='API for accessing LOPoCS',)


# -----------------------------------------------------------------------------
# basic api
# -----------------------------------------------------------------------------
infos_ns = api.namespace('infos/',
                         description='Information about LOPoCS')


@infos_ns.route("/global")
class InfosGlobal(Resource):

    def get(self):
        return "Light OpenSource PointCloud Server / Oslandia"


@infos_ns.route("/contact")
class InfosContact(Resource):

    def get(self):
        return "infos+li3ds@oslandia.com"


@infos_ns.route("/online")
class InfosOnline(Resource):

    def get(self):
        return "Congratulation, LOPoCS is online!!!"

# -----------------------------------------------------------------------------
# greyhound api
# -----------------------------------------------------------------------------
greyhound_ns = api.namespace('greyhound/',
                             description='Greyhound Potree Loader')


# info
@greyhound_ns.route("/info")
class Info(Resource):

    def get(self):
        return greyhound.GreyhoundInfo().run()

# read
greyhound_read_parser = reqparse.RequestParser()
greyhound_read_parser.add_argument('depthBegin', type=int, required=True)
greyhound_read_parser.add_argument('depthEnd', type=int, required=True)
greyhound_read_parser.add_argument('bounds', type=str, required=True)
greyhound_read_parser.add_argument('schema', type=str, required=True)
greyhound_read_parser.add_argument('scale', type=float, required=True)
greyhound_read_parser.add_argument('offset', type=str, required=True)
greyhound_read_parser.add_argument('compress', type=bool, required=True)


@greyhound_ns.route("/read")
class Read(Resource):

    @api.expect(greyhound_read_parser, validate=True)
    def get(self):
        args = greyhound_read_parser.parse_args()
        return greyhound.GreyhoundRead().run(args)

# hierarchy
greyhound_hierarchy_parser = reqparse.RequestParser()
greyhound_hierarchy_parser.add_argument('depthBegin', type=int, required=True)
greyhound_hierarchy_parser.add_argument('depthEnd', type=int, required=True)
greyhound_hierarchy_parser.add_argument('bounds', type=str, required=True)


@greyhound_ns.route("/hierarchy")
class Hierarchy(Resource):

    def get(self):
        args = greyhound_hierarchy_parser.parse_args()
        return greyhound.GreyhoundHierarchy().run(args)

# -----------------------------------------------------------------------------
# threedtiles api
# -----------------------------------------------------------------------------
threedtiles_ns = api.namespace('3dtiles/',
                               description='3DTiles format')


# info
@threedtiles_ns.route("/info")
class ThreeDTilesInfo(Resource):

    def get(self):
        return threedtiles.ThreeDTilesInfo().run()


# read
threedtiles_read_parser = reqparse.RequestParser()
threedtiles_read_parser.add_argument('v', type=float, required=True)
threedtiles_read_parser.add_argument('bounds', type=str, required=True)
threedtiles_read_parser.add_argument('lod', type=int, required=True)
threedtiles_read_parser.add_argument('offsets', type=str, required=True)
threedtiles_read_parser.add_argument('scale', type=float, required=True)


@threedtiles_ns.route("/read.pnts")
class ThreeDTilesRead(Resource):

    @api.expect(threedtiles_read_parser, validate=True)
    def get(self):
        args = threedtiles_read_parser.parse_args()
        return threedtiles.ThreeDTilesRead().run(args)
