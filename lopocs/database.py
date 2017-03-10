# -*- coding: utf-8 -*-
from functools import lru_cache
from multiprocessing import cpu_count

import psycopg2.extras
import psycopg2.extensions
from psycopg2.pool import ThreadedConnectionPool
from osgeo.osr import SpatialReference

from . import utils
from .potreeschema import pcschema


psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)


class LopocsException(Exception):
    pass


class Session():
    """
    Session object used as a global connection object to the db

    """
    db = None
    cache_pcid = {}

    @classmethod
    @lru_cache(maxsize=1)
    def table_list(cls):
        results = cls.query("""
            select concat(schema, '.', "table") as table, "column", srid
            from pointcloud_columns
        """)
        return {(res[0], res[1]): res[2] for res in results}

    @classmethod
    def init_app(cls, app):
        """
        Initialize db session lazily
        """
        query_con = ("postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:"
                     "{PG_PORT}/{PG_NAME}"
                     .format(**app.config))
        cls.pool = ThreadedConnectionPool(1, cpu_count(), query_con)
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

    @property
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
        return self.query(sql)[0][0]

    @property
    def patch_size(self):
        sql = (
            "select pc_summary({})::json->'npts' as npts from {} limit 1"
            .format(self.column, self.table)
        )
        return self.query(sql)[0][0]

    @property
    @lru_cache(maxsize=1)
    def max_patchs_per_query(self):
        sql = """
            select max_patchs_per_query
            from pointcloud_lopocs
            where tablename = %s limit 1
        """
        value = self.query(sql, (self.table, ))[0][0]
        return value

    @property
    def numpoints(self):
        sql = """
            select sum(pc_numpoints({}))
            from {}
        """.format(self.column, self.table)
        return self.query(sql)[0][0]

    @property
    def boundingbox(self):
        sql = """
            select bbox
            from pointcloud_lopocs
            where tablename = %s limit 1
        """
        res = self.query(sql, (self.table, ))
        if not res:
            return ''
        return res[0][0]

    def compute_boundingbox(self):
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
        bb_z = self.query(sql)[0]

        bb = {}
        bb.update(extent_2d)
        bb['zmin'] = float(bb_z[0])
        bb['zmax'] = float(bb_z[1])

        return bb

    def boundingbox2d(self):
        sql = (
            "SELECT ST_Extent({}::geometry) as table_extent from {}"
            .format(self.column, self.table)
        )
        bb = self.query(sql)[0][0]
        bb_xy = utils.list_from_str_box(bb)

        bb = {}
        bb['xmin'] = bb_xy[0]
        bb['ymin'] = bb_xy[1]
        bb['xmax'] = bb_xy[2]
        bb['ymax'] = bb_xy[3]

        return bb

    @property
    def srsid(self):
        return self.table_list()[(self.table, self.column)]

    @property
    def srs(self):
        sr = SpatialReference()
        sr.ImportFromEPSG(self.srsid)
        return sr.ExportToWkt()

    def schema(self):
        sql = """
            select pc_summary({})::json->'dims' as srsid
            from {}
            limit 1
        """.format(self.column, self.table)
        schema = self.query(sql)[0][0]
        return schema

    def output_pcid(self, scale):
        if (self.table, scale) in self.cache_pcid:
            return self.cache_pcid[(self.table, scale)]
        sql = """
            select pcid from pointcloud_lopocs
            where tablename = %s and scale = %s
        """
        pcid = self.query(sql, (self.table, scale))[0][0]
        self.cache_pcid[(self.table, scale)] = pcid
        return pcid

    @classmethod
    def create_pointcloud_lopocs_table(cls):
        """
        Create a metadata table that stores a link between an output schema
        for a given table (to be used by the couple greyhound/potree)
        """
        cls.execute("""
            create table if not exists pointcloud_lopocs (
                tablename varchar
                , pcid integer references pointcloud_formats(pcid) on delete cascade
                , scale float
                , max_patchs_per_query integer default 4096
                , bbox jsonb
                , primary key (tablename, pcid)
                , constraint uk_pointcloud_lopocs_table_scale unique (tablename, scale)
            )
            """)

    def load_lopocs_metadata(self, table, scale, srid, compression='none'):
        """
        Load schema used to stream patches with greyhound
        """
        fullbbox = self.compute_boundingbox()
        bbox = [fullbbox['xmin'], fullbbox['ymin'], fullbbox['zmin'],
                fullbbox['xmax'], fullbbox['ymax'], fullbbox['zmax']]

        x_offset = bbox[0] + (bbox[3] - bbox[0]) / 2
        y_offset = bbox[1] + (bbox[4] - bbox[1]) / 2
        z_offset = bbox[2] + (bbox[5] - bbox[2]) / 2

        x_offset = float("{0:.3f}".format(x_offset))
        y_offset = float("{0:.3f}".format(y_offset))
        z_offset = float("{0:.3f}".format(z_offset))

        # check if schema already exists
        res = Session.query(
            """ select pcid from pointcloud_formats
                where srid = %s and schema = %s
            """, (srid, pcschema.format(**locals()))
        )
        if not res:
            # insert schema
            res = self.query(
                """ with tmp as (
                        select max(pcid) + 1 as pcid
                        from pointcloud_formats
                    )
                    insert into pointcloud_formats
                    select pcid, %s, %s from tmp
                    returning pcid
                """, (srid, pcschema.format(**locals()))
            )

        pcid = res[0][0]

        # update entries in pointcloud_lopocs
        self.execute("""
            delete from pointcloud_lopocs where tablename = %s and pcid = %s;
            insert into pointcloud_lopocs (tablename, pcid, scale, bbox)
            values (%s, %s, %s, %s)
        """, (self.table, pcid, self.table, pcid, scale, fullbbox))

        # fill cache
        self.cache_pcid[(table, scale)] = pcid
        return pcid

    @classmethod
    def execute(cls, query, parameters=None):
        """Execute a pg statement without fetching results (use for DDL statement)
        """
        conn = cls.pool.getconn()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(query, parameters)
        cls.pool.putconn(conn)

    @classmethod
    def query(cls, query, parameters=None):
        """Performs a single query and fetch all results
        """
        conn = cls.pool.getconn()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(query, parameters)
        res = cur.fetchall()
        cls.pool.putconn(conn)
        return res
