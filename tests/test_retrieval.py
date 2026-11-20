"""Regression checks for connector-mediated retrieval. Run: python -m unittest discover -s tests"""
import unittest
from engine import project_sources, plan_retrieval, inspect_drive_record


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.source = next(s for s in project_sources("endaria")["sources"] if s["source_key"] == "operations_manual")
        self.kw = dict(project_id="endaria", source_key="operations_manual",
                       document_id=self.source["document_id"], revision_id="rev-test",
                       title="Operations Manual", paragraphs=[{"text": "Sweetwind visual rules and source evidence", "startIndex": 1, "endIndex": 44}],
                       query="Sweetwind")

    def test_registered_sources(self):
        self.assertEqual(len(project_sources("endaria")["sources"]), 5)

    def test_unknown_project_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "PROJECT_NOT_REGISTERED"):
            project_sources("starborne")

    def test_unknown_source_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_NOT_REGISTERED"):
            inspect_drive_record(**{**self.kw, "source_key": "other"})

    def test_wrong_document_id_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_ID_MISMATCH"):
            inspect_drive_record(**{**self.kw, "document_id": "wrong"})

    def test_missing_revision_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "REVISION_REQUIRED"):
            inspect_drive_record(**{**self.kw, "revision_id": ""})

    def test_matching_evidence_is_not_claimed_as_authenticated(self):
        result = inspect_drive_record(**self.kw)
        self.assertEqual(result["status"], "CONNECTOR_DATA_MATCHED")
        self.assertEqual(result["verification"], "REGISTERED_SOURCE_ID_AND_SUBMITTED_TEXT_ONLY")
        self.assertEqual(len(result["matches"]), 1)

    def test_no_match(self):
        result = inspect_drive_record(**{**self.kw, "query": "unrelated"})
        self.assertEqual(result["status"], "NO_MATCH_IN_SUBMITTED_PARAGRAPHS")

    def test_invalid_paragraph(self):
        with self.assertRaisesRegex(ValueError, "INVALID_PARAGRAPH_RECORD"):
            inspect_drive_record(**{**self.kw, "paragraphs": [{"text": 4}]})

    def test_oversized_payload(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_PAYLOAD_TOO_LARGE"):
            inspect_drive_record(**{**self.kw, "paragraphs": [{"text": "x" * 1200001}]})

    def test_visual_retrieval_plan_includes_atlas(self):
        result = plan_retrieval("endaria", "Sweetwind visual reference")
        self.assertIn("character_visual_atlas", [s["source_key"] for s in result["steps"]])
        self.assertIn("visual_atlas_a", [s["source_key"] for s in result["steps"]])
        self.assertEqual(result["status"], "LIVE_CONNECTOR_RETRIEVAL_REQUIRED")


if __name__ == "__main__":
    unittest.main()
