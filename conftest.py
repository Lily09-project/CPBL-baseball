from __future__ import annotations

import tempfile
from pathlib import Path


def pytest_configure(config) -> None:
    """Use a fresh project-local temp directory for each test session on Windows."""
    if config.option.basetemp is not None:
        return
    root = Path(__file__).resolve().parent / ".pytest_sessions"
    root.mkdir(exist_ok=True)
    config.option.basetemp = Path(tempfile.mkdtemp(prefix="run-", dir=root))