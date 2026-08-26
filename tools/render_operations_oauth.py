#!/usr/bin/env python3
"""Render/finalize registered StarIntel Operations OAuth configuration.

Only public registration metadata is accepted. OAuth client secret values belong
in Samsung Developer Center Configuration & Secrets and are never accepted here.
"""
from __future__ import annotations

import ipaddress
import os
import pathlib
import re
import tempfile
from urllib.parse import urlsplit

SAFE_ATOM = re.compile(r"^[A-Za-z0-9._:-]+$")
CAPSULE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)+$")
SCOPES = ("targets:dispatch", "starintel.autodig.read", "starintel.autodig.control")
OPERATIONS_ACTIONS = (
    "PrepareTarget", "CommitTarget", "GetAutoDigStatus", "GetAutoDigRun",
    "ListAutoDigRuns", "StartAutoDig", "PauseAutoDig", "ResumeAutoDig", "StopAutoDig",
)
REQUIRED_USER_AUTH = "authorization: user"


def _public_https_origin(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("OAuth origin must be a non-empty HTTPS origin")
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("OAuth origin must use HTTPS")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("OAuth origin must be an origin only")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or host == "star.intel" or host.endswith(".star.intel"):
        raise ValueError("OAuth origin must be public")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("OAuth origin must use a public address")
    return f"https://{parsed.netloc}".rstrip("/")


def _safe_atom(name: str, value: str) -> str:
    if not isinstance(value, str) or not SAFE_ATOM.fullmatch(value):
        raise ValueError(f"{name} contains characters unsafe for Bixby source")
    return value


def _registered_capsule_id(value: str) -> str:
    if not isinstance(value, str) or not CAPSULE_ID.fullmatch(value):
        raise ValueError("capsule ID is invalid")
    if value.startswith("playground."):
        raise ValueError("playground capsule IDs cannot be registration targets")
    return value


def bixby_redirect_uri(capsule_id: str) -> str:
    capsule_id = _registered_capsule_id(capsule_id)
    return f"https://{capsule_id.replace('.', '-')}.oauth.aibixby.com/auth/external/cb"


def render_authorization(oauth_origin: str, client_id: str, client_secret_key: str) -> str:
    origin = _public_https_origin(oauth_origin)
    client_id = _safe_atom("client ID", client_id)
    client_secret_key = _safe_atom("Developer Center secret-key name", client_secret_key)
    return (
        "authorization {\n"
        "  user {\n"
        "    oauth2-authorization-code (StarIntel) {\n"
        f'      authorize-endpoint ("{origin}/oauth/authorize")\n'
        f"      client-id ({client_id})\n"
        f"      client-secret-key ({client_secret_key})\n"
        f"      scope ({' '.join(SCOPES)})\n"
        f'      token-endpoint ("{origin}/oauth/token")\n'
        "    }\n"
        "  }\n"
        "}\n"
    )


def _replace_capsule_id(source: str, capsule_id: str) -> str:
    capsule_id = _registered_capsule_id(capsule_id)
    matches = list(re.finditer(r"(?m)^(\s*)id\s*\(([^)]+)\)\s*$", source))
    if len(matches) != 1:
        raise ValueError("capsule.bxb must contain exactly one capsule id")
    match = matches[0]
    current = match.group(2).strip()
    if current != capsule_id and not current.startswith("playground."):
        raise ValueError("capsule already names a different registered ID")
    return source[:match.start()] + f"{match.group(1)}id ({capsule_id})" + source[match.end():]


def _matching_brace(source: str, start: int) -> int:
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unbalanced Bixby source")


def _require_user_auth(source: str, action: str) -> str:
    pattern = re.compile(rf"(?m)^(\s*)action-endpoint\s*\({re.escape(action)}\)\s*\{{")
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"endpoints.bxb must contain exactly one {action} endpoint")
    match = matches[0]
    open_index = source.find("{", match.start(), match.end())
    close_index = _matching_brace(source, open_index)
    block = source[match.start():close_index + 1]
    auth_mentions = re.findall(r"\bauthorization\b", block)
    if auth_mentions:
        if block.count(REQUIRED_USER_AUTH) == 1 and "authorization: user: optional" not in block and len(auth_mentions) == 1:
            return source
        raise ValueError(f"{action} endpoint contains conflicting authorization")
    child_indent = match.group(1) + "  "
    close_line_start = source.rfind("\n", match.start(), close_index) + 1
    close_prefix = source[close_line_start:close_index]
    if not close_prefix.strip():
        return source[:close_line_start] + f"{child_indent}{REQUIRED_USER_AUTH}\n" + source[close_line_start:]
    insertion = f"\n{child_indent}{REQUIRED_USER_AUTH}\n{child_indent}"
    return source[:open_index + 1] + insertion + source[open_index + 1:]


def finalize_registered_sources(capsule_source: str, endpoints_source: str, capsule_id: str,
                                oauth_origin: str, client_id: str, client_secret_key: str) -> dict[str, str]:
    endpoints = endpoints_source
    for action in OPERATIONS_ACTIONS:
        endpoints = _require_user_auth(endpoints, action)
    return {
        "capsule.bxb": _replace_capsule_id(capsule_source, capsule_id),
        "endpoints.bxb": endpoints,
        "authorization.bxb": render_authorization(oauth_origin, client_id, client_secret_key),
        "redirect_uri": bixby_redirect_uri(capsule_id),
    }


def _replace_text(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    temp_path = pathlib.Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _commit_sources(updates: list[tuple[pathlib.Path, str]]) -> None:
    originals = {path: (path.exists(), path.read_text(encoding="utf-8") if path.exists() else None) for path, _ in updates}
    written = []
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


def finalize_capsule_tree(capsule_root: pathlib.Path | str, capsule_id: str, oauth_origin: str,
                          client_id: str, client_secret_key: str) -> dict[str, str]:
    root = pathlib.Path(capsule_root)
    capsule_path = root / "capsule.bxb"
    endpoints_path = root / "resources" / "base" / "endpoints.bxb"
    authorization_path = root / "authorization.bxb"
    if not capsule_path.is_file() or not endpoints_path.is_file():
        raise ValueError("capsule root is incomplete")
    result = finalize_registered_sources(
        capsule_path.read_text(encoding="utf-8"), endpoints_path.read_text(encoding="utf-8"),
        capsule_id, oauth_origin, client_id, client_secret_key,
    )
    if authorization_path.exists() and authorization_path.read_text(encoding="utf-8") != result["authorization.bxb"]:
        raise ValueError("authorization.bxb already contains different registration metadata")
    _commit_sources([
        (capsule_path, result["capsule.bxb"]),
        (endpoints_path, result["endpoints.bxb"]),
        (authorization_path, result["authorization.bxb"]),
    ])
    return result
