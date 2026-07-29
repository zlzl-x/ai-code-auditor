import json
import os
from pathlib import Path

import pytest

from backend.core.pipeline import run_scan


@pytest.mark.slow
def test_canary_scan_produces_findings(repo_root: Path, canary_project_path: str) -> None:
    if not Path(canary_project_path).exists():
        pytest.skip("Canary project path not available")

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("LLM_CLIENT", "mock")
        result = run_scan("novel-assistant-v3", repo_root=repo_root)

    findings_path = result.results_dir / "raw_findings.jsonl"
    verified_path = result.results_dir / "verified_findings.jsonl"
    recon_path = result.results_dir / "recon.json"
    report_path = result.results_dir / "AUDIT_REPORT.md"
    meta_path = result.results_dir / "scan_meta.json"

    for path in (findings_path, verified_path, recon_path, report_path, meta_path):
        assert path.exists(), f"missing {path.name}"

    recon = json.loads(recon_path.read_text(encoding="utf-8"))
    assert "languages" in recon

    lines = [line for line in findings_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines, "Expected at least one finding"
    findings = [json.loads(line) for line in lines]
    rule_ids = " ".join(item["rule_id"] for item in findings)
    subprocess_markers = ("spawn-shell", "subprocess", "bandit.B603", "bandit.B607")
    assert any(marker in rule_ids for marker in subprocess_markers)

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta.get("tokens_in", 0) >= 0
    assert meta.get("tokens_out", 0) >= 0
