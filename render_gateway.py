"""Byte-aware image editing transport adapted from the approved ENDARIA v1.2 adapter.
Actual input images are submitted together. API acceptance is not visual approval.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import urllib.request
from dataclasses import dataclass


class RenderBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class RenderReference:
    asset_id: str
    path: str
    sha256: str


def validated_references(refs):
    if not refs or len(refs) > 16 or len({r.asset_id for r in refs}) != len(refs):
        raise RenderBlocked("MISSING_DUPLICATE_OR_TOO_MANY_REFERENCES")
    out = []
    for ref in refs:
        path = Path(ref.path)
        if not path.is_file():
            raise RenderBlocked("REFERENCE_MISSING")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != ref.sha256:
            raise RenderBlocked("REFERENCE_HASH_MISMATCH")
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            mime, ext = "image/png", "png"
        elif data.startswith(b"\xff\xd8\xff"):
            mime, ext = "image/jpeg", "jpg"
        else:
            raise RenderBlocked("UNSUPPORTED_REFERENCE_FORMAT")
        if len(data) > 50 * 1024 * 1024:
            raise RenderBlocked("REFERENCE_TOO_LARGE")
        out.append((ref, data, mime, ext))
    return out


def multipart(fields, images):
    boundary = "upe-" + secrets.token_hex(18)
    chunks = []
    for key, val in fields.items():
        chunks.extend([
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
            str(val).encode(), b"\r\n",
        ])
    for i, (_, data, mime, ext) in enumerate(images):
        chunks.extend([
            f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="reference_{i}.{ext}"\r\nContent-Type: {mime}\r\n\r\n'.encode(),
            data, b"\r\n",
        ])
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class OpenAIImageEditProvider:
    """Existing adapter's provider, updated for active November 2026 image model."""
    def __init__(self, *, api_key=None, model="gpt-image-2.6-sunburst", sender=None):
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.sender = sender or self._send

    @staticmethod
    def _send(url, body, headers):
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read()

    def generate(self, *, prompt, references):
        if not self.api_key:
            raise RenderBlocked("API_CREDENTIALS_NOT_CONFIGURED")
        if not isinstance(prompt, str) or not prompt.strip():
            raise RenderBlocked("EMPTY_PROMPT")
        images = validated_references(references)
        body, content_type = multipart({"model": self.model, "prompt": prompt}, images)
        raw = self.sender("https://api.openai.com/v1/images/edits", body, {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": content_type,
        })
        try:
            result = base64.b64decode(json.loads(raw)["data"][0]["b64_json"], validate=True)
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise RenderBlocked("PROVIDER_RESPONSE_INVALID") from exc
        if not (result.startswith(b"\x89PNG\r\n\x1a\n") or result.startswith(b"\xff\xd8\xff")):
            raise RenderBlocked("PROVIDER_RESULT_NOT_IMAGE")
        return result


def render_staged(*, request_id, prompt, references, provider, output_dir):
    """Generate an explicitly UNAPPROVED draft and a hash-bound receipt."""
    if not isinstance(request_id, str) or not request_id or "/" in request_id or "\\" in request_id or request_id in (".", ".."):
        raise RenderBlocked("INVALID_REQUEST_ID")
    verified = validated_references(references)
    output = provider.generate(prompt=prompt, references=references)
    if not isinstance(output, bytes):
        raise RenderBlocked("PROVIDER_RESULT_INVALID")
    extension = ".png" if output.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg" if output.startswith(b"\xff\xd8\xff") else None
    if extension is None:
        raise RenderBlocked("PROVIDER_RESULT_NOT_IMAGE")
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / (request_id + extension)
    if destination.exists():
        raise RenderBlocked("REQUEST_OUTPUT_ALREADY_EXISTS")
    destination.write_bytes(output)
    receipt = {
        "request_id": request_id,
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "output_file": str(destination),
        "reference_hashes": {r.asset_id: r.sha256 for r, _, _, _ in verified},
        "reference_transport": "SENT_TO_EDIT_API_NOT_VISUAL_FIDELITY_VERIFIED",
        "status": "GENERATED_UNAPPROVED",
        "author_approval": False,
        "drive_backup_verified": False,
    }
    (directory / (request_id + ".json")).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt
