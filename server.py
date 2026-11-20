"""ChatGPT-facing Universal Project Engine MCP server.

The linked ChatGPT Google Drive connector performs authenticated source reads.
The public MCP server does not have authorization to perform them directly.
"""
from mcp.server.fastmcp import FastMCP
from engine import project_sources, plan_retrieval, inspect_drive_record
from adapter_integration import adapter_manifest, asset_reference_manifest

mcp = FastMCP("Universal Project Engine", host="0.0.0.0", stateless_http=True, json_response=True)


@mcp.tool()
def list_projects() -> dict:
    """List registered project identifiers; no source retrieval is performed."""
    return {
        "projects": [
            {"project_id": "endaria", "name": "ENDARIA", "status": "configured_for_testing"}
        ],
        "source": "static_milestone_1_configuration",
    }


@mcp.tool()
def get_project_sources(project_id: str) -> dict:
    """Return only this project's verified source IDs for authenticated connector reads."""
    return project_sources(project_id)


@mcp.tool()
def plan_drive_retrieval(project_id: str, topic: str) -> dict:
    """Plan fail-closed reads through ChatGPT's authenticated Google Drive connector."""
    return plan_retrieval(project_id, topic)


@mcp.tool()
def inspect_connector_evidence(
    project_id: str, source_key: str, document_id: str, revision_id: str,
    title: str, paragraphs: list[dict], query: str, max_results: int = 5,
) -> dict:
    """Check registered source ID and search exact live-connector-supplied paragraphs.

    This does not authenticate Google responses; ChatGPT must first perform a
    genuine live Google Drive read and pass the returned ID, revision and text.
    """
    return inspect_drive_record(project_id, source_key, document_id, revision_id,
                                title, paragraphs, query, max_results)


@mcp.tool()
def get_asset_adapter_manifest(project_id: str) -> dict:
    """Describe the registered project asset adapter and explicit integration limits."""
    return adapter_manifest(project_id)


@mcp.tool()
def get_asset_reference_manifest(project_id: str, asset_id: str) -> dict:
    """Return an archive-verified asset fingerprint, never private image bytes."""
    return asset_reference_manifest(project_id, asset_id)


app = mcp.streamable_http_app()
