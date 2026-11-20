"""Bridge contract for project-specific asset adapters.

No file bytes, private Drive content, or approval flags are accepted as trusted
merely because a caller supplied them. This module records registered adapter
identity and verifies provenance shape; actual live extraction remains external.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class AdapterRegistration:
    project_id: str
    name: str
    drive_archive_id: str
    archive_size: int
    status: str

ADAPTERS = {
    "endaria": AdapterRegistration(
        project_id="endaria",
        name="ENDARIA Retrieval Adapter v1.1",
        drive_archive_id="127qsaaOPtO6pxy5QzrMpjdJcl9yZlAxF",
        archive_size=12842090,
        status="EXTERNAL_ADAPTER_VERIFIED_LOCAL_TESTS_NOT_DEPLOYED",
    ),
}

ASSET_REFERENCES = {
    "endaria": {
        "END-SHIP-001": {"sha256": "675d60f418708387b484d5e46969ae9d252cf93b3402ecadea75e1138bea29fa", "bytes": 3059358, "atlas_source_key": "visual_atlas_a"},
        "VIS-SD-001": {"sha256": "d9260c60b2bb0d30a42973aada6084598fc1071b8f88f605a72a3fbf79e78a33", "bytes": 3807538, "atlas_source_key": "character_visual_atlas"},
    },
}


def asset_reference_manifest(project_id: str, asset_id: str) -> dict:
    adapter_manifest(project_id)
    asset = ASSET_REFERENCES[project_id].get(asset_id)
    if asset is None:
        raise ValueError("ASSET_NOT_REGISTERED")
    return {"project_id": project_id, "asset_id": asset_id, **asset,
            "status": "ARCHIVE_BYTES_HASHED_NOT_LIVE_RETRIEVED",
            "approved_visual_must_be_verified_against_live_atlas": True,
            "image_bytes_in_response": False}


def adapter_manifest(project_id: str) -> dict:
    if project_id not in ADAPTERS:
        raise ValueError("ADAPTER_NOT_REGISTERED")
    a = ADAPTERS[project_id]
    return {
        "project_id": a.project_id,
        "name": a.name,
        "drive_archive_id": a.drive_archive_id,
        "archive_size": a.archive_size,
        "status": a.status,
        "asset_byte_transport_available": False,
        "generator_reference_conditioning_verified": False,
        "live_server_integration_verified": False,
        "note": "Drive archive identity is a pointer, not proof of current asset bytes or approval.",
    }
