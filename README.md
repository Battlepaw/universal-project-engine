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


## Visual-production repair: actual failure first (21 November 2026)

**Incident**: Becca Marshall turnaround generation changed her approved blue-black hair and face, invented nonapproved qualification/captain devices, placed Sweetwind's circular patch off-centre from the bronze backing, then used that incorrect draft as the reference for a second (formal dress) generation. Author-approved master references were already present in Google Drive.

**Root cause**: The ChatGPT image-generation call was not controlled by this plugin. The plugin can locate registered docs and inspect submitted text metadata, but does not retrieve actual image bytes and deliver them to a reference-conditioned provider as the *same* request. No preflight metadata schema or later visual scoring is a substitute for a confirmed source-to-render handoff.

### Defect-ordered repair plan (do these in order; no unrelated new features)

| Order | Actual failure | Repair existing component | End-to-end acceptance condition |
|---|---|---|---|
| **P0. Approved image was not delivered** | Becca's original image was not the rendering input | Connect current authenticated Drive export + `docx_bridge.py` / `unified_bridge.py` extraction to existing `render_gateway.py`; do not invoke direct text-only `image_gen` for this workflow | Retrieve approved VIS-SD-001 image from current Atlas, verify embedded-object / exact caption / source revision and SHA-256, verify gateway sends those same bytes in edit multipart request; prove with a live provider round trip (not mocks) |
| **P1. Another approved image was silently approximated** | Sweetwind patch replaced by a visually similar, misaligned redraw | Include the approved END-SHIP-001-PATCH source as a second actual image input in the **same request**; preserve its unit-patch/backing relationship | Provider request receipt binds BOTH asset hashes; output reviewer can compare against BOTH actual source images |
| **P2. Unapproved generated draft became reference** | Formal portrait inherited blonde hair and incorrect uniform from prior draft | Keep `production_gate.py`'s approved-reference selection and `release_gate.py` promotion rules on the *only* render path; treat output as derivative until author approves | A follow-up formal-uniform edit resolves VIS-SD-001 again and rejects using a GENERATED_UNAPPROVED file as an approved master |
| **P3. Geometry and fidelity not demonstrated** | Centering and identity drift passed through to user | Test with Becca and Sweetwind regression cases against retrieved originals; do manual visual acceptance first, automate narrow geometry checks only if needed | No claim of success from API 200 or local unit tests; author reviews likeness, dark hair, costume, patch centering, shoulders; failures remain unapproved |

### Constraints and what is not fixed yet

- `inspect_visual_preflight` (merged into the live plugin) checks caller-supplied IDs, revisions, asset SHA-256 strings and rules. It **does not receive image bytes**, attest Drive content, submit the provider edit call or ensure adherence. Its `BLOCKED_REFERENCE_BYTES_AND_RENDER_TRANSPORT_NOT_VERIFIED` result is correct until P0/P1 live integration is proven.
- The local ENDARIA Retrieval Adapter **v1.2**, retained in the Master Document Registry, already has `production_gate.py`, the byte-aware `render_gateway.py` and exact-caption image extraction. Repair and integrate those; do not construct an unrelated second engine, new atlas, new approval hierarchy or additional generic checks.
- Built-in ChatGPT `image_gen` is a separate tool and **cannot be intercepted or forced** by this MCP plugin. A mandatory engine-owned path requires a secured, authenticated provider gateway and the model actually choosing that path. Until it is working, report image creation as blocked rather than bypassing it.
- Success requires a **live source-to-provider test using actual approved reference bytes** followed by author visual approval. Passing mocked/local tests does not satisfy this.
- No unapproved art is promoted; projects stay strictly isolated. No API credentials or private images go into the public MCP server. Live provider charges/credentials require owner action.
