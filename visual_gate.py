"""Fail-closed visual-generation work order inspection for all registered projects.

This public MCP process never receives Drive OAuth credentials or approved image
bytes. Consequently it can check *submitted* source/asset identities but must
never claim to have rendered or independently authenticated an image. The secure
rendering gateway must validate actual reference bytes and provide a verifiable
transport receipt before generation can be permitted.
"""
from __future__ import annotations

import re
from typing import Any
from engine import _project, _source, plan_retrieval

HEX_HASH = re.compile(r"^[a-f0-9]{64}$")
REQUIRED_ROLES = {
    "existing_character": {"character_master"},
    "existing_asset": {"design_master"},
    "new_design": {"style_master"},
}
CATEGORIES = {"identity", "continuity", "construction", "placement", "canon", "visual_style"}


def inspect_visual_work_order(project_id: str, subject_id: str, intent: str,
                              topic: str, source_evidence: list[dict],
                              approved_assets: list[dict],
                              visual_rules: list[dict],
                              additional_required_roles: list[str] | None = None) -> dict:
    """Check a proposed production job; never authorize text-only image generation."""
    _project(project_id)
    if intent not in REQUIRED_ROLES:
        raise ValueError("IMAGE_INTENT_UNSUPPORTED")
    if not isinstance(subject_id, str) or not subject_id.strip():
        raise ValueError("SUBJECT_ID_REQUIRED")
    plan = plan_retrieval(project_id, topic)
    if not isinstance(source_evidence, list) or not source_evidence:
        raise ValueError("SOURCE_EVIDENCE_MISSING")
    verified_source_keys = set()
    for item in source_evidence:
        if not isinstance(item, dict):
            raise ValueError("SOURCE_EVIDENCE_INVALID")
        key = item.get("source_key")
        if not isinstance(key, str):
            raise ValueError("SOURCE_KEY_MISSING")
        registered = _source(project_id, key)
        if item.get("document_id") != registered["id"]:
            raise ValueError("SOURCE_ID_MISMATCH")
        for field in ("revision_id", "tab_id", "exact_text"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError("SOURCE_REVISION_AND_PASSAGE_REQUIRED")
        if type(item.get("start_index")) is not int or type(item.get("end_index")) is not int or item["start_index"] >= item["end_index"]:
            raise ValueError("SOURCE_PASSAGE_LOCATION_REQUIRED")
        verified_source_keys.add(key)
    if not isinstance(approved_assets, list) or not approved_assets:
        raise ValueError("APPROVED_REFERENCE_REQUIRED")
    required_roles = set(REQUIRED_ROLES[intent])
    if additional_required_roles:
        if not isinstance(additional_required_roles, list) or not all(isinstance(x, str) and x.strip() for x in additional_required_roles):
            raise ValueError("INVALID_REQUIRED_ROLES")
        required_roles.update(additional_required_roles)
    found_roles, found_ids = set(), set()
    for asset in approved_assets:
        if not isinstance(asset, dict):
            raise ValueError("INVALID_REFERENCE")
        aid, role = asset.get("asset_id"), asset.get("role")
        if not isinstance(aid, str) or not aid.strip() or aid in found_ids:
            raise ValueError("DUPLICATE_OR_MISSING_ASSET_ID")
        found_ids.add(aid)
        if not isinstance(role, str) or not role.strip():
            raise ValueError("ASSET_ROLE_REQUIRED")
        found_roles.add(role)
        if asset.get("approval_status") != "AUTHOR_APPROVED":
            raise ValueError("UNAPPROVED_REFERENCE")
        key = asset.get("source_key")
        if key not in verified_source_keys:
            raise ValueError("REFERENCE_SOURCE_MISSING")
        s = _source(project_id, key)
        if asset.get("document_id") != s["id"]:
            raise ValueError("REFERENCE_SOURCE_ID_MISMATCH")
        if not any(e["source_key"] == key and e["revision_id"] == asset.get("revision_id") for e in source_evidence):
            raise ValueError("REFERENCE_SOURCE_REVISION_MISMATCH")
        if not isinstance(asset.get("sha256"), str) or not HEX_HASH.fullmatch(asset["sha256"]):
            raise ValueError("REFERENCE_SHA256_REQUIRED")
    if not required_roles.issubset(found_roles):
        raise ValueError("REQUIRED_IMAGE_REFERENCE_MISSING:" + ",".join(sorted(required_roles - found_roles)))
    if not isinstance(visual_rules, list) or not visual_rules:
        raise ValueError("VISUAL_RULES_REQUIRED")
    seen_rules = set()
    for rule in visual_rules:
        if not isinstance(rule, dict):
            raise ValueError("VISUAL_RULE_INVALID")
        rid = rule.get("rule_id")
        if not isinstance(rid, str) or not rid.strip() or rid in seen_rules:
            raise ValueError("VISUAL_RULE_ID_MISSING_OR_DUPLICATE")
        seen_rules.add(rid)
        if rule.get("category") not in CATEGORIES:
            raise ValueError("VISUAL_RULE_CATEGORY_INVALID")
        if not isinstance(rule.get("instruction"), str) or not rule["instruction"].strip():
            raise ValueError("VISUAL_RULE_INSTRUCTION_REQUIRED")
        if rule.get("source_key") not in verified_source_keys:
            raise ValueError("VISUAL_RULE_SOURCE_MISSING")
    return {
        "status": "BLOCKED_REFERENCE_BYTES_AND_RENDER_TRANSPORT_NOT_VERIFIED",
        "project_id": project_id,
        "subject_id": subject_id,
        "intent": intent,
        "retrieval_plan": plan["steps"],
        "source_keys": sorted(verified_source_keys),
        "approved_asset_ids": sorted(found_ids),
        "required_visual_checks": [r["rule_id"] for r in visual_rules],
        "source_authentication": "CONNECTOR_FIELDS_SUBMITTED_NOT_INDEPENDENTLY_AUTHENTICATED",
        "reference_image_bytes_received": False,
        "render_handoff_verified": False,
        "author_approval": False,
        "next_step": "Use a secured byte-aware rendering gateway with exact authenticated Drive export, hash verification, a request-bound image transport receipt, and post-render visual checks. Never substitute text-only image generation.",
    }
