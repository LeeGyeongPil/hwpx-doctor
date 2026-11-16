"""M001-M003: OPF manifest and spine consistency (both directions)."""

from __future__ import annotations

import re
from urllib.parse import unquote

from ..package import Package, is_opf_ns
from ..xmltree import Node
from . import Context

TRACKED_ENTRY = re.compile(r"Contents/section\d+\.xml|BinData/.+")


def normalize_href(href: str) -> str:
    href = unquote(href)
    while href.startswith("./"):
        href = href[2:]
    return href


def manifest_parts(pkg: Package) -> tuple[Node, Node, list[Node], list[Node]] | None:
    """Return ``(package root, manifest node, items, itemrefs)`` or None."""
    root = pkg.good_tree(pkg.rootfile)
    if root is None:
        return None
    manifest = next((n for n in root.iter() if n.local == "manifest" and is_opf_ns(n.uri)), None)
    if manifest is None:
        return None
    items = [n for n in manifest.children if n.local == "item" and is_opf_ns(n.uri)]
    refs = [n for n in root.iter() if n.local == "itemref" and is_opf_ns(n.uri)]
    return root, manifest, items, refs


def run(pkg: Package, ctx: Context) -> None:
    parts = manifest_parts(pkg)
    if parts is None:
        return
    _, manifest, items, refs = parts
    rootfile = pkg.rootfile
    hrefs: set[str] = set()
    ids: set[str] = set()
    for item in items:
        item_id = item.attrs.get("id", "")
        href = item.attrs.get("href")
        ids.add(item_id)
        if href is None or "://" in href:
            continue
        href = normalize_href(href)
        hrefs.add(href)
        if href not in pkg.nameset:
            ctx.add("M001", rootfile, item.path("href"), item.line, id=item_id, href=href)
    for name in dict.fromkeys(pkg.names):
        if TRACKED_ENTRY.fullmatch(name) and name not in hrefs:
            ctx.add("M002", rootfile, manifest.path(), manifest.line, part=name)
    for ref in refs:
        idref = ref.attrs.get("idref", "")
        if idref not in ids:
            ctx.add("M003", rootfile, ref.path("idref"), ref.line, idref=idref)
