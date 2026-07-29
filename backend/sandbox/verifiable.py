from __future__ import annotations

import os

from backend.core.context import Finding, Severity

VERIFIABLE_KEYWORDS = (
    "subprocess",
    "shell=true",
    "spawn-shell",
    "sql",
    "injection",
    "path-traversal",
    "pickle",
    "deserialize",
    "eval",
    "exec",
)

VERIFIABLE_CWES = ("CWE-78", "CWE-89", "CWE-22", "CWE-502", "CWE-94")


def max_sandbox_pocs() -> int:
    raw = os.environ.get("SANDBOX_MAX_POCS", "3").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 3


def is_verifiable(finding: Finding) -> bool:
    if not finding.verified:
        return False
    if finding.severity not in {Severity.CRITICAL, Severity.HIGH}:
        return False
    haystack = f"{finding.rule_id} {finding.message} {finding.cwe} {finding.evidence}".lower()
    if finding.cwe and any(cwe.lower() in finding.cwe.lower() for cwe in VERIFIABLE_CWES):
        return True
    if any(cwe.lower() in haystack for cwe in VERIFIABLE_CWES):
        return True
    return any(keyword in haystack for keyword in VERIFIABLE_KEYWORDS)


def build_poc_command(finding: Finding) -> list[str] | None:
    haystack = f"{finding.rule_id} {finding.message} {finding.evidence}".lower()
    if "pickle" in haystack or (finding.cwe and "cwe-502" in finding.cwe.lower()):
        return ["python", "-c", "print('sandbox-poc')"]
    if "sql" in haystack or "injection" in haystack:
        return ["python", "-c", "print('sandbox-poc')"]
    if "path" in haystack and "traversal" in haystack:
        return ["python", "-c", "import os; print(os.listdir('/work'))"]
    if "subprocess" in haystack or "shell" in haystack or "spawn-shell" in haystack:
        return ["python", "-c", "import subprocess; subprocess.run(['echo','poc'], check=False)"]
    if "eval" in haystack or "exec" in haystack:
        return ["python", "-c", "print('sandbox-poc')"]
    return ["python", "-c", "print('sandbox-poc')"]
