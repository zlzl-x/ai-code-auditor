from __future__ import annotations

from collections import Counter

from backend.core.context import Finding, ScanContext, Severity
from backend.core.registry import register_stage


def _dedup_key(finding: Finding) -> tuple[str, str, int]:
    return (finding.rule_id, finding.file, finding.line)


def _title_tokens(text: str) -> set[str]:
    return {token.lower() for token in text.split() if token}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


@register_stage("triage")
class TriageStage:
    id = "triage"

    def run(self, ctx: ScanContext) -> ScanContext:
        source = ctx.verified_findings or ctx.findings
        best_by_key: dict[tuple[str, str, int], Finding] = {}

        for finding in source:
            key = _dedup_key(finding)
            existing = best_by_key.get(key)
            if existing is None or _severity_rank(finding.severity) > _severity_rank(
                existing.severity
            ):
                best_by_key[key] = finding

        deduped = list(best_by_key.values())
        deduped = _merge_similar_messages(deduped)

        false_positive_candidates = [
            f.id for f in deduped if not f.verified and f.verify_note
        ]
        by_severity = Counter(f.severity.value for f in deduped)

        ctx.verified_findings = deduped
        ctx.triage_summary = {
            "total": len(source),
            "deduped": len(deduped),
            "by_severity": dict(by_severity),
            "false_positive_candidates": false_positive_candidates,
        }
        return ctx


def _severity_rank(severity: Severity) -> int:
    order = {
        Severity.CRITICAL: 5,
        Severity.HIGH: 4,
        Severity.MEDIUM: 3,
        Severity.LOW: 2,
        Severity.INFO: 1,
    }
    return order.get(severity, 0)


def _merge_similar_messages(findings: list[Finding]) -> list[Finding]:
    kept: list[Finding] = []
    for finding in findings:
        tokens = _title_tokens(finding.message)
        duplicate = False
        for index, other in enumerate(kept):
            if _jaccard(tokens, _title_tokens(other.message)) > 0.85:
                if _severity_rank(finding.severity) > _severity_rank(other.severity):
                    kept[index] = finding
                duplicate = True
                break
        if not duplicate:
            kept.append(finding)
    return kept
