import os
from pathlib import Path
from unittest.mock import patch

from backend.core.context import Finding, ProjectConfig, ScanContext, Severity
from backend.core.llm.client import LLMResponse
from backend.stages.verify_llm import VerifyLLMStage, should_verify


def test_should_verify_high_severity() -> None:
    finding = Finding(
        scan_id="s",
        project="p",
        severity=Severity.HIGH,
        confidence=0.95,
        source="semgrep",
        rule_id="r",
        file="a.py",
        message="m",
    )
    assert should_verify(finding, 0.8) is True


def test_should_verify_low_confidence() -> None:
    finding = Finding(
        scan_id="s",
        project="p",
        severity=Severity.MEDIUM,
        confidence=0.5,
        source="semgrep",
        rule_id="r",
        file="a.py",
        message="m",
    )
    assert should_verify(finding, 0.8) is True


@patch.dict(os.environ, {"LLM_CLIENT": "mock"})
def test_verify_llm_confirm_and_reject(tmp_path: Path) -> None:
    ctx = ScanContext(
        scan_id="s1",
        project_config=ProjectConfig(name="demo", path="."),
        project_root=tmp_path,
        results_dir=tmp_path / "out",
        findings=[
            Finding(
                scan_id="s1",
                project="demo",
                severity=Severity.HIGH,
                source="semgrep",
                rule_id="spawn-shell-true",
                file="main.js",
                line=1,
                message="shell",
            ),
            Finding(
                scan_id="s1",
                project="demo",
                severity=Severity.MEDIUM,
                confidence=0.5,
                source="semgrep",
                rule_id="fp",
                file="b.js",
                line=2,
                message="false-positive-marker",
            ),
        ],
    )
    ctx = VerifyLLMStage().run(ctx)
    assert len(ctx.verified_findings) == 2
    by_rule = {f.rule_id: f for f in ctx.verified_findings}
    assert by_rule["spawn-shell-true"].verified is True
    assert by_rule["fp"].verified is False
    assert ctx.scan_meta.tokens_in > 0


@patch.dict(os.environ, {"LLM_CLIENT": "mock"})
def test_verify_llm_parses_fenced_json_response(tmp_path: Path) -> None:
    class FencedMockClient:
        model = "mock-model"

        def complete(
            self,
            system: str,
            user: str,
            *,
            max_tokens: int = 1024,
            thinking: str | None = None,
            reasoning_effort: str | None = None,
            json_mode: bool = False,
        ) -> LLMResponse:
            return LLMResponse(
                text=(
                    "Here is my analysis.\n"
                    '```json\n'
                    '{"verdict":"confirm","confidence":0.95,"severity":"high","reasoning":"confirmed"}\n'
                    "```"
                ),
                tokens_in=20,
                tokens_out=10,
                model=self.model,
            )

    ctx = ScanContext(
        scan_id="s1",
        project_config=ProjectConfig(name="demo", path="."),
        project_root=tmp_path,
        results_dir=tmp_path / "out",
        findings=[
            Finding(
                scan_id="s1",
                project="demo",
                severity=Severity.HIGH,
                source="semgrep",
                rule_id="spawn-shell-true",
                file="main.js",
                line=1,
                message="shell",
            ),
        ],
    )
    with patch("backend.stages.verify_llm.get_llm_client", return_value=FencedMockClient()):
        ctx = VerifyLLMStage().run(ctx)

    assert len(ctx.verified_findings) == 1
    assert ctx.verified_findings[0].verified is True
