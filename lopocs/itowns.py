# -*- coding: utf-8 -*-
from struct import Struct
from collections import namedtuple

import numpy as np
from flask import make_response, abort

from .utils import read_uncompressed_patch, boundingbox_to_polygon
from .database import Session


the_bbox = namedtuple('bbox', ['xmin', 'ymin', 'zmin', 'xmax', 'ymax', 'zmax'])
binfloat = Struct('I')
binchar = Struct('B')

LOD_MIN = 0
LOD_MAX = 10
LOD_LEN = LOD_MAX + 1 - LOD_MIN

SMALL_LEAF = 10000

POINT_QUERY = """
    with patches as
    (
        select
            points
            , random() as rand
        from {session.table}
        where pc_intersects({session.column},
            st_geomfromtext('polygon (({poly}))', {session.srsid}))
        and zavg && numrange({z1}::numeric, {z2}::numeric)
    ), ordered as (
        select
            pc_filterbetween(pc_range({session.column}, {start}, {count}), 'Z', {z1}, {z2}) as points
        from patches
        order by rand
        {sql_limit}
    ) select {last_select} from ordered
"""


def ItownsRead(table, column, bbox_encoded, isleaf, last_modified):

    session = Session(table, column)

    bbox_encoded = bbox_encoded.strip('r.')
    lod = len(bbox_encoded)
    box = decode_bbox(session, bbox_encoded)
    stored_patches = session.lopocstable.filter_stored_output()
    schema = stored_patches['point_schema']
    pcid = stored_patches['pcid']
    scales = stored_patches['scales']
    offsets = stored_patches['offsets']
    try:
        tile = get_points(
            session,
            box,
            lod,
            offsets,
            pcid,
            scales,
            schema,
            isleaf
        )
    except TypeError:
        return abort(404)

    # build flask response
    response = make_response(tile)
    response.headers['content-type'] = 'application/octet-stream'
    response.headers['Last-Modified'] = last_modified
    return response


def ItownsHrc(table, column, bbox_encoded, last_modified):
    """
    Request for hierarchy
    [x1][n1][x11][n11][x12][n12]...[x111][n111]

    """
    session = Session(table, column)

    bbox_encoded = bbox_encoded.strip('r.')
    # print(bbox_encoded)
    lod = len(bbox_encoded)
    # print('lod', lod)
    box = decode_bbox(session, bbox_encoded)

    patch_size = session.patch_size

    npoints = get_numpoints(session, box, lod, patch_size)
    output = octree(session, 0, 2, box, npoints, lod, patch_size)

    response = make_response(output)
    response.headers['content-type'] = 'application/octet-stream'
    response.headers['Last-Modified'] = last_modified
    return response


def get_numpoints(session, box, lod, patch_size):
    poly = boundingbox_to_polygon([
        box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax
    ])

    # psize = 1
    psize = int(patch_size / LOD_LEN)
    start = lod * psize + 1
    count = psize

    maxppq = session.lopocstable.max_patches_per_query
    sql_limit = ''
    if maxppq:
        sql_limit = " limit {0} ".format(maxppq)

    sql = POINT_QUERY.format(
        z1=box.zmin, z2=box.zmax,
        last_select='sum(pc_numpoints(points))',
        **locals()
    )

    npoints = session.query(sql)[0][0]
    return npoints or 0


def octree(session, depth, depth_max, box, npoints, lod, patch_size, name='', buffer=None):

    if buffer is None:
        buffer = {}

    # root
    bitarray = ['0'] * 8

    cnpoints = []

    for child in range(8):
        cbox = get_child(box, child)
        cnpoints.append(get_numpoints(session, cbox, lod + 1, patch_size))

    # psize = 1
    psize = int(patch_size / LOD_LEN)
    child_desc = [
        (patch_size - (lod + 1) * psize) * (cp / psize)
        for cp in cnpoints
    ]

    if sum(child_desc) < SMALL_LEAF:
        npoints += sum(cnpoints)
    else:
        for child in range(8):
            cbox = get_child(box, child)
            if cnpoints[child] > 0:
                bitarray[child] = '1'
                if depth < depth_max:
                    octree(session, depth + 1, depth_max, cbox, cnpoints[child], lod + 1, patch_size, name + str(child), buffer)

    buffer[name] = [bitarray, npoints]

    if not depth:
        sorted_keys = sorted(buffer.keys(), key=lambda x: (len(x), x))
        output = b''.join([
            binchar.pack(int(''.join(buffer[key][0])[::-1], 2)) + binfloat.pack(buffer[key][1])
            for key in sorted_keys
        ])
        return output


