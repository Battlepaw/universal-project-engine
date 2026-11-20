"""Private production orchestration: retrieval → verified bytes → image edit → output.

No call is exposed as a public unauthenticated MCP tool. Outputs are unapproved
and must be reviewed before promotion to the Visual Atlas.
"""
from __future__ import annotations
from hashlib import sha256
import os
import json
from pathlib import Path
from retrieval_pipeline import retrieve_asset_bundle
from image_provider import send_image_edit

class ProductionJobBlocked(ValueError):
    pass

def run_production_job(*, project_id: str, asset_ids: list[str], prompt: str,
                       private_output_dir: str, transport=None, provider=None,
                       request_id: str) -> dict:
    if not request_id or not request_id.replace("-", "").replace("_", "").isalnum():
        raise ProductionJobBlocked("INVALID_REQUEST_ID")
    if not asset_ids or len(set(asset_ids)) != len(asset_ids):
        raise ProductionJobBlocked("ASSET_IDS_MISSING_OR_DUPLICATE")
    directory = Path(private_output_dir)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or (directory.stat().st_mode & 0o077):
        raise ProductionJobBlocked('PRIVATE_OUTPUT_DIRECTORY_PERMISSIONS_UNSAFE')
    bundles = []
    for asset_id in asset_ids:
        bundle = retrieve_asset_bundle(project_id, asset_id, transport,
                                       private_output_dir=str(directory / "references"))
        if bundle["status"] != "SOURCE_AND_IMAGE_BYTES_RESOLVED_NOT_PROVIDER_DELIVERED":
            raise ProductionJobBlocked("RETRIEVAL_NOT_COMPLETE")
        bundles.append(bundle)
    references = [{"asset_id": b["asset_id"], "private_reference_path": b["private_reference_path"],
                   "sha256": b["image"]["sha256"]} for b in bundles]
    send = provider or send_image_edit
    result = send(prompt=prompt, references=references)
    image = result.get("output_bytes")
    if not isinstance(image, bytes):
        raise ProductionJobBlocked("PROVIDER_OUTPUT_MISSING")
    if image.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = ".png"
    elif image.startswith(b"\xff\xd8\xff"):
        ext = ".jpg"
    else:
        raise ProductionJobBlocked("PROVIDER_OUTPUT_INVALID")
    output = directory / (request_id + ext)
    if output.exists():
        raise ProductionJobBlocked("OUTPUT_ALREADY_EXISTS")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(image)
    manifest = {"project_id":project_id,"request_id":request_id,
                "status":"GENERATED_UNAPPROVED",
                "output_sha256":sha256(image).hexdigest(),
                "reference_sources":[{"asset_id":b["asset_id"],"sourcebook":b["sourcebook"],
                                      "atlas":b["atlas"],"image":b["image"]} for b in bundles],
                "provider_transport_status":result.get("status"),
                "visual_fidelity_verified":False,"author_approved":False,
                "drive_output_backup_verified":False}
    manifest_path = directory / (request_id + '.json')
    fd = os.open(manifest_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(json.dumps(manifest, indent=2))
    return manifest
