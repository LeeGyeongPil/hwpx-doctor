"""Regenerate ``examples/`` (one clean HWPX + nine broken ones), deterministically.

Usage: python scripts/make_examples.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

import hwpxgen  # noqa: E402  (test helper that builds packages with the standard library)


def main() -> int:
    out = ROOT / "examples"
    (out / "broken").mkdir(parents=True, exist_ok=True)
    for variant in hwpxgen.EXPECTED:
        target = out / "ok.hwpx" if variant == "ok" else out / "broken" / f"{variant}.hwpx"
        target.write_bytes(hwpxgen.build(variant))
        print(f"wrote {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
