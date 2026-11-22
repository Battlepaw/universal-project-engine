"""ChatGPT-facing Universal Project Engine MCP server.

The linked ChatGPT Google Drive connector performs authenticated source reads.
The public MCP server does not have authorization to perform them directly.
"""
from mcp.server.fastmcp import FastMCP, Context, Image
from engine import project_sources, plan_retrieval, inspect_drive_record
from visual_gate import inspect_visual_work_order
from visual_transport import render_connector_job
from security import verify_bearer_header, SecurityConfigurationError
import os

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



@mcp.tool()
def visual_render_status() -> dict:
    """Diagnose visual gateway configuration without revealing credentials."""
    return {
        "adapter": "v1.2_connector_export_bridge",
        "retrieval": "chatgpt_authenticated_google_drive_connector",
        "render_model": "gpt-image-2.6-sunburst",
        "render_enabled": os.getenv("UPE_RENDER_ENABLED") == "1",
        "provider_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "transport_auth_configured": len(os.getenv("UPE_ACCESS_TOKEN", "")) >= 32,
        "reference_transport": "SIGNED_CONNECTOR_DOCX_EXPORT_TO_VERIFIED_BYTES",
        "warning": "This diagnostic cannot validate Google OAuth provenance or image likeness.",
    }


@mcp.tool()
def render_approved_visual(job: dict, exports: list[dict], ctx: Context) -> Image:
    """Edit with real approved image bytes, from authenticated Drive exports.

    Returns only an UNAPPROVED draft for author visual review. This privileged,
    metered tool is disabled until the server has a private bearer credential,
    OpenAI API credential and explicit UPE_RENDER_ENABLED=1. ChatGPT's connector
    must read source revisions and export current Atlas DOCX before each call.
    Each export supplies source_key, document_id, revision_id, signed_download_url.
    Each approved asset supplies section_anchor and approval_caption plus its
    registered source metadata, AUTHOR_APPROVED status and expected image hash.
    """
    if os.getenv("UPE_RENDER_ENABLED") != "1":
        raise ValueError("RENDER_DISABLED_UNTIL_SECURE_SETUP")
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("PROVIDER_API_KEY_NOT_CONFIGURED")
    try:
        request = ctx.request_context.request
        authorization = request.headers.get("authorization") if request is not None else None
    except (AttributeError, TypeError):
        authorization = None
    try:
        verified = verify_bearer_header(authorization)
    except SecurityConfigurationError as exc:
        raise ValueError("RENDER_AUTH_NOT_CONFIGURED") from exc
    if not verified:
        raise ValueError("RENDER_AUTHORIZATION_REQUIRED")
    manifest, image = render_connector_job(job=job, exports=exports)
    # FastMCP returns actual image bytes, not a text prompt or a Drive link.
    # The returned draft is unapproved regardless of provider HTTP success.
    return Image(data=image, format="png" if image.startswith(b"\x89PNG") else "jpeg")


app = mcp.streamable_http_app()
