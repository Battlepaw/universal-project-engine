"""Project-neutral registry-driven source/asset routing.

An authenticated connector supplies the live registry and Atlas paragraphs.
This planner validates their source IDs against the project's bootstrap registry
and resolves references dynamically; no per-asset Python registration required.
"""
from __future__ import annotations
import re
from engine import PROJECTS, _project

class RegistryResolutionError(ValueError):
    pass

def resolve_asset_dependencies(project_id: str, asset_id: str,
                               registry_document_id: str, registry_revision_id: str,
                               registry_paragraphs: list[dict],
                               atlas_records: list[dict]) -> dict:
    project = _project(project_id)
    if not isinstance(asset_id, str) or not re.fullmatch(r"[A-Z][A-Z0-9-]{2,80}", asset_id):
        raise RegistryResolutionError("INVALID_ASSET_ID")
    registry = project["sources"].get("document_registry")
    if not registry or registry_document_id != registry["id"] or not registry_revision_id:
        raise RegistryResolutionError("REGISTRY_ID_OR_REVISION_MISMATCH")
    if not isinstance(registry_paragraphs, list) or len(registry_paragraphs) > 6000:
        raise RegistryResolutionError("INVALID_REGISTRY")
    registry_text = "\n".join(p.get("text", "") for p in registry_paragraphs if isinstance(p, dict))
    if not registry_text or len(registry_text) > 1_200_000:
        raise RegistryResolutionError("EMPTY_OR_OVERSIZED_REGISTRY")
    matches = []
    for item in atlas_records:
        if not isinstance(item, dict):
            raise RegistryResolutionError("INVALID_ATLAS_RECORD")
        key = item.get("source_key")
        source = project["sources"].get(key)
        if not source or source.get("role", "").find("visual") < 0:
            raise RegistryResolutionError("UNREGISTERED_ATLAS")
        if item.get("document_id") != source["id"] or not item.get("revision_id"):
            raise RegistryResolutionError("ATLAS_ID_OR_REVISION_MISMATCH")
        paragraphs = item.get("paragraphs")
        if not isinstance(paragraphs, list) or len(paragraphs) > 6000:
            raise RegistryResolutionError("INVALID_ATLAS_PARAGRAPHS")
        content = "\n".join(p.get("text", "") for p in paragraphs if isinstance(p, dict))
        if len(content) > 1_200_000:
            raise RegistryResolutionError("OVERSIZED_ATLAS")
        # Anchor to a stable identifier, never fuzzy name matching.
        if re.search(r"(?<![A-Z0-9-])" + re.escape(asset_id) + r"(?![A-Z0-9-])", content):
            matches.append({"source_key": key, "document_id": source["id"],
                            "revision_id": item["revision_id"], "asset_id": asset_id})
    if len(matches) > 1:
        raise RegistryResolutionError("AMBIGUOUS_ASSET_ID")
    if not matches:
        return {"project_id": project_id, "asset_id": asset_id, "status": "BLOCKED",
                "blockers": ["ASSET_NOT_IN_VERIFIED_ATLAS"]}
    atlas = matches[0]
    # Confirm this Atlas itself is mentioned in the live registry, avoiding
    # accidental authority from a stale bootstrap configuration alone.
    if atlas["document_id"] not in registry_text:
        return {"project_id": project_id, "asset_id": asset_id, "status": "BLOCKED",
                "blockers": ["ATLAS_NOT_IN_LIVE_REGISTRY"]}
    return {"project_id": project_id, "asset_id": asset_id,
            "status": "ATLAS_RECORD_LOCATED_IMAGE_BYTES_NOT_VERIFIED",
            "registry_revision_id": registry_revision_id, "atlas": atlas,
            "required_next_steps": ["READ_SOURCEBOOK_DOSSIER", "VERIFY_ATLAS_APPROVAL",
                                    "EXTRACT_IMAGE_BYTES", "HASH_IMAGE_BYTES",
                                    "VERIFY_PROVIDER_REFERENCE_DELIVERY"],
            "note": "The live connector's identity and revisions are caller-supplied; this resolver cannot independently authenticate Google."}
