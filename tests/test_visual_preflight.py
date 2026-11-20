import unittest
from visual_preflight import check_visual_preflight, VisualPreflightBlocked
from adapter_integration import asset_reference_manifest

class VisualPreflightTests(unittest.TestCase):
    def test_blocks_text_only_render(self):
        result = check_visual_preflight("endaria", ["END-SHIP-001", "VIS-SD-001"], source_verified=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(len(result["blocking_reasons"]), 2)

    def test_blocks_unverified_source(self):
        result = check_visual_preflight("endaria", ["END-SHIP-001"])
        self.assertIn("SOURCE_EVIDENCE_NOT_VERIFIED", result["blocking_reasons"])

    def test_blocks_mismatched_reference(self):
        result = check_visual_preflight("endaria", ["END-SHIP-001"], [{"asset_id": "END-SHIP-001", "sha256": "wrong", "accepted": True, "reference_handle": "h"}], True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_valid_receipt_is_not_visual_approval(self):
        a = asset_reference_manifest("endaria", "END-SHIP-001")
        result = check_visual_preflight("endaria", ["END-SHIP-001"], [{"asset_id": "END-SHIP-001", "sha256": a["sha256"], "accepted": True, "reference_handle": "h"}], True)
        self.assertEqual(result["status"], "READY_FOR_EXPLORATORY_RENDER")
        self.assertFalse(result["author_approved"])
        self.assertFalse(result["visual_fidelity_verified"])

    def test_reject_other_projects(self):
        with self.assertRaises(VisualPreflightBlocked):
            check_visual_preflight("starborne", ["END-SHIP-001"])

    def test_reject_unknown_asset(self):
        with self.assertRaisesRegex(ValueError, "ASSET_NOT_REGISTERED"):
            check_visual_preflight("endaria", ["not-registered"])

if __name__ == "__main__":
    unittest.main()
