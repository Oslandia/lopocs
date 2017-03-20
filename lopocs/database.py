# -*- coding: utf-8 -*-
from multiprocessing import cpu_count
from collections import defaultdict

import psycopg2.extras
import psycopg2.extensions
from psycopg2.extras import Json
from psycopg2.pool import ThreadedConnectionPool
from osgeo.osr import SpatialReference

from .utils import iterable2pgarray, list_from_str_box, greyhound_types
from .potreeschema import create_pointcloud_schema

psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)


LOPOCS_TABLES_QUERY = """
create table if not exists pointcloud_lopocs (
    id serial primary key
    , schematable varchar
    , "column" varchar
    , srid integer
    , max_patches_per_query integer default 4096
    , max_points_per_patch integer default NULL
    , bbox jsonb
    , constraint uniq_table_col UNIQUE (schematable, "column")
    , constraint check_schematable_exists
        CHECK (to_regclass(schematable) is not null)
);
create table if not exists pointcloud_lopocs_outputs (
    id integer references pointcloud_lopocs(id) on delete cascade
    , pcid integer references pointcloud_formats(pcid) on delete cascade
    , scales float[3]
    , offsets float[3]
    , point_schema jsonb
    , stored boolean
    , bbox float[6]
    , constraint uniqschema UNIQUE (pcid, scales, offsets, point_schema)
);
-- trick to add a partial constraint
-- only one schema is used to store patches
create unique index if not exists uniqidx_pcid_stored
    on pointcloud_lopocs_outputs (pcid, stored) where (stored is true);
"""

# get a list of outputs formats available
LOPOCS_OUTPUTS_QUERY = """
select
    min(pl.schematable)
    , min(pl."column")
    , min(pl.srid)
    , min(pc.pcid)
    , array_agg(plo.pcid)
    , array_agg(plo.scales)
    , array_agg(plo.offsets)
    , array_agg(plo.point_schema)
    , array_agg(plo.bbox)
    , array_agg(plo.stored)
    , min(pl.max_patches_per_query)
    , min(pl.max_points_per_patch)
    , pl.bbox
from pointcloud_lopocs pl
join pointcloud_columns pc
    on concat(pc."schema", '.', pc."table") = pl.schematable
    and pc."column" = pl."column"
join pointcloud_lopocs_outputs plo on plo.id = pl.id
where
    to_regclass(schematable) is not null -- check if table still exists in pg catalog
group by pl.id, pl.bbox
"""


class LopocsException(Exception):
    pass


class LopocsTable():
    """
    Used to cache content of pointcloud_lopocs* tables and
    avoid roundtrips to the database.

    Outputs attribute looks like :
    outputs": [
        {
            "offsets": [728630.47, 4676727.02, 309.86],
            "scales": [0.01,0.01,0.01],
            "stored": true,
            "point_schema": [
                {
                    "type": "unsigned",
                    "name": "Intensity",
                    "size": 2
                },...
            ],
            "pcid": 1,
            "bbox": [xmin,ymin,zmin,xmax,ymax,zmax]
        },...
    ]
    """
    __slots__ = (
        'table', 'column', 'srid', 'pcid', 'outputs',
        'max_patches_per_query', 'max_points_per_patch', 'bbox'
    )

    def __init__(self, table, column, srid, pcid, outputs,
                 max_patches_per_query, max_points_per_patch, bbox):
        self.table = table
        self.column = column
        self.outputs = outputs
        self.srid = srid
        self.pcid = pcid
        self.max_patches_per_query = max_patches_per_query
        self.max_points_per_patch = max_points_per_patch
        self.bbox = bbox

    def filter_stored_output(self):
        '''
        Find and return the output corresponding to the stored patches
        '''
        return [
            output
            for output in self.outputs
            if output['stored']
        ][0]

    def asjson(self):
        '''
        return a json representation of this object
        '''
        return {
            'table': self.table,
            'column': self.column,
            'outputs': self.outputs,
            'srid': self.srid,
            'pcid': self.pcid,
            'max_patches_per_query': self.max_patches_per_query,
            'max_points_per_patch': self.max_points_per_patch,
            'bbox': self.bbox,
        }


