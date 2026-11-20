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
