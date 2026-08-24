#!/usr/bin/env python3
"""Render registered StarIntel Intelligence OAuth configuration.

This tool accepts only public registration metadata. It intentionally has no
argument for the OAuth client secret value; that value belongs in Samsung
Developer Center Configuration & Secrets.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
from urllib.parse import urlsplit


_SAFE_ATOM = re.compile(r"^[A-Za-z0-9._:-]+$")
_CAPSULE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)+$")
_READ_SCOPES = ("documents:read", "search:read")


def _public_https_origin(value: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not value:
        raise ValueError("OAuth origin must be a non-empty HTTPS origin")
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("OAuth origin must use HTTPS")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("OAuth origin must not contain credentials, query, or fragment")
    if parsed.path not in ("", "/"):
        raise ValueError("OAuth origin must not contain a path")

    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("OAuth origin must be public")
    if host == "star.intel" or host.endswith(".star.intel"):
        raise ValueError("OAuth origin must not expose private StarIntel DNS")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("OAuth origin must use a public address")

    authority = parsed.netloc
    return f"https://{authority}".rstrip("/")


def _safe_atom(name: str, value: str) -> str:
    if not isinstance(value, str) or not _SAFE_ATOM.fullmatch(value):
        raise ValueError(f"{name} contains characters unsafe for Bixby source")
    return value


def bixby_redirect_uri(capsule_id: str) -> str:
    """Return Samsung's documented callback for a registered capsule ID."""
    if not isinstance(capsule_id, str) or not _CAPSULE_ID.fullmatch(capsule_id):
        raise ValueError("capsule ID is invalid")
    if capsule_id.startswith("playground."):
        raise ValueError("development playground IDs are not valid registration targets")
    encoded = capsule_id.replace(".", "-")
    return f"https://{encoded}.oauth.aibixby.com/auth/external/cb"


def render_authorization(oauth_origin: str, client_id: str, client_secret_key: str) -> str:
    """Render authorization.bxb using public metadata only."""
    origin = _public_https_origin(oauth_origin)
    client_id = _safe_atom("client ID", client_id)
    client_secret_key = _safe_atom("Developer Center secret-key name", client_secret_key)
    scopes = " ".join(_READ_SCOPES)
    return (
        "authorization {\n"
        "  user {\n"
        "    oauth2-authorization-code (StarIntel) {\n"
        f'      authorize-endpoint ("{origin}/oauth/authorize")\n'
        f"      client-id ({client_id})\n"
        f"      client-secret-key ({client_secret_key})\n"
        f"      scope ({scopes})\n"
        f'      token-endpoint ("{origin}/oauth/token")\n'
        "    }\n"
        "  }\n"
        "}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oauth-origin", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret-key", required=True)
    parser.add_argument(
        "--capsule-id",
        help="registered capsule ID; when set, emit its Samsung callback as a comment",
    )
    args = parser.parse_args()

    if args.capsule_id:
        print(f"// registered redirect: {bixby_redirect_uri(args.capsule_id)}")
    print(render_authorization(args.oauth_origin, args.client_id, args.client_secret_key), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
