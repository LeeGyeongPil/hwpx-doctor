"""C001-C005: ZIP container rules."""

from __future__ import annotations

import zipfile
from collections import Counter

from ..package import CONTAINER_PART, HEADER_PART, Package
from . import Context

MIMETYPE = "mimetype"
EXPECTED_MIMETYPE = b"application/hwp+zip"


def run(pkg: Package, ctx: Context) -> None:
    for name, count in Counter(pkg.names).items():
        if count > 1:
            ctx.add("C005", name, name=name)

    if not pkg.names or pkg.names[0] != MIMETYPE:
        ctx.add("C001", MIMETYPE, first=pkg.names[0] if pkg.names else "")

    if MIMETYPE in pkg.nameset:
        info = pkg.zf.getinfo(MIMETYPE)
        if info.compress_type != zipfile.ZIP_STORED:
            ctx.add("C002", MIMETYPE, method=info.compress_type)
        content = pkg.read(MIMETYPE)
        if content != EXPECTED_MIMETYPE:
            ctx.add("C003", MIMETYPE, content=content[:40].decode("utf-8", "replace"))

    required = [CONTAINER_PART, pkg.rootfile, HEADER_PART]
    for part in required:
        if part not in pkg.nameset:
            ctx.add("C004", part, part=part)
    if not pkg.sections:
        ctx.add("C004", "Contents/section0.xml", part="Contents/section*.xml")
