# -*- coding: utf-8 -*-
from struct import pack
import codecs
import binascii
import json
import numpy

from lazperf import Compressor, buildNumpyDescription
from . import utils
from .conf import Config

class PgPointCloud(object):

    def __init__(self, session):
        self.session = session
        self.lod = 0

    def get_points(self, box, dims, offsets, scale, lod):
        buff = bytearray()
        n = -1

        if lod < Config.DEPTH:
            [n, buff] = self.__get_points_method2(box, dims, offsets, scale, lod)

        print("NUM POINTS RETURNED: ", n)

        return buff

    #def get_pointn(self, n, box, dims, offset, scale):

    #    points = []
    #    hexbuffer = bytearray()

    #    try:
    #        # build params
    #        poly = utils.boundingbox_to_polygon(box)

    #        # build sql query
    #        sql = ("select pc_get(pc_pointn({0}, {1})) as pt from {2} "
    #            "where pc_intersects({0}, st_geomfromtext('polygon (("
    #            "{3}))',{4}));"
    #            .format(self.session.column, n, self.session.table,
    #                    poly, self.session.srsid()))

    #        # run the database
    #        points = self.session.query_aslist(sql)

    #        hexbuffer = self._prepare_for_potree(points, offset, scale)
    #    except:
    #        points = []
    #        hexbuffer.extend(self.__hexa_signed_int32(0))

    #    return [len(points), hexbuffer]

    #def __get_points_method0(self, box, dims, offset, scale, lod):

    #    points = []
    #    hexbuffer = bytearray()

    #    try:
    #        # build params
    #        poly = utils.boundingbox_to_polygon(box)

    #        # build sql query
    #        sql = ("select pc_get(pc_explode({0})) from {1} "
    #            "where pc_intersects({0}, st_geomfromtext('polygon (("
    #            "{2}))',{3}));"
    #            .format(self.session.column, self.session.table,
    #                    poly, self.session.srsid()))

    #        # run the database
    #        points = self.session.query_aslist(sql)

    #        hexbuffer = self._prepare_for_potree(points, offset, scale)
    #    except:
    #        points = []
    #        hexbuffer.extend(self.__hexa_signed_int32(0))

    #    return [len(points), hexbuffer]

    #def __get_points_method1(self, box, dims, offsets, scale, lod):
    #    n = random.randint(0, 400)
    #    return self.get_pointn(n, box, dims, offsets, scale)

    def __get_points_method2(self, box, dims, offset, scale, lod):
        # build params
        poly = utils.boundingbox_to_polygon(box)

        # range
        beg = 0
        for i in range(0, lod-1):
            beg = beg + pow(4,i)

        end = 0
        for i in range(0, lod):
            end = end + pow(4,i)

        # build sql query
        sql = ("select pc_get(pc_explode(pc_filterbetween( pc_range({0}, {4}, {5}), 'Z', {6}, {7} ))) from {1} "
            "where pc_intersects({0}, st_geomfromtext('polygon (("
            "{2}))',{3}));"
            .format(self.session.column, self.session.table,
                    poly, self.session.srsid(), beg, end-beg,
                    box[2], box[5]))

        points = self.session.query_aslist(sql)
        hexbuffer = self._prepare_for_potree(points, offset, scale)

        return [len(points), hexbuffer]

    def __hexa_signed_int32(self, val):
        hex = pack('i', val)
        c = codecs.encode(hex, 'hex').decode()
        return binascii.unhexlify(c)

    def __hexa_signed_uint16(self, val):
        hex = pack('H', val)
        c = codecs.encode(hex, 'hex').decode()
        return binascii.unhexlify(c)

    def __hexa_signed_uint8(self, val):
        hex = pack('B', val)
        c = codecs.encode(hex, 'hex').decode()
        return binascii.unhexlify(c)

    def _prepare_for_potree(self, points, offset, scale):

        hexbuffer = bytearray()

        # get pgpointcloud schema to retrieve x/y/z position
        schema = utils.Schema()
        schema.parse_pgpointcloud_schema( self.session.schema() )
        xpos = schema.x_position()
        ypos = schema.y_position()
        zpos = schema.z_position()

        # update data with offset and scale
        scaled_points = []
        for pt in points:
            scaled_point = utils.Point()
            scaled_point.x = int((pt[xpos] - offset[0]) / scale)
            scaled_point.y = int((pt[ypos] - offset[1]) / scale)
            scaled_point.z = int((pt[zpos] - offset[2]) / scale)

            #print("----------------------------------------------")
            #print("x: ", pt[xpos], " scale_x: ", scaled_point.x, ", offset: ", offset[0])
            #print("y: ", pt[ypos], " scale_y: ", scaled_point.y, ", offset: ", offset[1])
            #print("z: ", pt[zpos], " scale_z: ", scaled_point.z, ", offset: ", offset[2])

            scaled_point.red = 0
            scaled_point.green = 0
            scaled_point.blue = 0

            if self.lod == 9:
                scaled_point.red = 255
                scaled_point.green = 255
                scaled_point.blue = 255
            elif self.lod == 10:
                scaled_point.red = 0
                scaled_point.green = 255
                scaled_point.blue = 255
            elif self.lod == 11:
                scaled_point.red = 255
                scaled_point.green = 0
                scaled_point.blue = 255
            elif self.lod == 12:
                scaled_point.red = 255
                scaled_point.green = 255
                scaled_point.blue = 0
            elif self.lod == 13:
                scaled_point.red = 255
                scaled_point.green = 0
                scaled_point.blue = 0
            elif self.lod == 14:
                scaled_point.red = 0
                scaled_point.green = 255
                scaled_point.blue = 0
            scaled_points.append( scaled_point )

        # build a buffer with hexadecimal data
        for pt in scaled_points:
            hexbuffer.extend(self.__hexa_signed_int32(pt.x))
            hexbuffer.extend(self.__hexa_signed_int32(pt.y))
            hexbuffer.extend(self.__hexa_signed_int32(pt.z))
            hexbuffer.extend(self.__hexa_signed_uint16(pt.intensity))
            hexbuffer.extend(self.__hexa_signed_uint8(pt.classification))
            hexbuffer.extend(self.__hexa_signed_uint16(pt.red))
            hexbuffer.extend(self.__hexa_signed_uint16(pt.green))
            hexbuffer.extend(self.__hexa_signed_uint16(pt.blue))

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
        hexbuffer.extend(self.__hexa_signed_int32(len(scaled_points)))

        return hexbuffer
