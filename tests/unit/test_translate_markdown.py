from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.core.context import ProjectConfig, ScanContext
from backend.core.llm.client import LLMResponse
from backend.reporters.translate_markdown import (
    split_markdown_sections,
    translate_audit_report,
    translate_section,
)


def test_split_markdown_sections_preserves_headings() -> None:
    text = "# Title\n\n## Summary\n\n- item\n\n## Findings\n\n### rule — high\n\nbody"
    sections = split_markdown_sections(text)
    assert sections[0].startswith("# Title")
    assert sections[1].startswith("## Summary")
    assert sections[2].startswith("## Findings")


def test_split_markdown_sections_splits_large_section_by_subheadings() -> None:
    body = "x" * 7000
    text = f"## Section\n\n### Part A\n\n{body}\n\n### Part B\n\nshort"
    sections = split_markdown_sections(text)
    assert len(sections) >= 2
    assert any(section.startswith("### Part B") for section in sections)


def test_translate_section_accumulates_tokens() -> None:
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=ProjectConfig(name="demo", path="."),
        project_root=Path("."),
        results_dir=Path("results"),
    )
    client = MagicMock()
    client.complete.return_value = LLMResponse(
        text="## 摘要\n\n- 项目",
        tokens_in=10,
        tokens_out=20,
        model="mock-model",
    )
    result = translate_section(client, "## Summary\n\n- item", ctx, role="translate", model="deepseek-v4-flash")
    assert "摘要" in result
    assert ctx.scan_meta.tokens_in == 10
    assert ctx.scan_meta.tokens_out == 20


def test_translate_audit_report_skips_mock_provider(tmp_path: Path) -> None:
    report = tmp_path / "AUDIT_REPORT.md"
    report.write_text("# Security Audit Report\n\n## Summary\n\n- one\n", encoding="utf-8")
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=ProjectConfig(name="demo", path=str(tmp_path)),
        project_root=tmp_path,
        results_dir=tmp_path,
        report_lang="zh",
    )
    with patch("backend.reporters.translate_markdown.resolve_llm_provider", return_value="mock"):
        output = translate_audit_report(ctx, report)
    assert output is None
    assert not (tmp_path / "AUDIT_REPORT.zh.md").exists()
    assert any("skipped" in error for error in ctx.errors)


def test_translate_audit_report_writes_zh_file(tmp_path: Path) -> None:
    report = tmp_path / "AUDIT_REPORT.md"
    report.write_text("# Security Audit Report\n\n## Summary\n\n- one\n", encoding="utf-8")
    ctx = ScanContext(
        scan_id="scan-1",
        project_config=ProjectConfig(name="demo", path=str(tmp_path)),
        project_root=tmp_path,
        results_dir=tmp_path,
        report_lang="zh",
    )
    client = MagicMock()
    client.complete.return_value = LLMResponse(
        text="[ZH] translated",
        tokens_in=5,
        tokens_out=5,
        model="deepseek-v4-flash",
    )

    with patch("backend.reporters.translate_markdown.resolve_llm_provider", return_value="deepseek"), patch(
        "backend.reporters.translate_markdown.is_provider_configured", return_value=True
    ), patch("backend.reporters.translate_markdown.resolve_llm_model", return_value="deepseek-v4-flash"), patch(
        "backend.reporters.translate_markdown.get_llm_client", return_value=client
    ):
        output = translate_audit_report(ctx, report)

    assert output is not None
    assert output.name == "AUDIT_REPORT.zh.md"
    assert "[ZH] translated" in output.read_text(encoding="utf-8")
    assert ctx.translated_report == "AUDIT_REPORT.zh.md"
