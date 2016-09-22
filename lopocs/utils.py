# -*- coding: utf-8 -*-
import json
import os
import decimal

# -----------------------------------------------------------------------------
# functions
# -----------------------------------------------------------------------------
def write_hierarchy_in_cache(d, filename):
    home = os.path.expanduser("~")
    dircache = os.path.join(home, ".cache/lopocs")
    path = os.path.join(dircache, filename)

    f = open(path, 'w')
    f.write(json.dumps(d))
    f.close()

def read_hierarchy_in_cache(filename):
    home = os.path.expanduser("~")
    dircache = os.path.join(home, ".cache/lopocs")
    path = os.path.join(dircache, filename)

    d = {}
    if os.path.exists(path):
        d = json.load(open(path))

    return d

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

def list_from_str_box( box_str ):
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

def build_hierarchy_from_pg(session, lod_max, bbox, lod):

    # range
    beg = 0
    for i in range(0, lod):
        beg = beg + pow(4, i)

    end = 0
    for i in range(0, lod+1):
        end = end + pow(4, i)

    # run sql
    poly = boundingbox_to_polygon(bbox)
    sql = ("select pc_numpoints(pc_union(pc_filterbetween("
           "pc_range({8}, {4}, {5}), 'Z', {6}, {7}))) from {0} "
           "where pc_intersects({1}, st_geomfromtext('polygon (("
           "{2}))',{3}));"
           .format(session.table, session.column, poly, session.srsid(),
                   beg, end-beg, bbox[2], bbox[5], session.column))
    res = session.query_aslist(sql)[0]

    hierarchy = {}
    if lod <= lod_max and res:
        hierarchy['n'] = res

    lod += 1

    if lod <= lod_max:
        # width / length / height
        width = bbox[3] - bbox[0]
        length = bbox[4] - bbox[1]
        height = bbox[5] - bbox[2]

        up = bbox[5]
        middle = up - height/2
        down = bbox[2]

        x = bbox[0]
        y = bbox[1]

        # nwd
        bbox_nwd = [x, y+length/2, down, x+width/2, y+length, middle]
        h_nwd = build_hierarchy_from_pg(session, lod_max, bbox_nwd, lod)
        if h_nwd:
            hierarchy['nwd'] = h_nwd

        # nwu
        bbox_nwu = [x, y+length/2, middle, x+width/2, y+length, up]
        h_nwu = build_hierarchy_from_pg(session, lod_max, bbox_nwu, lod)
        if h_nwu:
            hierarchy['nwu'] = h_nwu

        # ned
        bbox_ned = [x+width/2, y+length/2, down, x+width, y+length, middle]
        h_ned = build_hierarchy_from_pg(session, lod_max, bbox_ned, lod)
        if h_ned:
            hierarchy['ned'] = h_ned

        # neu
        bbox_neu = [x+width/2, y+length/2, middle, x+width, y+length, up]
        h_neu = build_hierarchy_from_pg(session, lod_max, bbox_neu, lod)
        if h_neu:
            hierarchy['neu'] = h_neu

        # swd
        bbox_swd = [x, y, down, x+width/2, y+length/2, middle]
        h_swd = build_hierarchy_from_pg(session, lod_max, bbox_swd, lod)
        if h_swd:
            hierarchy['swd'] = h_swd

        # swu
        bbox_swu = [x, y, middle, x+width/2, y+length/2, up]
        h_swu = build_hierarchy_from_pg(session, lod_max, bbox_swu, lod)
        if h_swu:
            hierarchy['swu'] = h_swu

        # sed
        bbox_sed = [x+width/2, y, down, x+width, y+length/2, middle]
        h_sed = build_hierarchy_from_pg(session, lod_max, bbox_sed, lod)
        if h_sed:
            hierarchy['sed'] = h_sed

        # seu
        bbox_seu = [x+width/2, y, middle, x+width, y+length/2, up]
        h_seu = build_hierarchy_from_pg(session, lod_max, bbox_seu, lod)
        if h_seu:
            hierarchy['seu'] = h_seu

    return hierarchy

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
            if d.name == name or d.name == name.upper() or d.name == name.title():
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

class TestSchema(Schema):

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
