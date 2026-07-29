from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _rules_root(repo_root: Path) -> Path:
    rules_dir = (repo_root / "rules").resolve()
    if ".." in rules_dir.parts:
        raise ValueError("Invalid rules directory")
    return rules_dir


def scan_rules(repo_root: Path) -> dict[str, Any]:
    rules_dir = _rules_root(repo_root)
    if not rules_dir.is_dir():
        return {"rule_files": [], "rule_ids": [], "rule_count": 0}

    rule_files: list[str] = []
    rule_ids: list[str] = []
    for path in sorted(rules_dir.rglob("*.yaml")):
        relative = str(path.relative_to(rules_dir)).replace("\\", "/")
        if ".." in relative.split("/"):
            continue
        rule_files.append(relative)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for rule in data.get("rules", []):
            if isinstance(rule, dict) and rule.get("id"):
                rule_ids.append(str(rule["id"]))

    return {
        "rule_files": rule_files,
        "rule_ids": rule_ids,
        "rule_count": len(rule_ids),
    }
