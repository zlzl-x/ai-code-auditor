from __future__ import annotations

import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from backend.core.subprocess_runner import run_command

DEFAULT_IMAGE = "python:3.12-slim"
FORBIDDEN_MOUNT_PARTS = {".env", "backend/data", ".git"}


@dataclass(frozen=True)
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    container_id: str = ""


def sanitize_log(text: str) -> str:
    return re.sub(r"[A-Za-z]:\\[^\s]+|/[\w./-]+", "<path>", text)


class SandboxRunner:
    def __init__(self, *, image: str = DEFAULT_IMAGE, timeout: int = 60) -> None:
        self.image = image
        self.timeout = timeout

    @staticmethod
    def is_available() -> bool:
        if shutil.which("docker") is None:
            return False
        result = run_command(["docker", "info"], timeout=15)
        return result.ok

    def create_snapshot(self, source: Path) -> Path:
        snapshot_root = Path(tempfile.mkdtemp(prefix="auditor-sandbox-"))
        if source.is_file():
            target = snapshot_root / source.name
            target.write_text(source.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            return snapshot_root
        if source.is_dir():
            for path in source.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(source)
                if any(part in FORBIDDEN_MOUNT_PARTS for part in relative.parts):
                    continue
                dest = snapshot_root / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(path.read_bytes())
            return snapshot_root
        snapshot_root.mkdir(parents=True, exist_ok=True)
        return snapshot_root

    def run_poc(self, command: list[str], snapshot: Path) -> SandboxResult:
        container_name = f"auditor-sandbox-{uuid.uuid4().hex[:12]}"
        mount = f"{snapshot.resolve()}:/work:ro"
        cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "-v",
            mount,
            "-w",
            "/work",
            self.image,
            *command,
        ]
        result = run_command(cmd, timeout=self.timeout)
        return SandboxResult(
            exit_code=result.returncode,
            stdout=sanitize_log(result.stdout),
            stderr=sanitize_log(result.stderr),
            timed_out=result.timed_out,
            container_id=container_name,
        )

    def cleanup(self, container_id: str) -> None:
        if not container_id:
            return
        run_command(["docker", "rm", "-f", container_id], timeout=15)
