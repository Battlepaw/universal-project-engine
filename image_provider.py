"""Private image-edit provider transport; sends actual verified reference bytes.

Never expose API credentials, image bytes or output paths on public MCP tools.
A successful response proves transport, not character/ship visual fidelity.
"""
from __future__ import annotations
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import urllib.request

class ProviderTransportBlocked(RuntimeError):
    pass

def send_image_edit(*, prompt: str, references: list[dict], sender=None,
                    api_key: str | None = None, model: str = "gpt-image-1") -> dict:
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ProviderTransportBlocked("IMAGE_PROVIDER_CREDENTIAL_MISSING")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ProviderTransportBlocked("PROMPT_REQUIRED")
    if not references or len({r.get("asset_id") for r in references}) != len(references):
        raise ProviderTransportBlocked("REFERENCES_MISSING_OR_DUPLICATED")
    validated = []
    for ref in references:
        path = Path(ref["private_reference_path"])
        if not path.is_file():
            raise ProviderTransportBlocked("REFERENCE_FILE_MISSING")
        data = path.read_bytes()
        digest = sha256(data).hexdigest()
        if digest != ref.get("sha256"):
            raise ProviderTransportBlocked("REFERENCE_HASH_MISMATCH")
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            mime, ext = "image/png", "png"
        elif data.startswith(b"\xff\xd8\xff"):
            mime, ext = "image/jpeg", "jpg"
        else:
            raise ProviderTransportBlocked("UNSUPPORTED_REFERENCE_IMAGE")
        validated.append((ref["asset_id"], data, digest, mime, ext))
    boundary = "upe-" + secrets.token_hex(16)
    chunks = []
    for name, value in (("model", model), ("prompt", prompt)):
        chunks.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode(), value.encode(), b'\r\n'])
    for i, (_, data, _, mime, ext) in enumerate(validated):
        chunks.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="reference_{i}.{ext}"\r\nContent-Type: {mime}\r\n\r\n'.encode(), data, b'\r\n'])
    chunks.append(f'--{boundary}--\r\n'.encode())
    body = b''.join(chunks)
    endpoint = "https://api.openai.com/v1/images/edits"
    headers = {"Authorization": "Bearer " + key,
               "Content-Type": "multipart/form-data; boundary=" + boundary}
    if sender is None:
        def sender(url, data, headers):
            request = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
    try:
        payload = json.loads(sender(endpoint, body, headers))
        raw = base64.b64decode(payload["data"][0]["b64_json"], validate=True)
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise ProviderTransportBlocked("INVALID_PROVIDER_RESPONSE") from exc
    if not (raw.startswith(b"\x89PNG\r\n\x1a\n") or raw.startswith(b"\xff\xd8\xff")):
        raise ProviderTransportBlocked("PROVIDER_RESULT_NOT_IMAGE")
    return {"status": "PROVIDER_ACCEPTED_REFERENCE_REQUEST",
            "references": [{"asset_id": asset_id, "sha256": digest, "accepted": True}
                           for asset_id, _, digest, _, _ in validated],
            "output_sha256": sha256(raw).hexdigest(),
            "output_bytes": raw,
            "visual_fidelity_verified": False,
            "author_approved": False}
