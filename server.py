"""ChatGPT-facing Universal Project Engine MCP server.

The linked ChatGPT Google Drive connector performs authenticated source reads.
The public MCP server does not have authorization to perform them directly.
"""
from mcp.server.fastmcp import FastMCP
from engine import project_sources, plan_retrieval, inspect_drive_record
from visual_gate import inspect_visual_work_order

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
def inspect_visual_preflight(
    project_id: str, subject_id: str, intent: str, topic: str,
    source_evidence: list[dict], approved_assets: list[dict],
    visual_rules: list[dict], additional_required_roles: list[str] | None = None,
) -> dict:
    """Fail-closed project-bound visual job inspection, not a rendering permit.

    Requires live connector evidence, approved reference metadata and mandatory
    visual standards. The secure byte-aware rendering gateway is not wired into
    this public plugin yet, so this tool cannot authorize a generation.
    """
    return inspect_visual_work_order(project_id, subject_id, intent, topic,
                                     source_evidence, approved_assets,
                                     visual_rules, additional_required_roles)


app = mcp.streamable_http_app()
