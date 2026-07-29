from backend.core.registry import get_enabled_detectors, load_modules_config


def test_load_modules_config(repo_root) -> None:
    config = load_modules_config(repo_root)
    assert "semgrep" in config["detectors"]
    assert "recon" in config["pipeline"]
    assert "verify_llm" in config["pipeline"]
    assert "markdown" in config["reporters"]


def test_get_enabled_detectors(repo_root) -> None:
    detectors = get_enabled_detectors(repo_root)
    ids = [detector.id for detector in detectors]
    assert ids == [
        "semgrep",
        "bandit",
        "gitleaks",
        "npm_audit",
        "eslint_security",
        "config_audit",
    ]
