"""X001: XML well-formedness."""

from __future__ import annotations

from ..package import XML_SUFFIXES, Package
from ..xmltree import XmlError
from . import Context


def run(pkg: Package, ctx: Context) -> None:
    for name in dict.fromkeys(pkg.names):
        if name.endswith(XML_SUFFIXES):
            tree = pkg.tree(name)
            if isinstance(tree, XmlError):
                ctx.add("X001", name, "", tree.line, detail=tree.message)
