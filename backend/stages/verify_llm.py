from __future__ import annotations

import json

from backend.core.context import Finding, ScanContext, Severity
from backend.core.llm import get_llm_client
from backend.core.llm.models import resolve_llm_model
from backend.core.llm.structured import complete_json
from backend.core.registry import load_modules_config, register_stage
from backend.prompts.untrusted import make_nonce
from backend.prompts.verify_prompt import VERIFY_SYSTEM_PROMPT, build_verify_user_prompt


def should_verify(finding: Finding, threshold: float) -> bool:
    if finding.severity in {Severity.CRITICAL, Severity.HIGH}:
        return True
    return finding.confidence < threshold


@register_stage("verify_llm")
class VerifyLLMStage:
    id = "verify_llm"

    def run(self, ctx: ScanContext) -> ScanContext:
        from backend.core.path_validation import get_repo_root

        config = load_modules_config(get_repo_root())
        llm_config = config.get("llm", {})
        model = resolve_llm_model("verify")
        threshold = float(llm_config.get("confidence_threshold", 0.8))

        client = get_llm_client(model, role="verify")
        verified: list[Finding] = []

        for finding in ctx.findings:
            if not should_verify(finding, threshold):
                verified.append(finding.model_copy())
                continue

            nonce = make_nonce()
            user_prompt = build_verify_user_prompt(
                rule_id=finding.rule_id,
                file=finding.file,
                line=finding.line,
                severity=finding.severity.value,
                message=finding.message,
                evidence=finding.evidence,
                nonce=nonce,
            )
            try:
                payload, response = complete_json(
                    client,
                    role="verify",
                    model=model,
                    system=VERIFY_SYSTEM_PROMPT,
                    user=user_prompt,
                    max_tokens=2048,
                )
            except json.JSONDecodeError:
                verified.append(
                    finding.model_copy(
                        update={
                            "verified": False,
                            "verify_note": "LLM response parse failed",
                        }
                    )
                )
                continue

            ctx.scan_meta.tokens_in += response.tokens_in
            ctx.scan_meta.tokens_out += response.tokens_out
            if response.model not in ctx.scan_meta.models_used:
                ctx.scan_meta.models_used.append(response.model)

            verdict = str(payload.get("verdict", "reject")).lower()
            reasoning = str(payload.get("reasoning", ""))
            updated = finding.model_copy(
                update={"verify_note": reasoning, "verified": verdict == "confirm"}
            )

            if verdict == "downgrade":
                sev_raw = str(payload.get("severity", finding.severity.value)).lower()
                try:
                    updated = updated.model_copy(update={"severity": Severity(sev_raw)})
                except ValueError:
                    pass
                updated = updated.model_copy(update={"verified": True})

            if verdict == "reject":
                updated = updated.model_copy(update={"verified": False})

            if verdict == "confirm":
                updated = updated.model_copy(update={"verified": True})

            verified.append(updated)

        ctx.verified_findings = verified
        return ctx
