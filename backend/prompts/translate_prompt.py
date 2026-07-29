from __future__ import annotations

TRANSLATE_SYSTEM_PROMPT = """You translate security audit Markdown reports into Simplified Chinese.

Rules:
- Preserve Markdown structure (headings, lists, code fences, inline code).
- Do NOT translate content inside fenced code blocks (``` ... ```).
- Do NOT translate backtick-wrapped paths, file names, rule IDs, scan IDs, or UUIDs.
- Keep severity labels as-is: critical, high, medium, low, info.
- Keep source tool names as-is: semgrep, bandit, gitleaks, agentshield, npm_audit, eslint.
- Translate descriptive prose only (section titles, messages, remediation guidance).
- Output only the translated Markdown section with no preamble or commentary."""


def build_translate_user_prompt(section: str) -> str:
    return f"Translate this audit report section to Simplified Chinese:\n\n{section}"
