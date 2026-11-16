"""Check a document made by a real generator (python-hwpx) with hwpx-doctor.

Optional, not part of the test suite. Run with the generator installed:

    uv run --with python-hwpx==6.12.0 python scripts/interop_python_hwpx.py

It builds ``ok.hwpx`` with python-hwpx, derives seven corrupted variants and
prints what hwpx-doctor reports. Files go to a temporary folder (not kept).
"""

from __future__ import annotations

import re
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    from hwpx import HwpxDocument
except ImportError:
    sys.exit("python-hwpx is not installed. Run: uv run --with python-hwpx==6.12.0 python scripts/interop_python_hwpx.py")

import hwpx_doctor

EXPECTED = {
    "mimetype_not_first": {"C001"},
    "mimetype_deflated": {"C002"},
    "malformed": {"X001"},
    "dangling_charpr": {"R001"},
    "itemcnt_wrong": {"R002"},
    "orphan_section": {"M002"},
    "manifest_missing_section": {"M002", "M003"},
}


def read_all(path: Path) -> list[tuple[zipfile.ZipInfo, bytes]]:
    with zipfile.ZipFile(path) as zf:
        return [(i, zf.read(i.filename)) for i in zf.infolist()]


def write(path: Path, entries, order=None, deflate_mimetype=False, extra=()) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for info, data in (order(entries) if order else entries):
            method = info.compress_type
            if info.filename == "mimetype":
                method = zipfile.ZIP_DEFLATED if deflate_mimetype else zipfile.ZIP_STORED
            zf.writestr(info.filename, data, compress_type=method)
        for name, data in extra:
            zf.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        base = out / "ok.hwpx"
        doc = HwpxDocument.new()
        doc.add_paragraph("2026 운영계획")
        doc.add_paragraph("추진 배경: 문서 자동화 품질 점검")
        doc.save_to_path(str(base))
        entries = read_all(base)

        def patch(name: str, fn, dst: str) -> None:
            new = [(i, fn(d.decode("utf-8")).encode("utf-8") if i.filename == name else d) for i, d in entries]
            write(out / dst, new)

        write(out / "mimetype_not_first.hwpx", entries, order=lambda e: e[1:] + e[:1])
        write(out / "mimetype_deflated.hwpx", entries, deflate_mimetype=True)
        patch("Contents/section0.xml", lambda s: re.sub(r'charPrIDRef="\d+"', 'charPrIDRef="999"', s, count=1),
              "dangling_charpr.hwpx")
        patch("Contents/header.xml",
              lambda s: re.sub(r'(<hh:charProperties itemCnt=")(\d+)"', r'\g<1>77"', s, count=1),
              "itemcnt_wrong.hwpx")
        section = dict((i.filename, d) for i, d in entries)["Contents/section0.xml"]
        write(out / "orphan_section.hwpx", entries, extra=[("Contents/section1.xml", section)])
        patch("Contents/content.hpf",
              lambda s: re.sub(r'<opf:item [^>]*href="Contents/section0.xml"[^>]*/>', "", s, count=1),
              "manifest_missing_section.hwpx")
        patch("Contents/section0.xml", lambda s: s.replace("</hs:sec>", "</hs:secX>"), "malformed.hwpx")

        report = hwpx_doctor.check(base)
        print(f"ok.hwpx: {len(report.findings)} findings")
        for f in report.findings:
            print(f"  {f.rule} {f.part}:{f.line} {f.message}")
        detected = 0
        for name, expected in EXPECTED.items():
            got = {f.rule for f in hwpx_doctor.check(out / f"{name}.hwpx").findings}
            hit = got == expected
            detected += hit
            print(f"{name}.hwpx: {sorted(got)} (expected {sorted(expected)}) {'ok' if hit else 'MISMATCH'}")
        print(f"detected {detected}/{len(EXPECTED)}")
        clean = not report.findings
    return 0 if clean and detected == len(EXPECTED) else 1


if __name__ == "__main__":
    raise SystemExit(main())
