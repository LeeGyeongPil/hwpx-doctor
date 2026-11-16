"""Rule implementations. Each module exposes ``run(pkg, ctx)``."""

from __future__ import annotations

from ..catalog import RULES
from ..i18n import t
from ..model import Finding


class Context:
    """Collects findings with localised messages and catalogue severities."""

    def __init__(self, lang: str) -> None:
        self.lang = lang
        self.findings: list[Finding] = []

    def add(self, rule: str, location: str, path: str = "", line: int | None = None, /,
            **params: object) -> None:
        self.findings.append(
            Finding(rule, RULES[rule].severity, location, path, line, t(self.lang, f"msg.{rule}", **params))
        )
