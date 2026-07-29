from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.core.context import ScanContext
from backend.core.env import load_env_file
from backend.core.events import EventEmitter, ScanEvent
from backend.core.path_validation import (
    get_repo_root,
    load_project_config,
    resolve_project_root,
)
from backend.core.registry import get_enabled_stages, get_pipeline_steps, load_modules_config


@dataclass(frozen=True)
class ScanResult:
    scan_id: str
    results_dir: Path
    finding_count: int
    ctx: ScanContext


def write_outputs(ctx: ScanContext, started_at: datetime) -> None:
    ctx.results_dir.mkdir(parents=True, exist_ok=True)
    (ctx.results_dir / "recon.json").write_text(
        json.dumps(ctx.recon_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with (ctx.results_dir / "raw_findings.jsonl").open("w", encoding="utf-8") as handle:
        for finding in ctx.findings:
            handle.write(finding.model_dump_json())
            handle.write("\n")

    verified = ctx.verified_findings or ctx.findings
    with (ctx.results_dir / "verified_findings.jsonl").open("w", encoding="utf-8") as handle:
        for finding in verified:
            handle.write(finding.model_dump_json())
            handle.write("\n")

    if ctx.triage_summary:
        (ctx.results_dir / "TRIAGE.json").write_text(
            json.dumps(ctx.triage_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    if ctx.threat_model_md:
        (ctx.results_dir / "THREAT_MODEL.md").write_text(
            ctx.threat_model_md,
            encoding="utf-8",
        )

    if ctx.sandbox_results:
        (ctx.results_dir / "SANDBOX.json").write_text(
            json.dumps(ctx.sandbox_results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    finished_at = datetime.now(timezone.utc)
    config = load_modules_config(get_repo_root())
    meta = {
        "scan_id": ctx.scan_id,
        "project": ctx.project_config.name,
        "mode": ctx.mode,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "pipeline": get_pipeline_steps(get_repo_root()),
        "detectors": config.get("detectors", []),
        "raw_finding_count": len(ctx.findings),
        "verified_finding_count": len(verified),
        "finding_count": len(verified),
        "tokens_in": ctx.scan_meta.tokens_in,
        "tokens_out": ctx.scan_meta.tokens_out,
        "models_used": ctx.scan_meta.models_used,
        "errors": ctx.errors,
        "report_lang": ctx.report_lang,
    }
    if ctx.translated_report:
        meta["translated_report"] = ctx.translated_report
    (ctx.results_dir / "scan_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def run_scan(
    project_id: str,
    *,
    mode: str | None = None,
    scan_id: str | None = None,
    emitter: EventEmitter | None = None,
    results_dir: Path | None = None,
    repo_root: Path | None = None,
    enable_sandbox: bool = False,
    report_lang: str = "en",
) -> ScanResult:
    root = repo_root or get_repo_root()
    project_config = load_project_config(project_id, root)
    project_root = resolve_project_root(project_config)
    scan_mode = mode or project_config.scan_mode or "quick"
    resolved_scan_id = scan_id or str(uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    resolved_results_dir = results_dir or (root / "results" / project_id / timestamp)
    started_at = datetime.now(timezone.utc)

    ctx = ScanContext(
        scan_id=resolved_scan_id,
        project_config=project_config,
        project_root=project_root,
        results_dir=resolved_results_dir,
        mode=scan_mode,
        enable_sandbox=enable_sandbox,
        report_lang=report_lang,
    )
    event_emitter = emitter or EventEmitter()
    if emitter is None:
        event_emitter.on(lambda event: print(f"[{event.stage}] {event.message}", flush=True))

    event_emitter.emit(
        ScanEvent.create("init", f"Scan started for {project_id} ({scan_mode})", 0.1)
    )
    for stage in get_enabled_stages(root):
        if stage.id == "find_llm" and scan_mode != "deep":
            event_emitter.emit(ScanEvent.create(stage.id, "Skipped (quick mode)", 0.5))
            continue
        event_emitter.emit(ScanEvent.create(stage.id, f"Running stage {stage.id}", 0.3))
        ctx = stage.run(ctx)
        if stage.id == "triage" and enable_sandbox:
            from backend.stages.verify_sandbox import VerifySandboxStage

            event_emitter.emit(
                ScanEvent.create("verify_sandbox", "Running stage verify_sandbox", 0.85)
            )
            ctx = VerifySandboxStage().run(ctx)
        if stage.id == "report_md" and ctx.report_lang == "zh":
            from backend.reporters.translate_markdown import translate_audit_report

            event_emitter.emit(
                ScanEvent.create("translate_report", "Translating audit report to zh", 0.95)
            )
            report_path = ctx.results_dir / "AUDIT_REPORT.md"
            translate_audit_report(ctx, report_path)

    write_outputs(ctx, started_at)
    verified_count = len(ctx.verified_findings or ctx.findings)
    event_emitter.emit(
        ScanEvent.create(
            "complete",
            f"Wrote {verified_count} verified findings to {resolved_results_dir}",
            1.0,
        )
    )
    return ScanResult(
        scan_id=resolved_scan_id,
        results_dir=resolved_results_dir,
        finding_count=verified_count,
        ctx=ctx,
    )


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description="AI code auditor pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Run a scan for a registered project")
    run_parser.add_argument("project_id", help="Project id under projects/")
    run_parser.add_argument(
        "--mode",
        choices=["quick", "deep"],
        default=None,
        help="Scan mode (default: project config or quick)",
    )
    run_parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help="Report language; zh generates AUDIT_REPORT.zh.md via LLM",
    )
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            result = run_scan(args.project_id, mode=args.mode, report_lang=args.lang)
        except Exception as exc:  # noqa: BLE001
            print(f"Scan failed: {exc}", file=sys.stderr)
            return 1
        print(f"Results: {result.results_dir}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
