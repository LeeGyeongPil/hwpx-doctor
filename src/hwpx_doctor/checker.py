"""Run all rules against one package."""

from __future__ import annotations

import os
import zipfile
from collections.abc import Iterable

from .catalog import parse_selectors, selected
from .model import Finding, Report
from .package import Package, read_source
from .rules import Context, container, manifest, refs, xmlwf


def run_rules(raw: bytes, label: str, lang: str) -> list[Finding]:
    ctx = Context(lang)
    try:
        pkg = Package(raw, label, lang)
    except zipfile.BadZipFile as exc:
        ctx.add("C000", label, detail=str(exc) or "bad ZIP data")
        return ctx.findings
    container.run(pkg, ctx)
    xmlwf.run(pkg, ctx)
    manifest.run(pkg, ctx)
    refs.run(pkg, ctx)
    return ctx.findings


def check(
    source: str | os.PathLike[str] | bytes,
    *,
    select: Iterable[str] | None = None,
    ignore: Iterable[str] | None = None,
    lang: str = "en",
    label: str | None = None,
) -> Report:
    """Check one ``.hwpx`` (path or raw bytes) and return a :class:`Report`.

    ``select``/``ignore`` take rule ids or prefixes (``"R"``, ``"C00"``).
    Raises :class:`~hwpx_doctor.InputError` for a missing/unreadable path or an
    unknown selector. ``label`` overrides the file name shown for raw bytes. A file that is not a ZIP is reported as rule C000, not raised.
    """
    select_t = parse_selectors(select, lang)
    ignore_t = parse_selectors(ignore, lang)
    shown, raw = read_source(source, lang)
    label = label or shown
    findings = [f for f in run_rules(raw, label, lang) if selected(f.rule, select_t, ignore_t)]
    findings.sort(key=lambda f: (f.rule, f.part, f.line or 0, f.path, f.message))
    return Report(label, findings)


__all__ = ["check", "run_rules"]
