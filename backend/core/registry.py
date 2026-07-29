from __future__ import annotations

from typing import Any, Callable, Protocol, TypeVar

from backend.core.context import ScanContext

T = TypeVar("T")


class Detector(Protocol):
    id: str
    name: str
    supported_languages: list[str]

    def run(self, ctx: ScanContext) -> list:
        ...


class PipelineStage(Protocol):
    id: str

    def run(self, ctx: ScanContext) -> ScanContext:
        ...


class Reporter(Protocol):
    id: str

    def write(self, ctx: ScanContext) -> Path:
        ...


DETECTOR_REGISTRY: dict[str, type] = {}
STAGE_REGISTRY: dict[str, type] = {}
REPORTER_REGISTRY: dict[str, type] = {}


def register_detector(detector_id: str) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        DETECTOR_REGISTRY[detector_id] = cls
        return cls

    return decorator


def register_stage(stage_id: str) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        STAGE_REGISTRY[stage_id] = cls
        return cls

    return decorator


def register_reporter(reporter_id: str) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        REPORTER_REGISTRY[reporter_id] = cls
        return cls

    return decorator


def load_modules_config(repo_root) -> dict[str, Any]:
    import yaml
    from pathlib import Path

    config_path = Path(repo_root) / "modules.yaml"
    if not config_path.is_file():
        return {"detectors": [], "pipeline": [], "reporters": []}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _import_stage_modules() -> None:
    import backend.stages.find_llm  # noqa: F401
    import backend.stages.find_rules  # noqa: F401
    import backend.stages.recon  # noqa: F401
    import backend.stages.report_md  # noqa: F401
    import backend.stages.triage  # noqa: F401
    import backend.stages.verify_llm  # noqa: F401
    import backend.stages.verify_sandbox  # noqa: F401


def _import_reporter_modules() -> None:
    import backend.reporters.json  # noqa: F401
    import backend.reporters.markdown  # noqa: F401
    import backend.reporters.sarif  # noqa: F401


def get_pipeline_steps(repo_root) -> list[str]:
    config = load_modules_config(repo_root)
    return list(config.get("pipeline", []))


def get_enabled_detectors(repo_root) -> list[Detector]:
    import backend.detectors.bandit  # noqa: F401
    import backend.detectors.config_audit  # noqa: F401
    import backend.detectors.eslint_security  # noqa: F401
    import backend.detectors.gitleaks  # noqa: F401
    import backend.detectors.npm_audit  # noqa: F401
    import backend.detectors.semgrep  # noqa: F401

    config = load_modules_config(repo_root)
    enabled = config.get("detectors", [])
    detectors: list[Detector] = []
    for detector_id in enabled:
        cls = DETECTOR_REGISTRY.get(detector_id)
        if cls is None:
            raise KeyError(f"Unknown detector: {detector_id}")
        detectors.append(cls())
    return detectors


def get_enabled_stages(repo_root) -> list[PipelineStage]:
    _import_stage_modules()
    config = load_modules_config(repo_root)
    enabled = config.get("pipeline", [])
    stages: list[PipelineStage] = []
    for stage_id in enabled:
        cls = STAGE_REGISTRY.get(stage_id)
        if cls is None:
            raise KeyError(f"Unknown stage: {stage_id}")
        stages.append(cls())
    return stages


def get_enabled_reporters(repo_root) -> list[Reporter]:
    _import_reporter_modules()
    config = load_modules_config(repo_root)
    enabled = config.get("reporters", [])
    reporters: list[Reporter] = []
    for reporter_id in enabled:
        cls = REPORTER_REGISTRY.get(reporter_id)
        if cls is None:
            raise KeyError(f"Unknown reporter: {reporter_id}")
        reporters.append(cls())
    return reporters
