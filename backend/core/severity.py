from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


def map_generic_severity(value: str, *, source: str) -> Severity:
    normalized = value.strip().lower()
    mapping = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "moderate": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
        "informational": Severity.INFO,
    }
    if normalized in mapping:
        return mapping[normalized]
    if source == "npm_audit":
        return _map_npm_severity(normalized)
    if source == "agentshield":
        return _map_agentshield_severity(normalized)
    return Severity.LOW


def _map_npm_severity(value: str) -> Severity:
    mapping = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "moderate": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }
    return mapping.get(value, Severity.LOW)


def _map_agentshield_severity(value: str) -> Severity:
    mapping = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }
    return mapping.get(value, Severity.MEDIUM)


def redact_secret(text: str, *, keep: int = 4) -> str:
    if not text:
        return ""
    if len(text) <= keep * 2:
        return "*" * len(text)
    return f"{text[:keep]}...{text[-keep:]}"
