# -*- coding: utf-8 -*-
import json
import math

import numpy as np
from flask import make_response

from py3dtiles.feature_table import (
    FeatureTableHeader, FeatureTableBody, FeatureTable
)
from py3dtiles.pnts import PntsBody, PntsHeader, Pnts

from .utils import (
    read_uncompressed_patch, boundingbox_to_polygon, list_from_str, patch_numpoints
)
from .conf import Config
from .database import Session

LOD_MIN = 0
LOD_MAX = 5
LOD_LEN = LOD_MAX + 1 - LOD_MIN


def ThreeDTilesInfo(table, column):

    session = Session(table, column)
    # bounding box
    box = session.boundingbox

    # number of points for the first patch
    npoints = session.approx_row_count * session.patch_size

    # srs
    srs = session.srs

    # build json
    return {
        "bounds": [box['xmin'], box['ymin'], box['zmin'],
                   box['xmax'], box['ymax'], box['zmax']],
        "numPoints": npoints,
        "srs": srs
    }


def ThreeDTilesRead(table, column, bounds, lod):

    session = Session(table, column)
    # offsets = [round(off, 2) for off in list_from_str(offsets)]
    box = list_from_str(bounds)
    # requested = [scales, offsets]
    stored_patches = session.lopocstable.filter_stored_output()
    schema = stored_patches['point_schema']
    pcid = stored_patches['pcid']
    # scales = [scale] * 3
    scales = stored_patches['scales']
    offsets = stored_patches['offsets']

    [tile, npoints] = get_points(session, box, lod, offsets, pcid, scales, schema)

    if Config.DEBUG:
        tile.sync()
        print("NPOINTS: ", npoints)

    # build flask response
    response = make_response(tile.to_array().tostring())
    response.headers['content-type'] = 'application/octet-stream'
    return response


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

    rgb_reduced = np.c_[red, green, blue]
    rgb = np.array(np.core.records.fromarrays(rgb_reduced.T, dtype=cdt))
    return rgb


cdt = np.dtype([('Red', np.uint8), ('Green', np.uint8), ('Blue', np.uint8)])
pdt = np.dtype([('X', np.float32), ('Y', np.float32), ('Z', np.float32)])


def get_points(session, box, lod, offsets, pcid, scales, schema):
    sql = sql_query(session, box, pcid, lod)
    if Config.DEBUG:
        print(sql)

    pcpatch_wkb = session.query(sql)[0][0]
    points, npoints = read_uncompressed_patch(pcpatch_wkb, schema)
    fields = points.dtype.fields.keys()

    if 'Red' in fields:
        if max(points['Red']) > 255:
            # normalize
            rgb_reduced = np.c_[points['Red'] % 255, points['Green'] % 255, points['Blue'] % 255]
            rgb = np.array(np.core.records.fromarrays(rgb_reduced.T, dtype=cdt))
        else:
            rgb = points[['Red', 'Green', 'Blue']].astype(cdt)
    elif 'Classification' in fields:
        rgb = classification_to_rgb(points)
    else:
        # No colors
        # FIXME: compute color gradient based on elevation
        rgb_reduced = np.zeros((npoints, 3), dtype=int)
        rgb = np.array(np.core.records.fromarrays(rgb_reduced, dtype=cdt))

    quantized_points_r = np.c_[
        points['X'] * scales[0],
        points['Y'] * scales[1],
        points['Z'] * scales[2]
    ]

    quantized_points = np.array(np.core.records.fromarrays(quantized_points_r.T, dtype=pdt))

    fth = FeatureTableHeader.from_dtype(
        quantized_points.dtype, rgb.dtype, npoints
    )
    ftb = FeatureTableBody()
    ftb.positions_itemsize = fth.positions_dtype.itemsize
    ftb.colors_itemsize = fth.colors_dtype.itemsize
    ftb.positions_arr = quantized_points.view(np.uint8)
    ftb.colors_arr = rgb.view(np.uint8)

    ft = FeatureTable()
    ft.header = fth
    ft.body = ftb

    # tile
    tb = PntsBody()
    tb.feature_table = ft
    th = PntsHeader()
    tile = Pnts()
    tile.body = tb
    tile.header = th
    tile.body.feature_table.header.rtc = offsets

    return [tile, npoints]


def sql_query(session, box, pcid, lod):
    poly = boundingbox_to_polygon(box)

    maxppp = session.lopocstable.max_points_per_patch
    # FIXME: need to be cached
    patch_size = session.patch_size

    if maxppp:
        range_min = 1
        range_max = maxppp
    else:
        # FIXME: may skip some points if patch_size/lod_len is decimal
        # we need to fix either here or at loading with the patch_size and lod bounds
        range_min = lod * int(patch_size / LOD_LEN) + 1
        range_max = (lod + 1) * int(patch_size / LOD_LEN)

    # build the sql query
    sql_limit = ""
    maxppq = session.lopocstable.max_patches_per_query
    if maxppq:
        sql_limit = " limit {0} ".format(maxppq)

    if Config.USE_MORTON:
        sql = ("select pc_union("
               "pc_filterbetween( "
               "pc_range({0}, {4}, {5}), 'Z', {6}, {7} )) from "
               "(select {0} from {1} "
               "where pc_intersects({0}, st_geomfromtext('polygon (("
               "{2}))',{3})) order by morton {8})_;"
               .format(session.column, session.table,
                       poly, session.srsid, range_min, range_max,
                       box[2] - 0.1, box[5] + 0.1, sql_limit,
                       pcid))
    else:
        sql = ("select pc_compress(pc_transform(pc_union("
               "pc_filterbetween( "
               "pc_range({0}, {4}, {5}), 'Z', {6}, {7} )), {9}), 'laz') from "
               "(select {0} from {1} where pc_intersects({0}, "
               "st_geomfromtext('polygon (({2}))',{3})) {8})_;"
               .format(session.column, session.table,
                       poly, session.srsid, range_min, range_max,
                       box[2], box[5], sql_limit,
                       pcid))

    return sql


