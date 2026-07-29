from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.core.context import ScanContext
from backend.core.registry import get_enabled_detectors, register_stage


@register_stage("find_rules")
class FindRulesStage:
    id = "find_rules"

    def run(self, ctx: ScanContext) -> ScanContext:
        from backend.core.path_validation import get_repo_root

        detectors = get_enabled_detectors(get_repo_root())
        if len(detectors) <= 1:
            for detector in detectors:
                ctx.findings.extend(detector.run(ctx))
            return ctx

        ordered: list[tuple[int, list]] = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(detector.run, ctx): index
                for index, detector in enumerate(detectors)
            }
            for future in as_completed(futures):
                index = futures[future]
                ordered.append((index, future.result()))
        for _, findings in sorted(ordered, key=lambda item: item[0]):
            ctx.findings.extend(findings)
        return ctx
