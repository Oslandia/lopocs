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
{dims}
<pc:metadata>
<Metadata name="compression" type="string"/>{compression}</pc:metadata>
<pc:orientation>point</pc:orientation>
</pc:PointCloudSchema>"""


def dim_mapper(dimension, scales, offsets, pos):
    '''redirect to correct xml description depending
    of the dimension type
    '''
    if dimension['name'].lower() in ('x', 'y', 'z'):
        return dim_skeleton_xyz.format(
            **dict(dimension,
                   ctype=ctypes_map[(dimension['type'], dimension['size'])],
                   scale=scales[dim_arr_index(dimension)],
                   offset=offsets[dim_arr_index(dimension)],
                   pos=pos)
        )

    return dim_skeleton.format(
        **dict(dimension,
               ctype=ctypes_map[(dimension['type'], dimension['size'])],
               pos=pos))


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
    pcschema = schema_skeleton.format(
        compression=compression,
        dims=''.join(
            dim_mapper(d, scales, offsets, pos)
            for pos, d in enumerate(dimensions, start=1)
        ),
    )
    return pcschema


potree_page = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="">
    <meta name="author" content="">
    <title>Potree Viewer</title>

    <link rel="stylesheet" type="text/css" href="potree/build/potree/potree.css">
    <link rel="stylesheet" type="text/css" href="potree/libs/jquery-ui/jquery-ui.min.css">
    <link rel="stylesheet" type="text/css" href="potree/libs/perfect-scrollbar/css/perfect-scrollbar.css">
    <link rel="stylesheet" href="potree/libs/openlayers3/ol.css" type="text/css">
  </head>

  <body>

    <script src="potree/libs/jquery/jquery-3.1.1.js"></script>

    <!--<script src="potree/libs/other/webgl-debug.js"></script>-->
    <script src="potree/libs/perfect-scrollbar/js/perfect-scrollbar.jquery.js"></script>
    <script src="potree/libs/jquery-ui/jquery-ui.min.js"></script>
    <script src="potree/libs/three.js/build/three.js"></script>
    <script src="potree/libs/other/stats.min.js"></script>
    <script src="potree/libs/other/BinaryHeap.js"></script>
    <script src="potree/libs/tween/tween.min.js"></script>
    <script src="potree/libs/d3/d3.js"></script>
    <script src="potree/libs/proj4/proj4.js"></script>
    <script src="potree/libs/openlayers3/ol.js"></script>
    <script src="potree/libs/i18next/i18next.js"></script>

    <script src="potree/build/potree/potree.js"></script>
    <script src="potree/libs/plasio/js/laslaz.js"></script>
    <script src="potree/libs/plasio/vendor/bluebird.js"></script>


    <div class="potree_container" style="position: absolute; width: 100%; height: 100%; left: 0px; top: 0px; ">

        <div id="potree_render_area">
            <div id="potree_map" class="mapBox" style="position: absolute; left: 50px; top: 50px; width: 400px; height: 400px; display: none">
                <div id="potree_map_header" style="position: absolute; width: 100%; height: 25px; top: 0px; background-color: rgba(0,0,0,0.5); z-index: 1000; border-top-left-radius: 3px; border-top-right-radius: 3px;">
                </div>
                <div id="potree_map_content" class="map" style="position: absolute; z-index: 100; top: 25px; width: 100%; height: calc(100% - 25px); border: 2px solid rgba(0,0,0,0.5); box-sizing: border-box;"></div>
            </div>

            <div id="potree_description" class="potree_info_text"></div>
        </div>

        <div id="potree_sidebar_container"> </div>
    </div>

    <script>

        window.viewer = new Potree.Viewer(document.getElementById("potree_render_area"));

        viewer.setEDLEnabled(true);
        viewer.setPointSize(3.0);
        viewer.setMaterial("RGB");
        viewer.setFOV(60);
        viewer.setPointSizing("Fixed");
        viewer.setQuality("Squares");
        viewer.setPointBudget(2*1000*1000);
        viewer.setIntensityRange(0, 300);
        viewer.setWeightClassification(1);
        viewer.loadSettingsFromURL();

        viewer.setDescription('Streaming point clouds from PostgreSQL with <a href="https://github.com/Oslandia/lopocs" target="_blank">LOPoCS</a>.');

        viewer.loadGUI(() => {{
            viewer.setLanguage('en');
            $("#menu_appearance").next().show();
            //viewer.toggleSidebar();
        }});

        var getQueryParam = function(name) {{
            name = name.replace(/[\[\]]/g, "\\$&");
            var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
                results = regex.exec(window.location.href);
            if (!results || !results[2]) return null;
            return decodeURIComponent(results[2].replace(/\+/g, " "));
        }}

        {{
            // var server = "greyhound://cache.greyhound.io/resource/";
            var server = "greyhound://{server_url}/greyhound/";

            var resource = "{resource}";

            if (getQueryParam("server")) {{
                server = getQueryParam("server");
            }}
            if (getQueryParam("resource")) {{
                resource = getQueryParam("resource");
            }}

            Potree.loadPointCloud(server + resource + "/", "", (e) => {{
                viewer.scene.addPointCloud(e.pointcloud);
                viewer.fitToScreen(0.5);
            }});
        }}

    </script>


  </body>
</html>"""
