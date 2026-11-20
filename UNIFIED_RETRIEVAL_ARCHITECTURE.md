# Unified Retrieval Engine — implementation contract (staging)

## Purpose
One retrieval authority for Sourcebook canon, manuscript passages, visual Atlas metadata, embedded approved images, and future asset types. This is a shared engine capability, not a Sweetwind-specific patch.

## Authority and project isolation
1. Select project before resolving anything. Load only that project's configured registry and Operations Manual.
2. Read live registry revision, resolve stable source IDs and editions, then retrieve applicable Sourcebook/manuscript records and visual Atlas records.
3. Link assets by stable IDs (e.g. END-SHIP-001), not filenames or keyword guesses. Every asset record points to its authoritative Atlas source and relevant Sourcebook/manuscript dossier.
4. Maintain separate content authority (manuscript/Sourcebook) and approved visual authority (Atlas). A disagreement is a flagged conflict, never silent overwrite.
5. Treat unavailable, changed, unapproved or mismatched dependencies as blockers.

## Common dependency graph
Production request → project → current registry revision → text evidence → Atlas approval record → actual image bytes → verified provider handoff → output record. The request is incomplete until every required edge is resolved.

## Verified evidence bundle
Each dependency has stable key, type, source ID, revision, digest, and provenance. For binary assets, digest must be computed from actual bytes; a caller-supplied digest alone is insufficient. Source origin must be established by authenticated connector callbacks. Never call a caller-supplied revision a Google-attested revision.

## Execution boundaries
- `retrieval_contract.py` is an initial pure validator and does not authenticate Google or perform Drive reads.
- Authenticated Drive adapter must bracket reads/exports and verify revisions and byte hashes. Reuse existing ENDARIA v1.1 extraction and session code, but keep project-specific lore out of shared modules.
- Asset delivery and provider receipt must be verified separately from retrieval. Provider receipt is not proof of visual fidelity.
- Store output manifests with source/asset IDs, hashes, revisions, generator parameters, output hash, quality gate and author approval state. Outputs must not overwrite approved masters.
- No unauthenticated private document bytes should be exposed on the public production MCP endpoint.

## Migration and acceptance
1. Replace keyword-driven selection with registered source relationships and stable identifiers; support newly added Atlas entries without code edits.
2. Add authenticated adapter that resolves a new Sourcebook entry and its Atlas image without manually registering its hash in Python.
3. Verify revision drift, mismatched project, stale image, missing manuscript, conflicting Atlas approval, and duplicate IDs all fail closed.
4. Verify end-to-end render with two approved image references and record provider receipt. Compare output against approved masters; require human approval.
5. Stage tests and connector validation before any production rollout; preserve existing Render URL and working MCP tools.

Current status: unified evidence validator implemented on security-staging; authenticated source discovery, automatic image extraction, and rendering transport are NOT implemented in the shared MCP engine.

## Implementation update (20 November 2026)
- `registry_resolver.py`: resolves future stable asset IDs against current registry and Atlas evidence.
- `atlas_binary.py`: extracts embedded images by stable heading; validated locally against real ENDARIA Atlas exports for END-SHIP-001, VIS-SD-001 and VIS-IE-041.
- `production_bundle.py`: combines registry, Sourcebook, Atlas revision and export bytes; does not claim independent attestation of caller-supplied evidence.
- `drive_transport.py`: optional server-side Google service account transport; needs GOOGLE_SERVICE_ACCOUNT_JSON configured securely and explicit Drive sharing to service account. Not yet provisioned or live-tested.
- `retrieval_pipeline.py`: resolves registered sources, reads through authenticated transport, exports DOCX, checks revisions and persists actual reference bytes in a private directory.
- `image_provider.py`: sends hash-verified image bytes in a multipart image-edit request; needs OPENAI_API_KEY, explicit paid API access and a real provider test.
- `production_job.py`: joins retrieval and provider handoff, stores unapproved output and evidence manifest. Does not yet back up to Drive or verify visual fidelity.
- Live production Render MCP is unchanged. Staging regression tests and mock integrations do not prove live Google or image-provider access.
- Never put service-account private keys or API keys into GitHub, chat, logs, or public MCP responses. Keep credentials in Render secrets and restrict private image file permissions.
