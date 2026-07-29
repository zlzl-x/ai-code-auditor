from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.core.severity import Severity, map_generic_severity, redact_secret


class FindingStatus(str, Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    SUPPRESSED = "suppressed"


class FocusArea(BaseModel):
    path: str
    description: str = ""


class ProjectConfig(BaseModel):
    name: str
    path: str
    languages: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    scan_mode: str = "quick"
    fail_on: str = "critical"
    focus_areas: list[FocusArea] = Field(default_factory=list)


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    scan_id: str
    project: str
    severity: Severity
    confidence: float = 1.0
    source: str
    rule_id: str
    file: str
    line: int = 0
    message: str
    evidence: str = ""
    cwe: str = ""
    status: FindingStatus = FindingStatus.NEW
    verified: bool = False
    verify_note: str = ""
    report_section: str = ""
    remediation: str = ""
    sandbox_verified: bool = False
    sandbox_note: str = ""

    @classmethod
    def from_semgrep(
        cls,
        item: dict[str, Any],
        *,
        scan_id: str,
        project: str,
    ) -> Finding:
        extra = item.get("extra", {})
        metadata = extra.get("metadata", {})
        severity_raw = str(extra.get("severity", "INFO")).upper()
        severity = _map_semgrep_severity(severity_raw)
        start = item.get("start", {})
        cwe_list = metadata.get("cwe", [])
        cwe = cwe_list[0] if isinstance(cwe_list, list) and cwe_list else ""
        return cls(
            scan_id=scan_id,
            project=project,
            severity=severity,
            source="semgrep",
            rule_id=str(item.get("check_id", "unknown")),
            file=str(item.get("path", "")),
            line=int(start.get("line", 0)),
            message=str(extra.get("message", "")),
            evidence=str(extra.get("lines", "")),
            cwe=str(cwe),
        )

    @classmethod
    def from_bandit(
        cls,
        item: dict[str, Any],
        *,
        scan_id: str,
        project: str,
    ) -> Finding:
        severity = _map_bandit_severity(str(item.get("issue_severity", "LOW")))
        return cls(
            scan_id=scan_id,
            project=project,
            severity=severity,
            source="bandit",
            rule_id=f"bandit.{item.get('test_id', 'unknown')}",
            file=str(item.get("filename", "")),
            line=int(item.get("line_number", 0)),
            message=str(item.get("issue_text", "")),
            evidence=str(item.get("code", "")),
            cwe=f"CWE-{item['issue_cwe']['id']}"
            if item.get("issue_cwe")
            else "",
        )

    @classmethod
    def from_gitleaks(
        cls,
        item: dict[str, Any],
        *,
        scan_id: str,
        project: str,
    ) -> Finding:
        secret = str(item.get("Secret", "") or item.get("Match", ""))
        severity = map_generic_severity(str(item.get("Severity", "high")), source="gitleaks")
        return cls(
            scan_id=scan_id,
            project=project,
            severity=severity,
            source="gitleaks",
            rule_id=f"gitleaks.{item.get('RuleID', item.get('Description', 'secret'))}",
            file=str(item.get("File", "")),
            line=int(item.get("StartLine", item.get("Line", 0)) or 0),
            message=str(item.get("Description", "Potential secret detected")),
            evidence=redact_secret(secret),
        )

    @classmethod
    def from_npm_audit(
        cls,
        package: str,
        vuln: dict[str, Any],
        *,
        scan_id: str,
        project: str,
    ) -> Finding:
        severity = map_generic_severity(str(vuln.get("severity", "moderate")), source="npm_audit")
        via = vuln.get("via", [])
        title = package
        if via and isinstance(via[0], dict):
            title = str(via[0].get("title", package))
        return cls(
            scan_id=scan_id,
            project=project,
            severity=severity,
            source="npm_audit",
            rule_id=f"npm.{package}",
            file="package.json",
            line=0,
            message=title,
            evidence=str(vuln.get("range", "")),
            remediation="Run npm audit fix or upgrade dependency",
        )

    @classmethod
    def from_agentshield(
        cls,
        item: dict[str, Any],
        *,
        scan_id: str,
        project: str,
    ) -> Finding:
        severity = map_generic_severity(str(item.get("severity", "medium")), source="agentshield")
        location = item.get("location", {}) or {}
        return cls(
            scan_id=scan_id,
            project=project,
            severity=severity,
            source="agentshield",
            rule_id=str(item.get("ruleId", item.get("id", "agentshield.unknown"))),
            file=str(location.get("file", item.get("file", ""))),
            line=int(location.get("line", item.get("line", 0)) or 0),
            message=str(item.get("message", item.get("title", ""))),
            evidence=str(item.get("evidence", item.get("snippet", ""))),
            remediation=str(item.get("remediation", "")),
        )

    @classmethod
    def from_eslint(
        cls,
        item: dict[str, Any],
        *,
        scan_id: str,
        project: str,
    ) -> Finding:
        severity = Severity.MEDIUM
        if int(item.get("severity", 1)) == 2:
            severity = Severity.HIGH
        return cls(
            scan_id=scan_id,
            project=project,
            severity=severity,
            source="eslint",
            rule_id=str(item.get("ruleId", "eslint.unknown")),
            file=str(item.get("filePath", "")),
            line=int(item.get("line", 0) or 0),
            message=str(item.get("message", "")),
            evidence=str(item.get("source", "")),
        )


class ScanMeta(BaseModel):
    tokens_in: int = 0
    tokens_out: int = 0
    models_used: list[str] = Field(default_factory=list)
    raw_finding_count: int = 0
    verified_finding_count: int = 0


class ScanContext(BaseModel):
    scan_id: str
    project_config: ProjectConfig
    project_root: Path
    results_dir: Path
    mode: str = "quick"
    recon_data: dict[str, Any] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    verified_findings: list[Finding] = Field(default_factory=list)
    triage_summary: dict[str, Any] = Field(default_factory=dict)
    threat_model_md: str = ""
    enable_sandbox: bool = False
    report_lang: str = "en"
    sandbox_results: dict[str, Any] = Field(default_factory=dict)
    translated_report: str = ""
    scan_meta: ScanMeta = Field(default_factory=ScanMeta)
    errors: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


def _map_semgrep_severity(value: str) -> Severity:
    mapping = {
        "ERROR": Severity.HIGH,
        "WARNING": Severity.MEDIUM,
        "INFO": Severity.INFO,
    }
    return mapping.get(value, Severity.LOW)


def _map_bandit_severity(value: str) -> Severity:
    mapping = {
        "HIGH": Severity.HIGH,
        "MEDIUM": Severity.MEDIUM,
        "LOW": Severity.LOW,
    }
    return mapping.get(value.upper(), Severity.LOW)
