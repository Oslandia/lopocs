# -*- coding: utf-8 -*-

cesium_page = """
<!DOCTYPE html>
<html lang="en">
<head>
  <!-- Use correct character set. -->
  <meta charset="utf-8">
  <!-- Tell IE to use the latest, best version. -->
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <!-- Make the application on mobile take up the full browser screen and disable user scaling. -->
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, minimum-scale=1, user-scalable=no">
  <title>Demo: {resource}</title>
  <script src="cesium/Cesium/Cesium.js"></script>
  <style>
      @import url(cesium/Cesium/Widgets/widgets.css);
      html, body, #cesiumContainer {{
          width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden;
      }}
  </style>
</head>
<body>
  <div id="cesiumContainer"></div>
  <script>

    var viewer = new Cesium.Viewer('cesiumContainer');

    viewer.extend(Cesium.viewerCesium3DTilesInspectorMixin);
    var inspectorViewModel = viewer.cesium3DTilesInspector.viewModel;

    var tileset = viewer.scene.primitives.add(new Cesium.Cesium3DTileset({{
      url : 'tileset-{resource}.json'
    }}));

    inspectorViewModel.tileset = tileset;

    tileset.readyPromise.then(function() {{
          console.log('Loaded tileset');
          var bounding = tileset._root._boundingVolume;
          var center = bounding.boundingSphere.center;
          var cart = Cesium.Ellipsoid.WGS84.cartesianToCartographic(center);
          var dest = Cesium.Cartesian3.fromDegrees(
                  cart.longitude * (180 / Math.PI),
                  cart.latitude * (180 / Math.PI),
                  bounding._boundingSphere.radius * 4); // was 2.2
          console.log(dest);
          viewer.camera.setView({{ destination: dest }});
      }});

  </script>
</body>
</html>
"""
