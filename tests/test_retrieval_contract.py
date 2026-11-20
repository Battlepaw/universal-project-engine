import hashlib
import unittest
from retrieval_contract import verify_bundle, RetrievalGateError

def sha(x):
    return hashlib.sha256(x).hexdigest()

class UnifiedRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.deps = [
            {"key": "canon", "kind": "text", "source_id": "sourcebook"},
            {"key": "portrait", "kind": "image", "source_id": "atlas", "sha256": sha(b"approved")},
        ]
        self.records = [
            {"key": "canon", "project_id": "endaria", "kind": "text", "source_id": "sourcebook", "revision_id": "r1", "content": "chapter", "payload_sha256": sha(b"chapter")},
            {"key": "portrait", "project_id": "endaria", "kind": "image", "source_id": "atlas", "revision_id": "r2", "content": b"approved", "payload_sha256": sha(b"approved")},
        ]

    def test_mixed_bundle(self):
        self.assertEqual(verify_bundle("endaria", self.deps, self.records)["status"], "RESOLVED")

    def test_missing_image_blocks(self):
        self.assertEqual(verify_bundle("endaria", self.deps, self.records[:1])["status"], "BLOCKED")

    def test_project_isolation(self):
        self.assertEqual(verify_bundle("starborne", self.deps, self.records)["status"], "BLOCKED")

    def test_binary_hash_mismatch(self):
        self.records[1]["content"] = b"other"
        self.assertEqual(verify_bundle("endaria", self.deps, self.records)["blockers"][0]["reason"], "CONTENT_HASH_MISMATCH")

    def test_revision_drift(self):
        self.deps[0]["revision_id"] = "old"
        self.assertEqual(verify_bundle("endaria", self.deps, self.records)["blockers"][0]["reason"], "REVISION_CHANGED")

    def test_no_digest_only_asset(self):
        del self.records[1]["content"]
        self.assertEqual(verify_bundle("endaria", self.deps, self.records)["blockers"][0]["reason"], "BINARY_BYTES_NOT_VERIFIED")

    def test_duplicate_evidence_rejected(self):
        with self.assertRaises(RetrievalGateError):
            verify_bundle("endaria", self.deps, self.records + self.records[:1])

    def test_duplicate_dependencies_rejected(self):
        with self.assertRaises(RetrievalGateError):
            verify_bundle("endaria", self.deps + self.deps[:1], self.records)

if __name__ == "__main__":
    unittest.main()
