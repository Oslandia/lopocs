# -*- coding: utf-8 -*-
from flask import request
from flask_restplus import Api, Resource, fields, reqparse

from .database import Session
from . import greyhound

api = Api(
        version='0.1', title='LOPoCS API',
        description='API for accessing LOPoCS',
        )

# -----------------------------------------------------------------------------
# basic api
# -----------------------------------------------------------------------------
@api.route("/lopocs")
class Test(Resource):

    def get(self):
        return "Light OpenSource PointCloud Server / Oslandia / contact@oslandia.com"

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

@greyhound_ns.route("/hierarchy")
class Hierarchy(Resource):

    def get(self):
        args = greyhound_hierarchy_parser.parse_args()
        return greyhound.GreyhoundHierarchy().run(args)
