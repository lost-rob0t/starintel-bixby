#!/usr/bin/env python3
"""Render and finalize registered StarIntel Intelligence OAuth configuration.

This tool accepts only public registration metadata. It intentionally has no
argument for the OAuth client secret value; that value belongs in Samsung
Developer Center Configuration & Secrets.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import pathlib
import re
import tempfile
from urllib.parse import urlsplit


_SAFE_ATOM = re.compile(r"^[A-Za-z0-9._:-]+$")
_CAPSULE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)+$")
_READ_SCOPES = ("documents:read", "search:read")
_INTELLIGENCE_ACTIONS = ("ResolvePerson", "SearchDocuments")
_OPTIONAL_USER_AUTH = "authorization: user: optional"


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


def _registered_capsule_id(capsule_id: str) -> str:
    if not isinstance(capsule_id, str) or not _CAPSULE_ID.fullmatch(capsule_id):
        raise ValueError("capsule ID is invalid")
    if capsule_id.startswith("playground."):
        raise ValueError("development playground IDs are not valid registration targets")
    return capsule_id


def bixby_redirect_uri(capsule_id: str) -> str:
    """Return Samsung's documented callback for a registered capsule ID."""
    capsule_id = _registered_capsule_id(capsule_id)
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


def _replace_capsule_id(source: str, capsule_id: str) -> str:
    capsule_id = _registered_capsule_id(capsule_id)
    matches = list(re.finditer(r"(?m)^(\s*)id\s*\(([^)]+)\)\s*$", source))
    if len(matches) != 1:
        raise ValueError("capsule.bxb must contain exactly one capsule id declaration")
    match = matches[0]
    current = match.group(2).strip()
    if current != capsule_id and not current.startswith("playground."):
        raise ValueError("capsule.bxb already names a different registered capsule")
    replacement = f"{match.group(1)}id ({capsule_id})"
    return source[: match.start()] + replacement + source[match.end() :]


def _matching_brace(source: str, open_index: int) -> int:
    depth = 0
    for index in range(open_index, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unbalanced Bixby source block")


def _annotate_optional_user(source: str, action: str) -> str:
    pattern = re.compile(rf"(?m)^(\s*)action-endpoint\s*\({re.escape(action)}\)\s*\{{")
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"endpoints.bxb must contain exactly one {action} endpoint")
    match = matches[0]
    open_index = source.find("{", match.start(), match.end())
    close_index = _matching_brace(source, open_index)
    block = source[match.start() : close_index + 1]

    authorization_mentions = re.findall(r"\bauthorization\b", block)
    if authorization_mentions:
        if block.count(_OPTIONAL_USER_AUTH) == 1 and len(authorization_mentions) == 1:
            return source
        raise ValueError(f"{action} endpoint already contains conflicting authorization")

    child_indent = match.group(1) + "  "
    close_line_start = source.rfind("\n", match.start(), close_index) + 1
    close_prefix = source[close_line_start:close_index]
    if not close_prefix.strip():
        insertion = f"{child_indent}{_OPTIONAL_USER_AUTH}\n"
        return source[:close_line_start] + insertion + source[close_line_start:]

    # Compact one-line endpoint blocks are valid source too. Expand only the
    # opening edge, preserving the existing endpoint body and closing brace.
    insertion = f"\n{child_indent}{_OPTIONAL_USER_AUTH}\n{child_indent}"
    return source[: open_index + 1] + insertion + source[open_index + 1 :]


def finalize_registered_sources(
    capsule_source: str,
    endpoints_source: str,
    capsule_id: str,
    oauth_origin: str,
    client_id: str,
    client_secret_key: str,
) -> dict[str, str]:
    """Return the complete registered Intelligence source set without writing it."""
    capsule = _replace_capsule_id(capsule_source, capsule_id)
    endpoints = endpoints_source
    for action in _INTELLIGENCE_ACTIONS:
        endpoints = _annotate_optional_user(endpoints, action)
    authorization = render_authorization(oauth_origin, client_id, client_secret_key)
    return {
        "capsule.bxb": capsule,
        "endpoints.bxb": endpoints,
        "authorization.bxb": authorization,
        "redirect_uri": bixby_redirect_uri(capsule_id),
    }


def _replace_text(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    temporary_path = pathlib.Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _commit_sources(updates: list[tuple[pathlib.Path, str]]) -> None:
    """Apply a small file transaction and restore the original tree on failure."""
    originals = {
        path: (path.exists(), path.read_text(encoding="utf-8") if path.exists() else None)
        for path, _ in updates
    }
    written: list[pathlib.Path] = []
    try:
        for path, content in updates:
            _replace_text(path, content)
            written.append(path)
    except Exception:
        for path in reversed(written):
            existed, content = originals[path]
            if existed:
                _replace_text(path, content or "")
            elif path.exists():
                path.unlink()
        raise


def finalize_capsule_tree(
    capsule_root: pathlib.Path | str,
    capsule_id: str,
    oauth_origin: str,
    client_id: str,
    client_secret_key: str,
) -> dict[str, str]:
    """Finalize the registered capsule after validating every output first."""
    root = pathlib.Path(capsule_root)
    capsule_path = root / "capsule.bxb"
    endpoints_path = root / "resources" / "base" / "endpoints.bxb"
    authorization_path = root / "authorization.bxb"
    if not capsule_path.is_file() or not endpoints_path.is_file():
        raise ValueError("capsule root is missing capsule.bxb or resources/base/endpoints.bxb")

    finalized = finalize_registered_sources(
        capsule_source=capsule_path.read_text(encoding="utf-8"),
        endpoints_source=endpoints_path.read_text(encoding="utf-8"),
        capsule_id=capsule_id,
        oauth_origin=oauth_origin,
        client_id=client_id,
        client_secret_key=client_secret_key,
    )

    if authorization_path.exists():
        current_authorization = authorization_path.read_text(encoding="utf-8")
        if current_authorization != finalized["authorization.bxb"]:
            raise ValueError("authorization.bxb already exists with different registration metadata")

    # All parsing/authority/registration validation completes before any write.
    _commit_sources(
        [
            (capsule_path, finalized["capsule.bxb"]),
            (endpoints_path, finalized["endpoints.bxb"]),
            (authorization_path, finalized["authorization.bxb"]),
        ]
    )
    return finalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oauth-origin", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret-key", required=True)
    parser.add_argument(
        "--capsule-id",
        help="registered capsule ID; required when finalizing a capsule tree",
    )
    parser.add_argument(
        "--capsule-root",
        type=pathlib.Path,
        help="capsule root to finalize; requires --write and --capsule-id",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the registered capsule ID, authorization.bxb, and optional-user endpoint annotations",
    )
    args = parser.parse_args()

    if args.write:
        if args.capsule_root is None or not args.capsule_id:
            parser.error("--write requires --capsule-root and --capsule-id")
        result = finalize_capsule_tree(
            args.capsule_root,
            capsule_id=args.capsule_id,
            oauth_origin=args.oauth_origin,
            client_id=args.client_id,
            client_secret_key=args.client_secret_key,
        )
        print(result["redirect_uri"])
        return 0

    if args.capsule_root is not None:
        parser.error("--capsule-root requires --write")
    if args.capsule_id:
        print(f"// registered redirect: {bixby_redirect_uri(args.capsule_id)}")
    print(render_authorization(args.oauth_origin, args.client_id, args.client_secret_key), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
