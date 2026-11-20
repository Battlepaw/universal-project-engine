import unittest
from adapter_integration import adapter_manifest, asset_reference_manifest


class AdapterIntegrationTests(unittest.TestCase):
    def test_endaria_adapter_registered(self):
        m = adapter_manifest("endaria")
        self.assertEqual(m["drive_archive_id"], "127qsaaOPtO6pxy5QzrMpjdJcl9yZlAxF")
        self.assertEqual(m["archive_size"], 12842090)
        self.assertFalse(m["asset_byte_transport_available"])
        self.assertFalse(m["generator_reference_conditioning_verified"])

    def test_archive_fingerprints(self):
        sweetwind = asset_reference_manifest("endaria", "END-SHIP-001")
        self.assertEqual(sweetwind["sha256"], "675d60f418708387b484d5e46969ae9d252cf93b3402ecadea75e1138bea29fa")
        self.assertFalse(sweetwind["image_bytes_in_response"])
        self.assertEqual(asset_reference_manifest("endaria", "VIS-SD-001")["atlas_source_key"], "character_visual_atlas")

    def test_unregistered_asset_rejected(self):
        with self.assertRaisesRegex(ValueError, "ASSET_NOT_REGISTERED"):
            asset_reference_manifest("endaria", "unknown")

    def test_other_projects_not_substituted(self):
        for project in ("starborne", "pocket_ventures", "", "ENDARIA"):
            with self.subTest(project=project):
                with self.assertRaisesRegex(ValueError, "ADAPTER_NOT_REGISTERED"):
                    adapter_manifest(project)


if __name__ == "__main__":
    unittest.main()
