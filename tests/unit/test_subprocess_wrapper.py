import sys

from backend.core.subprocess_runner import run_command


def test_run_command_uses_argument_list() -> None:
    result = run_command([sys.executable, "-c", "print('ok')"])
    assert result.ok
    assert "ok" in result.stdout


def test_run_command_returns_nonzero_result() -> None:
    result = run_command([sys.executable, "-c", "import sys; sys.exit(2)"])
    assert not result.ok
    assert result.returncode == 2
