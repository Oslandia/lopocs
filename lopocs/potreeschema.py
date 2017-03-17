# -*- coding: utf-8 -*-

potree_schema = [
    {
        "name": "X",
        "size": 4,
        "type": "signed"
    },
    {
        "name": "Y",
        "size": 4,
        "type": "signed"
    },
    {
        "name": "Z",
        "size": 4,
        "type": "signed"
    },
    {
        "name": "Intensity",
        "size": 2,
        "type": "unsigned"
    },
    {
        "name": "Classification",
        "size": 1,
        "type": "unsigned"
    },
    {
        "name": "Red",
        "size": 2,
        "type": "unsigned"
    },
    {
        "name": "Green",
        "size": 2,
        "type": "unsigned"
    },
    {
        "name": "Blue",
        "size": 2,
        "type": "unsigned"
    }
]

ctypes_map = {
    ('unsigned', 1): 'uint8_t',
    ('unsigned', 2): 'uint16_t',
    ('unsigned', 4): 'uint32_t',
    ('signed', 2): 'int16_t',
    ('signed', 4): 'int32_t',
    ('floating', 4): 'float',
}

dim_skeleton_xyz = """<pc:dimension>
    <pc:position>{pos}</pc:position>
    <pc:size>{size}</pc:size>
    <pc:description>{name}</pc:description>
    <pc:name>{name}</pc:name>
    <pc:interpretation>{ctype}</pc:interpretation>
    <pc:scale>{scale}</pc:scale>
    <pc:offset>{offset}</pc:offset>
    <pc:active>true</pc:active>
</pc:dimension>
"""

dim_skeleton = """<pc:dimension>
    <pc:position>{pos}</pc:position>
    <pc:size>{size}</pc:size>
    <pc:description>{name}</pc:description>
    <pc:name>{name}</pc:name>
    <pc:interpretation>{ctype}</pc:interpretation>
    <pc:active>true</pc:active>
</pc:dimension>
"""


schema_skeleton = """<?xml version="1.0" encoding="UTF-8"?>
<pc:PointCloudSchema xmlns:pc="http://pointcloud.org/schemas/PC/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
{dims_xyz}
{dims}
<pc:metadata>
<Metadata name="compression" type="string"/>{compression}</pc:metadata>
<pc:orientation>point</pc:orientation>
</pc:PointCloudSchema>"""


def dim_arr_index(dim):
    index = {'x': 0, 'y': 1, 'z': 2}
    return index[dim['name'].lower()]


def create_pointcloud_schema(dimensions, scales, offsets, compression='none'):
    '''
    Create a pointcloud schema corresponding with given parameters
    Dimensions looks like :
        [
            {
                "name": "X",
                "size": 4,
                "type": "signed"
            },...
        ]
    :param scales: array of 3 scales for x, y, z
    :param ofsets: array of 3 offset
    '''
    xyz_dims = [d for d in dimensions if d['name'].lower() in ('x', 'y', 'z')]
    other_dims = [d for d in dimensions if d['name'].lower() not in ('x', 'y', 'z')]

    pcschema = schema_skeleton.format(
        compression=compression,
        dims_xyz=''.join(dim_skeleton_xyz.format(
            **dict(d,
                   ctype=ctypes_map[(d['type'], d['size'])],
                   scale=scales[dim_arr_index(d)],
                   offset=offsets[dim_arr_index(d)],
                   pos=dim_arr_index(d) + 1))
            for d in xyz_dims
        ),
        dims=''.join(dim_skeleton.format(
            **dict(d, ctype=ctypes_map[(d['type'], d['size'])], pos=pos))
            for pos, d in enumerate(other_dims, start=4)
        )
    )

    return pcschema