def get_child(parent, numchild):
    half_size = (
        (parent.xmax - parent.xmin) / 2,
        (parent.ymax - parent.ymin) / 2,
        (parent.zmax - parent.zmin) / 2
    )
    if numchild == 0:
        child = the_bbox(
            parent.xmin,
            parent.ymin,
            parent.zmin,
            parent.xmin + half_size[0],
            parent.ymin + half_size[1],
            parent.zmin + half_size[2]
        )
    elif numchild == 1:
        child = the_bbox(
            parent.xmin,
            parent.ymin,
            parent.zmin + half_size[2],
            parent.xmin + half_size[0],
            parent.ymin + half_size[1],
            parent.zmin + 2 * half_size[2]
        )
    elif numchild == 2:
        child = the_bbox(
            parent.xmin,
            parent.ymin + half_size[1],
            parent.zmin,
            parent.xmin + half_size[0],
            parent.ymin + 2 * half_size[1],
            parent.zmin + half_size[2]
        )
    elif numchild == 3:
        child = the_bbox(
            parent.xmin,
            parent.ymin + half_size[1],
            parent.zmin + half_size[2],
            parent.xmin + half_size[0],
            parent.ymin + 2 * half_size[1],
            parent.zmin + 2 * half_size[2]
        )
    elif numchild == 4:
        child = the_bbox(
            parent.xmin + half_size[0],
            parent.ymin,
            parent.zmin,
            parent.xmin + 2 * half_size[0],
            parent.ymin + half_size[1],
            parent.zmin + half_size[2]
        )
    elif numchild == 5:
        child = the_bbox(
            parent.xmin + half_size[0],
            parent.ymin,
            parent.zmin + half_size[2],
            parent.xmin + 2 * half_size[0],
            parent.ymin + half_size[1],
            parent.zmin + 2 * half_size[2]
        )
    elif numchild == 6:
        child = the_bbox(
            parent.xmin + half_size[0],
            parent.ymin + half_size[1],
            parent.zmin,
            parent.xmin + 2 * half_size[0],
            parent.ymin + 2 * half_size[1],
            parent.zmin + half_size[2]
        )
    elif numchild == 7:
        child = the_bbox(
            parent.xmin + half_size[0],
            parent.ymin + half_size[1],
            parent.zmin + half_size[2],
            parent.xmax,
            parent.ymax,
            parent.zmax
        )
    return child


def decode_bbox(session, bbox):
    """
    returns a r0000.bin
    """
    root = the_bbox(
        session.boundingbox['xmin'],
        session.boundingbox['ymin'],
        session.boundingbox['zmin'],
        session.boundingbox['xmax'],
        session.boundingbox['ymax'],
        session.boundingbox['zmax']
    )
    if not bbox:
        return root

    for numchild in [int(l) for l in bbox]:
        root = get_child(root, numchild)

    # print('level', level, 'zdiff', root.zmax - root.zmin)
    return root


