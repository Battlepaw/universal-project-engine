"""Regressions for real image-byte extraction and gateway transfer; no paid API calls."""
import hashlib
from io import BytesIO
import tempfile
import unittest
from pathlib import Path
from docx import Document
from docx.shared import Inches
from PIL import Image as PILImage
from engine import PROJECTS
from visual_transport import extract_exact_approved_image, prepare_references, render_connector_job, download_signed_docx
from render_gateway import RenderBlocked, OpenAIImageEditProvider


def png(color):
    b = BytesIO()
    PILImage.new("RGB", (24, 24), color).save(b, format="PNG")
    return b.getvalue()


def atlas_docx(section, caption, image, *, delayed=False):
    d = Document()
    d.add_paragraph(section)
    d.add_paragraph(caption)
    if delayed:
        d.add_paragraph("Visual generation instruction guide")
        d.add_paragraph("The approved image is the master reference.")
    d.add_picture(BytesIO(image), width=Inches(1))
    b = BytesIO()
    d.save(b)
    return b.getvalue()


class VisualTransportTests(unittest.TestCase):
    def setUp(self):
        self.sources = PROJECTS["endaria"]["sources"]
        self.b = png((10, 30, 80))
        self.p = png((40, 130, 120))
        self.docs = {
            "character_visual_atlas": atlas_docx(
                'VIS-SD-001 — REBECCA "BECCA" MARSHALL',
                "Master image: author-approved 19 November 2026",
                self.b, delayed=True),
            "visual_atlas_a": atlas_docx(
                "SWEETWIND — APPROVED MESSENGER'S GUILD CREW PATCH",
                "Approved patch-system illustration:", self.p),
        }
        refs = []
        sources = []
        self.exports = []
        for key, role, aid, anchor, caption, blob in [
            ("character_visual_atlas", "character_master", "VIS-SD-001",
             'VIS-SD-001 — REBECCA "BECCA" MARSHALL',
             "Master image: author-approved 19 November 2026", self.b),
            ("visual_atlas_a", "unit_patch_master", "END-SHIP-001-PATCH",
             "SWEETWIND — APPROVED MESSENGER'S GUILD CREW PATCH",
             "Approved patch-system illustration:", self.p),
        ]:
            docid = self.sources[key]["id"]
            sources.append({"source_key": key, "document_id": docid, "revision_id": "rev-1",
                            "tab_id": "t0", "start_index": 1, "end_index": 40,
                            "exact_text": caption})
            refs.append({"asset_id": aid, "role": role, "source_key": key,
                         "document_id": docid, "revision_id": "rev-1",
                         "sha256": hashlib.sha256(blob).hexdigest(), "approval_status": "AUTHOR_APPROVED",
                         "section_anchor": anchor, "approval_caption": caption})
            self.exports.append({"source_key": key, "document_id": docid,
                                 "revision_id": "rev-1", "signed_download_url": "signed:" + key})
        self.job = {"project_id": "endaria", "subject_id": "VIS-SD-001",
                    "intent": "existing_character", "topic": "Becca Sweetwind patch",
                    "request_id": "beccatest", "scene_prompt": "Create working uniform turnaround.",
                    "source_evidence": sources, "approved_assets": refs,
                    "additional_required_roles": ["unit_patch_master"],
                    "visual_rules": [
                        {"rule_id": "likeness", "category": "identity",
                         "source_key": "character_visual_atlas", "instruction": "Keep approved face."},
                        {"rule_id": "patch", "category": "placement",
                         "source_key": "visual_atlas_a", "instruction": "Keep concentric patch."},
                    ]}
        self.downloader = lambda url: self.docs[url.split(":")[1]]

    def test_extracts_both_real_images_from_docx(self):
        for key, image in (("character_visual_atlas", self.b), ("visual_atlas_a", self.p)):
            asset = next(a for a in self.job["approved_assets"] if a["source_key"] == key)
            self.assertEqual(extract_exact_approved_image(self.docs[key],
                             anchor=asset["section_anchor"], caption=asset["approval_caption"]), image)

    def test_gateway_receives_both_verified_image_bytes(self):
        delivered = []
        class DummyProvider:
            def generate(self, *, prompt, references):
                delivered.extend(Path(r.path).read_bytes() for r in references)
                assert "Keep concentric patch" in prompt
                return self_result
        self_result = png((100, 100, 100))
        manifest, result_image = render_connector_job(job=self.job, exports=self.exports,
                                      provider=DummyProvider(), downloader=self.downloader)
        self.assertEqual(delivered, [self.b, self.p])
        self.assertEqual(result_image, self_result)
        self.assertEqual(manifest["status"], "GENERATED_UNAPPROVED")
        self.assertFalse(manifest["author_approval"])
        self.assertEqual(len(manifest["reference_hashes"]), 2)

    def test_bad_reference_hash_fail_closed(self):
        self.job["approved_assets"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RenderBlocked, "HASH_MISMATCH"):
                prepare_references(job=self.job, exports=self.exports,
                                   workspace=directory, downloader=self.downloader)

    def test_stale_export_revision_rejected(self):
        self.exports[0]["revision_id"] = "old"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RenderBlocked, "REVISION_MISMATCH"):
                prepare_references(job=self.job, exports=self.exports,
                                   workspace=directory, downloader=self.downloader)

    def test_unsigned_or_unknown_host_rejected(self):
        with self.assertRaisesRegex(RenderBlocked, "UNTRUSTED|ALLOWLISTED"):
            download_signed_docx("http://127.0.0.1/admin")
        with self.assertRaisesRegex(RenderBlocked, "ALLOWLISTED"):
            download_signed_docx("https://evil.example/files/123/raw?sig=x&se=y&sp=r")

    def test_retired_model_not_used(self):
        self.assertEqual(OpenAIImageEditProvider(api_key="mock").model, "gpt-image-2.6-sunburst")


if __name__ == "__main__":
    unittest.main()
