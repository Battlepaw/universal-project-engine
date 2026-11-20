import unittest
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from docx import Document
from PIL import Image
from engine import PROJECTS
from production_bundle import prepare_production_bundle, ProductionBundleBlocked

class ProductionBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        folder = Path(self.tmp.name)
        img = folder / "master.png"
        Image.new("RGB", (20, 10)).save(img)
        self.docx = folder / "atlas.docx"
        doc = Document()
        doc.add_paragraph("END-SHIP-001 — Example")
        doc.add_paragraph("Approved master illustration:")
        doc.add_picture(str(img))
        doc.save(self.docx)
        src = PROJECTS["endaria"]["sources"]
        self.args = dict(project_id="endaria", asset_id="END-SHIP-001",
            registry_document_id=src["document_registry"]["id"],
            registry_revision_id="registry-v1",
            registry_paragraphs=[{"text": src["visual_atlas_a"]["id"]}],
            sourcebook_document_id=src["master_sourcebook"]["id"],
            sourcebook_revision_id="source-v1",
            sourcebook_paragraphs=[{"text": "Dossier END-SHIP-001"}],
            atlas_source_key="visual_atlas_a",
            atlas_document_id=src["visual_atlas_a"]["id"],
            atlas_revision_id="atlas-v1",
            atlas_paragraphs=[{"text": "END-SHIP-001 — Example"}],
            atlas_docx_path=str(self.docx),
            export_attestation={"document_id": src["visual_atlas_a"]["id"],
                                "revision_id": "atlas-v1",
                                "authenticated_export": True,
                                "sha256": sha256(self.docx.read_bytes()).hexdigest()})

    def test_full_bundle(self):
        result = prepare_production_bundle(**self.args)
        self.assertEqual(result["status"], "SOURCE_AND_IMAGE_BYTES_RESOLVED_NOT_PROVIDER_DELIVERED")
        self.assertEqual(result["image"]["width"], 20)
        self.assertIsNone(result["provider_reference_receipt"])

    def test_sourcebook_missing_blocks(self):
        self.args["sourcebook_paragraphs"] = [{"text": "No dossier"}]
        with self.assertRaises(ProductionBundleBlocked):
            prepare_production_bundle(**self.args)

    def test_export_revision_drift_blocks(self):
        self.args["export_attestation"]["revision_id"] = "stale"
        with self.assertRaises(ProductionBundleBlocked):
            prepare_production_bundle(**self.args)

    def test_export_hash_mismatch_blocks(self):
        self.args["export_attestation"]["sha256"] = "0"*64
        with self.assertRaises(ProductionBundleBlocked):
            prepare_production_bundle(**self.args)

    def test_cross_project_blocks(self):
        self.args["project_id"] = "starborne"
        with self.assertRaises(ValueError):
            prepare_production_bundle(**self.args)

if __name__ == "__main__":
    unittest.main()
