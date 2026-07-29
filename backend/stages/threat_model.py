from __future__ import annotations

from backend.core.context import ScanContext


def build_threat_model(ctx: ScanContext) -> str:
    recon = ctx.recon_data
    languages = recon.get("languages", {})
    focus_areas = recon.get("focus_areas", [])
    entry_points = recon.get("entry_points", [])
    configured = recon.get("configured_languages", ctx.project_config.languages)

    focus_lines = []
    for area in focus_areas:
        status = "present" if area.get("exists") else "missing"
        desc = area.get("description", "")
        focus_lines.append(f"- `{area.get('path', '')}` ({status}){': ' + desc if desc else ''}")

    lang_lines = [f"- {name}: {count} files" for name, count in sorted(languages.items())]
    entry_lines = [f"- `{point}`" for point in entry_points] or ["- (none detected)"]
    configured_lines = [f"- {lang}" for lang in configured] or ["- (not specified)"]

    return "\n".join(
        [
            f"# Threat Model — {ctx.project_config.name}",
            "",
            "## Asset Boundary",
            f"- Project root: `{ctx.project_root}`",
            f"- Scan mode: `{ctx.mode}`",
            f"- File count (approx): {recon.get('file_count', 0)}",
            "",
            "## Entry Points",
            *entry_lines,
            "",
            "## Data Flow (draft)",
            "- User input → application code → external APIs / filesystem / subprocess",
            "- Agent skills and hooks may invoke tools with project-scoped permissions",
            "",
            "## Trust Boundaries",
            "- Untrusted: user prompts, fetched web content, third-party packages",
            "- Semi-trusted: `.cursor/` skills, MCP servers, npm dependencies",
            "- Trusted: local policy files, auditor rule packs",
            "",
            "## Languages Observed",
            *(lang_lines or ["- (none detected)"]),
            "",
            "## Configured Languages",
            *configured_lines,
            "",
            "## Suggested Focus Areas",
            *(focus_lines or ["- (none configured)"]),
            "",
            "## Hypotheses To Verify",
            "- Secrets or API keys in source, env samples, or agent config",
            "- Prompt injection via unsanitized user content in skills",
            "- Over-privileged MCP/tool hooks in `.cursor/` or `.claude/`",
            "- Dependency vulnerabilities in `package.json` lockfile",
            "",
        ]
    )
