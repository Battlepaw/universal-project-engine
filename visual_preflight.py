"""Fail-closed gate for visual production requests.

A retrieval match or asset fingerprint is not evidence that the image generator
received the reference image. No generation should be attempted until both
approved master images have a verified provider-side receipt.
"""
from adapter_integration import asset_reference_manifest

class VisualPreflightBlocked(ValueError):
    pass

def check_visual_preflight(project_id: str, required_assets: list[str],
                           provider_receipts: list[dict] | None = None,
                           source_verified: bool = False) -> dict:
    if project_id != "endaria":
        raise VisualPreflightBlocked("PROJECT_VISUAL_WORKFLOW_NOT_REGISTERED")
    if not required_assets or len(required_assets) != len(set(required_assets)):
        raise VisualPreflightBlocked("MISSING_OR_DUPLICATE_ASSETS")
    manifests = [asset_reference_manifest(project_id, key) for key in required_assets]
    receipts = {r.get("asset_id"): r for r in (provider_receipts or []) if isinstance(r, dict)}
    problems = []
    if not source_verified:
        problems.append("SOURCE_EVIDENCE_NOT_VERIFIED")
    for asset in manifests:
        receipt = receipts.get(asset["asset_id"])
        if not receipt or receipt.get("sha256") != asset["sha256"] or receipt.get("accepted") is not True or not receipt.get("reference_handle"):
            problems.append("PROVIDER_REFERENCE_RECEIPT_MISSING:" + asset["asset_id"])
    return {
        "project_id": project_id,
        "status": "READY_FOR_EXPLORATORY_RENDER" if not problems else "BLOCKED",
        "required_assets": [{"asset_id": a["asset_id"], "sha256": a["sha256"]} for a in manifests],
        "blocking_reasons": problems,
        "note": "Provider receipt verifies transport only, not visual fidelity or author approval.",
        "visual_fidelity_verified": False,
        "author_approved": False,
    }
