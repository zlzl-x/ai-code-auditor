from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect

from backend.api.scan_service import create_scan_job, execute_scan, get_event_log
from backend.api.security import check_local_origin
from backend.core.path_validation import get_repo_root, resolve_project_root
from backend.core.registry import get_enabled_detectors, get_pipeline_steps, load_modules_config
from backend.core.rules_loader import scan_rules
from backend.knowledge.backlog import read_backlog
from backend.knowledge.cli import refresh_feeds, top_feeds
from backend.knowledge.storage import KnowledgeStorage
from backend.knowledge.cli import default_db_path as knowledge_db_path
from backend.core.llm.factory import is_provider_configured, resolve_llm_provider
from backend.models.repository import AppRepository
from backend.models.schemas import (
    ApiResponse,
    FindingOut,
    FindingPatch,
    ProjectCreate,
    ProjectOut,
    ScanCreate,
    ScanOut,
    SettingsOut,
    SettingsPatch,
    StatsOut,
)

router = APIRouter(prefix="/api")


def get_repo() -> AppRepository:
    return AppRepository()


def get_settings_path() -> Path:
    return get_repo_root() / "backend" / "data" / "settings.json"


def load_settings() -> dict[str, Any]:
    path = get_settings_path()
    modules = load_modules_config(get_repo_root())
    llm = modules.get("llm", {})
    defaults = {
        "screening_model": llm.get("screening_model", "deepseek-v4-pro"),
        "verify_model": llm.get("verify_model", "deepseek-v4-pro"),
        "translate_model": llm.get("translate_model", "deepseek-v4-flash"),
        "report_mode": "report_only",
    }
    if not path.is_file():
        return defaults
    data = json.loads(path.read_text(encoding="utf-8"))
    return {**defaults, **data}


def save_settings(data: dict[str, Any]) -> dict[str, Any]:
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


@router.get("/health")
def health() -> ApiResponse[dict[str, str]]:
    return ApiResponse(data={"status": "ok", "version": "0.1.0"})


@router.get("/stats")
def stats(repo: AppRepository = Depends(get_repo)) -> ApiResponse[StatsOut]:
    detectors = get_enabled_detectors(get_repo_root())
    engines = [{"id": detector.id, "name": detector.name, "status": "ready"} for detector in detectors]
    return ApiResponse(
        data=StatsOut(
            scans_today=repo.scans_today(),
            severity_counts=repo.severity_counts(),
            engines=engines,
        )
    )


@router.get("/projects")
def list_projects(repo: AppRepository = Depends(get_repo)) -> ApiResponse[list[ProjectOut]]:
    projects = [ProjectOut(**item) for item in repo.list_projects()]
    return ApiResponse(data=projects)


