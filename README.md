# Universal Project Engine — Connector-Broker Retrieval (Milestone 2, partial)

ChatGPT is the primary user interface. This repository hosts the MCP server on Render. Google Drive is authoritative for source documents and approved assets. Different creative projects may **never** substitute records for each other.

## Deployment
```sh
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
python -m unittest discover -s tests -v
```
MCP endpoint: `/mcp`. Existing `list_projects` remains compatible.

## Retrieval workflow

1. Call `plan_retrieval(project_id, topic)` on the Universal Project Engine.
2. ChatGPT uses its **authenticated Google Drive connector** to read the exact live documents, in the returned order. Project registry resolves manuscript edition IDs.
3. Verify documentId, revisionId, source title and required indexes from the Google connector's actual response. If any read fails, stop; never use memory as substitute.
4. Call `inspect_drive_record` with selected connector-returned paragraph objects and actual ID/revision/title to search precisely and check project source identity. This function can only validate the **submitted data and registered IDs**; it cannot independently authenticate that the data truly came from Google Drive.
5. Present evidence, location, edition and unresolved conflicts; follow the project's Operations Manual before any edit.

## Security / limits

The public MCP endpoint holds **no Drive tokens or private document content**. Never add a service-account credential or refresh token to this public endpoint without first implementing client authentication and least-privilege access controls. It neither stores submitted excerpts nor reads Drive on its own. Connector-broker retrieval is an operational path when ChatGPT's Google Drive connector is installed, **not autonomous backend Google Drive access**.

Only ENDARIA has verified document references so far. Other projects must be registered from their own approved source records; never infer their canon or use ENDARIA materials.

Pending: authenticated server-side Drive read, source registry ingestion without a static manifest, asset retrieval, server-side authenticated project access, persistence/revision logs, rendering. None of these is claimed implemented.


## Visual-generation enforcement — feature branch (November 2026)

The plugin now exposes `inspect_visual_preflight` and registers the live ENDARIA Character Atlas, Atlas A, Heraldry Register, and recovered Sky Drifters manuscript source IDs. It checks source IDs and revisions, approved-asset metadata, explicit rule provenance, unique references and required image roles. A character edit requires a `character_master` asset; existing-design edits require `design_master`; specific insignia work can require a second role such as `unit_patch_master`.

**A passed metadata check is NOT permission to generate.** The response intentionally remains `BLOCKED_REFERENCE_BYTES_AND_RENDER_TRANSPORT_NOT_VERIFIED`. This public plugin has no Drive OAuth access, cannot confirm caller-supplied evidence authenticity, cannot hash a reference that it did not actually receive, and cannot intercept ChatGPT's separate built-in image generator. No source text or private visual bytes should be persisted on this public server. This gate cannot guarantee that an image model follows an instruction.

### Required implementation boundary

1. Retrieve the authenticated Google Docs revisions and the *actual approved image bytes* through the user's Google Drive connector. Stop on missing, stale, ambiguous, or conflicting records.
2. Pass the trusted live-source work order and SHA-256-verified actual image bytes to a **secured** rendering gateway that exclusively uses reference-image edit transport. The existing ENDARIA Retrieval Adapter v1.1 contains `render_gateway.py`; its 21 November 2026 local improvement adds `production_gate.py` and fixes exact-caption multi-image extraction. This is NOT automatically deployed from the plugin repository.
3. The rendering provider must accept the actual bytes for the same request. Log a transport receipt and generated image hash; **do not claim visual fidelity from an API success**.
4. Run explicit visual checks for character likeness, costume continuity, patch geometry and positioning. Return FAIL/UNKNOWN to revision queue. Never call a result canon without author approval.
5. Secure the Render MCP and gateway with authenticated access before attaching private Drive exports or API credentials. No keys in repository/Drive. API charges require user authorization and working credentials.

The deployment remains retrieval/preflight-only until an authenticated provider gateway is connected and exercised. Do not bypass this gate by generating a text-only image.
