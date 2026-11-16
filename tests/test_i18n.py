from __future__ import annotations

import pytest

from hwpx_doctor import cli, i18n
from hwpx_doctor.cli import main


def test_resolution_order() -> None:
    env = {"HWPX_DOCTOR_LANG": "ko", "LC_ALL": "en_US.UTF-8", "LC_MESSAGES": "en", "LANG": "en"}
    assert i18n.resolve_lang("en", env) == "en"  # --lang beats everything
    assert i18n.resolve_lang(None, env) == "ko"  # then HWPX_DOCTOR_LANG
    del env["HWPX_DOCTOR_LANG"]
    assert i18n.resolve_lang(None, env) == "en"  # LC_ALL
    env["LC_ALL"] = "ko_KR.UTF-8"
    assert i18n.resolve_lang(None, env) == "ko"
    assert i18n.resolve_lang(None, {"LC_ALL": "", "LC_MESSAGES": "ko_KR", "LANG": "en_US"}) == "ko"  # empty skipped
    assert i18n.resolve_lang(None, {"LC_MESSAGES": "en_US", "LANG": "ko_KR"}) == "en"  # LC_MESSAGES beats LANG
    assert i18n.resolve_lang(None, {"LANG": "ko_KR.UTF-8"}) == "ko"
    assert i18n.resolve_lang(None, {"LANG": "fr_FR"}) == "en"  # not ko -> English
    assert i18n.resolve_lang(None, {}) == "en"


def test_message_keys_equal() -> None:
    assert set(i18n.EN) == set(i18n.KO)
    assert all(i18n.EN[k] and i18n.KO[k] for k in i18n.EN)


def test_every_rule_has_title_and_message() -> None:
    from hwpx_doctor import RULES

    for rule_id in RULES:
        assert f"rule.{rule_id}.title" in i18n.EN
        assert f"msg.{rule_id}" in i18n.EN


def test_placeholders_match_between_languages() -> None:
    import string

    def fields(text: str) -> set[str]:
        return {name for _, name, _, _ in string.Formatter().parse(text) if name}

    for key in i18n.EN:
        assert fields(i18n.EN[key]) == fields(i18n.KO[key]), key


def test_help_language(capsys: pytest.CaptureFixture[str]) -> None:
    for lang, snippet in (("ko", "종료 코드"), ("en", "Exit codes")):
        with pytest.raises(SystemExit) as exc:
            main(["--lang", lang, "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert snippet in out
        with pytest.raises(SystemExit):
            main(["check", "--help", "--lang", lang])  # --lang after the subcommand also works
        assert ("경고도 실패로" if lang == "ko" else "treat warnings as failures") in capsys.readouterr().out


def test_text_output_and_rules_switch_language(make, capsys: pytest.CaptureFixture[str]) -> None:
    path = make("dangling_charpr")
    main(["--lang", "ko", "check", str(path)])
    ko = capsys.readouterr().out
    main(["--lang", "en", "check", str(path)])
    en = capsys.readouterr().out
    assert "경고" in ko and "정의에 없습니다" in ko and ko.splitlines()[-1].startswith("요약: 파일 1개")
    assert "warning" in en and "is not defined" in en and en.splitlines()[-1].startswith("Summary: 1 files")
    main(["--lang", "ko", "rules"])
    assert "무압축" in capsys.readouterr().out
    main(["--lang", "en", "rules"])
    assert "must be stored" in capsys.readouterr().out


def test_env_var_and_flag_priority_in_cli(make, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    path = make("itemcnt_wrong")
    monkeypatch.setenv("HWPX_DOCTOR_LANG", "ko")
    main(["check", str(path)])
    assert "요약:" in capsys.readouterr().out
    main(["--lang", "en", "check", str(path)])
    assert "Summary:" in capsys.readouterr().out


def test_json_messages_follow_language_but_keys_do_not(make, capsys) -> None:
    import json

    path = make("dangling_charpr")
    main(["--lang", "ko", "check", str(path), "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    finding = data["files"][0]["findings"][0]
    assert finding["rule"] == "R001" and "정의에 없습니다" in finding["message"]


def test_prescan_handles_equals_form() -> None:
    assert cli._prescan_lang(["check", "--lang=ko", "x"]) == "ko"
    assert cli._prescan_lang(["check", "x"]) is None
