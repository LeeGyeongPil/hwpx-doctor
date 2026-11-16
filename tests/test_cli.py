from __future__ import annotations

from pathlib import Path

import pytest

from hwpx_doctor.cli import main


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(["--lang", "en", *argv])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_exit_codes(make, capsys, tmp_path: Path) -> None:
    warn_only = make("itemcnt_wrong")
    assert run(capsys, "check", str(warn_only))[0] == 0  # warnings do not fail by default
    assert run(capsys, "check", str(warn_only), "--strict")[0] == 1
    assert run(capsys, "check", str(make("malformed")))[0] == 1
    code, _, err = run(capsys, "check", str(tmp_path / "missing.hwpx"))
    assert code == 2 and "path not found" in err
    assert run(capsys, "check", str(make("malformed", name="m2.hwpx")), "--exit-zero")[0] == 0
    assert run(capsys, "check", str(tmp_path / "missing.hwpx"), "--exit-zero")[0] == 2
    assert run(capsys, "check", str(make("ok")))[0] == 0


def test_select_ignore(make, capsys) -> None:
    path = make("itemcnt_wrong")
    _, out, _ = run(capsys, "check", str(path))
    assert "R002" in out
    _, out, _ = run(capsys, "check", str(path), "--ignore", "R")
    assert "R002" not in out and "no findings" in out
    _, out, _ = run(capsys, "check", str(path), "--select", "C")
    assert "R002" not in out
    _, out, _ = run(capsys, "check", str(path), "--select", "R002")
    assert "R002" in out
    # --strict with R ignored: nothing left to fail on
    assert run(capsys, "check", str(path), "--strict", "--ignore", "R")[0] == 0


def test_unknown_selector_is_usage_error(make, capsys) -> None:
    code, _, err = run(capsys, "check", str(make("ok")), "--select", "Z9")
    assert code == 2 and "unknown rule selector" in err


def test_folder_is_searched_recursively_and_sorted(make, capsys, tmp_path: Path) -> None:
    make("ok", name="b.hwpx")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "a.hwpx").write_bytes((tmp_path / "b.hwpx").read_bytes())
    (tmp_path / "note.txt").write_text("not a document")
    _, out, _ = run(capsys, "check", str(tmp_path))
    lines = [line for line in out.splitlines() if line.endswith("no findings")]
    assert [Path(line.split(":")[0]).name for line in lines] == ["b.hwpx", "a.hwpx"]
    assert out.splitlines()[-1] == "Summary: 2 files, 0 errors, 0 warnings"


def test_not_a_zip_is_a_finding_not_a_usage_error(capsys, tmp_path: Path) -> None:
    bad = tmp_path / "bad.hwpx"
    bad.write_bytes(b"plain text")
    code, out, _ = run(capsys, "check", str(bad))
    assert code == 1 and "C000" in out


def test_empty_folder_is_input_error(capsys, tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    for extra in ([], ["--strict"], ["--exit-zero"]):
        code, out, err = run(capsys, "check", str(empty), *extra)
        assert code == 2 and "no .hwpx files found" in err and "Summary" not in out
    code, _, err = main(["--lang", "ko", "check", str(empty)]), "", capsys.readouterr().err
    assert code == 2 and "하나도 없습니다" in err


def test_deep_nesting_reports_instead_of_crashing(make, capsys, tmp_path: Path) -> None:
    import zipfile

    from hwpx_doctor import check
    import hwpxgen

    parts, _ = hwpxgen.parts_for("ok")
    deep = b"<a>" * 3000 + b"</a>" * 3000
    parts = [(n, deep if n == "Contents/section0.xml" else d) for n, d in parts]
    path = tmp_path / "deep.hwpx"
    path.write_bytes(hwpxgen.zip_bytes(parts))
    assert zipfile.is_zipfile(path)
    assert isinstance(check(path).findings, list)
    assert run(capsys, "check", str(path), "--exit-zero")[0] == 0


def test_multibyte_encoding_declaration_is_not_called_malformed(tmp_path: Path) -> None:
    from hwpx_doctor.xmltree import XmlError, parse

    try:
        parse('<?xml version="1.0" encoding="EUC-KR"?><a/>'.encode())
    except XmlError as exc:
        assert "encoding" in exc.message and "ValueError" not in exc.message
    else:
        raise AssertionError("expected XmlError")
