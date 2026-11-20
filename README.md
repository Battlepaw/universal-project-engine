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
