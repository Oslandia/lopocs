# -*- coding: utf-8 -*-
import json
import numpy as np
from flask import make_response

from py3dtiles.feature_table import (FeatureTableHeader, FeatureTableBody, FeatureTable)
from py3dtiles.tile import TileBody, TileHeader, Tile

from .utils import (
    read_uncompressed_patch, boundingbox_to_polygon, list_from_str, patch_nbpoints_unc
)
from .conf import Config
from .database import Session

GEOMETRIC_ERROR_DEFAULT = 2000


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

# FIXME: change pdt type in case of quantized values
cdt = np.dtype([('Red', np.uint8), ('Green', np.uint8), ('Blue', np.uint8)])
pdt = np.dtype([('X', np.float32), ('Y', np.float32), ('Z', np.float32)])


# @profile
def get_points(session, box, lod, offsets, pcid, scales, schema):
    sql = sql_query(session, box, pcid, lod)
    if Config.DEBUG:
        print(sql)

    pcpatch_wkb = session.query(sql)[0][0]
    points, npoints = read_uncompressed_patch(pcpatch_wkb, schema)

    quantized_points_r = np.c_[points['X'] * scales[0], points['Y'] * scales[1], points['Z'] * scales[2]]
    quantized_points = np.array(np.core.records.fromarrays(quantized_points_r.T, dtype=pdt))
    rgb_reduced = np.c_[points['Red'] % 255, points['Green'] % 255, points['Blue'] % 255]
    rgb = np.array(np.core.records.fromarrays(rgb_reduced.T, dtype=cdt))

    fth = FeatureTableHeader.from_dtype(
        quantized_points.dtype, rgb.dtype, npoints,
        # quantized_volume_offset=offsets,
        # quantized_volume_scale=scales
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
    tb = TileBody()
    tb.feature_table = ft
    th = TileHeader()
    tile = Tile()
    tile.body = tb
    tile.header = th
    tile.body.feature_table.header.rtc = offsets

    return [tile, npoints]


def sql_query(session, box, pcid, lod, hierarchy=False):
    poly = boundingbox_to_polygon(box)

    maxppp = session.lopocstable.max_points_per_patch

    if maxppp:
        range_min = 0
        range_max = maxppp
    else:
        # adapted to midoc filter
        beg = 0
        for i in range(0, lod):
            beg = beg + pow(4, i)

        end = 0
        for i in range(0, lod + 1):
            end = end + pow(4, i)

        range_min = beg
        range_max = end - beg

    # build the sql query
    sql_limit = ""
    maxppq = session.lopocstable.max_patches_per_query
    if maxppq:
        sql_limit = " limit {0} ".format(maxppq)

    if Config.USE_MORTON:
        if hierarchy:
            sql = ("""select pc_union(pc_filterbetween(pc_range({0}, {4}, {5}), 'Z', {6}, {7} ))
                   from
                   (select {0} from {1}
                   where pc_intersects({0}, st_geomfromtext('polygon ((
                   {2}))',{3})) order by morton {8})_
                   """
                   .format(session.column, session.table,
                           poly, session.srsid, range_min, range_max,
                           box[2] - 0.1, box[5] + 0.1, sql_limit,
                           pcid))
        else:
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
        sql = ("select pc_compress(pc_setpcid(pc_union("
               "pc_filterbetween( "
               "pc_range({0}, {4}, {5}), 'Z', {6}, {7} )), {9}), 'laz') from "
               "(select {0} from {1} where pc_intersects({0}, "
               "st_geomfromtext('polygon (({2}))',{3})) {8})_;"
               .format(session.column, session.table,
                       poly, session.srsid, range_min, range_max,
                       box[2], box[5], sql_limit,
                       pcid))

    return sql


def build_hierarchy_from_pg(session, baseurl, lod_max, bbox, lod):

    stored_patches = session.lopocstable.filter_stored_output()
    pcid = stored_patches['pcid']
    offsets = stored_patches['offsets']
    tileset = {}
    tileset["asset"] = {"version": "0.0"}
    tileset["geometricError"] = GEOMETRIC_ERROR_DEFAULT  # (lod_max + 2)*20 - (lod+1)*20

    bvol = {}
    bvol["sphere"] = [offsets[0], offsets[1], offsets[2], 2000]

    lod_str = "lod={0}".format(lod)
    bounds = ("bounds=[{0},{1},{2},{3},{4},{5}]"
              .format(bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]))
    resource = "{}.{}".format(session.table, session.column)

    base_url = "{0}/3dtiles/{1}/read.pnts".format(baseurl, resource)
    url = (
        "{0}?{1}&{2}"
        .format(base_url, lod_str, bounds)
    )

    root = {}
    root["refine"] = "add"
    root["boundingVolume"] = bvol
    root["geometricError"] = GEOMETRIC_ERROR_DEFAULT / 2  # (lod_max + 2)*20 - (lod+2)*20
    root["content"] = {"url": url}

    lod = 1
    children_list = []
    for bb in split_bbox(bbox, lod):
        json_children = children(session, baseurl, lod_max, offsets, bb, lod, pcid)
        if len(json_children):
            children_list.append(json_children)

    if len(children_list):
        root["children"] = children_list

    tileset["root"] = root

    return json.dumps(tileset)  # , indent=0, separators=(',', ': ')


def build_children_section(session, baseurl, offsets, bbox, err, lod):

    cjson = {}

    lod = "lod={0}".format(lod)
    bounds = ("bounds=[{0},{1},{2},{3},{4},{5}]"
              .format(bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]))

    resource = "{}.{}".format(session.table, session.column)
    baseurl = "{0}/3dtiles/{1}/read.pnts".format(baseurl, resource)
    url = "{0}?{1}&{2}".format(baseurl, lod, bounds)

    bvol = {}
    bvol["sphere"] = [offsets[0], offsets[1], offsets[2], 2000]

    cjson["boundingVolume"] = bvol
    cjson["geometricError"] = err
    cjson["content"] = {"url": url}

    return cjson


def split_bbox(bbox, lod):
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


def children(session, baseurl, lod_max, offsets, bbox, lod, pcid):

    # run sql
    sql = sql_query(session, bbox, pcid, lod, True)
    pcpatch_wkb = session.query(sql)[0][0]

    json_me = {}
    if lod <= lod_max and pcpatch_wkb:
        npoints = patch_nbpoints_unc(pcpatch_wkb)
        if npoints > 0:
            err = GEOMETRIC_ERROR_DEFAULT / (2 * (lod + 1))
            json_me = build_children_section(session, baseurl, offsets, bbox, err, lod)

        lod += 1

        children_list = []
        if lod <= lod_max:
            for bb in split_bbox(bbox, lod):
                json_children = children(session, baseurl, lod_max, offsets, bb, lod, pcid)

                if len(json_children):
                    children_list.append(json_children)

        if len(children_list):
            json_me["children"] = children_list

    return json_me
