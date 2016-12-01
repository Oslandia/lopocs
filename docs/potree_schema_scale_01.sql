INSERT INTO pointcloud_formats (pcid, srid, schema) VALUES (2, !SRID!,
'<?xml version="1.0" encoding="UTF-8"?>
<pc:PointCloudSchema xmlns:pc="http://pointcloud.org/schemas/PC/1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <pc:dimension>
  <pc:position>1</pc:position>
  <pc:size>4</pc:size>
  <pc:description>X coordinate</pc:description>
  <pc:name>X</pc:name>
  <pc:interpretation>int32_t</pc:interpretation>
  <pc:scale>0.1</pc:scale>
  <pc:offset>!XOFFSET!</pc:offset>
  <pc:active>true</pc:active>
 </pc:dimension>
 <pc:dimension>
  <pc:position>2</pc:position>
  <pc:size>4</pc:size>
  <pc:description>Y coordinate</pc:description>
  <pc:name>Y</pc:name>
  <pc:interpretation>int32_t</pc:interpretation>
  <pc:scale>0.1</pc:scale>
  <pc:offset>!YOFFSET!</pc:offset>
  <pc:active>true</pc:active>
 </pc:dimension>
 <pc:dimension>
  <pc:position>3</pc:position>
  <pc:size>4</pc:size>
  <pc:description>Z coordinate</pc:description>
  <pc:name>Z</pc:name>
  <pc:interpretation>int32_t</pc:interpretation>
  <pc:scale>0.1</pc:scale>
  <pc:offset>!ZOFFSET!</pc:offset>
  <pc:active>true</pc:active>
 </pc:dimension>
 <pc:dimension>
  <pc:position>4</pc:position>
  <pc:size>2</pc:size>
  <pc:description>Representation of the pulse return magnitude</pc:description>
  <pc:name>Intensity</pc:name>
  <pc:interpretation>uint16_t</pc:interpretation>
  <pc:active>true</pc:active>
 </pc:dimension>
 <pc:dimension>
   <pc:position>5</pc:position>
   <pc:size>1</pc:size>
   <pc:description>ASPRS classification.  0 for no classification.</pc:description>
   <pc:name>Classification</pc:name>
   <pc:interpretation>uint8_t</pc:interpretation>
   <pc:active>true</pc:active>
 </pc:dimension>
 <pc:dimension>
  <pc:position>6</pc:position>
  <pc:size>2</pc:size>
  <pc:description>Red image channel value</pc:description>
  <pc:name>Red</pc:name>
  <pc:interpretation>uint16_t</pc:interpretation>
  <pc:active>true</pc:active>
 </pc:dimension>
 <pc:dimension>
  <pc:position>7</pc:position>
  <pc:size>2</pc:size>
  <pc:description>Green image channel value</pc:description>
  <pc:name>Green</pc:name>
  <pc:interpretation>uint16_t</pc:interpretation>
  <pc:active>true</pc:active>
 </pc:dimension>
 <pc:dimension>
  <pc:position>8</pc:position>
  <pc:size>2</pc:size>
  <pc:description>Blue image channel value</pc:description>
  <pc:name>Blue</pc:name>
  <pc:interpretation>uint16_t</pc:interpretation>
  <pc:active>true</pc:active>
 </pc:dimension>
 <pc:metadata>
<Metadata name="compression" type="string"/>none</pc:metadata>
 <pc:orientation>point</pc:orientation>
</pc:PointCloudSchema>');
