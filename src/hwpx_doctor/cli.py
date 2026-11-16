"""Command line interface: check, fix, rules."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from ._version import __version__
from .checker import check
from .fixer import fix
from .i18n import LANGS, resolve_lang, t
from .model import InputError
from .report import render_json, render_rules, render_sarif, render_text

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2


def _prescan_lang(argv: Sequence[str]) -> str | None:
    """Find ``--lang X`` / ``--lang=X`` before argparse runs, so --help can use it."""
    args = list(argv)
    for i, arg in enumerate(args):
        if arg == "--lang" and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    return None


def build_parser(lang: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hwpx-doctor", add_help=False, description=t(lang, "help.description"), epilog=t(lang, "help.epilog")
    )
    parser.add_argument("-h", "--help", action="help", help=t(lang, "help.help"))
    parser.add_argument("--lang", choices=LANGS, help=t(lang, "help.lang"))
    parser.add_argument("--version", action="version", version=f"hwpx-doctor {__version__}",
                        help=t(lang, "help.version"))
    sub = parser.add_subparsers(dest="command", required=True, metavar="{check,fix,rules}")

    def lang_opt(p: argparse.ArgumentParser) -> None:
        p.add_argument("-h", "--help", action="help", help=t(lang, "help.help"))
        p.add_argument("--lang", choices=LANGS, default=argparse.SUPPRESS, help=t(lang, "help.lang"))

    p_check = sub.add_parser("check", add_help=False, help=t(lang, "help.cmd.check"), description=t(lang, "help.cmd.check"))
    p_check.add_argument("paths", nargs="+", metavar="PATH", help=t(lang, "help.paths"))
    p_check.add_argument("--format", choices=("text", "json", "sarif"), default="text", help=t(lang, "help.format"))
    p_check.add_argument("--select", action="append", metavar="RULES", help=t(lang, "help.select"))
    p_check.add_argument("--ignore", action="append", metavar="RULES", help=t(lang, "help.ignore"))
    p_check.add_argument("--strict", action="store_true", help=t(lang, "help.strict"))
    p_check.add_argument("--exit-zero", action="store_true", help=t(lang, "help.exit_zero"))
    lang_opt(p_check)

    p_fix = sub.add_parser("fix", add_help=False, help=t(lang, "help.cmd.fix"), description=t(lang, "help.cmd.fix"))
    p_fix.add_argument("input", metavar="IN", help=t(lang, "help.fix.input"))
    p_fix.add_argument("-o", "--output", metavar="OUT", help=t(lang, "help.fix.output"))
    p_fix.add_argument("--in-place", action="store_true", help=t(lang, "help.fix.in_place"))
    p_fix.add_argument("--force", action="store_true", help=t(lang, "help.fix.force"))
    lang_opt(p_fix)

    p_rules = sub.add_parser("rules", add_help=False, help=t(lang, "help.cmd.rules"), description=t(lang, "help.cmd.rules"))
    lang_opt(p_rules)
    return parser


def collect_files(paths: Sequence[str], lang: str) -> list[str]:
    """Expand folders to ``*.hwpx`` (sorted, recursive); explicit files are kept as given."""
    files: list[str] = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise InputError(t(lang, "err.not_found", path=raw))
        if path.is_dir():
            for root, dirs, names in os.walk(path):
                dirs.sort()
                files.extend(os.path.join(root, n) for n in sorted(names) if n.lower().endswith(".hwpx"))
        else:
            files.append(raw)
    unique = list(dict.fromkeys(files))
    if not unique:
        raise InputError(t(lang, "err.no_files", paths=", ".join(paths)))
    return unique


def _cmd_check(args: argparse.Namespace, lang: str) -> int:
    files = collect_files(args.paths, lang)
    reports = [check(f, select=args.select, ignore=args.ignore, lang=lang) for f in files]
    if args.format == "json":
        print(render_json(reports))
    elif args.format == "sarif":
        print(render_sarif(reports, lang))
    else:
        print(render_text(reports, lang))
    failed = any(r.failed(strict=args.strict) for r in reports)
    return EXIT_FAIL if failed and not args.exit_zero else EXIT_OK


def _cmd_fix(args: argparse.Namespace, lang: str) -> int:
    if bool(args.output) == bool(args.in_place):
        raise InputError(t(lang, "err.fix_needs_out"))
    source = Path(args.input)
    if args.in_place:
        dest = source.with_name(source.name + ".fixed.tmp")
        result = fix(source, dest, force=True, lang=lang)
        if result.wrote:
            os.replace(dest, source)
        elif dest.exists():
            dest.unlink()
        shown = str(source)
    else:
        result = fix(source, args.output, force=args.force, lang=lang)
        shown = args.output
    if not result.wrote:
        print(t(lang, "fix.not_written"))
        print(render_text([result.report], lang))
        return EXIT_FAIL
    print(t(lang, "fix.applied", items=", ".join(result.applied)) if result.applied else t(lang, "fix.nothing"))
    print(t(lang, "fix.in_place_done" if args.in_place else "fix.wrote", path=shown))
    print(t(lang, "fix.recheck"))
    result.report.file = shown
    print(render_text([result.report], lang))
    left = sorted({f.rule for f in result.report.findings})
    if left:
        print(t(lang, "fix.left", rules=", ".join(left)))
    return EXIT_FAIL if result.report.failed() else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    args_in = list(sys.argv[1:] if argv is None else argv)
    lang = resolve_lang(_prescan_lang(args_in))
    parser = build_parser(lang)
    args = parser.parse_args(args_in)
    if args.lang:
        lang = args.lang
    try:
        if args.command == "check":
            return _cmd_check(args, lang)
        if args.command == "fix":
            return _cmd_fix(args, lang)
        print(render_rules(lang))
        return EXIT_OK
    except InputError as exc:
        print(f"hwpx-doctor: {exc}", file=sys.stderr)
        return EXIT_USAGE


__all__ = ["main", "build_parser"]
