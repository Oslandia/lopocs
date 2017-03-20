# -*- coding: utf-8 -*-
import json
import numpy as np
import py3dtiles
import struct
from flask import make_response

from . import utils
from .greyhound import decompress
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


def ThreeDTilesRead(table, column, offsets, scale, bounds, lod):

    session = Session(table, column)
    offsets = utils.list_from_str(offsets)
    box = utils.list_from_str(bounds)
    scales = [scale] * 3
    requested = [scales, offsets]
    pcid = None
    stored_patches = session.lopocstable.filter_stored_output()
    schema = stored_patches['point_schema']

    for output in session.lopocstable.outputs:
        if requested == [output['scales'], output['offsets']]:
            pcid = output['pcid']
        print(requested)
    if not pcid:
        pcid = session.add_output_schema(
            session.table, session.column,
            scales[0], scales[1], scales[2],
            offsets[0], offsets[1], offsets[2],
            session.lopocstable.srid, schema)

    [tile, npoints] = get_points(session, box, lod, offsets, pcid, scales, schema)

    if Config.DEBUG:
        tile.sync()
        print("NPOINTS: ", npoints)

    # build flask response
    response = make_response(tile.to_array().tostring())
    response.headers['content-type'] = 'application/octet-stream'
    return response


def get_points(session, box, lod, offsets, pcid, scales, schema):
    sql = sql_query(session, box, pcid, lod)
    if Config.DEBUG:
        print(sql)

    pcpatch_wkb = session.query(sql)[0][0]
    npoints = utils.npoints_from_wkb_pcpatch(pcpatch_wkb)

    # extract data
    [decompressed_str, itemsize] = decompress(pcpatch_wkb, schema)

    pdt = np.dtype([('X', '<f4'), ('Y', '<f4'), ('Z', '<f4')])
    cdt = np.dtype([('Red', 'u1'), ('Green', 'u1'), ('Blue', 'u1')])

    features = []
    for i in range(0, npoints):
        point = decompressed_str[itemsize * i:itemsize * (i + 1)]
        x = point[0:4]
        y = point[4:8]
        z = point[8:12]
        xd = struct.unpack("i", x)[0]
        yd = struct.unpack("i", y)[0]
        zd = struct.unpack("i", z)[0]

        if Config.CESIUM_COLOR == "classif":
            classif = point[14:15]
            classifd = struct.unpack("B", classif)[0]
            if classifd == 2:  # ground
                col_arr = np.array([(51, 25, 0)], dtype=cdt).view('uint8')
            elif classifd == 6:  # buildings
                col_arr = np.array([(153, 76, 0)], dtype=cdt).view('uint8')
            elif classifd == 5:  # vegetation
                col_arr = np.array([(51, 102, 0)], dtype=cdt).view('uint8')
        elif Config.CESIUM_COLOR == "colors":
            r = point[15:17]
            g = point[17:19]
            b = point[19:21]
            rd = struct.unpack("H", r)[0] % 255
            gd = struct.unpack("H", g)[0] % 255
            bd = struct.unpack("H", b)[0] % 255
            col_arr = np.array([(rd, gd, bd)], dtype=cdt).view('uint8')
        else:
            col_arr = np.array([(0, 0, 0)], dtype=cdt).view('uint8')

        xfin = xd * scales[0]
        yfin = yd * scales[1]
        zfin = zd * scales[2]
        pos_arr = np.array([(xfin, yfin, zfin)], dtype=pdt).view('uint8')

        feat = py3dtiles.Feature.from_array(pdt, pos_arr, cdt, col_arr)
        features.append(feat)

    tile = py3dtiles.Tile.from_features(pdt, cdt, features)
    tile.body.feature_table.header.rtc = offsets

    return [tile, npoints]


