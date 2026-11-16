from __future__ import annotations

import hwpxgen
import pytest

import hwpx_doctor


def rule_ids(data: bytes) -> set[str]:
    return {f.rule for f in hwpx_doctor.check(data).findings}


@pytest.mark.parametrize("variant", sorted(hwpxgen.EXPECTED))
def test_variant_matrix(variant: str) -> None:
    assert rule_ids(hwpxgen.build(variant)) == hwpxgen.EXPECTED[variant]


def test_ok_has_no_findings() -> None:
    assert hwpx_doctor.check(hwpxgen.build("ok")).findings == []


@pytest.mark.parametrize("variant", sorted(hwpxgen.EXPECTED))
def test_namespace_variants(variant: str) -> None:
    # 2016 namespace URIs and renamed prefixes: matching must go by URI, not prefix
    assert rule_ids(hwpxgen.build(variant, ns="2016")) == hwpxgen.EXPECTED[variant]


def test_locations_have_part_line_and_element_path() -> None:
    (finding,) = hwpx_doctor.check(hwpxgen.build("dangling_charpr")).findings
    assert finding.part == "Contents/section0.xml"
    assert finding.line == 4
    assert finding.path == "/hs:sec/hp:p[1]/hp:run[1]/@charPrIDRef"
    assert finding.severity == "warning"


def test_path_uses_original_prefixes() -> None:
    (finding,) = hwpx_doctor.check(hwpxgen.build("dangling_charpr", ns="2016")).findings
    assert finding.path == "/s:sec/p:p[1]/p:run[1]/@charPrIDRef"


def test_not_a_zip_is_c000_only() -> None:
    report = hwpx_doctor.check(b"this is not a zip")
    assert [f.rule for f in report.findings] == ["C000"]
    assert report.errors


def test_duplicate_entry_is_c005() -> None:
    parts, _ = hwpxgen.parts_for("ok")
    with pytest.warns(UserWarning):
        data = hwpxgen.zip_bytes(parts + [parts[-1]])
    assert "C005" in rule_ids(data)


def test_manifest_href_to_missing_entry_is_m001() -> None:
    parts, _ = hwpxgen.parts_for("ok")
    parts = [(n, d.replace(b'href="Contents/section0.xml"', b'href="Contents/gone.xml"') if n.endswith(".hpf") else d)
             for n, d in parts]
    assert rule_ids(hwpxgen.zip_bytes(parts)) == {"M001", "M002"}


def test_binary_reference_without_manifest_item_is_r003() -> None:
    parts, _ = hwpxgen.parts_for("ok")
    parts = [(n, d.replace(b"<hp:run ", b'<hp:run binaryItemIDRef="image9" ', 1) if n.endswith("section0.xml") else d)
             for n, d in parts]
    assert rule_ids(hwpxgen.zip_bytes(parts)) == {"R003"}


def test_no_reference_sentinel_is_not_dangling() -> None:
    parts, _ = hwpxgen.parts_for("ok")
    parts = [(n, d.replace(b'charPrIDRef="0"', b'charPrIDRef="4294967295"', 1) if n.endswith("section0.xml") else d)
             for n, d in parts]
    assert rule_ids(hwpxgen.zip_bytes(parts)) == set()


def test_malformed_part_is_excluded_from_reference_checks() -> None:
    # the broken section also has a dangling ref in a valid sibling would still be reported,
    # but the broken part itself yields only X001 (no cascade)
    report = hwpx_doctor.check(hwpxgen.build("malformed"))
    assert [f.rule for f in report.findings] == ["X001"]
    assert report.findings[0].line == 13
