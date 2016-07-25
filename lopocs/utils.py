# -*- coding: utf-8 -*-
import json
import decimal

# -----------------------------------------------------------------------------
# functions
# -----------------------------------------------------------------------------
def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError

def list_from_str( list_str ):
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
    boxstr = ("{0} {1}, {2} {3}, {4} {5}, {6} {7}, {0} {1}"
        .format(box[0], box[1], box[3], box[1], box[3], box[4], box[0], box[4]))
    return boxstr

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
            self.dims.append( Dimension(d['name'], d['type'], d['size']) )

    def dim_position(self, name):
        for idx, d in enumerate(self.dims):
            if d.name == name or d.name == name.upper():
                return idx
        return None

    def x_position(self):
        return self.dim_position('x')

    def y_position(self):
        return self.dim_position('y')

    def z_position(self):
        return self.dim_position('z')

class Dimension(object):

    def __init__(self, name, typename, size):
        self.name = name
        self.typename = typename
        self.size = size

    def json(self):
        return {"name" : self.name,
            "size" : self.size,
            "type" : self.typename}

class Point(object):

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.intensity = 0
        self.classification = 0
        self.red = 0
        self.green = 0
        self.blue = 0

# -----------------------------------------------------------------------------
# schema
# -----------------------------------------------------------------------------
class GreyhoundInfoSchema(Schema):

    def __init__(self):
        Schema.__init__(self)

        self.dims.append(Dimension( "X", "floating", 8 ))
        self.dims.append(Dimension( "Y", "floating", 8 ))
        self.dims.append(Dimension( "Z", "floating", 8 ))
        self.dims.append(Dimension( "Intensity", "unsigned", 2 ))
        self.dims.append(Dimension( "Classification", "unsigned", 1 ))
        self.dims.append(Dimension( "Red", "unsigned", 2 ))
        self.dims.append(Dimension( "Green", "unsigned", 2 ))
        self.dims.append(Dimension( "Blue", "unsigned", 2 ))

class GreyhoundReadSchema(Schema):

    def __init__(self):
        Schema.__init__(self)

        self.dims.append(Dimension( "X", "signed", 4 ))
        self.dims.append(Dimension( "Y", "signed", 4 ))
        self.dims.append(Dimension( "Z", "signed", 4 ))
        self.dims.append(Dimension( "Intensity", "unsigned", 2 ))
        self.dims.append(Dimension( "Classification", "unsigned", 1 ))
        self.dims.append(Dimension( "Red", "unsigned", 2 ))
        self.dims.append(Dimension( "Green", "unsigned", 2 ))
        self.dims.append(Dimension( "Blue", "unsigned", 2 ))
