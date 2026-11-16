"""Safe repairs: only mechanical defects whose fix cannot change document meaning.

* C001/C002  re-pack with ``mimetype`` first and stored (other entries keep
  their order, timestamps, compression and attributes)
* C003       replace the mimetype content (only if the package has a rootfile)
* R002       rewrite ``itemCnt`` digits in the start tag, bytes elsewhere untouched
* M002+M003  add the manifest item for a section the spine already references

XML is never re-serialised (that would rewrite namespace prefixes). Dangling
ID references and orphan sections are reported only: deleting or inventing
content is a decision for a human.
"""

from __future__ import annotations

import io
import os
import re
import zipfile
from pathlib import Path

from .checker import check
from .i18n import t
from .model import FixResult, InputError, Report
from .package import HEADER_PART, Package, read_source
from .rules.container import EXPECTED_MIMETYPE, MIMETYPE
from .rules.manifest import manifest_parts, normalize_href
from .rules.refs import itemcnt_mismatches
from .xmltree import start_tag_end

_ITEMCNT = re.compile(rb"""(?<![\w:.-])(itemCnt\s*=\s*)(["'])\s*\d+\s*\2""")
_SECTION_ID = re.compile(r"section\d+")


def _patch_itemcnt(data: bytes, mismatches: list) -> bytes:
    # Patch from the last tag to the first so earlier offsets stay valid.
    for node, _declared, actual in sorted(mismatches, key=lambda m: m[0].start, reverse=True):
        end = start_tag_end(data, node.start)
        tag = data[node.start:end]
        new_tag, n = _ITEMCNT.subn(lambda m: m.group(1) + m.group(2) + str(actual).encode() + m.group(2), tag, count=1)
        if n:
            data = data[:node.start] + new_tag + data[end:]
    return data


def _restore_spine(pkg: Package, data: bytes) -> tuple[bytes, bool]:
    parts = manifest_parts(pkg)
    if parts is None:
        return data, False
    _, manifest, items, refs = parts
    ids = {i.attrs.get("id", "") for i in items}
    hrefs = {normalize_href(i.attrs["href"]) for i in items if "href" in i.attrs}
    wanted: list[str] = []
    for ref in refs:
        idref = ref.attrs.get("idref", "")
        part = f"Contents/{idref}.xml"
        if (idref not in ids and idref not in wanted and _SECTION_ID.fullmatch(idref)
                and part in pkg.nameset and part not in hrefs):
            wanted.append(idref)
    if not wanted or manifest.self_closing:
        return data, False
    prefix = f"{manifest.prefix}:" if manifest.prefix else ""
    snippet = "".join(
        f'<{prefix}item id="{i}" href="Contents/{i}.xml" media-type="application/xml"/>' for i in wanted
    ).encode()
    return data[:manifest.end] + snippet + data[manifest.end:], True


def _repack(entries: list[tuple[zipfile.ZipInfo, bytes]]) -> bytes:
    """Write entries with the first ``mimetype`` entry first and stored; keep other metadata."""
    first = next((i for i, e in enumerate(entries) if e[0].filename == MIMETYPE), None)
    ordered = list(entries)
    if first is not None:
        ordered.insert(0, ordered.pop(first))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for info, data in ordered:
            zi = zipfile.ZipInfo(info.filename, info.date_time)
            zi.compress_type = zipfile.ZIP_STORED if info.filename == MIMETYPE else info.compress_type
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zf.writestr(zi, data)
    return buf.getvalue()


def fix(
    source: str | os.PathLike[str],
    dest: str | os.PathLike[str],
    *,
    force: bool = False,
    lang: str = "en",
) -> FixResult:
    """Write a repaired copy of ``source`` to ``dest`` and re-check it.

    The source is never modified. If nothing is repairable the output is a
    byte-for-byte copy. A file that is not a ZIP is not written
    (``FixResult.wrote`` is False). Raises :class:`~hwpx_doctor.InputError` if
    ``dest`` exists (without ``force``), is the source itself, or has no parent folder.
    """
    label, raw = read_source(source, lang)
    dest_path = Path(dest)
    if dest_path.exists():
        if Path(source).resolve() == dest_path.resolve() or os.path.samefile(source, dest_path):
            raise InputError(t(lang, "err.same_file", path=str(dest_path)))
        if not force:
            raise InputError(t(lang, "err.exists", path=str(dest_path)))
    if not dest_path.parent.is_dir():
        raise InputError(t(lang, "err.not_found", path=str(dest_path.parent)))

    before = check(raw, lang=lang, label=label)
    if any(f.rule == "C000" for f in before.findings):
        return FixResult([], False, before)

    pkg = Package(raw, label, lang)
    entries = [[info, pkg.zf.read(info)] for info in pkg.infos]
    applied: list[str] = []
    index = {name: i for i, name in reversed(list(enumerate(pkg.names)))}  # first entry per name

    mime_idx = index.get(MIMETYPE)
    if mime_idx is not None:
        if (entries[mime_idx][1] != EXPECTED_MIMETYPE and pkg.rootfile in pkg.nameset):
            entries[mime_idx][1] = EXPECTED_MIMETYPE
            applied.append("C003")
    if mime_idx is not None:
        if pkg.names[0] != MIMETYPE:
            applied.insert(0, "C001")
        if pkg.infos[mime_idx].compress_type != zipfile.ZIP_STORED:
            applied.insert(1 if "C001" in applied else 0, "C002")

    header = pkg.good_tree(HEADER_PART)
    if header is not None:
        mismatches = itemcnt_mismatches(header)
        if mismatches:
            patched = _patch_itemcnt(entries[index[HEADER_PART]][1], mismatches)
            if patched != entries[index[HEADER_PART]][1]:
                entries[index[HEADER_PART]][1] = patched
                applied.append("R002")

    root_idx = index.get(pkg.rootfile)
    if root_idx is not None:
        patched, changed = _restore_spine(pkg, entries[root_idx][1])
        if changed:
            entries[root_idx][1] = patched
            applied.append("M002+M003")

    if applied:
        out = _repack([(e[0], e[1]) for e in entries])
    else:
        out = raw  # nothing to repair: keep the exact bytes (makes fix idempotent)

    tmp = dest_path.with_name(dest_path.name + ".hwpx-doctor.tmp")
    try:
        tmp.write_bytes(out)
        os.replace(tmp, dest_path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return FixResult(applied, True, _recheck(out, dest_path, lang))


def _recheck(out: bytes, dest_path: Path, lang: str) -> Report:
    report = check(out, lang=lang)
    report.file = str(dest_path)
    return report
