import json
import unittest
from unittest.mock import MagicMock
from drive_transport import ServiceAccountDriveTransport, DriveTransportUnavailable

CREDS = json.dumps({"type":"service_account","client_email":"unit@example.invalid","private_key":"dummy"})
class DriveTransportTests(unittest.TestCase):
    def setUp(self):
        self.docs = MagicMock()
        self.drive = MagicMock()
        self.transport = ServiceAccountDriveTransport(
            credential_json=CREDS,
            service_factory=lambda name, version: self.docs if name == "docs" else self.drive)

    def test_no_credentials_blocks(self):
        with self.assertRaises(DriveTransportUnavailable):
            ServiceAccountDriveTransport(credential_json="")

    def test_live_read(self):
        self.docs.documents().get().execute.return_value = {
            "title":"Atlas", "body":{"content":[{"paragraph":{"elements":[{"textRun":{"content":"END-SHIP-001"}}]}}]}}
        self.drive.files().get().execute.return_value = {
            "id":"doc1","version":"8","mimeType":"application/vnd.google-apps.document"}
        snap = self.transport.read_document("doc1")
        self.assertEqual(snap.revision_id, "8")
        self.assertIn("END-SHIP-001", snap.paragraphs[0]["text"])

    def test_export_revision_stable(self):
        self.drive.files().get().execute.side_effect = [
            {"id":"doc1","version":"8"}, {"id":"doc1","version":"8"}]
        self.drive.files().export().execute.return_value = b"PK\x03\x04docx"
        content, version = self.transport.export_docx("doc1")
        self.assertEqual(version, "8")
        self.assertTrue(content.startswith(b"PK"))

    def test_export_revision_drift_blocks(self):
        self.drive.files().get().execute.side_effect = [
            {"id":"doc1","version":"8"}, {"id":"doc1","version":"9"}]
        self.drive.files().export().execute.return_value = b"PK\x03\x04docx"
        with self.assertRaises(DriveTransportUnavailable):
            self.transport.export_docx("doc1")

if __name__ == "__main__":
    unittest.main()
