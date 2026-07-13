from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))


@pytest.fixture
def workflow_fixture(tmp_path: Path) -> Path:
    target = tmp_path / "workflow"
    shutil.copytree(PACKAGE_ROOT / "tests" / "fixtures" / "workflow", target)
    return target
