"""MCP end-to-end smoke test; uses no private Google Drive data."""
import asyncio
import os
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    endpoint = os.getenv("UPE_MCP_URL", "http://127.0.0.1:8765/mcp")
    async with streamable_http_client(endpoint) as (read, write, _):
        async with ClientSession(read, write) as client:
            await client.initialize()
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            expected = {
                "list_projects", "get_project_sources",
                "plan_drive_retrieval", "inspect_connector_evidence",
                "inspect_visual_preflight", "visual_render_status", "render_approved_visual",
            }
            assert expected <= names, f"Missing MCP tools: {expected - names}"
            plan = await client.call_tool("plan_drive_retrieval", {
                "project_id": "endaria", "topic": "Sweetwind",
            })
            assert not plan.isError, f"Retrieval plan failed: {plan}"
            result = await client.call_tool("inspect_connector_evidence", {
                "project_id": "endaria",
                "source_key": "master_sourcebook",
                "document_id": "1LL5RVfaYOLdxjIveZem7-YCR73UeGvRHVBlTe9k7UjY",
                "revision_id": "test-revision",
                "title": "Test fixture only, not live Google Drive",
                "paragraphs": [{"text": "Sweetwind is an ironwood airship.", "startIndex": 1, "endIndex": 34}],
                "query": "Sweetwind",
            })
            assert not result.isError, f"Evidence processing failed: {result}"
            print("PASS: MCP initialize, tool discovery, retrieval plan, fixture evidence inspection")


if __name__ == "__main__":
    asyncio.run(main())
