# -*- coding: utf-8 -*-
from flask_restplus import Api, Resource, reqparse

from . import greyhound
from . import threedtiles
from .database import Session

api = Api(version='0.1', title='LOPoCS API',
          description='API for accessing LOPoCS',)


# -----------------------------------------------------------------------------
# basic api
# -----------------------------------------------------------------------------
infos_ns = api.namespace('infos/', description='Information about LOPoCS')


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


# info
@infos_ns.route("/sources")
class Sources(Resource):

    def get(self):
        """List tables with pointcloud data
        """
        Session.table_list.cache_clear()
        resp = [{
            'table': table,
            'column': column,
            'srid': srid
        } for (table, column), srid in Session.table_list().items()]
        return resp

# -----------------------------------------------------------------------------
# greyhound api
# -----------------------------------------------------------------------------
ghd_ns = api.namespace('greyhound/', description='Greyhound Potree Loader')


ghd_info = reqparse.RequestParser()
ghd_info.add_argument('table', type=str, required=False, default='patchs')
ghd_info.add_argument('column', type=str, required=False, default='pa')


@ghd_ns.route("/info")
class Info(Resource):

    @api.expect(ghd_info, validate=True)
    def get(self):
        args = ghd_info.parse_args()
        return greyhound.GreyhoundInfo(args)

# read
ghd_read = reqparse.RequestParser()
ghd_read.add_argument('depthBegin', type=int, required=True)
ghd_read.add_argument('depthEnd', type=int, required=True)
ghd_read.add_argument('bounds', type=str, required=True)
ghd_read.add_argument('scale', type=float, required=True)
ghd_read.add_argument('offset', type=str, required=True)
ghd_read.add_argument('compress', type=bool, required=True)
ghd_read.add_argument('table', type=str, required=False, default='patchs')
ghd_read.add_argument('column', type=str, required=False, default='pa')


@ghd_ns.route("/read")
class Read(Resource):

    @api.expect(ghd_read, validate=True)
    def get(self):
        args = ghd_read.parse_args()
        return greyhound.GreyhoundRead(args)

# hierarchy
ghd_hierarchy = reqparse.RequestParser()
ghd_hierarchy.add_argument('depthBegin', type=int, required=True)
ghd_hierarchy.add_argument('depthEnd', type=int, required=True)
ghd_hierarchy.add_argument('bounds', type=str, required=True)
ghd_hierarchy.add_argument('table', type=str, required=False, default='patchs')
ghd_hierarchy.add_argument('column', type=str, required=False, default='pa')


@ghd_ns.route("/hierarchy")
class Hierarchy(Resource):

    @api.expect(ghd_hierarchy, validate=True)
    def get(self):
        args = ghd_hierarchy.parse_args()
        return greyhound.GreyhoundHierarchy(args)

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
threedtiles_read = reqparse.RequestParser()
threedtiles_read.add_argument('v', type=float, required=True)
threedtiles_read.add_argument('bounds', type=str, required=True)
threedtiles_read.add_argument('lod', type=int, required=True)
threedtiles_read.add_argument('offsets', type=str, required=True)
threedtiles_read.add_argument('scale', type=float, required=True)


@threedtiles_ns.route("/read.pnts")
class ThreeDTilesRead(Resource):

    @api.expect(threedtiles_read, validate=True)
    def get(self):
        args = threedtiles_read.parse_args()
        return threedtiles.ThreeDTilesRead().run(args)
