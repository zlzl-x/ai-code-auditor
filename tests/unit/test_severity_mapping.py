from backend.core.context import Severity
from backend.core.severity import map_generic_severity, redact_secret


def test_map_npm_audit_severity() -> None:
    assert map_generic_severity("critical", source="npm_audit") == Severity.CRITICAL
    assert map_generic_severity("moderate", source="npm_audit") == Severity.MEDIUM


def test_map_agentshield_severity() -> None:
    assert map_generic_severity("high", source="agentshield") == Severity.HIGH
    assert map_generic_severity("unknown", source="agentshield") == Severity.MEDIUM


def test_map_gitleaks_severity() -> None:
    assert map_generic_severity("high", source="gitleaks") == Severity.HIGH


def test_redact_secret_masks_middle() -> None:
    assert redact_secret("abcdefghijklmnop") == "abcd...mnop"


def test_redact_secret_short_value() -> None:
    assert redact_secret("short") == "*****"
