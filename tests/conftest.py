from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import hwpxgen
import pytest


@pytest.fixture
def make(tmp_path: Path) -> Callable[..., Path]:
    """Write a generated variant into tmp_path and return its path."""

    def _make(variant: str = "ok", ns: str = "2011", name: str | None = None) -> Path:
        target = tmp_path / (name or f"{variant}.hwpx")
        target.write_bytes(hwpxgen.build(variant, ns))
        return target

    return _make
