# -*- coding: utf-8 -*-
from functools import lru_cache
from itertools import chain

from psycopg2 import connect
from psycopg2.extras import NamedTupleCursor
from osgeo.osr import SpatialReference

from . import utils
from .potreeschema import pcschema


class LopocsException(Exception):
    pass


class Session():
    """
    Session object used as a global connection object to the db

    """
    db = None

    @classmethod
    def forkme(cls):
        cls.db = connect(cls.query_con)

    @classmethod
    @lru_cache(maxsize=1)
    def table_list(cls):
        results = cls.query("""
            select concat(schema, '.', "table") as table, "column" from pointcloud_columns
        """)
        return [(res.table, res.column) for res in results]

    @classmethod
    def init_app(cls, app):
        """
        Initialize db session lazily
        """
        query_con = ("postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:"
                     "{PG_PORT}/{PG_NAME}"
                     .format(**app.config))
        cls.query_con = query_con
        cls.db = connect(query_con, cursor_factory=NamedTupleCursor)

        # autocommit mode for performance (we don't need transaction)
        cls.db.autocommit = True

        # keep some configuration element
        cls.dbname = app.config["PG_NAME"]

    def __init__(self, table, column='pa'):
        """
        :param table: table name (with schema if needed) ex: public.mytable
        """
        if '.' not in table:
            self.table = 'public.{}'.format(table)
        else:
            self.table = table
        if (self.table, column) not in self.table_list():
            raise LopocsException('table or column does not exists')
        self.column = column

    def approx_row_count(self):
        schema, table = self.table.split('.')
        sql = """
            SELECT
                reltuples ::BIGINT AS approximate_row_count
            FROM pg_class
            JOIN pg_catalog.pg_namespace n
            ON n.oid = pg_class.relnamespace
            WHERE relname = '{}' and nspname = '{}'
        """.format(table, schema)
        return self.query_aslist(sql)[0]

    def patch_size(self):
        sql = (
            "select sum(pc_numpoints({})) from {} where id = 1"
            .format(self.column, self.table)
        )
        return self.query_aslist(sql)[0]

    def numpoints(self):
        sql = "select sum(pc_numpoints({})) from {}".format(self.column, self.table)
        raise Exception(sql)
        return self.query_aslist(sql)[0]

    def boundingbox(self):
        """
        It's faster to use st_extent to find x/y extent then to use
        pc_intersect to find the z extent than using pc_intersect for each
        dimension.
        """
        extent_2d = self.boundingbox2d()

        sql = """
            select
                min(pc_patchmin({0}, 'z')) as zmin
               ,max(pc_patchmax({0}, 'z')) as zmax
            from {1}
        """.format(self.column, self.table)
        bb_z = self.query_asdict(sql)[0]

        bb = {}
        bb.update(extent_2d)
        bb['zmin'] = float(bb_z['zmin'])
        bb['zmax'] = float(bb_z['zmax'])

        return bb

    def boundingbox2d(self):
        sql = (
            "SELECT ST_Extent({}::geometry) as table_extent from {}"
            .format(self.column, self.table)
        )
        bb = self.query_aslist(sql)[0]
        bb_xy = utils.list_from_str_box(bb)

        bb = {}
        bb['xmin'] = bb_xy[0]
        bb['ymin'] = bb_xy[1]
        bb['xmax'] = bb_xy[2]
        bb['ymax'] = bb_xy[3]

        return bb

    def srsid(self):
        sql = """
            select pc_summary({})::json->'srid' as srsid from {} limit 1
        """.format(self.column, self.table)
        return self.query_aslist(sql)[0]

    def srs(self):
        sr = SpatialReference()
        sr.ImportFromEPSG(self.srsid())
        return sr.ExportToWkt()

    def schema(self):
        sql = """
            select pc_summary({})::json->'dims' as srsid from {} limit 1
        """.format(self.column, self.table)
        schema = self.query_aslist(sql)[0]
        return schema

    @property
    def output_pcid(self):
        sql = "select pcid from pointcloud_streaming_schemas where tablename = %s"
        schema_pcid = self.query_aslist(sql, (self.table,))[0]
        return schema_pcid

    @classmethod
    def create_pointcloud_streaming_table(cls):
        """
        Create a metadata table that stores a link between an output schema
        for a given table (to be used by the couple greyhound/potree)
        """
        cls.execute("""
            create table if not exists pointcloud_streaming_schemas (
                tablename varchar unique primary key
                ,pcid integer references pointcloud_formats(pcid) on delete cascade
            )
            """)

    def load_streaming_schema(self, table, bbox, scale, srid, compression='none'):
        """
        Load schema used to stream patches with greyhound
        """
        x_offset = bbox[0] + (bbox[3] - bbox[0]) / 2
        y_offset = bbox[1] + (bbox[4] - bbox[1]) / 2
        z_offset = bbox[2] + (bbox[5] - bbox[2]) / 2

        x_offset = float("{0:.3f}".format(x_offset))
        y_offset = float("{0:.3f}".format(y_offset))
        z_offset = float("{0:.3f}".format(z_offset))

        # check if schema already exists
        res = Session.query_aslist(
            """ select pcid from pointcloud_formats
                where srid = %s and schema = %s
            """, (srid, pcschema.format(**locals()))
        )
        if not res:
            # insert schema
            res = self.query_aslist(
                """ with tmp as (
                        select max(pcid) + 1 as pcid
                        from pointcloud_formats
                    )
                    INSERT INTO pointcloud_formats
                    SELECT pcid, %s, %s from tmp
                    returning pcid
                """, (srid, pcschema.format(**locals()))
            )

        pcid = res[0]

        # insert new entry in pointcloud_streaming_schemas
        self.execute("""
            INSERT INTO pointcloud_streaming_schemas (tablename, pcid) VALUES (%s, %s)
        """, (self.table, pcid))

        return pcid

    @classmethod
    def execute(cls, query, parameters=None):
        """Execute a pg statement without fetching results (use for DDL statement)
        """
        cur = cls.db.cursor()
        cur.execute(query, parameters)

    @classmethod
    def query(cls, query, parameters=None):
        """Performs a single query and fetch all results
        """
        cur = cls.db.cursor()
        cur.execute(query, parameters)
        return cur.fetchall()

    @classmethod
    def _query(cls, query, parameters=None):
        """Performs a query and yield results
        """
        cur = cls.db.cursor()
        cur.execute(query, parameters)
        if not cur.rowcount:
            return []
        for row in cur:
            yield row

    @classmethod
    def query_asdict(cls, query, parameters=None):
        """Iterates over results and returns namedtuples
        """
        return [
            line._asdict()
            for line in cls._query(query, parameters=parameters)
        ]

    @classmethod
    def query_aslist(cls, query, parameters=None):
        """Iterates over results and returns values in a flat list
        (usefull if one column only)
        """
        return list(chain(*cls._query(query, parameters=parameters)))
