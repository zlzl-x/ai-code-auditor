from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: str | None = None


class ProjectCreate(BaseModel):
    id: str
    name: str
    path: str
    languages: list[str] = Field(default_factory=list)
    scan_mode: str = "quick"


class ProjectOut(BaseModel):
    id: str
    name: str
    path: str
    languages: list[str]
    scan_mode: str
    created_at: str


class ScanCreate(BaseModel):
    project_id: str
    mode: str = "quick"


class ScanOut(BaseModel):
    id: str
    project_id: str
    mode: str
    status: str
    results_dir: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    finding_count: int | None = None


class FindingOut(BaseModel):
    id: str
    scan_id: str
    project: str
    severity: str
    confidence: float
    source: str
    rule_id: str
    file: str
    line: int
    message: str
    evidence: str
    cwe: str
    status: str
    verified: bool
    verify_note: str
    remediation: str


class FindingPatch(BaseModel):
    status: str


class SettingsOut(BaseModel):
    api_key_configured: bool
    llm_provider: str
    screening_provider: str
    verify_provider: str
    deepseek_api_key_configured: bool
    anthropic_api_key_configured: bool
    screening_model: str
    verify_model: str
    report_mode: str


class SettingsPatch(BaseModel):
    screening_model: str | None = None
    verify_model: str | None = None
    report_mode: str | None = None


class StatsOut(BaseModel):
    scans_today: int
    severity_counts: dict[str, int]
    engines: list[dict[str, Any]]