class Session():
    """
    Session object used as a global connection object to the db

    ``catalog`` contains lopocs table cache
    catalog  = {
        ('public.table'): LopocsTableInstance
    }
    """
    db = None
    catalog = defaultdict(dict)

    @classmethod
    def clear_catalog(cls):
        cls.catalog.clear()

    @classmethod
    def fill_catalog(cls):
        """
        Get all output tables and fill the catalog
        Each output table should have :


        """
        keys = ('pcid', 'scales', 'offsets', 'point_schema', 'bbox', 'stored')
        results = cls.query(LOPOCS_OUTPUTS_QUERY)
        for res in results:
            cls.catalog[(res[0], res[1])] = LopocsTable(
                res[0], res[1], res[2], res[3],
                [
                    dict(zip(keys, values))
                    for values in zip(res[4], res[5], res[6], res[7], res[8], res[9])
                ],
                res[10], res[11], res[12]
            )

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

    def __init__(self, table, column):
        """
        Initialize a session for a given couple of table and column.

        :param table: table name (with schema prefixed) ex: public.mytable
        :param column: column name for patches
        """
        if (table, column) not in self.catalog:
            if not self.catalog:
                # catalog empty
                self.fill_catalog()
            if (table, column) not in self.catalog:
                raise LopocsException('table or column not found in database')

        self.lopocstable = self.catalog[(table, column)]
        self.table = table
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
    def numpoints(self):
        sql = """
            select sum(pc_numpoints({}))
            from {}
        """.format(self.column, self.table)
        return self.query(sql)[0][0]

    @property
    def boundingbox(self):
        return self.lopocstable.bbox

    @classmethod
    def compute_boundingbox(cls, table, column):
        """
        It's faster to use st_extent to find x/y extent then to use
        pc_intersect to find the z extent than using pc_intersect for each
        dimension.
        """
        sql = (
            "SELECT ST_Extent({}::geometry) as table_extent from {}"
            .format(column, table)
        )
        bb = cls.query(sql)[0][0]
        bb_xy = list_from_str_box(bb)

        extent = {}
        extent['xmin'] = bb_xy[0]
        extent['ymin'] = bb_xy[1]
        extent['xmax'] = bb_xy[2]
        extent['ymax'] = bb_xy[3]

        sql = """
            select
                min(pc_patchmin({0}, 'z')) as zmin
               ,max(pc_patchmax({0}, 'z')) as zmax
            from {1}
        """.format(column, table)
        bb_z = cls.query(sql)[0]

        bb = {}
        bb.update(extent)
        bb['zmin'] = float(bb_z[0])
        bb['zmax'] = float(bb_z[1])

        return bb

    @property
    def srsid(self):
        return self.lopocstable.srid

    @property
    def srs(self):
        sr = SpatialReference()
        sr.ImportFromEPSG(self.srsid)
        return sr.ExportToWkt()

    @classmethod
    def patch2greyhoundschema(cls, table, column):
        '''Returns json schema used by Greyhound
        with dimension types adapted.
        - https://github.com/hobu/greyhound/blob/master/doc/clientDevelopment.rst#schema
        - https://www.pdal.io/dimensions.html
        '''
        dims = cls.query("""
            select pc_summary({})::json->'dims' from {} limit 1
        """.format(column, table))[0][0]
        schema = []
        for dim in dims:
            schema.append({
                'size': dim['size'],
                'type': greyhound_types(dim['type']),
                'name': dim['name'],
            })
        return schema

    @classmethod
    def create_pointcloud_lopocs_table(cls):
        '''
        Create some meta tables that stores informations used by lopocs to
        stream patches in various formats
        '''
        cls.execute(LOPOCS_TABLES_QUERY)

    @classmethod
    def update_metadata(cls, table, column, srid, scale_x, scale_y, scale_z,
                        offset_x, offset_y, offset_z):
        '''
        Add an entry to the lopocs metadata tables to use.
        To be used after a fresh pc table creation.
        '''
        pcid = cls.query("""
            select pcid from pointcloud_columns
            where "schema" = %s and "table" = %s and "column" = %s
            """, (table.split('.')[0], table.split('.')[1], column)
        )[0][0]

        bbox = cls.compute_boundingbox(table, column)
        # compute bbox with offset and scale applied
        bbox_scaled = [0] * 6
        bbox_scaled[0] = (bbox['xmin'] - offset_x) / scale_x
        bbox_scaled[1] = (bbox['ymin'] - offset_y) / scale_y
        bbox_scaled[2] = (bbox['zmin'] - offset_z) / scale_z
        bbox_scaled[3] = (bbox['xmax'] - offset_x) / scale_x
        bbox_scaled[4] = (bbox['ymax'] - offset_y) / scale_y
        bbox_scaled[5] = (bbox['zmax'] - offset_z) / scale_z

        res = cls.query("""
            delete from pointcloud_lopocs where schematable = %s and "column" = %s;
            insert into pointcloud_lopocs (schematable, "column", srid, bbox)
            values (%s, %s, %s, %s) returning id
            """, (table, column, table, column, srid, bbox))
        plid = res[0][0]

        scales = scale_x, scale_y, scale_z
        offsets = offset_x, offset_y, offset_z

        json_schema = cls.patch2greyhoundschema(table, column)

        cls.execute("""
            insert into pointcloud_lopocs_outputs
            (id, pcid, scales, offsets, stored, bbox, point_schema)
            values (%s, %s, %s, %s, True, %s, %s)
        """, (
            plid, pcid, iterable2pgarray(scales), iterable2pgarray(offsets),
            iterable2pgarray(bbox_scaled), Json(json_schema)))

    @classmethod
    def add_output_schema(cls, table, column,
                          scale_x, scale_y, scale_z,
                          offset_x, offset_y, offset_z, srid,
                          schema, compression='none'):
        """
        Adds a new schema used to stream points.
        The new point format will be added to the database if it doesn't exists
        """
        bbox = cls.compute_boundingbox(table, column)

        # compute bbox with offset and scale applied
        bbox_scaled = [0] * 6
        bbox_scaled[0] = (bbox['xmin'] - offset_x) / scale_x
        bbox_scaled[1] = (bbox['ymin'] - offset_y) / scale_y
        bbox_scaled[2] = (bbox['zmin'] - offset_z) / scale_z
        bbox_scaled[3] = (bbox['xmax'] - offset_x) / scale_x
        bbox_scaled[4] = (bbox['ymax'] - offset_y) / scale_y
        bbox_scaled[5] = (bbox['zmax'] - offset_z) / scale_z

        scales = scale_x, scale_y, scale_z
        offsets = offset_x, offset_y, offset_z

        xmlschema = create_pointcloud_schema(schema, scales, offsets)

        # check if the schema already exists
        res = Session.query(
            """ select pcid from pointcloud_formats
                where srid = %s and schema = %s
            """, (srid, xmlschema)
        )
        if not res:
            # insert schema
            res = cls.query(
                """ with tmp as (
                        select max(pcid) + 1 as pcid
                        from pointcloud_formats
                    )
                    insert into pointcloud_formats
                    select pcid, %s, %s from tmp
                    returning pcid
                """, (srid, xmlschema)
            )

        pcid = res[0][0]

        # check if lopocs already contains this configuration
        plid = cls.query("""
            select id from pointcloud_lopocs
                where schematable = %s and "column" = %s;
        """, (table, column))[0][0]

        cls.execute("""
            insert into pointcloud_lopocs_outputs
            (id, pcid, scales, offsets, stored, bbox, point_schema)
            values (%s, %s, %s, %s, False, %s, %s)
        """, (
            plid, pcid, iterable2pgarray(scales), iterable2pgarray(offsets),
            iterable2pgarray(bbox_scaled), Json(schema)))

        return pcid, bbox_scaled

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
