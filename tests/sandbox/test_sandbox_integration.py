import platform

import pytest

from backend.sandbox.runner import SandboxRunner


@pytest.mark.sandbox
@pytest.mark.skipif(platform.system() != "Linux", reason="sandbox integration requires Linux/WSL2")
def test_docker_probe_runs_with_network_none() -> None:
    if not SandboxRunner.is_available():
        pytest.skip("docker not available")
    runner = SandboxRunner()
    snapshot = runner.create_snapshot(__import__("pathlib").Path("."))
    result = runner.run_poc(["python", "-c", "print('ok')"], snapshot)
    assert result.exit_code == 0
    assert "ok" in result.stdout
