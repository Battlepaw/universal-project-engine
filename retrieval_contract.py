"""Shared retrieval contract: project-agnostic, revision-bound source and asset dependencies.

This module validates evidence supplied by an authenticated adapter. It never
claims to fetch Drive or to attest that a caller is trustworthy.
"""
from __future__ import annotations
import hashlib
from typing import Any

class RetrievalGateError(ValueError):
    pass

def verify_bundle(project_id: str, dependencies: list[dict], evidence: list[dict]) -> dict:
    """Resolve required text and binary dependencies, refusing partial substitutions.

    dependencies: [{key, kind, source_id, revision_id?, sha256?}]
    evidence: [{key, kind, source_id, revision_id, payload_sha256, content?}]
    A caller-provided digest is only a claim; actual binary bytes must be
    verified at the authenticated connector/asset transport boundary.
    """
    if not isinstance(project_id, str) or not project_id.strip():
        raise RetrievalGateError("PROJECT_REQUIRED")
    if not isinstance(dependencies, list) or not dependencies:
        raise RetrievalGateError("DEPENDENCIES_REQUIRED")
    if not isinstance(evidence, list):
        raise RetrievalGateError("INVALID_EVIDENCE")
    seen = set()
    for e in evidence:
        if not isinstance(e, dict) or not isinstance(e.get("key"), str):
            raise RetrievalGateError("INVALID_EVIDENCE")
        if e["key"] in seen:
            raise RetrievalGateError("DUPLICATE_EVIDENCE")
        seen.add(e["key"])
    indexed = {e["key"]: e for e in evidence}
    resolved, blockers = [], []
    dep_keys = set()
    for d in dependencies:
        if not isinstance(d, dict) or not isinstance(d.get("key"), str) or not d["key"]:
            raise RetrievalGateError("INVALID_DEPENDENCY")
        key = d["key"]
        if key in dep_keys:
            raise RetrievalGateError("DUPLICATE_DEPENDENCY")
        dep_keys.add(key)
        if d.get("kind") not in ("text", "image", "document", "binary") or not d.get("source_id"):
            raise RetrievalGateError("INVALID_DEPENDENCY")
        e = indexed.get(key)
        if not e:
            blockers.append({"key": key, "reason": "MISSING_EVIDENCE"})
            continue
        if e.get("project_id") != project_id or e.get("kind") != d["kind"] or e.get("source_id") != d["source_id"]:
            blockers.append({"key": key, "reason": "PROJECT_OR_SOURCE_MISMATCH"})
            continue
        if not isinstance(e.get("revision_id"), str) or not e["revision_id"]:
            blockers.append({"key": key, "reason": "REVISION_MISSING"})
            continue
        if d.get("revision_id") and d["revision_id"] != e["revision_id"]:
            blockers.append({"key": key, "reason": "REVISION_CHANGED"})
            continue
        digest = e.get("payload_sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            blockers.append({"key": key, "reason": "INVALID_DIGEST"})
            continue
        if d.get("sha256") and d["sha256"] != digest:
            blockers.append({"key": key, "reason": "ASSET_HASH_MISMATCH"})
            continue
        if "content" in e:
            payload = e["content"]
            if not isinstance(payload, (str, bytes)):
                blockers.append({"key": key, "reason": "INVALID_CONTENT"})
                continue
            raw = payload.encode("utf-8") if isinstance(payload, str) else payload
            if hashlib.sha256(raw).hexdigest() != digest:
                blockers.append({"key": key, "reason": "CONTENT_HASH_MISMATCH"})
                continue
        elif d["kind"] in ("image", "binary"):
            blockers.append({"key": key, "reason": "BINARY_BYTES_NOT_VERIFIED"})
            continue
        else:
            blockers.append({"key": key, "reason": "TEXT_NOT_VERIFIED"})
            continue
        resolved.append({"key": key, "kind": d["kind"], "source_id": e["source_id"],
                         "revision_id": e["revision_id"], "sha256": digest})
    return {"project_id": project_id, "status": "RESOLVED" if not blockers else "BLOCKED",
            "resolved": resolved, "blockers": blockers,
            "verification": "CALLER_SUPPLIED_BYTES_AND_METADATA_ONLY",
            "note": "Authenticated provider origin and asset approval require separate trusted adapter checks."}
