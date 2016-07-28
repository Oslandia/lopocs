# -*- coding: utf-8 -*-
import time
from itertools import chain
from psycopg2 import connect
from psycopg2.extras import NamedTupleCursor
from osgeo.osr import SpatialReference

from .pgpointcloud import PgPointCloud
from . import utils

def timing(f):
    def wrap(*args):
        t1 = time.time()
        ret = f(*args)
        t2 = time.time()
        print('function took %0.3f ms' % ((t2-t1)*1000.0))
        return ret
    return wrap

class Session():
    """
    Session object used as a global connection object to the db

    # FIXME: handle disconnection
    """
    db = None

    @classmethod
    #@timing
    def approx_row_count(cls):
        return cls.query_aslist(
                "SELECT reltuples ::BIGINT AS approximate_row_count "
                "FROM pg_class WHERE relname = '{0}';"
                .format(cls.table))[0]

    @classmethod
    #@timing
    def patch_size(cls):
        return cls.query_aslist(
                "select sum(pc_numpoints({0})) from {1} where id =1"
                .format(cls.column, cls.table))[0]

    @classmethod
    #@timing
    def numpoints(cls):
        return cls.query_aslist(
            "select sum(pc_numpoints({0})) from {1}"
            .format(cls.column, cls.table))[0]

    @classmethod
    #@timing
    def boundingbox(cls):
        return cls.query_asdict(
            "select min(pc_patchmin({0}, 'x')) as xmin"
            ",max(pc_patchmax({0}, 'x')) as xmax"
            ",min(pc_patchmin({0}, 'y')) as ymin"
            ",max(pc_patchmax({0}, 'y')) as ymax"
            ",min(pc_patchmin({0}, 'z')) as zmin"
            ",max(pc_patchmax({0}, 'z')) as zmax"
            " from {1}"
            .format(cls.column, cls.table))[0]

    @classmethod
    #@timing
    def boundingbox2(cls):
        bb = cls.query_aslist(
                "SELECT ST_Extent({0}::geometry) as table_extent FROM {1};"
                .format(cls.column, cls.table))[0]
        bb_xy = utils.list_from_str_box(bb)

        bb_z = cls.query_asdict(
            "select "
            "min(pc_patchmin({0}, 'z')) as zmin"
            ",max(pc_patchmax({0}, 'z')) as zmax"
            " from {1}"
            .format(cls.column, cls.table))[0]

        bb = {}
        bb['xmin'] = bb_xy[0]
        bb['ymin'] = bb_xy[1]
        bb['zmin'] = bb_z['zmin']
        bb['xmax'] = bb_xy[2]
        bb['ymax'] = bb_xy[3]
        bb['zmax'] = bb_z['zmax']

        return bb

    @classmethod
    def srsid(cls):
        return cls.query_aslist(
            "select pc_summary({0})::json->'srid' as srsid from {1} where id = 1"
            .format(cls.column, cls.table))[0]

    @classmethod
    #@timing
    def srs(cls):
        sr = SpatialReference()
        sr.ImportFromEPSG( cls.srsid() )
        return sr.ExportToWkt()

    @classmethod
    def schema(cls):
        schema = cls.query_aslist(
            "select pc_summary({0})::json->'dims' as srsid from {1} where id = 1"
            .format(cls.column, cls.table))[0]
        return schema

    @classmethod
    def get_points(cls, box, dims, offset, scale, lod):
        return PgPointCloud(cls).get_points(box, dims, offset, scale, lod)

    @classmethod
    def get_pointn(cls, n, box, dims, offset, scale):
        """
        Return the nth point for each PC_PATCH intersecting with the box
        """
        return PgPointCloud(cls).get_pointn(box, dims, offset, scale)

    @classmethod
    def query(cls, query, parameters=None):
        """Performs a query and yield results
        """
        cur = cls.db.cursor()
        cur.execute(query, parameters)
        if not cur.rowcount:
            return None
        for row in cur:
            yield row

    @classmethod
    def query_asdict(cls, query, parameters=None):
        """Iterates over results and returns namedtuples
        """
        return [
            line._asdict()
            for line in cls.query(query, parameters=parameters)
        ]

    @classmethod
    def query_aslist(cls, query, parameters=None):
        """Iterates over results and returns values in a flat list
        (usefull if one column only)
        """
        return list(chain(*cls.query(query, parameters=parameters)))

    @classmethod
    def init_app(cls, app):
        """
        Initialize db session lazily
        """
        cls.db = connect(
            "postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_NAME}"
            .format(**app.config),
            cursor_factory=NamedTupleCursor,
        )
        # autocommit mode for performance (we don't need transaction)
        cls.db.autocommit = True

        # keep some configuration element
        cls.column = app.config["PG_COLUMN"]
        cls.table = app.config["PG_TABLE"]
