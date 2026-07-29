from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_ALLOWLIST = (
    ("api.deepseek.com", 443),
    ("api.anthropic.com", 443),
)


@dataclass(frozen=True)
class EgressRule:
    host: str
    port: int


def parse_allowlist(value: str | None = None) -> tuple[EgressRule, ...]:
    raw = value if value is not None else os.environ.get("SANDBOX_EGRESS_ALLOWLIST", "")
    if not raw.strip():
        return tuple(EgressRule(host=host, port=port) for host, port in DEFAULT_ALLOWLIST)
    rules: list[EgressRule] = []
    for item in raw.split(","):
        entry = item.strip()
        if not entry:
            continue
        if ":" in entry:
            host, port_text = entry.rsplit(":", 1)
            rules.append(EgressRule(host=host.strip().lower(), port=int(port_text)))
        else:
            rules.append(EgressRule(host=entry.lower(), port=443))
    return tuple(rules)


def is_allowed(host: str, port: int, rules: tuple[EgressRule, ...] | None = None) -> bool:
    normalized_host = host.strip().lower().rstrip(".")
    allowlist = rules if rules is not None else parse_allowlist()
    return any(rule.host == normalized_host and rule.port == port for rule in allowlist)
