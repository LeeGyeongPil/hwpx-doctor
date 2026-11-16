from __future__ import annotations

import json

from hwpx_doctor.cli import main

FINDING_KEYS = {"rule", "severity", "part", "path", "line", "message"}


def run_json(capsys, *args: str) -> dict:
    main(["--lang", "en", "check", *args])
    return json.loads(capsys.readouterr().out)


def test_json_shape(make, capsys, tmp_path) -> None:
    make("manifest_missing_section")
    make("dangling_charpr")
    make("ok")
    data = run_json(capsys, str(tmp_path), "--format", "json")
    assert list(data) == ["tool", "version", "files", "summary"]
    assert data["tool"] == "hwpx-doctor"
    assert data["summary"] == {"files": 3, "errors": 0, "warnings": 3}
    names = [f["file"] for f in data["files"]]
    assert names == sorted(names)  # deterministic file order
    for file_entry in data["files"]:
        assert set(file_entry) == {"file", "findings"}
        for finding in file_entry["findings"]:
            assert set(finding) == FINDING_KEYS
    mm = next(f for f in data["files"] if f["file"].endswith("manifest_missing_section.hwpx"))
    assert [f["rule"] for f in mm["findings"]] == ["M002", "M003"]  # sorted by rule id


def test_json_is_stable_between_runs(make, capsys) -> None:
    path = make("manifest_missing_section")
    first = run_json(capsys, str(path), "--format", "json")
    second = run_json(capsys, str(path), "--format", "json")
    assert first == second


def test_sarif_matches_json(make, capsys, tmp_path) -> None:
    make("manifest_missing_section")
    make("malformed")
    make("dangling_charpr")
    as_json = run_json(capsys, str(tmp_path), "--format", "json")
    sarif = run_json(capsys, str(tmp_path), "--format", "sarif")
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "hwpx-doctor"
    assert len(run["tool"]["driver"]["rules"]) == 13
    expected = [
        (f["rule"], f["severity"], file_entry["file"], f["part"])
        for file_entry in as_json["files"]
        for f in file_entry["findings"]
    ]
    actual = [
        (r["ruleId"], r["level"], r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
         r["properties"]["part"])
        for r in run["results"]
    ]
    assert actual == expected
    assert all(r["locations"][0]["logicalLocations"][0]["fullyQualifiedName"] for r in run["results"])
