"""A small expat based tree that remembers what ElementTree throws away.

For every element we keep: namespace URI, local name, the original prefix,
the line number, and byte offsets of the start tag and end tag. Lines feed
``part:line`` locations; byte offsets let the fixer patch a document without
re-serialising it (re-serialising would rewrite namespace prefixes).
"""

from __future__ import annotations

from collections.abc import Iterator
from xml.parsers import expat


class XmlError(Exception):
    """The part is not well-formed XML."""

    def __init__(self, message: str, line: int | None) -> None:
        super().__init__(message)
        self.message = message
        self.line = line


class Node:
    __slots__ = ("uri", "local", "prefix", "attrs", "line", "start", "end", "parent", "children", "index")

    def __init__(self, uri: str, local: str, prefix: str, attrs: dict[str, str], line: int, start: int,
                 parent: Node | None, index: int) -> None:
        self.uri = uri
        self.local = local
        self.prefix = prefix
        self.attrs = attrs  # local attribute name -> value (first one wins)
        self.line = line
        self.start = start  # byte offset of '<' of the start tag
        self.end = start  # byte offset of '</' of the end tag (== start for <a/>)
        self.parent = parent
        self.children: list[Node] = []
        self.index = index  # 1-based position among same-named siblings

    @property
    def qname(self) -> str:
        return f"{self.prefix}:{self.local}" if self.prefix else self.local

    @property
    def self_closing(self) -> bool:
        return self.end == self.start

    def path(self, attr: str | None = None) -> str:
        """``/hs:sec/hp:p[2]/hp:run[1]`` (+ ``/@attr``); original prefixes."""
        parts: list[str] = []
        node: Node | None = self
        while node is not None:
            parts.append(node.qname if node.parent is None else f"{node.qname}[{node.index}]")
            node = node.parent
        text = "/" + "/".join(reversed(parts))
        return f"{text}/@{attr}" if attr else text

    def iter(self) -> Iterator[Node]:
        """Depth-first, document order; iterative so deep nesting cannot hit the recursion limit."""
        stack: list[Node] = [self]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))


def _split(name: str) -> tuple[str, str, str]:
    parts = name.split(" ")
    if len(parts) == 1:
        return "", parts[0], ""
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], parts[1], parts[2]


def parse(data: bytes) -> Node:
    """Parse ``data`` into a :class:`Node` tree or raise :class:`XmlError`."""
    parser = expat.ParserCreate(namespace_separator=" ")
    parser.namespace_prefixes = True
    parser.buffer_text = False
    stack: list[Node] = []
    counters: list[dict[tuple[str, str], int]] = []
    root: list[Node] = []

    def on_start(name: str, attributes: dict[str, str]) -> None:
        uri, local, prefix = _split(name)
        attrs: dict[str, str] = {}
        for key, value in attributes.items():
            attrs.setdefault(_split(key)[1], value)
        parent = stack[-1] if stack else None
        counts = counters[-1] if counters else {}
        counts[(uri, local)] = counts.get((uri, local), 0) + 1
        node = Node(uri, local, prefix, attrs, parser.CurrentLineNumber, parser.CurrentByteIndex,
                    parent, counts[(uri, local)])
        if parent is not None:
            parent.children.append(node)
        else:
            root.append(node)
        stack.append(node)
        counters.append({})

    def on_end(name: str) -> None:
        node = stack.pop()
        counters.pop()
        node.end = parser.CurrentByteIndex

    parser.StartElementHandler = on_start
    parser.EndElementHandler = on_end
    try:
        parser.Parse(data, True)
    except expat.ExpatError as exc:
        raise XmlError(expat.ErrorString(exc.code), exc.lineno) from exc
    except ValueError as exc:
        # expat cannot read multi-byte declared encodings (e.g. EUC-KR); the XML may be fine.
        if "multi-byte" in str(exc):
            raise XmlError("unsupported encoding declaration (expat reads only UTF-8/16 and "
                           "single-byte encodings); save this part as UTF-8", None) from exc
        raise
    if not root:
        raise XmlError("no root element", None)
    return root[0]


def start_tag_end(data: bytes, start: int) -> int:
    """Return the offset just past the ``>`` that closes the start tag at ``start``."""
    quote = 0
    i = start
    while i < len(data):
        ch = data[i]
        if quote:
            if ch == quote:
                quote = 0
        elif ch in (0x22, 0x27):
            quote = ch
        elif ch == 0x3E:
            return i + 1
        i += 1
    return len(data)
