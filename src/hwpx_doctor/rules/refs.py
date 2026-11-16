"""R001-R003: ID references and itemCnt in header.xml / sections.

The attribute -> definition table below is the only place that decides which
reference attributes are judged. It lists attributes whose target is
unambiguous in OWPML head definitions; anything not listed is never reported
(false positives are worse than misses for a CI gate).
"""

from __future__ import annotations

from ..package import HEADER_PART, Package, is_head_ns
from ..xmltree import Node
from . import Context
from .manifest import manifest_parts

# definition list element -> definition element it contains
DEFINITION_LISTS = {
    "charProperties": "charPr",
    "paraProperties": "paraPr",
    "styles": "style",
    "borderFills": "borderFill",
    "tabProperties": "tabPr",
}

# reference attribute -> definition kind it must resolve to
REF_ATTRS = {
    "charPrIDRef": "charPr",
    "paraPrIDRef": "paraPr",
    "styleIDRef": "style",
    "nextStyleIDRef": "style",
    "borderFillIDRef": "borderFill",
    "tabPrIDRef": "tabPr",
}

BINARY_REF = "binaryItemIDRef"

# 0xFFFFFFFF (unsigned -1) means "no reference" in real documents (seen in python-hwpx output).
NO_REFERENCE = frozenset({"4294967295", "-1"})


def definitions(header: Node) -> dict[str, set[str]]:
    """Defined ids per kind. A kind whose list is absent from the header is omitted."""
    out: dict[str, set[str]] = {}
    for node in header.iter():
        kind = DEFINITION_LISTS.get(node.local)
        if kind and is_head_ns(node.uri):
            ids = out.setdefault(kind, set())
            for child in node.children:
                if child.local == kind and "id" in child.attrs:
                    ids.add(child.attrs["id"])
    return out


def itemcnt_mismatches(header: Node) -> list[tuple[Node, str, int]]:
    """Direct children of ``refList`` whose ``itemCnt`` differs from their child count."""
    out: list[tuple[Node, str, int]] = []
    for ref_list in (n for n in header.iter() if n.local == "refList" and is_head_ns(n.uri)):
        for child in ref_list.children:
            raw = child.attrs.get("itemCnt")
            if raw is not None and raw.strip().isdigit() and int(raw) != len(child.children):
                out.append((child, raw.strip(), len(child.children)))
    return out


def run(pkg: Package, ctx: Context) -> None:
    header = pkg.good_tree(HEADER_PART)
    defined = definitions(header) if header is not None else {}
    parts = manifest_parts(pkg)
    manifest_ids = {i.attrs.get("id", "") for i in parts[2]} if parts else None

    if header is not None:
        for node, declared, actual in itemcnt_mismatches(header):
            ctx.add("R002", HEADER_PART, node.path("itemCnt"), node.line,
                    list=node.qname, declared=declared, actual=actual)

    scanned = ([HEADER_PART] if header is not None else []) + pkg.sections
    for name in dict.fromkeys(scanned):
        root = pkg.good_tree(name)
        if root is None:
            continue
        for node in root.iter():
            for attr, value in node.attrs.items():
                kind = REF_ATTRS.get(attr)
                if kind and kind in defined and value not in defined[kind] and value not in NO_REFERENCE:
                    ctx.add("R001", name, node.path(attr), node.line, attr=attr, value=value, kind=kind)
                elif attr == BINARY_REF and manifest_ids is not None and value not in manifest_ids:
                    ctx.add("R003", name, node.path(attr), node.line, value=value)
