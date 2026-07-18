from __future__ import annotations

from pathlib import Path

import pytest

from svtorture.catalog import Catalog, load_catalog

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def catalog(root: Path) -> Catalog:
    return load_catalog(root)
