import unittest
from adapter_integration import adapter_manifest


class AdapterIntegrationTests(unittest.TestCase):
    def test_endaria_adapter_registered(self):
        m = adapter_manifest("endaria")
        self.assertEqual(m["drive_archive_id"], "127qsaaOPtO6pxy5QzrMpjdJcl9yZlAxF")
        self.assertEqual(m["archive_size"], 12842090)
        self.assertFalse(m["asset_byte_transport_available"])
        self.assertFalse(m["generator_reference_conditioning_verified"])

    def test_other_projects_not_substituted(self):
        for project in ("starborne", "pocket_ventures", "", "ENDARIA"):
            with self.subTest(project=project):
                with self.assertRaisesRegex(ValueError, "ADAPTER_NOT_REGISTERED"):
                    adapter_manifest(project)


if __name__ == "__main__":
    unittest.main()
