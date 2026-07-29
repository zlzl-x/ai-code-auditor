from __future__ import annotations

from pathlib import Path

from backend.core.context import ScanContext
from backend.core.llm import get_llm_client, is_provider_configured, resolve_llm_provider
from backend.core.llm.models import deepseek_completion_options, resolve_llm_model
from backend.prompts.translate_prompt import TRANSLATE_SYSTEM_PROMPT, build_translate_user_prompt

MAX_SECTION_CHARS = 6000
TRANSLATE_MAX_TOKENS = 4096


def split_markdown_sections(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    parts = normalized.split("\n## ")
    sections: list[str] = [parts[0]]
    for part in parts[1:]:
        sections.append(f"## {part}")
    return _split_oversized_sections(sections)


def _split_oversized_sections(sections: list[str]) -> list[str]:
    result: list[str] = []
    for section in sections:
        if len(section) <= MAX_SECTION_CHARS:
            result.append(section)
            continue
        result.extend(_split_by_subheadings(section))
    return result


def _split_by_subheadings(section: str) -> list[str]:
    parts = section.split("\n### ")
    if len(parts) == 1:
        return _split_by_length(section)

    chunks: list[str] = [parts[0]]
    for part in parts[1:]:
        chunks.append(f"### {part}")
    return _split_oversized_sections(chunks)


def _split_by_length(section: str) -> list[str]:
    if len(section) <= MAX_SECTION_CHARS:
        return [section]
    chunks: list[str] = []
    start = 0
    while start < len(section):
        end = min(start + MAX_SECTION_CHARS, len(section))
        chunks.append(section[start:end])
        start = end
    return chunks


def translate_section(client, section: str, ctx: ScanContext, *, role: str, model: str) -> str:
    options = deepseek_completion_options(role=role, model=model)
    response = client.complete(
        TRANSLATE_SYSTEM_PROMPT,
        build_translate_user_prompt(section),
        max_tokens=TRANSLATE_MAX_TOKENS,
        thinking=options.get("thinking"),
        reasoning_effort=options.get("reasoning_effort"),
    )
    ctx.scan_meta.tokens_in += response.tokens_in
    ctx.scan_meta.tokens_out += response.tokens_out
    if response.model and response.model not in ctx.scan_meta.models_used:
        ctx.scan_meta.models_used.append(response.model)
    return response.text.strip()


def translate_audit_report(ctx: ScanContext, source: Path) -> Path | None:
    if ctx.report_lang != "zh":
        return None

    provider = resolve_llm_provider("translate")
    if provider == "mock" or not is_provider_configured(provider):
        ctx.errors.append("translate_report: skipped (mock LLM or provider not configured)")
        return None

    if not source.is_file():
        ctx.errors.append("translate_report: AUDIT_REPORT.md not found")
        return None

    model = resolve_llm_model("translate")
    client = get_llm_client(model, role="translate")

    text = source.read_text(encoding="utf-8")
    sections = split_markdown_sections(text)
    translated_sections = [
        translate_section(client, section, ctx, role="translate", model=model) for section in sections
    ]
    output_path = source.with_name("AUDIT_REPORT.zh.md")
    output_path.write_text("\n\n".join(translated_sections) + "\n", encoding="utf-8")
    ctx.translated_report = output_path.name
    return output_path
