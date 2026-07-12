from __future__ import annotations

import tomllib
from pathlib import Path

import chatgpt_haber


def test_package_version_is_1_1_0():
    assert chatgpt_haber.__version__ == "1.1.0"


def test_pyproject_version_matches_package_version():
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["version"] == chatgpt_haber.__version__
