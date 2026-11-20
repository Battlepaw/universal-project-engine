import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from production_job import run_production_job, ProductionJobBlocked

class ProductionJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.image = Path(self.tmp.name) / "ref.png"
        Image.new("RGB", (10, 10)).save(self.image)
        import hashlib
        self.hash = hashlib.sha256(self.image.read_bytes()).hexdigest()

    def bundle(self, project_id, asset_id, transport, private_output_dir):
        return {"asset_id":asset_id,
                "status":"SOURCE_AND_IMAGE_BYTES_RESOLVED_NOT_PROVIDER_DELIVERED",
                "private_reference_path":str(self.image),
                "image":{"sha256":self.hash},
                "sourcebook":{"revision_id":"v1"},
                "atlas":{"revision_id":"v1"}}

    def provider(self, prompt, references):
        self.assertEqual(len(references), 2)
        self.assertEqual(references[0]["sha256"], self.hash)
        return {"status":"PROVIDER_ACCEPTED_REFERENCE_REQUEST",
                "output_bytes":self.image.read_bytes()}

    def test_full_job_with_two_references(self):
        with patch("production_job.retrieve_asset_bundle", side_effect=self.bundle):
            result = run_production_job(project_id="endaria",
                asset_ids=["END-SHIP-001","VIS-SD-001"], prompt="Six panels",
                private_output_dir=self.tmp.name, request_id="intro-01", provider=self.provider)
        self.assertEqual(result["status"], "GENERATED_UNAPPROVED")
        self.assertTrue((Path(self.tmp.name) / "intro-01.png").exists())
        self.assertTrue((Path(self.tmp.name) / "intro-01.json").exists())
        self.assertFalse(result["author_approved"])

    def test_duplicate_assets_block(self):
        with self.assertRaises(ProductionJobBlocked):
            run_production_job(project_id="endaria",
                asset_ids=["VIS-SD-001","VIS-SD-001"], prompt="Test",
                private_output_dir=self.tmp.name, request_id="intro-01", provider=self.provider)

if __name__ == "__main__":
    unittest.main()
