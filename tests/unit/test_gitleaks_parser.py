from backend.core.context import Finding, Severity


def test_finding_from_gitleaks_redacts_secret() -> None:
    item = {
        "RuleID": "generic-api-key",
        "File": "src/config.py",
        "StartLine": 12,
        "Description": "Generic API Key",
        "Secret": "sk-live-abcdefghijklmnopqrstuvwxyz",
        "Severity": "high",
    }
    finding = Finding.from_gitleaks(item, scan_id="scan-1", project="demo")
    assert finding.source == "gitleaks"
    assert finding.severity == Severity.HIGH
    assert "sk-l" in finding.evidence
    assert "wxyz" in finding.evidence
    assert "abcdefghijklmnopqrst" not in finding.evidence


def test_finding_from_npm_audit() -> None:
    vuln = {
        "severity": "high",
        "range": "<1.2.3",
        "via": [{"title": "Prototype pollution"}],
    }
    finding = Finding.from_npm_audit("lodash", vuln, scan_id="scan-1", project="demo")
    assert finding.source == "npm_audit"
    assert finding.message == "Prototype pollution"


def test_finding_from_agentshield() -> None:
    item = {
        "ruleId": "agentshield.hooks.dangerous",
        "severity": "high",
        "message": "Dangerous hook",
        "location": {"file": ".cursor/hooks.json", "line": 3},
    }
    finding = Finding.from_agentshield(item, scan_id="scan-1", project="demo")
    assert finding.source == "agentshield"
    assert finding.file.endswith("hooks.json")


def test_finding_from_eslint() -> None:
    item = {
        "ruleId": "security/detect-eval-with-expression",
        "filePath": "app/main.ts",
        "line": 8,
        "severity": 2,
        "message": "eval can be harmful",
        "source": "eval(userInput)",
    }
    finding = Finding.from_eslint(item, scan_id="scan-1", project="demo")
    assert finding.source == "eslint"
    assert finding.severity == Severity.HIGH
