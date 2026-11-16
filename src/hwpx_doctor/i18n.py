"""English / Korean message tables and language resolution.

All user-visible text lives in ``MESSAGES``. Rule ids, JSON keys and SARIF
fields are language independent; only human text changes.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

LANGS = ("en", "ko")
ENV_VAR = "HWPX_DOCTOR_LANG"

EN: dict[str, str] = {
    # --- rule titles (rules command, SARIF shortDescription) ---
    "rule.C000.title": "Not a readable ZIP archive (later checks are skipped)",
    "rule.C001.title": "First ZIP entry is not 'mimetype'",
    "rule.C002.title": "'mimetype' entry is compressed (must be stored)",
    "rule.C003.title": "'mimetype' content is not 'application/hwp+zip'",
    "rule.C004.title": "Required package part is missing",
    "rule.C005.title": "Duplicate ZIP entry name",
    "rule.X001.title": "XML part is not well-formed",
    "rule.M001.title": "Manifest item points to a missing ZIP entry",
    "rule.M002.title": "Section or BinData entry is not listed in the manifest",
    "rule.M003.title": "Spine itemref is not in the manifest",
    "rule.R001.title": "Style/ID reference has no definition in header.xml",
    "rule.R002.title": "Header list itemCnt differs from the actual child count",
    "rule.R003.title": "binaryItemIDRef is not a manifest item id",
    # --- rule messages ---
    "msg.C000": "not a valid ZIP archive: {detail}",
    "msg.C001": "first ZIP entry is {first!r}, expected 'mimetype'",
    "msg.C002": "mimetype is compressed (method {method}); it must be stored",
    "msg.C003": "mimetype content is {content!r}, expected 'application/hwp+zip'",
    "msg.C004": "required part is missing: {part}",
    "msg.C005": "duplicate ZIP entry name: {name}",
    "msg.X001": "XML is not well-formed: {detail}",
    "msg.M001": "manifest item {id!r} points to {href!r}, which is not in the package",
    "msg.M002": "{part} is in the package but not listed in the manifest",
    "msg.M003": "spine itemref {idref!r} is not in the manifest",
    "msg.R001": '{attr}="{value}" is not defined in the header.xml {kind} list',
    "msg.R002": "{list} declares itemCnt={declared} but has {actual} children",
    "msg.R003": 'binaryItemIDRef="{value}" is not a manifest item id',
    # --- generic words ---
    "sev.error": "error",
    "sev.warning": "warning",
    "evidence.documented": "documented",
    "evidence.structural": "structural",
    "evidence.unverified": "unverified",
    "fix.yes": "yes",
    "fix.partly": "partly",
    "fix.no": "no",
    # --- check output ---
    "out.no_findings": "no findings",
    "out.summary": "Summary: {files} files, {errors} errors, {warnings} warnings",
    # --- fix output ---
    "fix.applied": "Applied repairs: {items}",
    "fix.nothing": "Nothing to repair (output is a byte-for-byte copy).",
    "fix.wrote": "Wrote {path}",
    "fix.not_written": "Nothing written: the file is not a readable HWPX package.",
    "fix.recheck": "Re-check of the result:",
    "fix.left": "Left as is (reported only, fixing would change meaning): {rules}",
    "fix.in_place_done": "Replaced {path} in place",
    # --- rules command ---
    "rules.col.id": "ID",
    "rules.col.severity": "Severity",
    "rules.col.evidence": "Evidence",
    "rules.col.fix": "Fix",
    "rules.col.title": "Description",
    # --- errors ---
    "err.not_found": "path not found: {path} (check the spelling or pass a .hwpx file or folder)",
    "err.not_file": "not a file: {path} (pass a .hwpx file)",
    "err.no_files": "no .hwpx files found under: {paths} (check the path or the generator output)",
    "err.read": "cannot read {path}: {detail}",
    "err.exists": "output exists: {path} (pass --force to overwrite)",
    "err.same_file": "output is the same file as the input: {path} (use --in-place to replace the input)",
    "err.unknown_rule": "unknown rule selector {sel!r} (valid ids: {valid}; a prefix such as 'R' also works)",
    "err.too_large": "package expands to more than {limit} MiB: {path}",
    "err.fix_needs_out": "fix needs -o OUT or --in-place",
    # --- CLI help ---
    "help.description": "Check generated HWPX (OWPML) files for container, manifest and ID-reference defects, and safely repair the mechanical ones.",
    "help.epilog": "Exit codes: 0 no failing findings, 1 failing findings, 2 usage or input error.",
    "help.help": "show this help message and exit",
    "help.lang": "output language: en or ko (default: HWPX_DOCTOR_LANG, then LC_ALL, LC_MESSAGES, LANG)",
    "help.version": "show the version and exit",
    "help.cmd.check": "check .hwpx files or folders",
    "help.cmd.fix": "apply safe repairs and re-check",
    "help.cmd.rules": "list the rules",
    "help.paths": ".hwpx files or folders (searched recursively)",
    "help.format": "output format (default: text)",
    "help.select": "comma-separated rule ids or prefixes to run, e.g. C,R001",
    "help.ignore": "comma-separated rule ids or prefixes to skip",
    "help.strict": "treat warnings as failures (exit code 1)",
    "help.exit_zero": "always exit 0 for findings (usage errors still exit 2)",
    "help.fix.input": "the .hwpx file to repair",
    "help.fix.output": "write the repaired copy here",
    "help.fix.in_place": "replace the input file with the repaired copy",
    "help.fix.force": "overwrite the output file if it exists",
}

KO: dict[str, str] = {
    "rule.C000.title": "ZIP 으로 열 수 없음(이후 검사 생략)",
    "rule.C001.title": "첫 ZIP 항목이 'mimetype' 이 아님",
    "rule.C002.title": "'mimetype' 항목이 압축되어 있음(무압축이어야 함)",
    "rule.C003.title": "'mimetype' 내용이 'application/hwp+zip' 이 아님",
    "rule.C004.title": "필수 패키지 파트가 없음",
    "rule.C005.title": "같은 이름의 ZIP 항목이 중복됨",
    "rule.X001.title": "XML 파트가 정형(well-formed)이 아님",
    "rule.M001.title": "매니페스트 항목이 가리키는 ZIP 항목이 없음",
    "rule.M002.title": "section·BinData 항목이 매니페스트에 없음",
    "rule.M003.title": "spine itemref 가 매니페스트에 없음",
    "rule.R001.title": "스타일·ID 참조가 header.xml 에 정의되어 있지 않음",
    "rule.R002.title": "header 목록의 itemCnt 가 실제 자식 수와 다름",
    "rule.R003.title": "binaryItemIDRef 가 매니페스트 item id 에 없음",
    "msg.C000": "올바른 ZIP 파일이 아닙니다: {detail}",
    "msg.C001": "첫 ZIP 항목이 {first!r} 입니다('mimetype' 이어야 함)",
    "msg.C002": "mimetype 이 압축되어 있습니다(방식 {method}). 무압축이어야 합니다",
    "msg.C003": "mimetype 내용이 {content!r} 입니다('application/hwp+zip' 이어야 함)",
    "msg.C004": "필수 파트가 없습니다: {part}",
    "msg.C005": "ZIP 항목 이름이 중복됩니다: {name}",
    "msg.X001": "XML 이 정형이 아닙니다: {detail}",
    "msg.M001": "매니페스트 항목 {id!r} 이(가) 패키지에 없는 {href!r} 를 가리킵니다",
    "msg.M002": "{part} 이(가) 패키지에는 있지만 매니페스트에 없습니다",
    "msg.M003": "spine itemref {idref!r} 이(가) 매니페스트에 없습니다",
    "msg.R001": '{attr}="{value}" 이(가) header.xml {kind} 정의에 없습니다',
    "msg.R002": "{list} 의 itemCnt={declared} 이지만 실제 자식은 {actual}개입니다",
    "msg.R003": 'binaryItemIDRef="{value}" 이(가) 매니페스트 item id 에 없습니다',
    "sev.error": "오류",
    "sev.warning": "경고",
    "evidence.documented": "문서 근거",
    "evidence.structural": "구조 결함",
    "evidence.unverified": "미확인",
    "fix.yes": "가능",
    "fix.partly": "조건부",
    "fix.no": "불가",
    "out.no_findings": "결함 없음",
    "out.summary": "요약: 파일 {files}개, 오류 {errors}개, 경고 {warnings}개",
    "fix.applied": "적용한 수리: {items}",
    "fix.nothing": "고칠 것이 없습니다(출력은 입력의 바이트 단위 복사본입니다).",
    "fix.wrote": "{path} 에 썼습니다",
    "fix.not_written": "쓰지 않았습니다: 읽을 수 있는 HWPX 패키지가 아닙니다.",
    "fix.recheck": "결과 재검사:",
    "fix.left": "그대로 둠(보고만 함, 고치면 의미가 바뀜): {rules}",
    "fix.in_place_done": "{path} 을(를) 제자리에서 교체했습니다",
    "rules.col.id": "ID",
    "rules.col.severity": "심각도",
    "rules.col.evidence": "근거",
    "rules.col.fix": "수리",
    "rules.col.title": "설명",
    "err.not_found": "경로를 찾을 수 없습니다: {path} (철자를 확인하거나 .hwpx 파일·폴더를 넘기세요)",
    "err.not_file": "파일이 아닙니다: {path} (.hwpx 파일을 넘기세요)",
    "err.no_files": ".hwpx 파일이 하나도 없습니다: {paths} (경로나 생성기 출력을 확인하세요)",
    "err.read": "{path} 을(를) 읽을 수 없습니다: {detail}",
    "err.exists": "출력 파일이 이미 있습니다: {path} (덮어쓰려면 --force)",
    "err.same_file": "출력이 입력과 같은 파일입니다: {path} (입력을 바꾸려면 --in-place)",
    "err.unknown_rule": "알 수 없는 규칙 {sel!r} (사용 가능한 ID: {valid}, 'R' 같은 접두어도 가능)",
    "err.too_large": "패키지가 {limit} MiB 를 넘게 풀립니다: {path}",
    "err.fix_needs_out": "fix 에는 -o OUT 또는 --in-place 가 필요합니다",
    "help.description": "생성된 HWPX(OWPML) 파일의 컨테이너·매니페스트·ID 참조 결함을 검사하고, 기계적인 결함은 안전하게 고칩니다.",
    "help.epilog": "종료 코드: 0 실패 결함 없음, 1 실패 결함 있음, 2 사용·입력 오류.",
    "help.help": "도움말을 보여 주고 끝냅니다",
    "help.lang": "출력 언어 en 또는 ko (기본: HWPX_DOCTOR_LANG, LC_ALL, LC_MESSAGES, LANG 순)",
    "help.version": "버전을 보여 주고 끝냅니다",
    "help.cmd.check": ".hwpx 파일·폴더를 검사합니다",
    "help.cmd.fix": "안전한 수리를 적용하고 재검사합니다",
    "help.cmd.rules": "규칙 목록을 보여 줍니다",
    "help.paths": ".hwpx 파일 또는 폴더(하위까지 재귀 탐색)",
    "help.format": "출력 형식(기본: text)",
    "help.select": "실행할 규칙 ID·접두어(쉼표 구분), 예: C,R001",
    "help.ignore": "건너뛸 규칙 ID·접두어(쉼표 구분)",
    "help.strict": "경고도 실패로 처리(종료 코드 1)",
    "help.exit_zero": "결함이 있어도 항상 종료 코드 0(사용 오류는 여전히 2)",
    "help.fix.input": "고칠 .hwpx 파일",
    "help.fix.output": "수리본을 쓸 경로",
    "help.fix.in_place": "입력 파일을 수리본으로 교체",
    "help.fix.force": "출력 파일이 있으면 덮어씀",
}

MESSAGES: Mapping[str, Mapping[str, str]] = {"en": EN, "ko": KO}


def normalize(value: str | None) -> str | None:
    """Map a locale-like string (``ko_KR.UTF-8``, ``en``) to ``en``/``ko``; None if empty."""
    if value is None:
        return None
    value = value.strip().lower()
    if not value:
        return None
    return "ko" if value.startswith("ko") else "en"


def resolve_lang(cli_value: str | None = None, environ: Mapping[str, str] | None = None) -> str:
    """Resolve the output language.

    Order: ``--lang`` value, ``HWPX_DOCTOR_LANG``, ``LC_ALL``, ``LC_MESSAGES``,
    ``LANG``. The first non-empty value decides; anything not starting with
    ``ko`` means English.
    """
    env = os.environ if environ is None else environ
    for candidate in (cli_value, env.get(ENV_VAR), env.get("LC_ALL"), env.get("LC_MESSAGES"), env.get("LANG")):
        lang = normalize(candidate)
        if lang is not None:
            return lang
    return "en"


def t(lang: str, key: str, **params: object) -> str:
    """Look up ``key`` in ``lang`` (falls back to English) and format it."""
    table = MESSAGES.get(lang, EN)
    template = table.get(key) or EN[key]
    return template.format(**params) if params else template
