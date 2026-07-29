from __future__ import annotations

import html
import re
from pathlib import Path

from fastapi import HTTPException, Request

LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


def escape_html(text: str) -> str:
    return html.escape(text, quote=True)


def check_local_origin(request: Request) -> None:
    if request.method not in {"POST", "PATCH", "PUT", "DELETE"}:
        return
    host = (request.headers.get("host") or "").split(":")[0].lower()
    origin = request.headers.get("origin")
    if origin:
        origin_host = re.sub(r"^https?://", "", origin).split(":")[0].lower()
        if origin_host not in LOCAL_HOSTS:
            raise HTTPException(status_code=403, detail="Origin not allowed")
    elif host not in LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="Host not allowed")


def validate_results_path(repo_root: Path, project_id: str, results_path: Path) -> Path:
    expected_root = (repo_root / "results" / project_id).resolve()
    resolved = results_path.resolve()
    if expected_root not in resolved.parents and resolved != expected_root:
        raise HTTPException(status_code=403, detail="Results path outside project scope")
    results_root = (repo_root / "results").resolve()
    if results_root not in resolved.parents and resolved != results_root:
        raise HTTPException(status_code=403, detail="Results path outside results directory")
    return resolved
