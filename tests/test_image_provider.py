import base64
import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from image_provider import send_image_edit, ProviderTransportBlocked

class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "ref.png"
        Image.new("RGB", (16, 16)).save(self.path)
        self.ref = {"asset_id":"VIS-SD-001","private_reference_path":str(self.path),
                    "sha256":hashlib.sha256(self.path.read_bytes()).hexdigest()}

    def test_actual_bytes_sent(self):
        def fake(url, data, headers):
            self.assertIn(self.path.read_bytes(), data)
            self.assertIn(b'image[]', data)
            self.assertTrue(url.startswith("https://api.openai.com/"))
            return json.dumps({"data":[{"b64_json":base64.b64encode(self.path.read_bytes()).decode()}]}).encode()
        result = send_image_edit(prompt="Test", references=[self.ref], api_key="test", sender=fake)
        self.assertEqual(result["status"], "PROVIDER_ACCEPTED_REFERENCE_REQUEST")
        self.assertEqual(result["references"][0]["sha256"], self.ref["sha256"])
        self.assertFalse(result["visual_fidelity_verified"])

    def test_no_key_blocks(self):
        with self.assertRaises(ProviderTransportBlocked):
            send_image_edit(prompt="Test", references=[self.ref], api_key="", sender=lambda *a: b"{}")

    def test_mismatched_hash_blocks(self):
        self.ref["sha256"] = "0"*64
        with self.assertRaises(ProviderTransportBlocked):
            send_image_edit(prompt="Test", references=[self.ref], api_key="test", sender=lambda *a: b"{}")

if __name__ == "__main__":
    unittest.main()
