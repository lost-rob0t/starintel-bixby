#!/usr/bin/env python3
from __future__ import annotations

import ipaddress
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


class PolicyError(RuntimeError):
    pass


TEXT_SUFFIXES = {".bxb", ".js", ".json", ".md", ".txt", ".yaml", ".yml"}
URL_RE = re.compile(r"https?://[^\s\"'<>)}]+", re.IGNORECASE)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:client[_-]?secret|api[_-]?key|access[_-]?token|bearer[_-]?token|password)\b\s*[:=]\s*[\"'][^\"']{8,}[\"']"
)


def _policy_files(root: Path):
    for base in (root / "capsules", root / "contracts", root / "fixtures"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                yield path


def _is_private_host(host: str) -> bool:
    lowered = host.rstrip(".").lower()
    if lowered.endswith(".star.intel") or lowered == "star.intel":
        return True
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return not address.is_global


def _check_internal_urls(path: Path, text: str) -> None:
    for match in URL_RE.finditer(text):
        candidate = match.group(0)
        if "\\" in candidate or "${" in candidate:
            continue
        try:
            parsed = urlparse(candidate)
        except ValueError:
            raise PolicyError(f"{path}: malformed URL-like endpoint is forbidden")
        if parsed.hostname and _is_private_host(parsed.hostname):
            raise PolicyError(f"{path}: private/internal endpoint is forbidden")


def _check_capsule_secrets(root: Path, path: Path, text: str) -> None:
    try:
        relative = path.relative_to(root / "capsules")
    except ValueError:
        return
    if relative.parts and SECRET_ASSIGNMENT_RE.search(text):
        raise PolicyError(f"{path}: secret-like credential assignment is forbidden")


def validate_tree(root: Path | str) -> None:
    root = Path(root).resolve()
    for path in _policy_files(root):
        text = path.read_text(encoding="utf-8")
        _check_internal_urls(path, text)
        _check_capsule_secrets(root, path, text)


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    try:
        validate_tree(root)
    except PolicyError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
