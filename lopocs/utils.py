# -*- coding: utf-8 -*-
import json
from struct import pack, unpack
import codecs
import os
import decimal

from .conf import Config


# -----------------------------------------------------------------------------
# functions
# -----------------------------------------------------------------------------
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


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


def list_from_str(list_str):
    """
    Transform a string ['[', '1', '.', '5', ',', '2', ',', '3', ']']
    to a list [1,2,3]
    """
    list_str = list_str.replace('[', '')
    list_str = list_str.replace(']', '')
    l = [float(x) for x in list_str.split(',')]

    return l


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
    return unpack("I", codecs.decode(npoints_hexa, "hex"))[0]


def hexdata_from_wkb_pcpatch(pcpatch_wkb):
    return codecs.decode(pcpatch_wkb[34:], "hex")


# -----------------------------------------------------------------------------
# class
# -----------------------------------------------------------------------------
class Schema(object):

    def __init__(self):
        self.dims = []

    def json(self):
        json = []
        for dim in self.dims:
            json.append(dim.json())

        return json

    def parse_pgpointcloud_schema(self, schema):
        for d in schema:
            self.dims.append(Dimension(d['name'], d['type'], d['size']))

    def dim_position(self, name):
        for idx, d in enumerate(self.dims):
            if d.name == name or d.name == name.upper() \
                    or d.name == name.title():
                return idx
        return None

    def x_position(self):
        return self.dim_position('x')

    def y_position(self):
        return self.dim_position('y')

    def z_position(self):
        return self.dim_position('z')

    def red_position(self):
        return self.dim_position('red')

    def green_position(self):
        return self.dim_position('green')

    def blue_position(self):
        return self.dim_position('blue')

    def classification_position(self):
        return self.dim_position('classification')

    def intensity_position(self):
        return self.dim_position('intensity')


class Dimension(object):

    def __init__(self, name, typename, size):
        self.name = name
        self.typename = typename
        self.size = size

    def json(self):
        return {"name": self.name,
                "size": self.size,
                "type": self.typename}
