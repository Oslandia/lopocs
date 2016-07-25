# -*- coding: utf-8 -*-
from struct import pack
import codecs
import binascii
import json
import numpy
import random

from lazperf import Decompressor, Compressor, buildNumpyDescription
from . import utils

class PgPointCloud(object):

    def __init__(self, session):
        self.session = session

    def get_points(self, box, dims, offsets, scale, lod):
        return self.__get_points_method1( box, dims, offsets, scale, lod )

    def get_pointn(self, n, box, dims, offset, scale):

        hexbuffer = bytearray()

        try:
            # build params
            poly = utils.boundingbox_to_polygon(box)

            # build sql query
            sql = ("select pc_get(pc_pointn({0}, {1})) as pt from {2} "
                "where pc_intersects({0}, st_geomfromtext('polygon (("
                "{3}))',{4}));"
                .format(self.session.column, n, self.session.table,
                        poly, self.session.srsid()))

            # run the database
            points = self.session.query_aslist(sql)

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
        except:
            hexbuffer.extend(self.__hexa_signed_int32(0))

        print("Returns " + str(len(scaled_points)) + " points")

        return hexbuffer

    def __get_points_method1(self, box, dims, offsets, scale, lod):
        n = random.randint(0, 400)
        return self.get_pointn(n, box, dims, offsets, scale)

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
