# Universal Project Engine — Milestone 1

Minimal ChatGPT connection test, following the November 19, 2026 development handover.

## Scope

Exposes one MCP tool, `list_projects`, with a static ENDARIA test configuration. This is **not** live Google Drive retrieval, asset extraction, or a completed ChatGPT integration. Google Drive remains the authoritative storage medium for project documents and visual assets. No credentials or project content are stored in this repository.

## Run

```sh
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

The MCP Streamable HTTP endpoint is `/mcp`. Register the HTTPS endpoint with a supported ChatGPT custom integration mechanism, invoke `list_projects` from a real ChatGPT conversation, and retain evidence. Do not claim Milestone 1 complete until this is verified.

## Status

Source deployed or hosted does **not** prove ChatGPT registration. No subsequent milestones are authorized until the real ChatGPT invocation passes.
