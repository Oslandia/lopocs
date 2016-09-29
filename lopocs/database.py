# -*- coding: utf-8 -*-

from itertools import chain
from psycopg2 import connect
from psycopg2.extras import NamedTupleCursor
from osgeo.osr import SpatialReference

from . import utils


class Session():
    """
    Session object used as a global connection object to the db

    # FIXME: handle disconnection
    """
    db = None

    @classmethod
    def approx_row_count(cls):
        if '.' in cls.table:
            schema, table = cls.table.split('.')
        else:
            table, schema = cls.table, 'public'

        sql = ("SELECT reltuples ::BIGINT AS approximate_row_count "
               "FROM pg_class JOIN pg_catalog.pg_namespace n "
               "ON n.oid = pg_class.relnamespace "
               "WHERE relname = '{0}' and nspname = '{1}' "
               .format(table, schema))

        return cls.query_aslist(sql)[0]

    @classmethod
    def patch_size(cls):
        sql = ("select sum(pc_numpoints({0})) from {1} where id =1"
               .format(cls.column, cls.table))
        return cls.query_aslist(sql)[0]

    @classmethod
    def numpoints(cls):
        sql = ("select sum(pc_numpoints({0})) from {1}"
               .format(cls.column, cls.table))
        return cls.query_aslist(sql)[0]

    @classmethod
    def boundingbox(cls):
        """
        It's faster to use st_extent to find x/y extent then to use
        pc_intersect to find the z extent than using pc_intersect for each
        dimension.
        """

        extent_2d = cls.boundingbox2d()

        sql = ("select "
               "min(pc_patchmin({0}, 'z')) as zmin"
               ",max(pc_patchmax({0}, 'z')) as zmax"
               " from {1}".format(cls.column, cls.table))
        bb_z = cls.query_asdict(sql)[0]

        bb = {}
        bb.update(extent_2d)
        bb['zmin'] = float(bb_z['zmin'])
        bb['zmax'] = float(bb_z['zmax'])

        return bb

    @classmethod
    def boundingbox2d(cls):
        sql = ("SELECT ST_Extent({0}::geometry) as table_extent FROM {1};"
               .format(cls.column, cls.table))
        bb = cls.query_aslist(sql)[0]
        bb_xy = utils.list_from_str_box(bb)

        bb = {}
        bb['xmin'] = bb_xy[0]
        bb['ymin'] = bb_xy[1]
        bb['xmax'] = bb_xy[2]
        bb['ymax'] = bb_xy[3]

        return bb

    @classmethod
    def srsid(cls):
        sql = ("select pc_summary({0})::json->'srid' as srsid from {1} "
               "where id = 1"
               .format(cls.column, cls.table))
        return cls.query_aslist(sql)[0]

    @classmethod
    def srs(cls):
        sr = SpatialReference()
        sr.ImportFromEPSG(cls.srsid())
        return sr.ExportToWkt()

    @classmethod
    def schema(cls):
        sql = ("select pc_summary({0})::json->'dims' as srsid from {1} "
               "where id = 1"
               .format(cls.column, cls.table))
        schema = cls.query_aslist(sql)[0]
        return schema

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

        query_con = ("postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:"
                     "{PG_PORT}/{PG_NAME}"
                     .format(**app.config))
        cls.db = connect(query_con, cursor_factory=NamedTupleCursor,)

        # autocommit mode for performance (we don't need transaction)
        cls.db.autocommit = True

        # keep some configuration element
        cls.dbname = app.config["PG_NAME"]
        cls.column = app.config["PG_COLUMN"]
        cls.table = app.config["PG_TABLE"]
