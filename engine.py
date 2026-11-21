"""Project-isolated retrieval planning and source-evidence checks.

Google Drive document contents must come from a live, authenticated connector.
This module deliberately holds no Google credentials and does not claim direct
server-side Drive access. It never persists manuscript or asset contents.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

PROJECTS = {
    "endaria": {
        "name": "ENDARIA",
        "sources": {
            "operations_manual": {
                "id": "1jjZv2KnPIj8b0DjlyBGo-QLkO0tcpXZyg7m-zrbOw3Y",
                "title": "ENDARIA Universe — Operations Manual",
                "role": "workflow",
            },
            "document_registry": {
                "id": "1Eyn8gRrkbSQ69UqjxkjrRK7x_LfbPsFmuqgxujxtLPo",
                "title": "ENDARIA Universe — Master Document Registry",
                "role": "index",
            },
            "master_sourcebook": {
                "id": "1LL5RVfaYOLdxjIveZem7-YCR73UeGvRHVBlTe9k7UjY",
                "title": "ENDARIA Universe — Master Sourcebook",
                "role": "canon_reference",
            },
            "character_visual_atlas": {
                "id": "1uKCj5cIB_moaFVuzmmqcPXA8dS27qjoJVlT1apch-p4",
                "title": "Character Visual Atlas",
                "role": "approved_character_visuals",
            },
            "visual_atlas_a": {
                "id": "1cLoPTR-rzxFZJuWAGL5cm9hbQDGAsQIXP8Ev10t0uVA",
                "title": "ENDARIA Universe — Visual Atlas A: Vessels and Creatures",
                "role": "approved_vessel_and_patch_visuals",
            },
            "heraldry_register": {
                "id": "1kQxe5v5geV6qkaNcR0Kh45mJ-m-hW8TnMIMirDvOuHk",
                "title": "ENDARIA — Heraldry, Insignia & Symbols Working Register (Provisional)",
                "role": "visual_working_inventory",
            },
            "sky_drifters_manuscript": {
                "id": "1FcxcbdBbjiQo6rlRTjcHlww7gHe4cqKhnZ3B_6iGKwU",
                "title": "Sky Drifters (RR Recovered Version)",
                "role": "verified_narrative_evidence",
            },
        },
    },
}
STOPWORDS = {"the", "and", "for", "with", "from", "what", "how", "does", "into", "this", "that", "about", "give", "find", "show", "which", "where", "their", "these"}
MAX_PARAGRAPHS = 6000
MAX_TOTAL_CHARS = 1_200_000


def _project(project_id: str) -> dict:
    if not isinstance(project_id, str) or project_id not in PROJECTS:
        raise ValueError("PROJECT_NOT_REGISTERED: no project substitution is permitted")
    return PROJECTS[project_id]


def _source(project_id: str, source_key: str) -> dict:
    project = _project(project_id)
    if source_key not in project["sources"]:
        raise ValueError("SOURCE_NOT_REGISTERED: consult this project's live document registry; do not guess an ID")
    return project["sources"][source_key]


def project_sources(project_id: str) -> dict:
    project = _project(project_id)
    return {
        "project_id": project_id,
        "name": project["name"],
        "retrieval_mode": "chatgpt_google_drive_connector",
        "direct_google_drive_access": False,
        "sources": [
            {
                "source_key": key,
                "document_id": value["id"],
                "title": value["title"],
                "role": value["role"],
                "url": f'https://docs.google.com/document/d/{value["id"]}/edit',
            }
            for key, value in project["sources"].items()
        ],
        "warning": "Source IDs are routing aids, not proof of current content. Retrieve live revisions through the connected Google Drive tool.",
    }


def plan_retrieval(project_id: str, topic: str) -> dict:
    _project(project_id)
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("QUERY_REQUIRED")
    keys = ["operations_manual", "document_registry", "master_sourcebook"]
    if re.search(r"visual|character|atlas|image|portrait|render|design|art|sweetwind|becca", topic, re.I):
        keys.append("character_visual_atlas")
    if re.search(r"patch|insignia|herald|ship|sweetwind|uniform|design|image|visual", topic, re.I):
        keys.append("visual_atlas_a")
        keys.append("heraldry_register")
    if re.search(r"becca|rebecca|sky drifters|sweetwind|neil|captain", topic, re.I):
        keys.append("sky_drifters_manuscript")
    steps = []
    for key in keys:
        s = _source(project_id, key)
        steps.append({
            "source_key": key,
            "document_id": s["id"],
            "document_url": f'https://docs.google.com/document/d/{s["id"]}/edit',
            "connector_action": "Google Drive get_document_text",
            "require_document_id_match": True,
            "require_revision_id": True,
            "required_before_canon_claim": True,
        })
    return {
        "project_id": project_id,
        "topic": topic.strip(),
        "status": "LIVE_CONNECTOR_RETRIEVAL_REQUIRED",
        "steps": steps,
        "retrieval_order": "Read operations manual and live registry first; then applicable current Sourcebook dossiers, Atlas and registered manuscript evidence.",
        "edition_check": "Resolve manuscript authority and edition in live project registry; do not infer authority from a filename.",
        "abort_if_unavailable": True,
        "notes": "This is a retrieval plan, NOT retrieved content. The plugin cannot access ChatGPT's Google OAuth credentials.",
    }


def inspect_drive_record(
    project_id: str,
    source_key: str,
    document_id: str,
    revision_id: str,
    title: str,
    paragraphs: list[dict[str, Any]],
    query: str,
    max_results: int = 5,
) -> dict:
    """Search exact connector-supplied paragraphs, checking registered source identity.

    Only the connected Google Drive tool can establish that submitted fields
    actually came from a current live Google Doc; this is not an attestation.
    """
    s = _source(project_id, source_key)
    if document_id != s["id"]:
        raise ValueError("SOURCE_ID_MISMATCH: fail closed")
    if not isinstance(revision_id, str) or not revision_id.strip():
        raise ValueError("REVISION_REQUIRED: a live document read must supply its revision")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("TITLE_REQUIRED")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("QUERY_REQUIRED")
    if type(max_results) is not int or not 1 <= max_results <= 10:
        raise ValueError("MAX_RESULTS_RANGE: 1..10")
    if not isinstance(paragraphs, list) or len(paragraphs) > MAX_PARAGRAPHS:
        raise ValueError("INVALID_PARAGRAPHS")
    normalized = re.findall(r"\w+", query.casefold())
    terms = [t for t in normalized if len(t) > 2 and t not in STOPWORDS]
    if not terms:
        terms = normalized[:5]
    hits = []
    total = 0
    for position, p in enumerate(paragraphs):
        if not isinstance(p, dict) or not isinstance(p.get("text"), str):
            raise ValueError("INVALID_PARAGRAPH_RECORD")
        value = p["text"]
        total += len(value)
        if total > MAX_TOTAL_CHARS:
            raise ValueError("SOURCE_PAYLOAD_TOO_LARGE")
        folded = value.casefold()
        score = sum(1 for t in set(terms) if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", folded))
        if len(terms) > 1 and query.strip().casefold() in folded:
            score += len(terms) + 2
        if not score:
            continue
        start = p.get("startIndex")
        end = p.get("endIndex")
        hits.append({
            "score": score,
            "paragraph_position": position,
            "start_index": start if type(start) is int else None,
            "end_index": end if type(end) is int else None,
            "text": value[:1200],
            "truncated": len(value) > 1200,
            "sha256_full_paragraph": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        })
    hits.sort(key=lambda h: (-h["score"], h["paragraph_position"]))
    return {
        "project_id": project_id,
        "source_key": source_key,
        "source_id": s["id"],
        "source_url": f'https://docs.google.com/document/d/{s["id"]}/edit',
        "connector_reported_title": title,
        "connector_reported_revision_id": revision_id,
        "status": "CONNECTOR_DATA_MATCHED" if hits else "NO_MATCH_IN_SUBMITTED_PARAGRAPHS",
        "matches": hits[:max_results],
        "submitted_paragraph_count": len(paragraphs),
        "verification": "REGISTERED_SOURCE_ID_AND_SUBMITTED_TEXT_ONLY",
        "limitations": [
            "This plugin did not independently read Google Drive.",
            "The current revision and original authorship must be checked against the connected Google Drive response.",
            "No canon claim is verified from this result alone; check linked dossiers and manuscript evidence.",
        ],
    }
