import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from docx import Document
from PIL import Image
from drive_transport import DriveSnapshot
from engine import PROJECTS
from retrieval_pipeline import retrieve_asset_bundle, RetrievalPipelineBlocked

class MockDrive:
    def __init__(self, snapshots, docx):
        self.snapshots = snapshots
        self.docx = docx
        self.export_revision = "v1"
    def read_document(self, document_id):
        return self.snapshots[document_id]
    def export_docx(self, document_id):
        return self.docx, self.export_revision

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        folder = Path(self.tmp.name)
        png = folder / "test.png"
        Image.new("RGB", (30, 20)).save(png)
        docx = folder / "atlas.docx"
        d = Document()
        d.add_paragraph("END-SHIP-001 — Test")
        d.add_picture(str(png))
        d.save(docx)
        s = PROJECTS["endaria"]["sources"]
        self.atlas_id = s["visual_atlas_a"]["id"]
        self.registry_id = s["document_registry"]["id"]
        self.sourcebook_id = s["master_sourcebook"]["id"]
        snapshots = {
            self.registry_id: DriveSnapshot(self.registry_id, "v1", "Registry", [{"text":self.atlas_id}]),
            self.sourcebook_id: DriveSnapshot(self.sourcebook_id, "v1", "Sourcebook", [{"text":"END-SHIP-001 dossier"}]),
            self.atlas_id: DriveSnapshot(self.atlas_id, "v1", "Atlas", [{"text":"END-SHIP-001 — Test"}]),
        }
        self.transport = MockDrive(snapshots, docx.read_bytes())

    def test_integrated_retrieval(self):
        result = retrieve_asset_bundle("endaria", "END-SHIP-001", self.transport)
        self.assertEqual(result["image"]["width"], 30)
        self.assertEqual(result["status"], "SOURCE_AND_IMAGE_BYTES_RESOLVED_NOT_PROVIDER_DELIVERED")

    def test_persisted_reference_bytes(self):
        import hashlib
        target = Path(self.tmp.name) / 'private'
        result = retrieve_asset_bundle('endaria', 'END-SHIP-001', self.transport,
                                       private_output_dir=str(target))
        saved = Path(result['private_reference_path'])
        self.assertTrue(saved.is_file())
        self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(), result['image']['sha256'])

    def test_missing_sourcebook_blocks(self):
        self.transport.snapshots[self.sourcebook_id] = DriveSnapshot(
            self.sourcebook_id, "v1", "Sourcebook", [{"text":"other"}])
        with self.assertRaises(ValueError):
            retrieve_asset_bundle("endaria", "END-SHIP-001", self.transport)

    def test_export_drift_blocks(self):
        self.transport.export_revision = "v2"
        with self.assertRaises(RetrievalPipelineBlocked):
            retrieve_asset_bundle("endaria", "END-SHIP-001", self.transport)

    def test_new_asset_without_python_registry_entry(self):
        self.transport.snapshots[self.sourcebook_id] = DriveSnapshot(
            self.sourcebook_id, "v1", "Sourcebook", [{"text":"END-SHIP-999 dossier"}])
        self.transport.snapshots[self.atlas_id] = DriveSnapshot(
            self.atlas_id, "v1", "Atlas", [{"text":"END-SHIP-999 — Test"}])
        # The export still contains END-SHIP-001; correct fail-closed behavior.
        with self.assertRaises(ValueError):
            retrieve_asset_bundle("endaria", "END-SHIP-999", self.transport)

if __name__ == "__main__":
    unittest.main()
