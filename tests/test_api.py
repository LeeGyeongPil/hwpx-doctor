from __future__ import annotations

import ast
import dataclasses
import re
import sys
from pathlib import Path

import hwpxgen
import pytest

import hwpx_doctor

ROOT = Path(__file__).resolve().parent.parent


def test_public_api(make, tmp_path: Path) -> None:
    assert set(hwpx_doctor.__all__) >= {"check", "fix", "RULES", "Finding", "Report", "FixResult", "InputError"}
    assert issubclass(hwpx_doctor.InputError, hwpx_doctor.HwpxDoctorError)

    # RULES: 13 rules with the documented metadata
    assert len(hwpx_doctor.RULES) == 13
    rule = hwpx_doctor.RULES["R001"]
    assert (rule.id, rule.severity, rule.evidence, rule.fixable) == ("R001", "warning", "unverified", False)
    assert hwpx_doctor.RULES["C002"].severity == "error" and hwpx_doctor.RULES["C002"].evidence == "documented"

    # check: path, PathLike and bytes all work; select/ignore filter
    broken = make("manifest_missing_section")
    for source in (str(broken), broken, broken.read_bytes()):
        report = hwpx_doctor.check(source)
        assert isinstance(report, hwpx_doctor.Report)
        assert [f.rule for f in report.findings] == ["M002", "M003"]
    assert [f.rule for f in hwpx_doctor.check(broken, select=["M003"]).findings] == ["M003"]
    assert hwpx_doctor.check(broken, ignore=["M"]).findings == []
    assert hwpx_doctor.check(broken, lang="ko").findings[0].message.endswith("매니페스트에 없습니다")

    # Report helpers
    report = hwpx_doctor.check(broken)
    assert len(report.warnings) == 2 and report.errors == []
    assert not report.failed() and report.failed(strict=True)
    assert report.to_dict()["findings"][0].keys() == {"rule", "severity", "part", "path", "line", "message"}

    # Finding is a frozen dataclass
    finding = report.findings[0]
    assert dataclasses.is_dataclass(finding)
    with pytest.raises(dataclasses.FrozenInstanceError):
        finding.rule = "X"  # type: ignore[misc]

    # fix
    result = hwpx_doctor.fix(broken, tmp_path / "fixed.hwpx")
    assert isinstance(result, hwpx_doctor.FixResult)
    assert result.applied == ["M002+M003"] and result.wrote and result.report.findings == []


def test_input_errors() -> None:
    with pytest.raises(hwpx_doctor.InputError, match="path not found"):
        hwpx_doctor.check("/definitely/not/here.hwpx")
    with pytest.raises(hwpx_doctor.InputError, match="unknown rule selector"):
        hwpx_doctor.check(hwpxgen.build("ok"), select=["Q"])
    with pytest.raises(hwpx_doctor.InputError, match="not a file"):
        hwpx_doctor.check(ROOT)


def test_no_runtime_dependencies() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    # tomllib needs Python 3.11+, so read the dependency list with a regex (works on 3.10)
    match = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.M | re.S)
    assert match is not None and match.group(1).strip() == ""

    stdlib = set(sys.stdlib_module_names)
    foreign: set[str] = set()
    for path in (ROOT / "src" / "hwpx_doctor").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            else:
                continue
            foreign |= {n for n in names if n not in stdlib}
    assert foreign == set()


def test_decompression_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from hwpx_doctor import package

    monkeypatch.setattr(package, "MAX_UNCOMPRESSED_MIB", 0)
    with pytest.raises(hwpx_doctor.InputError, match="expands to more than"):
        hwpx_doctor.check(hwpxgen.build("ok"))