def classification_to_rgb(points):
    """
    map LAS Classification to RGB colors.
    See LAS spec for codes :
    http://www.asprs.org/wp-content/uploads/2010/12/asprs_las_format_v11.pdf

    :param points: points as a structured numpy array
    :returns: numpy.record with dtype [('Red', 'u1'), ('Green', 'u1'), ('Blue', 'u1')])
    """
    # building (brown)
    building_mask = (points['Classification'] == 6).astype(np.int)
    red = building_mask * 186
    green = building_mask * 79
    blue = building_mask * 63
    # high vegetation (green)
    veget_mask = (points['Classification'] == 5).astype(np.int)
    red += veget_mask * 140
    green += veget_mask * 156
    blue += veget_mask * 8
    # medium vegetation
    veget_mask = (points['Classification'] == 4).astype(np.int)
    red += veget_mask * 171
    green += veget_mask * 200
    blue += veget_mask * 116
    # low vegetation
    veget_mask = (points['Classification'] == 3).astype(np.int)
    red += veget_mask * 192
    green += veget_mask * 213
    blue += veget_mask * 160
    # water (blue)
    water_mask = (points['Classification'] == 9).astype(np.int)
    red += water_mask * 141
    green += water_mask * 179
    blue += water_mask * 198
    # ground (light brown)
    grd_mask = (points['Classification'] == 2).astype(np.int)
    red += grd_mask * 226
    green += grd_mask * 230
    blue += grd_mask * 229
    # Unclassified (grey)
    grd_mask = (points['Classification'] == 1).astype(np.int)
    red += grd_mask * 176
    green += grd_mask * 185
    blue += grd_mask * 182

    alpha = np.ones(points.shape)

    rgb_reduced = np.c_[red, green, blue, alpha]
    rgb = np.array(np.core.records.fromarrays(rgb_reduced.T, dtype=cdt))
    return rgb


cdt = np.dtype([('Red', np.uint8), ('Green', np.uint8), ('Blue', np.uint8), ('Alpha', np.uint8)])
pdt = np.dtype([('X', np.float32), ('Y', np.float32), ('Z', np.float32)])


def get_points(session, box, lod, offsets, pcid, scales, schema, isleaf):
    sql = sql_query(session, box, pcid, lod, isleaf)

    pcpatch_wkb = session.query(sql)[0][0]
    points, npoints = read_uncompressed_patch(pcpatch_wkb, schema)
    print('npoints', npoints)
    fields = points.dtype.fields.keys()

    if 'Red' in fields:
        if max(points['Red']) > 255:
            # normalize
            rgb_reduced = np.c_[points['Red'] % 255, points['Green'] % 255, points['Blue'] % 255, np.ones(npoints) * 255]
            rgb = np.array(np.core.records.fromarrays(rgb_reduced.T, dtype=cdt))
        else:
            rgb = points[['Red', 'Green', 'Blue']].astype(cdt)
    elif 'Classification' in fields:
        rgb = classification_to_rgb(points)
    else:
        # No colors
        # FIXME: compute color gradient based on elevation
        rgb_reduced = np.zeros((npoints, 3), dtype=int)
        rgb = np.array(np.core.records.fromarrays(rgb_reduced.T, dtype=cdt))

    # print(box)

    quantized_points_r = np.c_[
        (points['X'] * scales[0] + offsets[0]) - box.xmin,
        (points['Y'] * scales[1] + offsets[1]) - box.ymin,
        (points['Z'] * scales[2] + offsets[2]) - box.zmin
    ]

    quantized_points = np.array(np.core.records.fromarrays(quantized_points_r.T, dtype=pdt))
    header = np.array(
        [
            0, 0, 0,
            box.xmax - box.xmin, box.ymax - box.ymin, box.zmax - box.zmin
        ], dtype='float32')

    buffer = header.tostring() + quantized_points.tostring() + rgb.tostring()
    return buffer


def sql_query(session, box, pcid, lod, isleaf):
    poly = boundingbox_to_polygon([
        box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax
    ])

    maxppp = session.lopocstable.max_points_per_patch
    patch_size = session.patch_size

    sql_limit = ""
    maxppq = session.lopocstable.max_patches_per_query
    if maxppq and not isleaf:
        sql_limit = " limit {0} ".format(maxppq)

    psize = int(patch_size / LOD_LEN)
    # psize = 1
    start = lod * psize + 1
    count = psize

    # print('patch_size', patch_size)
    # print('psize', psize)
    # print('start', start)
    # print('count', count)
    if isleaf:
        # we want all points left
        count = patch_size - start

    sql = POINT_QUERY.format(z1=box.zmin, z2=box.zmax,
                             last_select='pc_union(points)',
                             **locals())
    return sql
