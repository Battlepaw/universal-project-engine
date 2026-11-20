import unittest
from engine import PROJECTS
from registry_resolver import resolve_asset_dependencies, RegistryResolutionError

REG = PROJECTS["endaria"]["sources"]
def atlas(key, text, revision="r2"):
    return {"source_key": key, "document_id": REG[key]["id"], "revision_id": revision,
            "paragraphs": [{"text": text}]}

class RegistryResolverTests(unittest.TestCase):
    def setUp(self):
        self.args = dict(project_id="endaria", asset_id="END-SHIP-001",
                         registry_document_id=REG["document_registry"]["id"],
                         registry_revision_id="r1",
                         registry_paragraphs=[{"text": "Visual Atlas A: " + REG["visual_atlas_a"]["id"]}],
                         atlas_records=[atlas("visual_atlas_a", "END-SHIP-001 — SWEETWIND")])

    def test_dynamic_asset_discovery(self):
        self.assertEqual(resolve_asset_dependencies(**self.args)["status"], "ATLAS_RECORD_LOCATED_IMAGE_BYTES_NOT_VERIFIED")

    def test_future_asset_id_without_code_edit(self):
        self.args["asset_id"] = "END-SHIP-999"
        self.args["atlas_records"] = [atlas("visual_atlas_a", "END-SHIP-999 — NEW SHIP")]
        self.assertEqual(resolve_asset_dependencies(**self.args)["atlas"]["asset_id"], "END-SHIP-999")

    def test_missing_asset_blocks(self):
        self.args["asset_id"] = "END-SHIP-002"
        self.assertEqual(resolve_asset_dependencies(**self.args)["status"], "BLOCKED")

    def test_wrong_registry_blocks(self):
        self.args["registry_document_id"] = "wrong"
        with self.assertRaises(RegistryResolutionError):
            resolve_asset_dependencies(**self.args)

    def test_unregistered_atlas_blocks(self):
        self.args["atlas_records"][0]["document_id"] = "wrong"
        with self.assertRaises(RegistryResolutionError):
            resolve_asset_dependencies(**self.args)

    def test_duplicate_atlas_match_blocks(self):
        self.args["atlas_records"].append(atlas("character_visual_atlas", "END-SHIP-001"))
        with self.assertRaises(RegistryResolutionError):
            resolve_asset_dependencies(**self.args)

    def test_unlisted_atlas_blocks(self):
        self.args["registry_paragraphs"] = [{"text": "no approved atlas"}]
        self.assertEqual(resolve_asset_dependencies(**self.args)["blockers"], ["ATLAS_NOT_IN_LIVE_REGISTRY"])

    def test_cross_project_blocks(self):
        self.args["project_id"] = "starborne"
        with self.assertRaises(ValueError):
            resolve_asset_dependencies(**self.args)

if __name__ == "__main__":
    unittest.main()