def sql_query(session, box, pcid, lod):
    poly = utils.boundingbox_to_polygon(box)

    # retrieve the number of points to select in a pcpatch
    range_min = 0
    range_max = 1
    if Config.MAX_POINTS_PER_PATCH:
        range_min = 0
        range_max = Config.MAX_POINTS_PER_PATCH
    else:
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
    if Config.MAX_PATCHS_PER_QUERY:
        sql_limit = " limit {0} ".format(Config.MAX_PATCHS_PER_QUERY)

    if Config.USE_MORTON:
        sql = ("select pc_compress(pc_setpcid(pc_union("
               "pc_filterbetween( "
               "pc_range({0}, {4}, {5}), 'Z', {6}, {7} )), {9}), 'laz') from "
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

    tileset = {}
    tileset["asset"] = {"version": "0.0"}
    tileset["geometricError"] = GEOMETRIC_ERROR_DEFAULT  # (lod_max+2)*20 - (lod+1)*20

    bvol = {}
    center_x = bbox[0] + (bbox[3] - bbox[0]) / 2
    center_y = bbox[1] + (bbox[4] - bbox[1]) / 2
    center_z = bbox[2] + (bbox[5] - bbox[2]) / 2
    offsets = [center_x, center_y, center_z]
    bvol["sphere"] = [center_x, center_y, center_z, 2000]

    lod_str = "lod={0}".format(lod)
    bounds = ("bounds=[{0},{1},{2},{3},{4},{5}]"
              .format(bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]))
    offsets_str = "offsets=[{0},{1},{2}]".format(center_x, center_y, center_z)
    paramscale = "scale=0.1"
    resource = "{}.{}".format(session.table, session.column)

    base_url = "{0}/3dtiles/{1}/read.pnts".format(baseurl, resource)
    url = (
        "{0}?{1}&{2}&{3}&{4}"
        .format(base_url, lod_str, bounds, offsets_str, paramscale)
    )

    root = {}
    root["refine"] = "add"
    root["boundingVolume"] = bvol
    root["geometricError"] = GEOMETRIC_ERROR_DEFAULT / 2  # (lod_max+2)*20 - (lod+2)*20
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

    return json.dumps(tileset, indent=4, separators=(',', ': '))


def build_children_section(session, baseurl, offsets, bbox, err, lod):

    cjson = {}

    lod = "lod={0}".format(lod)
    bounds = ("bounds=[{0},{1},{2},{3},{4},{5}]"
              .format(bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]))
    offsets_str = "offsets=[{0},{1},{2}]".format(offsets[0], offsets[1], offsets[2])
    scale = "scale=0.1"

    resource = "{}.{}".format(session.table, session.column)
    baseurl = "{0}/3dtiles/{1}/read.pnts".format(baseurl, resource)
    url = "{0}?{1}&{2}&{3}&{4}".format(baseurl, lod, bounds, offsets_str, scale)

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

    bbox_nwd = [x, y+length/2, down, x+width/2, y+length, middle]
    bbox_nwu = [x, y+length/2, middle, x+width/2, y+length, up]
    bbox_ned = [x+width/2, y+length/2, down, x+width, y+length, middle]
    bbox_neu = [x+width/2, y+length/2, middle, x+width, y+length, up]
    bbox_swd = [x, y, down, x+width/2, y+length/2, middle]
    bbox_swu = [x, y, middle, x+width/2, y+length/2, up]
    bbox_sed = [x+width/2, y, down, x+width, y+length/2, middle]
    bbox_seu = [x+width/2, y, middle, x+width, y+length/2, up]

    return [bbox_nwd, bbox_nwu, bbox_ned, bbox_neu, bbox_swd, bbox_swu,
            bbox_sed, bbox_seu]


def children(session, baseurl, lod_max, offsets, bbox, lod, pcid):

    # run sql
    sql = sql_query(session, bbox, pcid, lod)
    pcpatch_wkb = session.query(sql)[0][0]

    json_me = {}
    if lod <= lod_max and pcpatch_wkb:
        npoints = utils.npoints_from_wkb_pcpatch(pcpatch_wkb)
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
