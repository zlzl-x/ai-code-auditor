from __future__ import annotations

from pathlib import Path


def load_env_file() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    from backend.core.path_validation import get_repo_root

    env_path = get_repo_root() / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
