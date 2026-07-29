from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


@dataclass(frozen=True)
class ScanEvent:
    stage: str
    message: str
    timestamp: str
    progress: float = 0.0

    @classmethod
    def create(cls, stage: str, message: str, progress: float = 0.0) -> ScanEvent:
        return cls(
            stage=stage,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            progress=progress,
        )


class EventEmitter:
    def __init__(self) -> None:
        self._listeners: list[Callable[[ScanEvent], None]] = []

    def on(self, listener: Callable[[ScanEvent], None]) -> None:
        self._listeners.append(listener)

    def emit(self, event: ScanEvent) -> None:
        for listener in list(self._listeners):
            listener(event)
