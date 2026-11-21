"""Regression tests for source/asset/image preflight, including spoofed projects."""
import copy
import unittest
from engine import PROJECTS
from visual_gate import inspect_visual_work_order


class VisualGateTests(unittest.TestCase):
    def setUp(self):
        self.project = "endaria"
        sources = PROJECTS[self.project]["sources"]
        self.cond = {
            "project_id": self.project, "subject_id": "VIS-SD-001",
            "intent": "existing_character", "topic": "Becca Marshall Sweetwind uniform and patches",
            "source_evidence": [
                {"source_key": "character_visual_atlas",
                 "document_id": sources["character_visual_atlas"]["id"],
                 "revision_id": "live-test-rev-1", "tab_id": "t0",
                 "start_index": 1, "end_index": 60,
                 "exact_text": "VIS-SD-001 approved reference; preserve likeness."},
                {"source_key": "visual_atlas_a",
                 "document_id": sources["visual_atlas_a"]["id"],
                 "revision_id": "live-test-rev-2", "tab_id": "t0",
                 "start_index": 1, "end_index": 60,
                 "exact_text": "Sweetwind approved patch with concentric brocade backing."},
            ],
            "approved_assets": [
                {"asset_id": "VIS-SD-001", "role": "character_master",
                 "source_key": "character_visual_atlas",
                 "document_id": sources["character_visual_atlas"]["id"],
                 "revision_id": "live-test-rev-1",
                 "sha256": "1" * 64, "approval_status": "AUTHOR_APPROVED"},
                {"asset_id": "END-SHIP-001-PATCH", "role": "unit_patch_master",
                 "source_key": "visual_atlas_a",
                 "document_id": sources["visual_atlas_a"]["id"],
                 "revision_id": "live-test-rev-2",
                 "sha256": "2" * 64, "approval_status": "AUTHOR_APPROVED"},
            ],
            "visual_rules": [
                {"rule_id": "likeness", "category": "identity",
                 "instruction": "Face and dark blue-black hair must match approved character.",
                 "source_key": "character_visual_atlas"},
                {"rule_id": "patch", "category": "placement",
                 "instruction": "Right shoulder ship patch centered on bronze brocade backing.",
                 "source_key": "visual_atlas_a"},
            ],
            "additional_required_roles": ["unit_patch_master"],
        }

    def call(self, **changes):
        c = copy.deepcopy(self.cond)
        c.update(changes)
        return inspect_visual_work_order(**c)

    def test_positive_preflight_is_still_blocked_without_real_image_bytes(self):
        r = self.call()
        self.assertEqual(r["status"], "BLOCKED_REFERENCE_BYTES_AND_RENDER_TRANSPORT_NOT_VERIFIED")
        self.assertFalse(r["reference_image_bytes_received"])
        self.assertFalse(r["author_approval"])
        self.assertIn("visual_atlas_a", r["source_keys"])
        self.assertEqual(len(r["required_visual_checks"]), 2)

    def test_reject_source_from_other_project(self):
        p = copy.deepcopy(self.cond["source_evidence"])
        p[0]["document_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "SOURCE_ID_MISMATCH"):
            self.call(source_evidence=p)

    def test_reject_missing_character_reference(self):
        a = self.cond["approved_assets"][1:]
        with self.assertRaisesRegex(ValueError, "REQUIRED_IMAGE_REFERENCE_MISSING"):
            self.call(approved_assets=a)

    def test_reject_unapproved_asset(self):
        a = copy.deepcopy(self.cond["approved_assets"])
        a[0]["approval_status"] = "PROVISIONAL"
        with self.assertRaisesRegex(ValueError, "UNAPPROVED_REFERENCE"):
            self.call(approved_assets=a)

    def test_reject_stale_revision(self):
        a = copy.deepcopy(self.cond["approved_assets"])
        a[1]["revision_id"] = "stale-rev"
        with self.assertRaisesRegex(ValueError, "REFERENCE_SOURCE_REVISION_MISMATCH"):
            self.call(approved_assets=a)

    def test_reject_bad_hash(self):
        a = copy.deepcopy(self.cond["approved_assets"])
        a[1]["sha256"] = "not hash"
        with self.assertRaisesRegex(ValueError, "REFERENCE_SHA256_REQUIRED"):
            self.call(approved_assets=a)

    def test_reject_missing_rules(self):
        with self.assertRaisesRegex(ValueError, "VISUAL_RULES_REQUIRED"):
            self.call(visual_rules=[])

    def test_reject_missing_rule_source(self):
        a = copy.deepcopy(self.cond["visual_rules"])
        a[0]["source_key"] = "other_project_atlas"
        with self.assertRaisesRegex(ValueError, "VISUAL_RULE_SOURCE_MISSING"):
            self.call(visual_rules=a)

    def test_reject_unknown_project(self):
        with self.assertRaisesRegex(ValueError, "PROJECT_NOT_REGISTERED"):
            self.call(project_id="other_story")

    def test_reject_unspecified_grade_hierarchy(self):
        with self.assertRaisesRegex(ValueError, "IMAGE_INTENT_UNSUPPORTED"):
            self.call(intent="auto_invent_guild_lore")


if __name__ == "__main__":
    unittest.main()
