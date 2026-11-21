"""Read-only project boundary and evidence-routing tests."""
import unittest
from engine import PROJECTS, project_sources, plan_retrieval, inspect_drive_record


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.sid = PROJECTS["endaria"]["sources"]["master_sourcebook"]["id"]
        self.paras = [
            {"text": "Sweetwind has a polished ironwood hull.", "startIndex": 1, "endIndex": 42},
            {"text": "Other engineering references remain unresolved.", "startIndex": 42, "endIndex": 96},
        ]

    def test_project_manifest(self):
        result = project_sources("endaria")
        self.assertEqual(result["project_id"], "endaria")
        self.assertFalse(result["direct_google_drive_access"])
        self.assertGreaterEqual(len(result["sources"]), 4)

    def test_reject_unknown_project(self):
        with self.assertRaisesRegex(ValueError, "PROJECT_NOT_REGISTERED"):
            plan_retrieval("starborne", "Sweetwind")

    def test_required_read_order(self):
        r = plan_retrieval("endaria", "Sweetwind reference")
        self.assertEqual(r["steps"][0]["source_key"], "operations_manual")
        self.assertEqual(r["steps"][1]["source_key"], "document_registry")
        self.assertIn("character_visual_atlas", [s["source_key"] for s in r["steps"]])

    def test_source_identity_and_retrieval(self):
        r = inspect_drive_record("endaria", "master_sourcebook", self.sid, "revision-1",
                                 "ENDARIA Universe — Master Sourcebook", self.paras, "Sweetwind")
        self.assertEqual(r["status"], "CONNECTOR_DATA_MATCHED")
        self.assertEqual(r["matches"][0]["paragraph_position"], 0)
        self.assertIn("ironwood", r["matches"][0]["text"])

    def test_source_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_ID_MISMATCH"):
            inspect_drive_record("endaria", "master_sourcebook", "wrong", "rev", "t", self.paras, "Sweetwind")

    def test_revision_required(self):
        with self.assertRaisesRegex(ValueError, "REVISION_REQUIRED"):
            inspect_drive_record("endaria", "master_sourcebook", self.sid, "", "t", self.paras, "Sweetwind")

    def test_no_hallucinated_match(self):
        r = inspect_drive_record("endaria", "master_sourcebook", self.sid, "rev", "t", self.paras, "dragons")
        self.assertEqual(r["status"], "NO_MATCH_IN_SUBMITTED_PARAGRAPHS")

    def test_unknown_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_NOT_REGISTERED"):
            inspect_drive_record("endaria", "pocket_ventures", self.sid, "rev", "t", self.paras, "Sweetwind")

    def test_max_results_range(self):
        with self.assertRaisesRegex(ValueError, "MAX_RESULTS_RANGE"):
            inspect_drive_record("endaria", "master_sourcebook", self.sid, "rev", "t", self.paras, "Sweetwind", 100)

    def test_large_payload_rejected(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_PAYLOAD_TOO_LARGE"):
            inspect_drive_record("endaria", "master_sourcebook", self.sid, "rev", "t",
                                 [{"text": "x" * 1_200_001}], "x")

if __name__ == "__main__":
    unittest.main()
