"""Render reports as text, JSON or SARIF 2.1.0."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from ._version import __version__
from .catalog import PARTLY_FIXABLE, RULES
from .i18n import t
from .model import Report

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
INFO_URI = "https://github.com/LeeGyeongPil/hwpx-doctor"


def summary(reports: Sequence[Report]) -> dict[str, int]:
    return {
        "files": len(reports),
        "errors": sum(len(r.errors) for r in reports),
        "warnings": sum(len(r.warnings) for r in reports),
    }


def render_text(reports: Sequence[Report], lang: str) -> str:
    lines: list[str] = []
    for report in reports:
        if not report.findings:
            lines.append(f"{report.file}: {t(lang, 'out.no_findings')}")
            continue
        lines.append(report.file)
        for f in report.findings:
            where = f"{f.part}:{f.line}" if f.line is not None else f.part
            lines.append(f"  {f.rule} {t(lang, 'sev.' + f.severity)} {where} {f.message}")
            if f.path:
                lines.append(f"      {f.path}")
    lines.append(t(lang, "out.summary", **summary(reports)))
    return "\n".join(lines)


def render_json(reports: Sequence[Report]) -> str:
    data = {
        "tool": "hwpx-doctor",
        "version": __version__,
        "files": [r.to_dict() for r in reports],
        "summary": summary(reports),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def render_sarif(reports: Sequence[Report], lang: str) -> str:
    rules = [
        {
            "id": rule.id,
            "name": rule.id,
            "shortDescription": {"text": t(lang, rule.title_key)},
            "defaultConfiguration": {"level": rule.severity},
            "properties": {"evidence": rule.evidence},
        }
        for rule in RULES.values()
    ]
    results: list[dict[str, Any]] = []
    for report in reports:
        uri = report.file.replace("\\", "/")
        for f in report.findings:
            props: dict[str, Any] = {"part": f.part}
            if f.line is not None:
                props["line"] = f.line
            results.append({
                "ruleId": f.rule,
                "level": f.severity,
                "message": {"text": f.message},
                "locations": [{
                    "physicalLocation": {"artifactLocation": {"uri": uri}},
                    "logicalLocations": [{"fullyQualifiedName": f"{f.part}{f.path}"}],
                }],
                "properties": props,
            })
    sarif = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "hwpx-doctor",
                "version": __version__,
                "informationUri": INFO_URI,
                "rules": rules,
            }},
            "results": results,
        }],
    }
    return json.dumps(sarif, ensure_ascii=False, indent=2)


def render_rules(lang: str) -> str:
    header = [t(lang, "rules.col.id"), t(lang, "rules.col.severity"), t(lang, "rules.col.evidence"),
              t(lang, "rules.col.fix"), t(lang, "rules.col.title")]
    rows = [header]
    for rule in RULES.values():
        fix = "fix.partly" if rule.id in PARTLY_FIXABLE else ("fix.yes" if rule.fixable else "fix.no")
        rows.append([rule.id, t(lang, "sev." + rule.severity), t(lang, "evidence." + rule.evidence),
                     t(lang, fix), t(lang, rule.title_key)])
    widths = [max(_width(r[i]) for r in rows) for i in range(4)]
    out = []
    for row in rows:
        cells = [row[i] + " " * (widths[i] - _width(row[i])) for i in range(4)]
        out.append("  ".join(cells + [row[4]]))
    return "\n".join(out)


def _width(text: str) -> int:
    """Display width: Hangul and other wide characters take two columns."""
    return sum(2 if ord(c) >= 0x1100 and _is_wide(c) else 1 for c in text)


def _is_wide(c: str) -> bool:
    o = ord(c)
    return 0x1100 <= o <= 0x115F or 0x2E80 <= o <= 0xA4CF or 0xAC00 <= o <= 0xD7A3 or 0xF900 <= o <= 0xFAFF
