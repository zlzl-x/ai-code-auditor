from __future__ import annotations

from pathlib import Path

from backend.core.context import ScanContext
from backend.core.registry import get_enabled_reporters, register_stage


@register_stage("report_md")
class ReportMdStage:
    id = "report_md"

    def run(self, ctx: ScanContext) -> ScanContext:
        from backend.core.path_validation import get_repo_root

        for reporter in get_enabled_reporters(get_repo_root()):
            reporter.write(ctx)
        return ctx
