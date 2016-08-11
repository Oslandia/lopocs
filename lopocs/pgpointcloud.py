# -*- coding: utf-8 -*-
from struct import pack
import json
import numpy
import random

from lazperf import Compressor, buildNumpyDescription
from . import utils
from .conf import Config

class PgPointCloud(object):

    def __init__(self, session):
        self.session = session

    def get_points(self, box, dims, offsets, scale, lod):
        buff = bytearray()
        n = -1

        print("LOD: ", lod)
        print("DEPTH: ", Config.DEPTH)

        if Config.METHOD:
            if Config.METHOD == "random":
                [n, buff] = self.__get_points_method1(box, dims, offsets, scale, lod)
            elif Config.METHOD == "midoc":
                if lod < Config.DEPTH:
                    [n, buff] = self.__get_points_method2(box, dims, offsets, scale, lod)
        else:
            [n, buff] = self.__get_points_method1(box, dims, offsets, scale, lod)

        print("NUM POINTS RETURNED: ", n)

        return buff

    def get_pointn(self, n, box, dims, offset, scale):

        points = []
        hexbuffer = bytearray()

        try:
            # build params
            poly = utils.boundingbox_to_polygon(box)

            # build sql query
            sql = ("select pc_get(pc_explode(pc_range({0}, {1}, 1))) as pt from {2} "
                "where pc_intersects({0}, st_geomfromtext('polygon (("
                "{3}))',{4}));"
                .format(self.session.column, n, self.session.table,
                        poly, self.session.srsid()))

            print(sql)

            # run the database
            points = self.session.query_aslist(sql)

            #print(points)

            hexbuffer = self._prepare_for_potree(points, offset, scale)
        except:
            points = []
            hexbuffer.extend(self.__hexa_signed_int32(0))

        return [len(points), hexbuffer]

    def __get_points_method1(self, box, dims, offsets, scale, lod):
        """
        Randomly select 1 point in each patch within the bounding box.
        """

        n = random.randint(0, 400)
        return self.get_pointn(n, box, dims, offsets, scale)

    def __get_points_method2(self, box, dims, offset, scale, lod):
        """
        Select n points in each patch within the bounding box
        according to the LOD.
        """

        # build params
        poly = utils.boundingbox_to_polygon(box)

        # range
        beg = 0
        for i in range(0, lod-1):
            beg = beg + pow(4, i)

        end = 0
        for i in range(0, lod):
            end = end + pow(4, i)

        # build sql query
        sql = ("select pc_get(pc_explode(pc_filterbetween( "
               "pc_range({0}, {4}, {5}), 'Z', {6}, {7} ))) from {1} "
               "where pc_intersects({0}, st_geomfromtext('polygon (("
               "{2}))',{3}));"
               .format(self.session.column, self.session.table,
                       poly, self.session.srsid(), beg, end-beg,
                       box[2], box[5]))

        print(sql)

        points = self.session.query_aslist(sql)
        hexbuffer = self._prepare_for_potree(points, offset, scale)

        return [len(points), hexbuffer]

    def __hexa_signed_int32(self, val):
        return pack('i', val)

    def __hexa_signed_uint16(self, val):
        return pack('H', val)

    def __hexa_signed_uint8(self, val):
        return pack('B', val)

    def _prepare_for_potree(self, points, offset, scale):

        hexbuffer = bytearray()

        # get pgpointcloud schema to retrieve x/y/z position
        schema = utils.Schema()
        schema.parse_pgpointcloud_schema(self.session.schema())
        xpos = schema.x_position()
        ypos = schema.y_position()
        zpos = schema.z_position()
        red_pos = schema.red_position()
        green_pos = schema.green_position()
        blue_pos = schema.blue_position()
        classif_pos = schema.classification_position()
        intensity_pos = schema.intensity_position()

        # update data with offset and scale
        for pt in points:
            scaled_point = utils.Point()
            scaled_point.x = int((pt[xpos] - offset[0]) / scale)
            scaled_point.y = int((pt[ypos] - offset[1]) / scale)
            scaled_point.z = int((pt[zpos] - offset[2]) / scale)
            scaled_point.intensity = int(pt[intensity_pos])

            if red_pos and green_pos and blue_pos:
                scaled_point.red = int(pt[red_pos]) % 255
                scaled_point.green = int(pt[green_pos]) % 255
                scaled_point.blue = int(pt[blue_pos]) % 255

            if classif_pos:
                scaled_point.classification = int(pt[classif_pos])

            hexbuffer.extend(self.__hexa_signed_int32(scaled_point.x))
            hexbuffer.extend(self.__hexa_signed_int32(scaled_point.y))
            hexbuffer.extend(self.__hexa_signed_int32(scaled_point.z))
            hexbuffer.extend(self.__hexa_signed_uint16(scaled_point.intensity))
            hexbuffer.extend(self.__hexa_signed_uint8(scaled_point.classification))
            hexbuffer.extend(self.__hexa_signed_uint16(scaled_point.red))
            hexbuffer.extend(self.__hexa_signed_uint16(scaled_point.green))
            hexbuffer.extend(self.__hexa_signed_uint16(scaled_point.blue))

        # compress with laz
        s = json.dumps(utils.GreyhoundReadSchema().json()).replace("\\","")
        dtype = buildNumpyDescription(json.loads(s))

        c = Compressor(s)
        arr = numpy.fromstring(bytes(hexbuffer), dtype = dtype)
        c = c.compress(arr)
        hexbuffer = bytearray(numpy.asarray(c))

        #d = Decompressor(c, s)
        #output = numpy.zeros(len(scaled_points) * dtype.itemsize, dtype = numpy.uint8)
        #decompressed = d.decompress(output)
        #decompressed_str = numpy.ndarray.tostring( decompressed )

        # add nomber of points as footer
        hexbuffer.extend(self.__hexa_signed_int32(len(points)))

        return hexbuffer
