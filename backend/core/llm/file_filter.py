from __future__ import annotations

import fnmatch
from pathlib import Path

MAX_BYTES_PER_FILE = 4096

DENYLIST_PATTERNS = (
    ".env",
    ".env.*",
    "*secret*",
    "*credential*",
    "*password*",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_rsa.*",
)


def is_denied_path(path: Path) -> bool:
    name = path.name.lower()
    for pattern in DENYLIST_PATTERNS:
        if fnmatch.fnmatch(name, pattern.lower()):
            return True
    return False


def read_file_snippet(path: Path, max_bytes: int = MAX_BYTES_PER_FILE) -> str | None:
    if not path.is_file() or is_denied_path(path):
        return None
    try:
        data = path.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="replace")
    except OSError:
        return None
