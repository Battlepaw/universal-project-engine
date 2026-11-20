"""Optional server-side Google Drive transport for the shared retrieval engine.

Uses an explicitly provisioned Google service account, never ChatGPT OAuth.
The account must be granted access to each project document. Private bytes
must not be exposed through unauthenticated MCP tools.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass

class DriveTransportUnavailable(RuntimeError):
    pass

@dataclass(frozen=True)
class DriveSnapshot:
    document_id: str
    revision_id: str
    title: str
    paragraphs: list[dict]

class ServiceAccountDriveTransport:
    def __init__(self, credential_json: str | None = None, service_factory=None):
        raw = credential_json if credential_json is not None else os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not raw:
            raise DriveTransportUnavailable("GOOGLE_SERVICE_ACCOUNT_NOT_CONFIGURED")
        try:
            info = json.loads(raw)
            if info.get("type") != "service_account" or not info.get("client_email") or not info.get("private_key"):
                raise ValueError("incomplete service account")
        except (ValueError, TypeError) as exc:
            raise DriveTransportUnavailable("GOOGLE_SERVICE_ACCOUNT_INVALID") from exc
        if service_factory is None:
            try:
                from google.oauth2.service_account import Credentials
                from googleapiclient.discovery import build
            except ImportError as exc:
                raise DriveTransportUnavailable("GOOGLE_API_DEPENDENCIES_MISSING") from exc
            credentials = Credentials.from_service_account_info(info, scopes=[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/documents.readonly"])
            service_factory = lambda name, version: build(name, version, credentials=credentials, cache_discovery=False)
        self._docs = service_factory("docs", "v1")
        self._drive = service_factory("drive", "v3")

    def read_document(self, document_id: str) -> DriveSnapshot:
        if not document_id or "/" in document_id:
            raise DriveTransportUnavailable("INVALID_DOCUMENT_ID")
        document = self._docs.documents().get(documentId=document_id, includeTabsContent=True).execute()
        paragraphs = []
        def visit(elements):
            for element in elements or []:
                p = element.get("paragraph")
                if p:
                    text = "".join(t.get("textRun", {}).get("content", "") for t in p.get("elements", []))
                    if text:
                        paragraphs.append({"text": text, "startIndex": element.get("startIndex"),
                                           "endIndex": element.get("endIndex")})
                table = element.get("table")
                if table:
                    for row in table.get("tableRows", []):
                        for cell in row.get("tableCells", []):
                            visit(cell.get("content", []))
        tabs = document.get("tabs")
        if tabs:
            def visit_tabs(items):
                for tab in items:
                    visit(tab.get("documentTab", {}).get("body", {}).get("content", []))
                    visit_tabs(tab.get("childTabs", []))
            visit_tabs(tabs)
        else:
            visit(document.get("body", {}).get("content", []))
        metadata = self._drive.files().get(fileId=document_id, fields="id,name,version,mimeType").execute()
        if metadata.get("id") != document_id or metadata.get("mimeType") != "application/vnd.google-apps.document":
            raise DriveTransportUnavailable("DOCUMENT_ID_OR_TYPE_MISMATCH")
        revision = str(metadata.get("version", ""))
        if not revision:
            raise DriveTransportUnavailable("DOCUMENT_REVISION_UNAVAILABLE")
        return DriveSnapshot(document_id, revision, document.get("title", ""), paragraphs)

    def export_docx(self, document_id: str) -> tuple[bytes, str]:
        before = self._drive.files().get(fileId=document_id, fields="id,version").execute()
        content = self._drive.files().export(
            fileId=document_id, mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ).execute()
        after = self._drive.files().get(fileId=document_id, fields="id,version").execute()
        if before.get("id") != document_id or before.get("version") != after.get("version"):
            raise DriveTransportUnavailable("EXPORT_REVISION_CHANGED_RETRY")
        if not isinstance(content, bytes) or not content.startswith(b"PK"):
            raise DriveTransportUnavailable("EXPORT_INVALID_DOCX")
        return content, str(after["version"])
