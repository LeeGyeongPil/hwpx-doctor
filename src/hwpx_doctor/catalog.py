"""Rule metadata: id, default severity, evidence level, fixability.

Severity principle: only defects that are documented to break opening in the
Hancom Office, or that make a part unreadable for any OWPML consumer, are
errors. Everything else is a warning (use ``--strict`` to fail on those).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .i18n import LANGS, t
from .model import InputError


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str  # "error" | "warning"
    evidence: str  # "documented" | "structural" | "unverified"
    fixable: bool
    title_key: str


def _rule(rule_id: str, severity: str, evidence: str, fixable: bool = False) -> Rule:
    return Rule(rule_id, severity, evidence, fixable, f"rule.{rule_id}.title")


RULES: Mapping[str, Rule] = {
    r.id: r
    for r in (
        _rule("C000", "error", "structural"),
        _rule("C001", "error", "documented", True),
        _rule("C002", "error", "documented", True),
        _rule("C003", "error", "documented", True),
        _rule("C004", "error", "structural"),
        _rule("C005", "warning", "unverified"),
        _rule("X001", "error", "structural"),
        _rule("M001", "warning", "unverified"),
        _rule("M002", "warning", "unverified", True),
        _rule("M003", "warning", "unverified", True),
        _rule("R001", "warning", "unverified"),
        _rule("R002", "warning", "unverified", True),
        _rule("R003", "warning", "unverified"),
    )
}

# Rules that are only repaired under extra conditions.
PARTLY_FIXABLE = frozenset({"C003", "M002", "M003"})


def parse_selectors(values: Iterable[str] | None, lang: str = "en") -> tuple[str, ...]:
    """Normalise ``--select``/``--ignore`` values; reject selectors that match no rule."""
    out: list[str] = []
    for raw in values or ():
        for token in str(raw).split(","):
            token = token.strip().upper()
            if not token:
                continue
            if not any(rid.startswith(token) for rid in RULES):
                raise InputError(t(lang, "err.unknown_rule", sel=token, valid=", ".join(RULES)))
            out.append(token)
    return tuple(out)


def selected(rule_id: str, select: tuple[str, ...], ignore: tuple[str, ...]) -> bool:
    if select and not any(rule_id.startswith(s) for s in select):
        return False
    return not any(rule_id.startswith(s) for s in ignore)


__all__ = ["RULES", "Rule", "PARTLY_FIXABLE", "LANGS", "parse_selectors", "selected"]
