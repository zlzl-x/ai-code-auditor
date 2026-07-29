from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import Sequence


class SubprocessError(Exception):
    """Raised when a subprocess fails in a non-recoverable way."""


@dataclass(frozen=True)
class SubprocessResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def _resolve_command(cmd: Sequence[str]) -> list[str]:
    command = list(cmd)
    if not command:
        return command
    resolved = shutil.which(command[0])
    if resolved:
        command[0] = resolved
    return command


def run_command(
    cmd: Sequence[str],
    *,
    timeout: int = 300,
    cwd: Path | None = None,
) -> SubprocessResult:
    if not cmd:
        raise SubprocessError("Command must not be empty")
    command = _resolve_command(cmd)
    try:
        completed = subprocess.run(  # nosec B603 - hardened wrapper enforces shell=False
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
            shell=False,
            check=False,
        )
        return SubprocessResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return SubprocessResult(
            command=command,
            returncode=-1,
            stdout=stdout,
            stderr=stderr or "Command timed out",
            timed_out=True,
        )
