"""Unified server-side Sourcebook and Atlas retrieval, without hardcoded asset paths.

This is a private engine operation. Do not expose document text or image bytes
through an unauthenticated public MCP endpoint.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from engine import _project
from drive_transport import ServiceAccountDriveTransport, DriveTransportUnavailable
from production_bundle import prepare_production_bundle, ProductionBundleBlocked
from atlas_binary import extract_assets

class RetrievalPipelineBlocked(ValueError):
    pass

def retrieve_asset_bundle(project_id: str, asset_id: str,
                          transport: ServiceAccountDriveTransport | None = None,
                          private_output_dir: str | None = None) -> dict:
    sources = _project(project_id)["sources"]
    if not all(k in sources for k in ("document_registry", "master_sourcebook")):
        raise RetrievalPipelineBlocked("PROJECT_BOOTSTRAP_SOURCES_MISSING")
    drive = transport if transport is not None else ServiceAccountDriveTransport()
    registry_id = sources["document_registry"]["id"]
    sourcebook_id = sources["master_sourcebook"]["id"]
    registry = drive.read_document(registry_id)
    sourcebook = drive.read_document(sourcebook_id)
    candidate_atlases = [(key, s) for key, s in sources.items() if "visual" in s.get("role", "")]
    if not candidate_atlases:
        raise RetrievalPipelineBlocked("NO_ATLAS_SOURCES_REGISTERED")
    registry_text = "\n".join(p["text"] for p in registry.paragraphs)
    resolved = []
    for key, source in candidate_atlases:
        if source["id"] not in registry_text:
            continue
        atlas = drive.read_document(source["id"])
        text = "\n".join(p["text"] for p in atlas.paragraphs)
        import re
        if re.search(r"(?<![A-Z0-9-])" + re.escape(asset_id) + r"(?![A-Z0-9-])", text):
            resolved.append((key, atlas))
    if len(resolved) != 1:
        raise RetrievalPipelineBlocked("ASSET_ATLAS_MISSING_OR_AMBIGUOUS")
    key, atlas = resolved[0]
    with TemporaryDirectory() as tmp:
        raw, revision = drive.export_docx(atlas.document_id)
        if revision != atlas.revision_id:
            raise RetrievalPipelineBlocked("ATLAS_CHANGED_BETWEEN_READ_AND_EXPORT")
        path = Path(tmp) / "atlas.docx"
        path.write_bytes(raw)
        result = prepare_production_bundle(
            project_id=project_id, asset_id=asset_id,
            registry_document_id=registry.document_id,
            registry_revision_id=registry.revision_id,
            registry_paragraphs=registry.paragraphs,
            sourcebook_document_id=sourcebook.document_id,
            sourcebook_revision_id=sourcebook.revision_id,
            sourcebook_paragraphs=sourcebook.paragraphs,
            atlas_source_key=key, atlas_document_id=atlas.document_id,
            atlas_revision_id=atlas.revision_id,
            atlas_paragraphs=atlas.paragraphs, atlas_docx_path=str(path),
            export_attestation={"document_id":atlas.document_id,
                                "revision_id":revision,
                                "sha256":sha256(raw).hexdigest(),
                                "authenticated_export":True})
        # Recheck text revisions after export to prevent stale mixed snapshots.
        for snapshot in (registry, sourcebook, atlas):
            latest = drive.read_document(snapshot.document_id)
            if latest.revision_id != snapshot.revision_id:
                raise RetrievalPipelineBlocked("SOURCE_CHANGED_DURING_RETRIEVAL")
        if private_output_dir is not None:
            # Write actual verified reference bytes for the private rendering gateway.
            # Never return binary bytes from the public MCP endpoint.
            import os
            import tempfile
            asset = extract_assets(path, asset_id)[0]
            output_dir = Path(private_output_dir)
            output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            if output_dir.is_symlink():
                raise RetrievalPipelineBlocked('UNSAFE_OUTPUT_DIRECTORY')
            suffix = '.png' if asset.format == 'PNG' else '.jpg' if asset.format == 'JPEG' else None
            if suffix is None:
                raise RetrievalPipelineBlocked('UNSUPPORTED_IMAGE_FORMAT')
            target = output_dir / (asset_id + '_' + asset.sha256[:16] + suffix)
            if target.exists():
                if sha256(target.read_bytes()).hexdigest() != asset.sha256:
                    raise RetrievalPipelineBlocked('EXISTING_OUTPUT_HASH_MISMATCH')
            else:
                fd, temp = tempfile.mkstemp(dir=str(output_dir), prefix='.asset_')
                try:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(asset.data)
                    os.chmod(temp, 0o600)
                    os.replace(temp, target)
                finally:
                    if os.path.exists(temp):
                        os.unlink(temp)
            result['private_reference_path'] = str(target)
            result['reference_bytes_persisted'] = True
        return result