@router.post("/projects")
def create_project(
    payload: ProjectCreate,
    request: Request,
    repo: AppRepository = Depends(get_repo),
) -> ApiResponse[ProjectOut]:
    check_local_origin(request)
    if ".." in Path(payload.path).parts:
        raise HTTPException(status_code=400, detail="Invalid project path")
    from backend.core.context import ProjectConfig

    try:
        resolve_project_root(
            ProjectConfig(
                name=payload.name,
                path=payload.path,
                languages=payload.languages,
                scan_mode=payload.scan_mode,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    project = repo.create_project(payload.model_dump())
    return ApiResponse(data=ProjectOut(**project))


@router.post("/scans")
def start_scan(
    payload: ScanCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    repo: AppRepository = Depends(get_repo),
) -> ApiResponse[ScanOut]:
    check_local_origin(request)
    try:
        repo.get_project(payload.project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    scan = create_scan_job(payload.project_id, payload.mode, repo)
    background_tasks.add_task(execute_scan, scan["id"], payload.project_id, payload.mode, repo)
    return ApiResponse(data=ScanOut(**scan))


@router.get("/scans/{scan_id}")
def get_scan(scan_id: str, repo: AppRepository = Depends(get_repo)) -> ApiResponse[ScanOut]:
    try:
        scan = repo.get_scan(scan_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Scan not found") from exc
    return ApiResponse(data=ScanOut(**scan))


@router.websocket("/scans/{scan_id}/stream")
async def scan_stream(
    websocket: WebSocket,
    scan_id: str,
    repo: AppRepository = Depends(get_repo),
) -> None:
    await websocket.accept()
    try:
        scan = repo.get_scan(scan_id)
    except KeyError:
        await websocket.close(code=4404)
        return

    sent = 0
    import asyncio

    while True:
        events = get_event_log(scan_id)
        while sent < len(events):
            await websocket.send_json(events[sent])
            sent += 1
        scan = repo.get_scan(scan_id)
        if scan["status"] in {"completed", "failed"}:
            if sent >= len(events):
                await websocket.send_json(
                    {
                        "stage": "complete" if scan["status"] == "completed" else "error",
                        "message": scan.get("error") or "Scan finished",
                        "progress": 1.0,
                    }
                )
                break
        try:
            await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        except WebSocketDisconnect:
            return
    await websocket.close()


@router.get("/findings")
def list_findings(
    scan_id: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 100,
    repo: AppRepository = Depends(get_repo),
) -> ApiResponse[list[FindingOut]]:
    findings = repo.list_findings(scan_id=scan_id, severity=severity, status=status, limit=limit)
    return ApiResponse(data=[FindingOut(**item) for item in findings])


@router.patch("/findings/{finding_id}")
def patch_finding(
    finding_id: str,
    payload: FindingPatch,
    request: Request,
    repo: AppRepository = Depends(get_repo),
) -> ApiResponse[FindingOut]:
    check_local_origin(request)
    try:
        finding = repo.update_finding_status(finding_id, payload.status)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Finding not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=FindingOut(**finding))


@router.get("/rules")
def list_rules() -> ApiResponse[dict[str, Any]]:
    repo_root = get_repo_root()
    rule_sets = []
    rules_dir = repo_root / "rules"
    if rules_dir.is_dir():
        for path in rules_dir.rglob("*.yaml"):
            rule_sets.append(
                {
                    "id": str(path.relative_to(rules_dir)).replace("\\", "/"),
                    "path": str(path.relative_to(repo_root)),
                }
            )
    return ApiResponse(data={"rule_sets": rule_sets, "detectors": load_modules_config(repo_root).get("detectors", [])})


@router.post("/rules/reload")
def reload_rules(request: Request, path: str | None = None) -> ApiResponse[dict[str, Any]]:
    check_local_origin(request)
    repo_root = get_repo_root()
    if path:
        normalized = path.replace("\\", "/").strip("/")
        if ".." in normalized.split("/"):
            raise HTTPException(status_code=400, detail="Path traversal rejected")
        rules_dir = (repo_root / "rules").resolve()
        requested = (rules_dir / normalized).resolve()
        if not str(requested).startswith(str(rules_dir)):
            raise HTTPException(status_code=400, detail="Only rules/ directory is allowed")
    rules_info = scan_rules(repo_root)
    config = load_modules_config(repo_root)
    return ApiResponse(
        data={
            "pipeline": config.get("pipeline", []),
            "detectors": config.get("detectors", []),
            "rule_files": rules_info["rule_files"],
            "rule_ids": rules_info["rule_ids"],
            "rule_count": rules_info["rule_count"],
        }
    )


@router.get("/modules")
def list_modules() -> ApiResponse[dict[str, Any]]:
    repo_root = get_repo_root()
    return ApiResponse(
        data={
            "pipeline": get_pipeline_steps(repo_root),
            "detectors": [detector.id for detector in get_enabled_detectors(repo_root)],
        }
    )


@router.get("/knowledge/feed")
def knowledge_feed(limit: int = 20, min_score: float | None = None) -> ApiResponse[list[dict[str, Any]]]:
    return ApiResponse(data=top_feeds(limit=limit, min_score=min_score))


@router.post("/knowledge/refresh")
def knowledge_refresh(request: Request) -> ApiResponse[dict[str, int]]:
    check_local_origin(request)
    count = refresh_feeds()
    return ApiResponse(data={"upserted": count})


@router.post("/knowledge/mark-seen/{item_id}")
def knowledge_mark_seen(item_id: str, request: Request) -> ApiResponse[dict[str, str]]:
    check_local_origin(request)
    storage = KnowledgeStorage(knowledge_db_path())
    storage.mark_seen(item_id)
    return ApiResponse(data={"id": item_id, "status": "seen"})


@router.post("/knowledge/ignore-source/{source_id}")
def knowledge_ignore_source(source_id: str, request: Request) -> ApiResponse[dict[str, str]]:
    check_local_origin(request)
    storage = KnowledgeStorage(knowledge_db_path())
    storage.ignore_source(source_id)
    return ApiResponse(data={"source_id": source_id, "status": "ignored"})


@router.get("/knowledge/backlog")
def knowledge_backlog(limit: int = 20) -> ApiResponse[list[dict[str, Any]]]:
    return ApiResponse(data=read_backlog(get_repo_root(), limit=limit))


def build_settings_out(settings: dict[str, Any]) -> SettingsOut:
    modules = load_modules_config(get_repo_root()).get("llm", {})
    screening_provider = resolve_llm_provider("screening")
    verify_provider = resolve_llm_provider("verify")
    configured_provider = str(modules.get("provider", "deepseek")).lower()
    return SettingsOut(
        api_key_configured=is_provider_configured(screening_provider)
        or is_provider_configured(verify_provider),
        llm_provider=configured_provider,
        screening_provider=screening_provider,
        verify_provider=verify_provider,
        deepseek_api_key_configured=is_provider_configured("deepseek"),
        anthropic_api_key_configured=is_provider_configured("anthropic"),
        screening_model=settings["screening_model"],
        verify_model=settings["verify_model"],
        report_mode=settings["report_mode"],
    )


@router.get("/settings")
def get_settings() -> ApiResponse[SettingsOut]:
    settings = load_settings()
    return ApiResponse(data=build_settings_out(settings))


@router.patch("/settings")
def patch_settings(payload: SettingsPatch, request: Request) -> ApiResponse[SettingsOut]:
    check_local_origin(request)
    settings = load_settings()
    for field in ("screening_model", "verify_model", "report_mode"):
        value = getattr(payload, field)
        if value is not None:
            settings[field] = value
    settings = save_settings(settings)
    return ApiResponse(data=build_settings_out(settings))
