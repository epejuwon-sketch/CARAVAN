"""Regression test for Vercel Serverless Function packaging and diagnostic shield."""

import pytest
import sys
from pathlib import Path


def test_api_directory_contains_complete_application():
    """Verify api/ directory contains all required modules for Vercel serverless packaging."""
    repo_root = Path(__file__).resolve().parents[2]
    api_dir = repo_root / "api"
    api_app_dir = api_dir / "app"
    api_requirements = api_dir / "requirements.txt"
    api_index = api_dir / "index.py"

    assert api_dir.exists(), "api/ directory must exist"
    assert api_app_dir.exists(), "api/app directory must exist for @vercel/python lambda bundling"
    assert (api_app_dir / "main.py").exists(), "api/app/main.py must exist"
    assert (api_app_dir / "core" / "config.py").exists(), "api/app/core/config.py must exist"
    assert api_requirements.exists(), "api/requirements.txt must exist"
    assert api_index.exists(), "api/index.py must exist"


def test_api_index_imports_cleanly():
    """Verify api/index.py can be loaded as an ASGI application without import errors."""
    repo_root = Path(__file__).resolve().parents[2]
    api_path = str(repo_root / "api")
    if api_path not in sys.path:
        sys.path.insert(0, api_path)

    import index
    assert index.app is not None, "index.app must be defined"
