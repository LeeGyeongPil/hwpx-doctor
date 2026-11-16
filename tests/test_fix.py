from __future__ import annotations

import zipfile
from pathlib import Path

import hwpxgen
import pytest

import hwpx_doctor
from hwpx_doctor.cli import main


def read_part(path: Path, name: str) -> bytes:
    with zipfile.ZipFile(path) as zf:
        return zf.read(name)


@pytest.mark.parametrize(
    ("variant", "applied"),
    [
        ("mimetype_not_first", ["C001"]),
        ("mimetype_deflated", ["C002"]),
        ("mimetype_wrong", ["C003"]),
        ("itemcnt_wrong", ["R002"]),
        ("manifest_missing_section", ["M002+M003"]),
    ],
)
def test_safe_repairs_clear_the_rule(make, tmp_path: Path, variant: str, applied: list[str]) -> None:
    src = make(variant)
    result = hwpx_doctor.fix(src, tmp_path / "out.hwpx")
    assert result.applied == applied
    assert result.wrote
    assert result.report.findings == []
    assert hwpx_doctor.check(tmp_path / "out.hwpx").findings == []


@pytest.mark.parametrize("variant", ["dangling_charpr", "orphan_section"])
def test_unsafe_defects_are_reported_not_fixed(make, tmp_path: Path, variant: str) -> None:
    src = make(variant)
    result = hwpx_doctor.fix(src, tmp_path / "out.hwpx")
    assert result.applied == []
    assert {f.rule for f in result.report.findings} == hwpxgen.EXPECTED[variant]
    assert (tmp_path / "out.hwpx").read_bytes() == src.read_bytes()  # byte-for-byte copy


def test_input_bytes_are_unchanged(make, tmp_path: Path) -> None:
    src = make("mimetype_not_first")
    before = src.read_bytes()
    hwpx_doctor.fix(src, tmp_path / "out.hwpx")
    assert src.read_bytes() == before


def test_header_differs_only_in_itemcnt_value(make, tmp_path: Path) -> None:
    src = make("itemcnt_wrong")
    out = tmp_path / "out.hwpx"
    hwpx_doctor.fix(src, out)
    original = read_part(src, "Contents/header.xml")
    patched = read_part(out, "Contents/header.xml")
    assert patched == original.replace(b'<hh:charProperties itemCnt="7">', b'<hh:charProperties itemCnt="2">')
    assert patched != original


def test_spine_repair_inserts_one_item_with_the_document_prefix(make, tmp_path: Path) -> None:
    for ns, prefix in (("2011", b"opf"), ("2016", b"pkg")):
        src = make("manifest_missing_section", ns=ns, name=f"src{ns}.hwpx")
        out = tmp_path / f"out{ns}.hwpx"
        hwpx_doctor.fix(src, out)
        new = read_part(out, "Contents/content.hpf")
        old = read_part(src, "Contents/content.hpf")
        snippet = b'<' + prefix + b':item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
        assert new == old.replace(b"</" + prefix + b":manifest>", snippet + b"</" + prefix + b":manifest>")


def test_fix_twice_is_byte_identical(make, tmp_path: Path) -> None:
    parts, _ = hwpxgen.parts_for("itemcnt_wrong")
    broken = hwpxgen.zip_bytes(parts, deflate_mimetype=True)  # two repairs at once
    src = tmp_path / "multi.hwpx"
    src.write_bytes(broken)
    first = tmp_path / "first.hwpx"
    second = tmp_path / "second.hwpx"
    r1 = hwpx_doctor.fix(src, first)
    assert r1.applied == ["C002", "R002"]
    r2 = hwpx_doctor.fix(first, second)
    assert r2.applied == []
    assert first.read_bytes() == second.read_bytes()


def test_repack_keeps_other_entries_metadata(make, tmp_path: Path) -> None:
    src = make("mimetype_not_first")
    out = tmp_path / "out.hwpx"
    hwpx_doctor.fix(src, out)
    with zipfile.ZipFile(src) as a, zipfile.ZipFile(out) as b:
        assert b.namelist()[0] == "mimetype"
        assert b.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert [n for n in b.namelist() if n != "mimetype"] == [n for n in a.namelist() if n != "mimetype"]
        for name in b.namelist():
            assert b.getinfo(name).date_time == a.getinfo(name).date_time
            assert b.read(name) == a.read(name)
            if name != "mimetype":
                assert b.getinfo(name).compress_type == a.getinfo(name).compress_type


def test_existing_output_needs_force(make, tmp_path: Path) -> None:
    src = make("mimetype_deflated")
    out = tmp_path / "out.hwpx"
    out.write_bytes(b"old")
    with pytest.raises(hwpx_doctor.InputError, match="--force"):
        hwpx_doctor.fix(src, out)
    assert out.read_bytes() == b"old"
    hwpx_doctor.fix(src, out, force=True)
    assert out.read_bytes() != b"old"


def test_cli_exit_code_2_on_output_conflict(make, tmp_path: Path, capsys) -> None:
    src = make("mimetype_deflated")
    out = tmp_path / "out.hwpx"
    out.write_bytes(b"old")
    assert main(["--lang", "en", "fix", str(src), "-o", str(out)]) == 2
    assert "output exists" in capsys.readouterr().err
    assert main(["--lang", "en", "fix", str(src), "-o", str(out), "--force"]) == 0


def test_cli_in_place(make, tmp_path: Path, capsys) -> None:
    src = make("mimetype_deflated")
    assert main(["--lang", "en", "fix", str(src), "--in-place"]) == 0
    assert hwpx_doctor.check(src).findings == []
    assert not list(tmp_path.glob("*.tmp"))
    assert "Applied repairs: C002" in capsys.readouterr().out


def test_cli_fix_reports_what_was_left(make, tmp_path: Path, capsys) -> None:
    src = make("dangling_charpr")
    code = main(["--lang", "en", "fix", str(src), "-o", str(tmp_path / "o.hwpx")])
    out = capsys.readouterr().out
    assert code == 0  # warning only
    assert "Nothing to repair" in out and "R001" in out and "Left as is" in out


def test_cli_fix_requires_output_or_in_place(make, capsys) -> None:
    assert main(["--lang", "en", "fix", str(make("ok"))]) == 2
    assert "needs -o OUT or --in-place" in capsys.readouterr().err


def test_not_a_zip_is_not_written(tmp_path: Path) -> None:
    src = tmp_path / "bad.hwpx"
    src.write_bytes(b"not a zip")
    result = hwpx_doctor.fix(src, tmp_path / "out.hwpx")
    assert not result.wrote and not (tmp_path / "out.hwpx").exists()
    assert [f.rule for f in result.report.findings] == ["C000"]


def test_missing_output_folder_is_input_error(make, tmp_path: Path) -> None:
    with pytest.raises(hwpx_doctor.InputError):
        hwpx_doctor.fix(make("ok"), tmp_path / "nope" / "out.hwpx")


def test_same_file_is_input_error(make) -> None:
    src = make("mimetype_deflated")
    with pytest.raises(hwpx_doctor.InputError, match="same file"):
        hwpx_doctor.fix(src, src, force=True)


def test_fix_errors_keep_the_input_path(tmp_path: Path) -> None:
    src = tmp_path / "in.txt.hwpx"
    src.write_bytes(b"not a zip")
    result = hwpx_doctor.fix(src, tmp_path / "out.hwpx")
    assert not result.wrote and result.report.file == str(src)
