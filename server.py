"""Milestone 1: minimal ChatGPT-facing MCP endpoint.

Project files and assets remain in Google Drive. This endpoint performs no retrieval.
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Universal Project Engine", stateless_http=True, json_response=True)

@mcp.tool()
def list_projects() -> dict:
    """List registered project identifiers; no source retrieval is performed."""
    return {
        "projects": [
            {"project_id": "endaria", "name": "ENDARIA", "status": "configured_for_testing"}
        ],
        "source": "static_milestone_1_configuration",
    }

app = mcp.streamable_http_app()
