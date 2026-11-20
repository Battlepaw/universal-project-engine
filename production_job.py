"""Private production orchestration: retrieval → verified bytes → image edit → output.

No call is exposed as a public unauthenticated MCP tool. Outputs are unapproved
and must be reviewed before promotion to the Visual Atlas.
"""
from __future__ import annotations
from hashlib import sha256
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
    output.write_bytes(image)
    manifest = {"project_id":project_id,"request_id":request_id,
                "status":"GENERATED_UNAPPROVED",
                "output_sha256":sha256(image).hexdigest(),
                "reference_sources":[{"asset_id":b["asset_id"],"sourcebook":b["sourcebook"],
                                      "atlas":b["atlas"],"image":b["image"]} for b in bundles],
                "provider_transport_status":result.get("status"),
                "visual_fidelity_verified":False,"author_approved":False,
                "drive_output_backup_verified":False}
    (directory / (request_id + ".json")).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
