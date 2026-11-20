"""Resolve a Sourcebook + Atlas + binary reference as one production dependency.

The caller must obtain all inputs from authenticated Google Drive reads and
exports. No caller-supplied metadata is treated as Google-authenticated here.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import re
from atlas_binary import extract_assets, AtlasExtractionError
from registry_resolver import resolve_asset_dependencies
from engine import _project

class ProductionBundleBlocked(ValueError):
    pass

def prepare_production_bundle(*, project_id: str, asset_id: str,
                              registry_document_id: str, registry_revision_id: str,
                              registry_paragraphs: list[dict],
                              sourcebook_document_id: str, sourcebook_revision_id: str,
                              sourcebook_paragraphs: list[dict],
                              atlas_source_key: str, atlas_document_id: str,
                              atlas_revision_id: str, atlas_paragraphs: list[dict],
                              atlas_docx_path: str,
                              export_attestation: dict) -> dict:
    sources = _project(project_id)["sources"]
    sourcebook = sources.get("master_sourcebook")
    if not sourcebook or sourcebook_document_id != sourcebook["id"] or not sourcebook_revision_id:
        raise ProductionBundleBlocked("SOURCEBOOK_ID_OR_REVISION_MISMATCH")
    if not isinstance(sourcebook_paragraphs, list) or not sourcebook_paragraphs:
        raise ProductionBundleBlocked("SOURCEBOOK_CONTENT_MISSING")
    canon = "\n".join(p.get("text", "") for p in sourcebook_paragraphs if isinstance(p, dict))
    if not re.search(r"(?<![A-Z0-9-])" + re.escape(asset_id) + r"(?![A-Z0-9-])", canon):
        raise ProductionBundleBlocked("ASSET_NOT_IN_SOURCEBOOK")
    atlas_record = {"source_key": atlas_source_key, "document_id": atlas_document_id,
                    "revision_id": atlas_revision_id, "paragraphs": atlas_paragraphs}
    resolution = resolve_asset_dependencies(project_id, asset_id, registry_document_id,
                                             registry_revision_id, registry_paragraphs,
                                             [atlas_record])
    if resolution["status"] != "ATLAS_RECORD_LOCATED_IMAGE_BYTES_NOT_VERIFIED":
        raise ProductionBundleBlocked("ATLAS_NOT_RESOLVED:" + ",".join(resolution.get("blockers", [])))
    if not isinstance(export_attestation, dict):
        raise ProductionBundleBlocked("EXPORT_ATTESTATION_REQUIRED")
    if export_attestation.get("document_id") != atlas_document_id or export_attestation.get("revision_id") != atlas_revision_id:
        raise ProductionBundleBlocked("EXPORT_SOURCE_OR_REVISION_MISMATCH")
    if export_attestation.get("authenticated_export") is not True:
        raise ProductionBundleBlocked("EXPORT_AUTHENTICATION_NOT_ATTESTED")
    path = Path(atlas_docx_path)
    if not path.is_file():
        raise ProductionBundleBlocked("EXPORT_MISSING")
    export_hash = sha256(path.read_bytes()).hexdigest()
    if export_attestation.get("sha256") != export_hash:
        raise ProductionBundleBlocked("EXPORT_HASH_MISMATCH")
    try:
        asset = extract_assets(path, asset_id)[0]
    except AtlasExtractionError as exc:
        raise ProductionBundleBlocked(str(exc)) from exc
    return {"project_id": project_id, "asset_id": asset_id,
            "status": "SOURCE_AND_IMAGE_BYTES_RESOLVED_NOT_PROVIDER_DELIVERED",
            "sourcebook": {"document_id": sourcebook_document_id, "revision_id": sourcebook_revision_id},
            "registry": {"document_id": registry_document_id, "revision_id": registry_revision_id},
            "atlas": {"document_id": atlas_document_id, "revision_id": atlas_revision_id,
                      "source_key": atlas_source_key, "export_sha256": export_hash},
            "image": asset.metadata(),
            "provider_reference_receipt": None,
            "visual_approval_verified": False,
            "note": "Authenticated provenance and approval require trusted connector checks; caller-supplied attestation is not independently authenticated."}