def buildbox(bbox):
    width = bbox[3] - bbox[0]
    depth = bbox[4] - bbox[1]
    height = bbox[5] - bbox[2]
    midx = bbox[0] + width / 2
    midy = bbox[1] + depth / 2
    midz = bbox[2] + height / 2

    box = [midx, midy, midz]
    box.append(width / 2.0)
    box.append(0.0)
    box.append(0.0)
    box.append(0.0)
    box.append(depth / 2.0)
    box.append(0.0)
    box.append(0.0)
    box.append(0.0)
    box.append(height / 2.0)
    return box


def build_hierarchy_from_pg(session, baseurl, bbox):

    stored_patches = session.lopocstable.filter_stored_output()
    pcid = stored_patches['pcid']
    offsets = stored_patches['offsets']
    tileset = {}
    tileset["asset"] = {"version": "0.0"}
    tileset["geometricError"] = math.sqrt(
        (bbox[3] - bbox[0]) ** 2 + (bbox[4] - bbox[1]) ** 2 + (bbox[5] - bbox[2]) ** 2
    )
    if Config.DEBUG:
        print('tileset geometricErroc', tileset["geometricError"])

    bvol = {}
    bvol["box"] = buildbox(bbox)

    lod_str = "lod={0}".format(LOD_MIN)
    bounds = ("bounds=[{0},{1},{2},{3},{4},{5}]"
              .format(bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]))
    resource = "{}.{}".format(session.table, session.column)

    base_url = "{0}/3dtiles/{1}/read.pnts".format(baseurl, resource)
    url = (
        "{0}?{1}&{2}"
        .format(base_url, lod_str, bounds)
    )

    GEOMETRIC_ERROR = tileset["geometricError"]

    root = {}
    root["refine"] = "add"
    root["boundingVolume"] = bvol
    root["geometricError"] = GEOMETRIC_ERROR / 20
    root["content"] = {"url": url}

    lod = 1
    children_list = []
    for bb in split_bbox(bbox):
        json_children = children(
            session, baseurl, offsets, bb, lod, pcid, GEOMETRIC_ERROR / 40
        )
        if len(json_children):
            children_list.append(json_children)

    if len(children_list):
        root["children"] = children_list

    tileset["root"] = root

    return json.dumps(tileset, indent=2, separators=(',', ': '))


def build_children_section(session, baseurl, offsets, bbox, err, lod):

    cjson = {}

    lod = "lod={0}".format(lod)
    bounds = ("bounds=[{0},{1},{2},{3},{4},{5}]"
              .format(bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]))

    resource = "{}.{}".format(session.table, session.column)
    baseurl = "{0}/3dtiles/{1}/read.pnts".format(baseurl, resource)
    url = "{0}?{1}&{2}".format(baseurl, lod, bounds)

    bvol = {}
    bvol["box"] = buildbox(bbox)

    cjson["boundingVolume"] = bvol
    cjson["geometricError"] = err
    cjson["content"] = {"url": url}

    return cjson


def split_bbox(bbox):
    width = bbox[3] - bbox[0]
    length = bbox[4] - bbox[1]
    height = bbox[5] - bbox[2]

    up = bbox[5]
    middle = up - height / 2
    down = bbox[2]

    x = bbox[0]
    y = bbox[1]

    bbox_nwd = [x, y + length / 2, down, x + width / 2, y + length, middle]
    bbox_nwu = [x, y + length / 2, middle, x + width / 2, y + length, up]
    bbox_ned = [x + width / 2, y + length / 2, down, x + width, y + length, middle]
    bbox_neu = [x + width / 2, y + length / 2, middle, x + width, y + length, up]
    bbox_swd = [x, y, down, x + width / 2, y + length / 2, middle]
    bbox_swu = [x, y, middle, x + width / 2, y + length / 2, up]
    bbox_sed = [x + width / 2, y, down, x + width, y + length / 2, middle]
    bbox_seu = [x + width / 2, y, middle, x + width, y + length / 2, up]

    return [bbox_nwd, bbox_nwu, bbox_ned, bbox_neu, bbox_swd, bbox_swu,
            bbox_sed, bbox_seu]


def children(session, baseurl, offsets, bbox, lod, pcid, err):

    # run sql
    sql = sql_query(session, bbox, pcid, lod)
    pcpatch_wkb = session.query(sql)[0][0]

    json_me = {}
    if lod <= LOD_MAX and pcpatch_wkb:
        npoints = patch_numpoints(pcpatch_wkb)
        if npoints > 0:
            json_me = build_children_section(session, baseurl, offsets, bbox, err, lod)

        lod += 1

        children_list = []
        if lod <= LOD_MAX:
            for bb in split_bbox(bbox):
                json_children = children(
                    session, baseurl, offsets, bb, lod, pcid, err / 2
                )

                if len(json_children):
                    children_list.append(json_children)

        if len(children_list):
            json_me["children"] = children_list

    return json_me
