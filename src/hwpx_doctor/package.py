"""Read an HWPX package (a ZIP) without extracting it to disk."""

from __future__ import annotations

import io
import os
import re
import zipfile
from pathlib import Path

from . import xmltree
from .i18n import t
from .model import InputError
from .xmltree import Node, XmlError

MAX_UNCOMPRESSED_MIB = 200
HEADER_PART = "Contents/header.xml"
CONTAINER_PART = "META-INF/container.xml"
DEFAULT_ROOTFILE = "Contents/content.hpf"
SECTION_RE = re.compile(r"Contents/section\d+\.xml")
XML_SUFFIXES = (".xml", ".hpf", ".rdf")


def is_head_ns(uri: str) -> bool:
    """OWPML head namespaces differ by year (2011, 2016, owpml.org); match the tail."""
    return uri.endswith("/head")


def is_opf_ns(uri: str) -> bool:
    return uri.rstrip("/") == "http://www.idpf.org/2007/opf"


def read_source(source: str | os.PathLike[str] | bytes, lang: str = "en") -> tuple[str, bytes]:
    """Return ``(display name, bytes)`` for a path or raw bytes."""
    if isinstance(source, (bytes, bytearray)):
        return "<bytes>", bytes(source)
    path = Path(source)
    if not path.exists():
        raise InputError(t(lang, "err.not_found", path=str(path)))
    if not path.is_file():
        raise InputError(t(lang, "err.not_file", path=str(path)))
    try:
        return str(path), path.read_bytes()
    except OSError as exc:
        raise InputError(t(lang, "err.read", path=str(path), detail=exc.strerror or str(exc))) from exc


class Package:
    """Entries of the ZIP in their original order plus lazily parsed XML parts."""

    def __init__(self, raw: bytes, label: str = "<bytes>", lang: str = "en") -> None:
        self.label = label
        self.zf = zipfile.ZipFile(io.BytesIO(raw))  # raises BadZipFile for non-ZIP input
        self.infos = self.zf.infolist()
        total = sum(i.file_size for i in self.infos)
        if total > MAX_UNCOMPRESSED_MIB * 1024 * 1024:
            raise InputError(t(lang, "err.too_large", limit=MAX_UNCOMPRESSED_MIB, path=label))
        self.names = [i.filename for i in self.infos]
        self.nameset = set(self.names)
        self._trees: dict[str, Node | XmlError] = {}

    def read(self, name: str) -> bytes:
        return self.zf.read(name)

    def tree(self, name: str) -> Node | XmlError | None:
        """Parsed root node, an :class:`XmlError`, or None if the entry does not exist."""
        if name not in self.nameset:
            return None
        if name not in self._trees:
            try:
                self._trees[name] = xmltree.parse(self.read(name))
            except XmlError as exc:
                self._trees[name] = exc
            except Exception as exc:  # unreadable entry: bad CRC, unsupported compression, ...
                self._trees[name] = XmlError(f"{type(exc).__name__}: {exc}", None)
        return self._trees[name]

    def good_tree(self, name: str) -> Node | None:
        tree = self.tree(name)
        return tree if isinstance(tree, Node) else None

    @property
    def rootfile(self) -> str:
        """Package document named by container.xml (default ``Contents/content.hpf``)."""
        root = self.good_tree(CONTAINER_PART)
        if root is not None:
            files = [n for n in root.iter() if n.local == "rootfile" and n.attrs.get("full-path")]
            for node in files:
                if node.attrs.get("media-type") == "application/hwpml-package+xml":
                    return node.attrs["full-path"]
            if files:
                return files[0].attrs["full-path"]
        return DEFAULT_ROOTFILE

    @property
    def sections(self) -> list[str]:
        return [n for n in self.names if SECTION_RE.fullmatch(n)]
