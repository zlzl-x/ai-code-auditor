from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from backend.core.baseline import (
    apply_baseline_diff,
    load_baseline,
    resolve_baseline_path,
    save_baseline,
)
from backend.core.env import load_env_file
from backend.core.path_validation import get_repo_root
from backend.core.pipeline import run_scan
from backend.core.scan_gate import evaluate_exit_code, resolve_fail_on
from backend.knowledge.cli import refresh_feeds
from backend.reporters.json import JsonReporter
from backend.reporters.markdown import MarkdownReporter
from backend.reporters.pr_comment import write_pr_comment
from backend.reporters.sarif import SarifReporter


def _write_format_output(
    ctx,
    *,
    fmt: str,
    output: Path | None,
    new_only: bool,
    include_evidence: bool,
) -> Path:
    if fmt == "sarif":
        return SarifReporter().write(ctx, new_only=new_only, output_path=output)
    if fmt == "json":
        return JsonReporter().write(
            ctx,
            new_only=new_only,
            include_evidence=include_evidence,
            output_path=output,
        )
    return MarkdownReporter().write(ctx)


def _apply_baseline(ctx, project_id: str, baseline: str | None, repo_root: Path):
    if not baseline:
        return ctx
    baseline_file = resolve_baseline_path(repo_root, project_id, baseline)
    if baseline_file is None:
        return ctx
    baseline_findings = load_baseline(baseline_file)
    updated = apply_baseline_diff(ctx.verified_findings or ctx.findings, baseline_findings)
    ctx.verified_findings = updated
    return ctx


def _update_scan_meta(
    results_dir: Path,
    *,
    report_mode: str,
    gate_failed: bool,
    new_finding_count: int,
) -> None:
    meta_path = results_dir / "scan_meta.json"
    if not meta_path.is_file():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(
        {
            "report_mode": report_mode,
            "gate_failed": gate_failed,
            "new_finding_count": new_finding_count,
        }
    )
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_scan(args: argparse.Namespace) -> int:
    repo_root = get_repo_root()
    try:
        result = run_scan(
            args.project,
            mode=args.mode,
            repo_root=repo_root,
            enable_sandbox=args.enable_sandbox,
            report_lang=args.lang,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Scan failed: {exc}", file=sys.stderr)
        return 1

    ctx = _apply_baseline(result.ctx, args.project, args.baseline, repo_root)
    new_only = not args.all_findings
    output = Path(args.output) if args.output else None

    if args.format == "markdown":
        MarkdownReporter().write(ctx)
    else:
        _write_format_output(
            ctx,
            fmt=args.format,
            output=output,
            new_only=new_only,
            include_evidence=args.include_evidence,
        )

    if args.pr_comment_out:
        write_pr_comment(ctx, args.pr_comment_out, new_only=new_only)

    if args.save_baseline:
        save_path = resolve_baseline_path(repo_root, args.project, args.save_baseline)
        if save_path is None:
            save_path = Path(args.save_baseline)
        save_baseline(
            ctx.verified_findings or ctx.findings,
            save_path,
            project=args.project,
            branch=args.save_baseline,
        )

    findings = ctx.verified_findings or ctx.findings
    new_findings = [f for f in findings if f.status.value == "new"] if new_only else findings
    fail_on = resolve_fail_on(
        cli_fail_on=args.fail_on,
        project_fail_on=ctx.project_config.fail_on,
    )
    exit_code = evaluate_exit_code(
        findings,
        fail_on=fail_on,
        report_mode=args.report_mode,
        new_only=new_only,
    )
    _update_scan_meta(
        result.results_dir,
        report_mode=args.report_mode,
        gate_failed=exit_code == 1,
        new_finding_count=len(new_findings),
    )
    print(f"Results: {result.results_dir}")
    if output and args.format != "markdown":
        print(f"Wrote: {output}")
    return exit_code


def cmd_self_audit(_args: argparse.Namespace) -> int:
    repo_root = get_repo_root()
    commands = [
        [sys.executable, "-m", "pytest", "tests/", "-m", "not slow", "-q"],
        ["semgrep", "--config", "auto", "backend/"],
        ["bandit", "-r", "backend/"],
        [
            "npx",
            "ecc-agentshield",
            "scan",
            "--path",
            str(repo_root),
            "--format",
            "json",
            "--min-severity",
            "medium",
        ],
    ]
    for cmd in commands:
        print(f"Running: {' '.join(cmd)}", flush=True)
        try:
            completed = subprocess.run(cmd, cwd=repo_root, check=False)  # nosec B603
        except FileNotFoundError:
            print(f"Skipped missing command: {cmd[0]}", file=sys.stderr)
            continue
        if completed.returncode != 0 and cmd[0] in {sys.executable, "semgrep", "bandit"}:
            return completed.returncode
    return 0


def cmd_knowledge_refresh(_args: argparse.Namespace) -> int:
    count = refresh_feeds()
    print(f"Upserted {count} items")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-auditor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Run project scan")
    scan_parser.add_argument("--project", required=True, help="Project id under projects/")
    scan_parser.add_argument("--mode", choices=["quick", "deep"], default=None)
    scan_parser.add_argument("--format", choices=["markdown", "sarif", "json"], default="markdown")
    scan_parser.add_argument("-o", "--output", default=None, help="Output file path")
    scan_parser.add_argument(
        "--fail-on",
        choices=["critical", "high", "medium", "low", "info", "none"],
        default=None,
    )
    scan_parser.add_argument(
        "--report-mode",
        choices=["report_only", "block"],
        default="report_only",
    )
    scan_parser.add_argument("--baseline", default=None, help="Branch name or baseline file path")
    scan_parser.add_argument("--all-findings", action="store_true")
    scan_parser.add_argument("--include-evidence", action="store_true")
    scan_parser.add_argument("--pr-comment-out", default=None)
    scan_parser.add_argument("--save-baseline", default=None)
    scan_parser.add_argument(
        "--enable-sandbox",
        action="store_true",
        help="Run dynamic PoC verification in Docker (Linux/WSL2)",
    )
    scan_parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help="Report language; zh generates AUDIT_REPORT.zh.md via LLM",
    )
    scan_parser.set_defaults(handler=cmd_scan)

    self_audit_parser = subparsers.add_parser("self-audit", help="Run self-audit checks")
    self_audit_parser.set_defaults(handler=cmd_self_audit)

    knowledge_parser = subparsers.add_parser("knowledge", help="Knowledge feed commands")
    knowledge_sub = knowledge_parser.add_subparsers(dest="knowledge_command", required=True)
    refresh_parser = knowledge_sub.add_parser("refresh", help="Refresh RSS/GitHub feeds")
    refresh_parser.set_defaults(handler=cmd_knowledge_refresh)
    return parser


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.error("command required")
    return handler(args)
