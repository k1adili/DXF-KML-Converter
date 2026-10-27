# DXF and KML Converter

`dxf2kml.py` converts DXF files to KML and KML files back to DXF. DXF-to-KML
supports points, lines, polylines (including bulge arcs), circles, arcs,
ellipses, splines, hatches, 2D/3D faces, `TEXT`, `MTEXT`, and block contents.
Curves are approximated as line segments for KML; closed polylines and faces
are exported as polygons. KML-to-DXF supports `Point`, `LineString`, `Polygon`,
and `MultiGeometry`. Unsupported DXF entities are skipped with a warning.

## Install

```powershell
python -m pip install -r requirements.txt
```

## Launch the graphical interface

```powershell
python DXF-KML-Converter.py
```

The window opens centered on screen. Select the conversion direction, input
and output files, and a coordinate system from the dropdown. It includes
WGS 84 Geographic and all 60 UTM zones in both the northern and southern
hemispheres.

## Build a Windows executable

Install PyInstaller and build a standalone, windowed executable:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DXF-KML-Converter --icon app.ico --add-data "app.ico;." --collect-all pyproj DXF-KML-Converter.py
```

The executable is created at `dist\DXF-KML-Converter.exe`.

## Convert DXF to KML

Specify the coordinate system of the DXF file using `--source-crs`. KML uses
WGS 84 longitude and latitude.

```powershell
python dxf2kml.py dxf-to-kml input.dxf output.kml --source-crs EPSG:32639
```

## Convert KML to DXF

Specify the coordinate system of the output DXF using `--target-crs`:

```powershell
python dxf2kml.py kml-to-dxf input.kml output.dxf --target-crs EPSG:32639
```

Valid `EPSG` identifiers and other CRS inputs accepted by PROJ can be used.
If the DXF uses local coordinates or has no known coordinate system, georeference
it or transform it to a suitable geographic/projected CRS first. Guessing a CRS
can place the output in the wrong location.

The UTM zone is part of the coordinate system and must match the drawing. The
program cannot reliably infer it from the file coordinates. Select WGS 84
Geographic only when the file contains longitude/latitude values in degrees.

DXF dimensions and visual styling are not preserved. Hatch boundaries are
exported as separate geometries, so hole/island relationships are not retained.
DXF layer names become KML Placemark names; on conversion back, Placemark names
become DXF layer names. `TEXT` and `MTEXT` are exported as point placemarks at
their insertion locations, with the text as the placemark name.
