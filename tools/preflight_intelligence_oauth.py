#!/usr/bin/env python3
"""Verify the public StarIntel OAuth surface before finalizing Bixby registration.

The probe is intentionally credential-free. It verifies that the two OAuth
protocol paths are reachable while the dedicated host rejects unrelated paths.
It never authenticates a user, registers a client, or mutates StarIntel state.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import NamedTuple


_TOOL_DIR = pathlib.Path(__file__).resolve().parent
_RENDERER = _TOOL_DIR / "render_intelligence_oauth.py"


def _load_renderer():
    spec = importlib.util.spec_from_file_location("render_intelligence_oauth", _RENDERER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Intelligence OAuth renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProbeResult(NamedTuple):
    status: int
    body: bytes = b""


class PreflightReport(NamedTuple):
    ok: bool
    origin: str
    authorize_status: int | None = None
    token_status: int | None = None
    root_status: int | None = None
    unapproved_status: int | None = None
    error_code: str | None = None
    public_message: str = ""


Request = Callable[..., ProbeResult]
_HEADERS: Mapping[str, str] = {
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.1",
    "User-Agent": "starintel-bixby-oauth-preflight/1",
}
_TIMEOUT_SECONDS = 5
_UNAPPROVED_PATH = "/api/v1/search"
_DNS_FAILURE_MARKERS = (
    "name or service not known",
    "temporary failure in name resolution",
    "nodename nor servname provided",
    "no address associated with hostname",
    "getaddrinfo failed",
)


def _request(method: str, url: str, *, headers: Mapping[str, str], timeout: int, body: bytes) -> ProbeResult:
    outbound = urllib.request.Request(
        url,
        data=body if method == "POST" else None,
        headers=dict(headers),
        method=method,
    )
    try:
        with urllib.request.urlopen(outbound, timeout=timeout) as response:
            return ProbeResult(response.status, response.read(512))
    except urllib.error.HTTPError as exc:
        return ProbeResult(exc.code, exc.read(512))
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise OSError(str(reason)) from exc


def _surface_exists(status: int) -> bool:
    return 200 <= status < 500 and status != 404


def _reachability_failure(exc: OSError) -> tuple[str, str]:
    """Map transport failures to stable, non-sensitive operator diagnostics."""
    detail = str(exc).lower()
    if any(marker in detail for marker in _DNS_FAILURE_MARKERS):
        return "DNS_UNRESOLVED", "public OAuth hostname does not resolve"
    return "UNREACHABLE", "public OAuth origin is not reachable over HTTPS"


def preflight(oauth_origin: str, *, request: Request = _request) -> PreflightReport:
    """Probe the public OAuth origin without sending user or client credentials."""
    renderer = _load_renderer()
    origin = renderer._public_https_origin(oauth_origin)

    probes = (
        ("authorize_status", "GET", f"{origin}/oauth/authorize"),
        ("token_status", "POST", f"{origin}/oauth/token"),
        ("root_status", "GET", f"{origin}/"),
        ("unapproved_status", "GET", f"{origin}{_UNAPPROVED_PATH}"),
    )
    statuses: dict[str, int] = {}
    try:
        for field, method, url in probes:
            result = request(
                method,
                url,
                headers=_HEADERS,
                timeout=_TIMEOUT_SECONDS,
                body=b"",
            )
            statuses[field] = result.status
    except OSError as exc:
        error_code, public_message = _reachability_failure(exc)
        return PreflightReport(
            ok=False,
            origin=origin,
            **statuses,
            error_code=error_code,
            public_message=public_message,
        )

    if not _surface_exists(statuses["authorize_status"]) or not _surface_exists(statuses["token_status"]):
        return PreflightReport(
            ok=False,
            origin=origin,
            **statuses,
            error_code="OAUTH_SURFACE_UNAVAILABLE",
            public_message="OAuth authorize/token surface is unavailable",
        )

    if statuses["root_status"] != 404 or statuses["unapproved_status"] != 404:
        return PreflightReport(
            ok=False,
            origin=origin,
            **statuses,
            error_code="UNAPPROVED_ROUTE_EXPOSED",
            public_message="OAuth host exposes a route outside the approved OAuth surface",
        )

    return PreflightReport(
        ok=True,
        origin=origin,
        **statuses,
        public_message="OAuth surface is reachable and unrelated routes fail closed",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oauth-origin", required=True)
    args = parser.parse_args()

    report = preflight(args.oauth_origin)
    print(f"origin={report.origin}")
    print(f"authorize_status={report.authorize_status}")
    print(f"token_status={report.token_status}")
    print(f"root_status={report.root_status}")
    print(f"unapproved_status={report.unapproved_status}")
    print(f"result={'PASS' if report.ok else 'FAIL'}")
    if report.error_code:
        print(f"error={report.error_code}")
    print(report.public_message)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
