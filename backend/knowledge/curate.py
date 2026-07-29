from __future__ import annotations

import json
import logging
import os
from typing import Any

from backend.core.llm.factory import is_provider_configured
from backend.core.path_validation import get_repo_root
from backend.core.registry import load_modules_config
from backend.knowledge.storage import KnowledgeStorage

logger = logging.getLogger(__name__)


def _should_curate() -> bool:
    return os.environ.get("AUTO_LLM_CURATE", "").strip().lower() in {"1", "true", "yes"}


def _parse_curate_response(text: str) -> tuple[str, str]:
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return (
                str(payload.get("one_line_summary", "")).strip(),
                str(payload.get("category", "blog")).strip() or "blog",
            )
    except json.JSONDecodeError:
        pass
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return (lines[0] if lines else text[:200], "blog")


def curate_top_items(
    storage: KnowledgeStorage,
    *,
    limit: int = 5,
    repo_root=None,
) -> int:
    if not _should_curate():
        return 0
    if not is_provider_configured("deepseek"):
        logger.warning("AUTO_LLM_CURATE enabled but DEEPSEEK_API_KEY is missing; skipping")
        return 0

    root = repo_root or get_repo_root()
    modules = load_modules_config(root).get("llm", {})
    from backend.core.llm.models import resolve_llm_model

    model = resolve_llm_model("screening")
    from backend.core.llm.deepseek_client import DeepSeekClient

    client = DeepSeekClient(model=model)

    rows = storage.list_backlog(limit=limit * 2, min_score=0)
    updated = 0
    for row in rows:
        summary = str(row.get("summary", "")).strip()
        if summary and len(summary) > 40 and not summary.startswith("{"):
            continue
        system = (
            "You summarize security feed items for an engineering backlog. "
            "Return JSON only: {\"one_line_summary\": \"...\", \"category\": \"tool|blog|methodology\"}."
        )
        user = f"Title: {row['title']}\nURL: {row['url']}\nExisting summary: {summary or '(empty)'}"
        try:
            response = client.complete(system, user)
        except Exception as exc:  # noqa: BLE001
            logger.warning("AUTO_LLM_CURATE failed for %s: %s", row["id"], exc)
            continue
        one_line, category = _parse_curate_response(response.text)
        if one_line:
            storage.update_summary(row["id"], one_line, category)
            updated += 1
        if updated >= limit:
            break
    return updated
