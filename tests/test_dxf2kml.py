import tempfile
import unittest
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import ezdxf

from dxf2kml import convert_dxf_to_kml, convert_kml_to_dxf

GUI_PATH = Path(__file__).resolve().parents[1] / "DXF-KML-Converter.py"
GUI_SPEC = importlib.util.spec_from_file_location("converter_gui", GUI_PATH)
if GUI_SPEC is None or GUI_SPEC.loader is None:
    raise ImportError(f"Could not load GUI module from {GUI_PATH}")
GUI_MODULE = importlib.util.module_from_spec(GUI_SPEC)
GUI_SPEC.loader.exec_module(GUI_MODULE)
CRS_OPTIONS = GUI_MODULE.CRS_OPTIONS


class ConversionTests(unittest.TestCase):
    def test_gui_lists_all_utm_zones_in_both_hemispheres(self):
        codes = set(CRS_OPTIONS.values())

        self.assertEqual(len(CRS_OPTIONS), 121)
        self.assertIn("EPSG:4326", codes)
        self.assertIn("EPSG:32639", codes)
        self.assertEqual(
            {code for code in codes if code.startswith("EPSG:326")},
            {f"EPSG:{code}" for code in range(32601, 32661)},
        )
        self.assertEqual(
            {code for code in codes if code.startswith("EPSG:327")},
            {f"EPSG:{code}" for code in range(32701, 32761)},
        )

    def test_dxf_to_kml_exports_point_line_and_polygon(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.dxf"
            target = Path(directory) / "result.kml"
            drawing = ezdxf.new()
            modelspace = drawing.modelspace()
            modelspace.add_point((51, 35, 10))
            modelspace.add_line((51, 35), (52, 36))
            modelspace.add_lwpolyline(
                [(51, 35), (52, 35), (52, 36)], close=True
            )
            drawing.saveas(source)

            count = convert_dxf_to_kml(source, target, "EPSG:4326")
            root = ET.parse(target).getroot()
            geometry_types = {
                element.tag.rsplit("}", 1)[-1]
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1]
                in {"Point", "LineString", "Polygon"}
            }

            self.assertEqual(count, 3)
            self.assertEqual(geometry_types, {"Point", "LineString", "Polygon"})

    def test_dxf_to_kml_converts_curves_surfaces_and_block_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "curves.dxf"
            target = Path(directory) / "curves.kml"
            drawing = ezdxf.new()
            modelspace = drawing.modelspace()
            modelspace.add_circle((10, 10), 5)
            modelspace.add_arc((20, 10), 5, 0, 180)
            modelspace.add_ellipse((30, 10), (5, 0), 0.5)
            modelspace.add_spline([(40, 10), (42, 15), (45, 10)])
            modelspace.add_solid([(50, 10), (55, 10), (55, 15), (50, 15)])
            modelspace.add_lwpolyline([(80, 10, 1), (85, 10, 0)])
            hatch = modelspace.add_hatch()
            hatch.paths.add_polyline_path(
                [(60, 10), (65, 10), (65, 15), (60, 15)],
                is_closed=True,
            )
            block = drawing.blocks.new("SYMBOL")
            block.add_circle((0, 0), 2)
            modelspace.add_blockref("SYMBOL", (70, 10))
            drawing.saveas(source)

            count = convert_dxf_to_kml(source, target, "EPSG:4326")
            root = ET.parse(target).getroot()
            geometry_types = [
                element.tag.rsplit("}", 1)[-1]
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1]
                in {"Point", "LineString", "Polygon"}
            ]

            self.assertEqual(count, 8)
            self.assertEqual(geometry_types.count("Polygon"), 5)
            self.assertEqual(geometry_types.count("LineString"), 3)

    def test_dxf_to_kml_exports_text_and_mtext_as_labeled_points(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "labels.dxf"
            target = Path(directory) / "labels.kml"
            drawing = ezdxf.new()
            modelspace = drawing.modelspace()
            modelspace.add_text("Street name", dxfattribs={"insert": (51, 35, 12)})
            modelspace.add_mtext(
                r"First line\PSecond line",
                dxfattribs={"insert": (52, 36, 24)},
            )
            block = drawing.blocks.new("LABEL")
            block.add_text("Block label", dxfattribs={"insert": (0, 0, 5)})
            modelspace.add_blockref("LABEL", (53, 37, 10))
            drawing.saveas(source)

            count = convert_dxf_to_kml(source, target, "EPSG:4326")
            root = ET.parse(target).getroot()
            placemarks = [
                node
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1] == "Placemark"
            ]
            names = [
                next(
                    child.text
                    for child in placemark
                    if child.tag.rsplit("}", 1)[-1] == "name"
                )
                for placemark in placemarks
            ]
            coordinates = [
                next(
                    child.text
                    for geometry in placemark
                    if geometry.tag.rsplit("}", 1)[-1] == "Point"
                    for child in geometry
                    if child.tag.rsplit("}", 1)[-1] == "coordinates"
                )
                for placemark in placemarks
            ]

            self.assertEqual(count, 3)
            self.assertEqual(names, ["Street name", "First line\nSecond line", "Block label"])
            self.assertEqual(coordinates[0], "51,35,12")
            self.assertEqual(coordinates[1], "52,36,24")
            self.assertEqual(coordinates[2], "53,37,15")

    def test_kml_to_dxf_creates_supported_entity_types(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.kml"
            target = Path(directory) / "result.dxf"
            source.write_text(
                """<?xml version="1.0"?>
                <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
                  <Placemark><name>Test</name><Point><coordinates>51,35,0</coordinates></Point></Placemark>
                  <Placemark><name>Test</name><LineString><coordinates>51,35 52,36</coordinates></LineString></Placemark>
                  <Placemark><name>Test</name><Polygon><outerBoundaryIs><LinearRing>
                    <coordinates>51,35 52,35 52,36 51,35</coordinates>
                  </LinearRing></outerBoundaryIs></Polygon></Placemark>
                </Document></kml>""",
                encoding="utf-8",
            )

            count = convert_kml_to_dxf(source, target, "EPSG:4326")
            entities = list(ezdxf.readfile(target).modelspace())

            self.assertEqual(count, 3)
            self.assertEqual(
                [entity.dxftype() for entity in entities],
                ["POINT", "LWPOLYLINE", "LWPOLYLINE"],
            )
            self.assertTrue(entities[2].closed)

    def test_kml_to_dxf_preserves_altitude_in_3d_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.kml"
            target = Path(directory) / "result.dxf"
            source.write_text(
                """<kml xmlns="http://www.opengis.net/kml/2.2"><Placemark>
                  <name>3D route</name><LineString>
                    <coordinates>51,35,100 52,36,200</coordinates>
                  </LineString>
                </Placemark></kml>""",
                encoding="utf-8",
            )

            convert_kml_to_dxf(source, target, "EPSG:4326")
            entity = list(ezdxf.readfile(target).modelspace())[0]

            self.assertEqual(entity.dxftype(), "POLYLINE")
            self.assertEqual(
                [vertex.dxf.location.z for vertex in entity.vertices],
                [100, 200],
            )


if __name__ == "__main__":
    unittest.main()
