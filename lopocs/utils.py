# -*- coding: utf-8 -*-
import json
import math
from struct import pack, unpack
from binascii import unhexlify
import os
import decimal

import numpy as np
from lazperf import buildNumpyDescription, Decompressor

from .conf import Config


numpy_types_map = {
    ('unsigned', 1): np.uint8,
    ('unsigned', 2): np.uint16,
    ('unsigned', 4): np.uint32,
    ('signed', 2): np.int16,
    ('signed', 4): np.int32,
    ('floating', 4): np.float32,
    ('floating', 8): np.float64,
}


def schema_dtype(schema):
    '''Given a patch schema (greyhound like schema)
    convert it into a numpy dtype description
    http://docs.scipy.org/doc/numpy/reference/generated/numpy.dtype.html
    '''
    formats = [
        numpy_types_map[(dim['type'], dim['size'])]
        for dim in schema
    ]

    return np.dtype(
        {'names': [dim['name'] for dim in schema], 'formats': formats})


def read_uncompressed_patch(pcpatch_wkb, schema):
    '''
    Patch binary structure uncompressed:
    byte:         endianness (1 = NDR, 0 = XDR)
    uint32:       pcid (key to POINTCLOUD_SCHEMAS)
    uint32:       0 = no compression
    uint32:       npoints
    pointdata[]:  interpret relative to pcid
    '''
    patchbin = unhexlify(pcpatch_wkb)
    npoints = unpack("I", patchbin[9:13])[0]
    dt = schema_dtype(schema)
    patch = np.fromstring(patchbin[13:], dtype=dt)
    # debug
    # print(patch[:10])
    return patch, npoints


def decompress(points, schema):
    """
    Decode patch encoded with lazperf.
    'points' is a pcpatch in wkb
    """

    # retrieve number of points in wkb pgpointcloud patch
    npoints = patch_numpoints(points)
    hexbuffer = unhexlify(points[34:])
    hexbuffer += hexa_signed_int32(npoints)

    # uncompress
    s = json.dumps(schema).replace("\\", "")
    dtype = buildNumpyDescription(json.loads(s))
    lazdata = bytes(hexbuffer)

    arr = np.fromstring(lazdata, dtype=np.uint8)
    d = Decompressor(arr, s)
    output = np.zeros(npoints * dtype.itemsize, dtype=np.uint8)
    decompressed = d.decompress(output)

    return decompressed


def compute_scale_for_cesium(coordmin, coordmax):
    '''
    Cesium quantized positions need to be in uint16
    This function computes the best scale to apply to coordinates
    to fit the range [0, 65535]
    '''
    max_int = np.iinfo(np.uint16).max
    delta = abs(coordmax - coordmin)
    scale = 10 ** -(math.floor(math.log1p(max_int / delta) / math.log1p(10)))
    return scale


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


def patch_numpoints(pcpatch_wkb):
    '''get number of points in a patch
    '''
    npoints_hexa = pcpatch_wkb[18:26]
    return unpack("I", unhexlify(npoints_hexa))[0]
