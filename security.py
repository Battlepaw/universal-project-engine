"""Optional bearer-token authentication building block.

Not wired into the MCP server yet. Enabling authentication requires confirming
ChatGPT's supported credential flow first. Never log tokens or store them in Git.
"""
from __future__ import annotations

import hmac
import os


class SecurityConfigurationError(RuntimeError):
    """The deployment is missing a required security setting."""


def verify_bearer_header(authorization: str | None, *, token: str | None = None) -> bool:
    """Validate an Authorization header without leaking token values.

    No configured secret means DENY, not allow. This function is deliberately
    separate from the running app until a compatible client flow is confirmed.
    """
    secret = token if token is not None else os.environ.get("UPE_ACCESS_TOKEN")
    if not secret or len(secret) < 32:
        raise SecurityConfigurationError("UPE_ACCESS_TOKEN must be at least 32 characters")
    if not isinstance(authorization, str):
        return False
    scheme, separator, supplied = authorization.partition(" ")
    if not separator or scheme.casefold() != "bearer" or not supplied:
        return False
    return hmac.compare_digest(supplied, secret)
