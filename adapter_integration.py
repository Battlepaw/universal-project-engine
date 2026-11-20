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
