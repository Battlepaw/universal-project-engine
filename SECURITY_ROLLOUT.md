# Universal Project Engine — authentication rollout gates

Status: **NOT ENABLED**. The live MCP connection uses unauthenticated transport; Google Drive reads remain authenticated through ChatGPT's separate connector.

## Non-negotiable safety rules
1. Do not require a bearer token on the live /mcp endpoint until a compatible ChatGPT credential exchange is proven on an isolated deployment.
2. Never put access tokens in Git, project files, tool results, URLs, or logs. Render environment variables may hold server secrets, but that alone does not provide credentials to ChatGPT.
3. Preserve the existing Render service and GitHub main branch while staging and testing.
4. Do not grant the server broad Google Drive access.
5. Never describe a token-validation helper as active endpoint protection.

## Deployment acceptance criteria
- Confirm ChatGPT's supported custom MCP authentication mode from current official documentation.
- Implement that mode end-to-end on the **staging** server, including any discovery/metadata and authorization endpoints it requires.
- Verify authorized ChatGPT requests can call list_projects and get_project_sources on staging.
- Verify unauthorized requests fail and no credentials appear in logs.
- Verify the Google Drive connector retrieval workflow remains isolated and functional.
- Verify rollback procedure and live main endpoint before any production cutover.
- Only then consider a controlled change to the production server.

## Recovery
Keep the known-working main commit and production Render service available. If a future authentication deployment breaks the connection, restore the previous known-good deployment via Render/GitHub; do not change ChatGPT settings to an untested mode.
