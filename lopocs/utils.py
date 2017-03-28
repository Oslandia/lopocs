# -*- coding: utf-8 -*-
import json
from struct import pack, unpack
from binascii import unhexlify
import os
import decimal

import numpy
from lazperf import buildNumpyDescription, Decompressor

from .conf import Config


def decompress(points, schema):
    """
    'points' is a pcpatch in wkb
    """

    # retrieve number of points in wkb pgpointcloud patch
    npoints = npoints_from_wkb_pcpatch(points)
    hexbuffer = hexdata_from_wkb_pcpatch(points)
    hexbuffer += hexa_signed_int32(npoints)

    # uncompress
    s = json.dumps(schema).replace("\\", "")
    dtype = buildNumpyDescription(json.loads(s))
    lazdata = bytes(hexbuffer)

    arr = numpy.fromstring(lazdata, dtype=numpy.uint8)
    d = Decompressor(arr, s)
    output = numpy.zeros(npoints * dtype.itemsize, dtype=numpy.uint8)
    decompressed = d.decompress(output)

    return decompressed


def greyhound_types(typ):
    '''
    https://github.com/hobu/greyhound/blob/master/doc/clientDevelopment.rst#schema
    '''
    if typ[0] == 'u':
        return "unsigned"
    elif typ in ('double', 'float'):
        return "floating"
    return "signed"


def write_in_cache(d, filename):
    path = os.path.join(Config.CACHE_DIR, filename)
    if not os.path.exists(Config.CACHE_DIR):
        os.mkdir(Config.CACHE_DIR)
    f = open(path, 'w')
    f.write(json.dumps(d))
    f.close()


def read_in_cache(filename):
    path = os.path.join(Config.CACHE_DIR, filename)

    d = {}
    if os.path.exists(path):
        d = json.load(open(path))

    return d


def iterable2pgarray(iterable):
    """Convert a python iterable to a postgresql array
    """
    return '{' + ','.join([str(elem) for elem in iterable]) + '}'


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


def list_from_str(list_str):
    """
    Transform a string ['[', '1', '.', '5', ',', '2', ',', '3', ']']
    to a list [1,2,3]
    """
    return [float(val) for val in list_str[1:-1].split(',')]


def boundingbox_to_polygon(box):
    """
    input box = [xmin, ymin, zmin, xmax, ymax, zmax]
    output box = 'xmin ymin, xmax ymin, xmax ymax, xmin ymax, xmin ymin'
    """
    boxstr = (
        "{0} {1}, {2} {3}, {4} {5}, {6} {7}, {0} {1}"
        .format(box[0], box[1], box[3], box[1], box[3], box[4], box[0], box[4])
    )
    return boxstr


def list_from_str_box(box_str):
    """
    Transform a string 'BOX(xmin, ymin, xmax, ymax)' to
    a list [xmin, ymin, xmin, xmax]
    """
    box_str = box_str.replace('BOX', '')
    box_str = box_str.replace('(', '')
    box_str = box_str.replace(')', '')
    box_str = box_str.replace(' ', ',')

    l = [float(x) for x in box_str.split(',')]
    return l


def hexa_signed_int32(val):
    return pack('i', val)


def hexa_signed_uint16(val):
    return pack('H', val)


def hexa_signed_uint8(val):
    return pack('B', val)


def npoints_from_wkb_pcpatch(pcpatch_wkb):
    npoints_hexa = pcpatch_wkb[18:26]
    return unpack("I", unhexlify(npoints_hexa))[0]


def hexdata_from_wkb_pcpatch(pcpatch_wkb):
    return unhexlify(pcpatch_wkb[34:])
