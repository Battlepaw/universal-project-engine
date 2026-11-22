"""Authenticated-connector handoff into the existing approved-image rendering path.

The connected ChatGPT Google Drive tool reads a live revision and exports DOCX.
This bridge accepts only temporary signed file transport URLs, verifies the
approved image bytes and hashes, and supplies them to the image-edit provider.
The server does not possess Google's OAuth token. Caller evidence is NOT a
cryptographic attestation of a Google Docs revision.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPRedirectHandler, Request
from zipfile import ZipFile, BadZipFile
import hashlib
import json
import re

from docx import Document
from visual_gate import inspect_visual_work_order
from render_gateway import RenderReference, OpenAIImageEditProvider, render_staged, RenderBlocked


class _DenyRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise RenderBlocked("SIGNED_URL_REDIRECT_BLOCKED")


def download_signed_docx(url: str, *, max_bytes: int = 25_000_000) -> bytes:
    """Accept only short-lived signed connector downloads, not arbitrary URLs."""
    if not isinstance(url, str) or len(url) > 4096:
        raise RenderBlocked("EXPORT_URL_INVALID")
    u = urlparse(url)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or u.username or u.password or u.port not in (None, 443):
        raise RenderBlocked("EXPORT_URL_UNTRUSTED")
    if not re.fullmatch(r"sdmntpr[a-z0-9-]+\.oaiusercontent\.com", host):
        raise RenderBlocked("EXPORT_HOST_NOT_ALLOWLISTED")
    if not re.fullmatch(r"/files/[a-zA-Z0-9_-]+/raw", u.path):
        raise RenderBlocked("EXPORT_PATH_NOT_ALLOWLISTED")
    if not all(p in u.query for p in ("sig=", "se=", "sp=")):
        raise RenderBlocked("EXPORT_UNSIGNED")
    request = Request(url, headers={"Accept": "application/octet-stream"})
    with build_opener(_DenyRedirects).open(request, timeout=30) as response:
        if response.status != 200:
            raise RenderBlocked("EXPORT_HTTP_ERROR")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RenderBlocked("EXPORT_TOO_LARGE")
    try:
        with ZipFile(BytesIO(data)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise RenderBlocked("NOT_DOCX_EXPORT")
    except BadZipFile as exc:
        raise RenderBlocked("NOT_DOCX_EXPORT") from exc
    return data


def extract_exact_approved_image(docx_bytes: bytes, *, anchor: str, caption: str) -> bytes:
    """Use source-section identity plus precise caption; never choose first image."""
    if not anchor or not caption:
        raise RenderBlocked("IMAGE_ANCHOR_AND_CAPTION_REQUIRED")
    doc = Document(BytesIO(docx_bytes))
    paras = doc.paragraphs
    starts = [i for i, p in enumerate(paras) if p.text.strip().casefold().startswith(anchor.strip().casefold())]
    if len(starts) != 1:
        raise RenderBlocked("SECTION_ANCHOR_NOT_UNIQUE")
    start = starts[0]
    end = next((i for i in range(start + 1, len(paras)) if
        (paras[i].style.name.startswith("Heading") and paras[i].text.strip()) or
        (paras[i].text.strip().startswith(("END-", "VIS-")) and " — " in paras[i].text)),
        len(paras))
    if caption.casefold() not in "\n".join(p.text for p in paras[start:end]).casefold():
        raise RenderBlocked("APPROVAL_CAPTION_OUTSIDE_SECTION")
    embed_key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
    matches = []
    for index in range(start + 1, end):
        p = paras[index]
        for blip in p._p.xpath(".//a:blip"):
            rid = blip.get(embed_key)
            if rid not in doc.part.rels:
                raise RenderBlocked("IMAGE_RELATION_UNRESOLVED")
            label = next((paras[j].text.strip() for j in range(index-1, start-1, -1) if paras[j].text.strip()), "")
            if label.casefold() == caption.strip().casefold():
                matches.append(doc.part.related_parts[rid].blob)
    if len(matches) != 1:
        raise RenderBlocked("APPROVED_CAPTION_IMAGE_NOT_UNIQUE")
    if not (matches[0].startswith(b"\x89PNG\r\n\x1a\n") or matches[0].startswith(b"\xff\xd8\xff")):
        raise RenderBlocked("APPROVED_IMAGE_FORMAT_UNSUPPORTED")
    return matches[0]


def prepare_references(*, job: dict, exports: list[dict], workspace: str,
                       downloader=download_signed_docx) -> tuple[list[RenderReference], dict]:
    """Fail closed on missing revision-bound source evidence and byte mismatches."""
    result = inspect_visual_work_order(
        project_id=job["project_id"], subject_id=job["subject_id"],
        intent=job["intent"], topic=job["topic"],
        source_evidence=job["source_evidence"], approved_assets=job["approved_assets"],
        visual_rules=job["visual_rules"],
        additional_required_roles=job.get("additional_required_roles"),
    )
    # This metadata-only preflight intentionally says BLOCKED. We now supply
    # actual bytes and verify each approved reference before allowing transport.
    if result["status"] != "BLOCKED_REFERENCE_BYTES_AND_RENDER_TRANSPORT_NOT_VERIFIED":
        raise RenderBlocked("PREFLIGHT_STATUS_UNEXPECTED")
    by_source = {}
    for export in exports:
        key = export.get("source_key")
        if key in by_source or not key:
            raise RenderBlocked("DUPLICATE_OR_MISSING_EXPORT")
        if not isinstance(export.get("revision_id"), str):
            raise RenderBlocked("EXPORT_REVISION_REQUIRED")
        by_source[key] = export
    cache = {}
    refs = []
    for asset in job["approved_assets"]:
        key = asset["source_key"]
        export = by_source.get(key)
        if export is None or export.get("document_id") != asset["document_id"] or export.get("revision_id") != asset["revision_id"]:
            raise RenderBlocked("REFERENCE_EXPORT_ID_OR_REVISION_MISMATCH")
        if key not in cache:
            cache[key] = downloader(export["signed_download_url"])
        data = extract_exact_approved_image(cache[key], anchor=asset.get("section_anchor"),
                                           caption=asset.get("approval_caption"))
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != asset["sha256"]:
            raise RenderBlocked("APPROVED_REFERENCE_HASH_MISMATCH")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", asset["asset_id"]):
            raise RenderBlocked("INVALID_ASSET_NAME")
        path = Path(workspace) / (asset["asset_id"] + (".png" if data.startswith(b"\x89PNG") else ".jpg"))
        path.write_bytes(data)
        refs.append(RenderReference(asset_id=asset["asset_id"], path=str(path), sha256=actual_hash))
    return refs, {"source_keys": result["source_keys"], "asset_hashes": {ref.asset_id: ref.sha256 for ref in refs},
                  "status": "REFERENCE_BYTES_HASH_MATCHED", "source_authentication": "CONNECTOR_ATTESTATION_EXTERNAL"}


def render_connector_job(*, job: dict, exports: list[dict], provider=None,
                         downloader=download_signed_docx) -> tuple[dict, bytes]:
    """Full verified-byte render path; output is always GENERATED_UNAPPROVED."""
    if not isinstance(job, dict) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", job.get("request_id", "")):
        raise RenderBlocked("INVALID_REQUEST_ID")
    scene = job.get("scene_prompt")
    if not isinstance(scene, str) or not scene.strip():
        raise RenderBlocked("SCENE_PROMPT_REQUIRED")
    with TemporaryDirectory(prefix="upe_visual_") as temp:
        refs, evidence = prepare_references(job=job, exports=exports, workspace=temp, downloader=downloader)
        rules = "\n".join(f"- [{r['rule_id']}] {r['instruction']}" for r in job["visual_rules"])
        prompt = ("EDIT WITH ALL SUPPLIED AUTHOR-APPROVED IMAGES AS PRIMARY REFERENCES. "
                  "Preserve identity, equipment and insignia geometry. Never invent new ranks, patches, "
                  "heraldry or ornamental elements. Required checks:\n" + rules +
                  "\nRequested edit:\n" + scene +
                  "\nAny output remains UNAPPROVED pending author review.")
        manifest = render_staged(request_id=job["request_id"], prompt=prompt,
            references=refs, provider=provider or OpenAIImageEditProvider(), output_dir=temp)
        blob = Path(manifest["output_file"]).read_bytes()
        manifest.pop("output_file")
        manifest["project_id"] = job["project_id"]
        manifest["subject_id"] = job["subject_id"]
        manifest["evidence"] = evidence
        manifest["visual_checks"] = {r["rule_id"]: "PENDING_REVIEW" for r in job["visual_rules"]}
        return manifest, blob
