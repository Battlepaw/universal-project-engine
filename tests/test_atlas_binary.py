import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from docx import Document
from docx.shared import Inches
from PIL import Image
from atlas_binary import extract_assets, AtlasExtractionError

class AtlasBinaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "atlas.docx"
        self.image = Path(self.tmp.name) / "image.png"
        Image.new("RGB", (24, 18), (12, 30, 90)).save(self.image)

    def make_doc(self, headings):
        doc = Document()
        for heading in headings:
            doc.add_paragraph(heading)
            doc.add_paragraph("Approved master illustration:")
            doc.add_picture(str(self.image), width=Inches(1))
        doc.save(self.path)

    def test_two_distinct_assets(self):
        self.make_doc(["END-SHIP-001 — Sweetwind", "VIS-SD-001 — Becca"])
        assets = extract_assets(self.path)
        self.assertEqual([a.asset_id for a in assets], ["END-SHIP-001", "VIS-SD-001"])
        self.assertEqual(assets[0].width, 24)
        self.assertEqual(len(assets[0].sha256), 64)

    def test_future_asset_without_registration(self):
        self.make_doc(["END-SHIP-999 — Future ship"])
        self.assertEqual(extract_assets(self.path, "END-SHIP-999")[0].asset_id, "END-SHIP-999")

    def test_missing_asset_fails(self):
        self.make_doc(["END-SHIP-001 — Sweetwind"])
        with self.assertRaises(AtlasExtractionError):
            extract_assets(self.path, "VIS-SD-001")

    def test_ambiguous_asset_fails(self):
        self.make_doc(["END-SHIP-001 — One", "END-SHIP-001 — Two"])
        with self.assertRaises(AtlasExtractionError):
            extract_assets(self.path, "END-SHIP-001")

    def test_unanchored_image_fails(self):
        doc = Document()
        doc.add_picture(str(self.image))
        doc.save(self.path)
        with self.assertRaises(AtlasExtractionError):
            extract_assets(self.path)

if __name__ == "__main__":
    unittest.main()
