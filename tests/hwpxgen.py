"""Build a minimal valid HWPX and corrupted variants with only the standard library.

The documents are hand-written (no third-party generator, no copied template),
so the test suite has no runtime dependency. ``build("ok")`` is a clean
package; every other variant breaks exactly the rules listed in ``EXPECTED``.
"""

from __future__ import annotations

import io
import zipfile

DATE = (2026, 1, 1, 0, 0, 0)

# variant name -> exact set of rule ids hwpx-doctor must report
EXPECTED: dict[str, set[str]] = {
    "ok": set(),
    "mimetype_not_first": {"C001"},
    "mimetype_deflated": {"C002"},
    "mimetype_wrong": {"C003"},
    "missing_header": {"C004"},
    "malformed": {"X001"},
    "dangling_charpr": {"R001"},
    "itemcnt_wrong": {"R002"},
    "orphan_section": {"M002"},
    "manifest_missing_section": {"M002", "M003"},
}

# prefixes/URIs per namespace flavour; "2016" also renames every prefix to prove URI matching
FLAVOURS = {
    "2011": dict(h="hh", hu="http://www.hancom.co.kr/hwpml/2011/head",
                 s="hs", su="http://www.hancom.co.kr/hwpml/2011/section",
                 p="hp", pu="http://www.hancom.co.kr/hwpml/2011/paragraph", o="opf"),
    "2016": dict(h="h", hu="http://www.hancom.co.kr/hwpml/2016/head",
                 s="s", su="http://www.hancom.co.kr/hwpml/2016/section",
                 p="p", pu="http://www.hancom.co.kr/hwpml/2016/paragraph", o="pkg"),
}


def _header(f: dict[str, str], char_cnt: int = 2) -> str:
    h = f["h"]
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<{h}:head xmlns:{h}="{f['hu']}" version="1.5" secCnt="1">
  <{h}:refList>
    <{h}:fontfaces itemCnt="1">
      <{h}:fontface lang="HANGUL" fontCnt="1">
        <{h}:font id="0" face="Sample Sans" type="TTF" isEmbedded="0"/>
      </{h}:fontface>
    </{h}:fontfaces>
    <{h}:borderFills itemCnt="1">
      <{h}:borderFill id="1" threeD="0" shadow="0"/>
    </{h}:borderFills>
    <{h}:charProperties itemCnt="{char_cnt}">
      <{h}:charPr id="0" height="1000" borderFillIDRef="1"/>
      <{h}:charPr id="1" height="1400" borderFillIDRef="1"/>
    </{h}:charProperties>
    <{h}:tabProperties itemCnt="1">
      <{h}:tabPr id="0" autoTabLeft="0" autoTabRight="0"/>
    </{h}:tabProperties>
    <{h}:paraProperties itemCnt="2">
      <{h}:paraPr id="0" tabPrIDRef="0"/>
      <{h}:paraPr id="1" tabPrIDRef="0"/>
    </{h}:paraProperties>
    <{h}:styles itemCnt="2">
      <{h}:style id="0" name="Normal" paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0"/>
      <{h}:style id="1" name="Title" paraPrIDRef="1" charPrIDRef="1" nextStyleIDRef="0"/>
    </{h}:styles>
  </{h}:refList>
</{h}:head>
"""


def _section(f: dict[str, str], char_ref: str = "0") -> str:
    s, p = f["s"], f["p"]
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<{s}:sec xmlns:{s}="{f['su']}" xmlns:{p}="{f['pu']}">
  <{p}:p id="0" paraPrIDRef="1" styleIDRef="1">
    <{p}:run charPrIDRef="{char_ref}">
      <{p}:t>2026 운영계획</{p}:t>
    </{p}:run>
  </{p}:p>
  <{p}:p id="1" paraPrIDRef="0" styleIDRef="0">
    <{p}:run charPrIDRef="0">
      <{p}:t>추진 배경: 문서 자동화 품질 점검</{p}:t>
    </{p}:run>
  </{p}:p>
</{s}:sec>
"""


def _hpf(f: dict[str, str], with_header: bool = True, with_section0: bool = True) -> str:
    o = f["o"]
    items = ""
    if with_header:
        items += f'\n    <{o}:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
    if with_section0:
        items += f'\n    <{o}:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
    refs = ""
    if with_header:
        refs += f'\n    <{o}:itemref idref="header" linear="yes"/>'
    refs += f'\n    <{o}:itemref idref="section0" linear="yes"/>'
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<{o}:package xmlns:{o}="http://www.idpf.org/2007/opf/" version="" unique-identifier="" id="">
  <{o}:manifest>{items}
  </{o}:manifest>
  <{o}:spine>{refs}
  </{o}:spine>
</{o}:package>
"""


CONTAINER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container">
  <ocf:rootfiles>
    <ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>
  </ocf:rootfiles>
</ocf:container>
"""


def parts_for(variant: str, ns: str = "2011") -> tuple[list[tuple[str, bytes]], bool]:
    """Return ``(ordered parts, deflate_mimetype)`` for a variant."""
    f = FLAVOURS[ns]
    mimetype = b"application/zip" if variant == "mimetype_wrong" else b"application/hwp+zip"
    header = _header(f, char_cnt=7 if variant == "itemcnt_wrong" else 2)
    section = _section(f, char_ref="999" if variant == "dangling_charpr" else "0")
    if variant == "malformed":  # closing tag name differs from the opening tag
        section = section.replace(f"</{f['s']}:sec>", f"</{f['s']}:secX>")
    hpf = _hpf(f, with_header=variant != "missing_header", with_section0=variant != "manifest_missing_section")
    parts: list[tuple[str, bytes]] = [
        ("mimetype", mimetype),
        ("META-INF/container.xml", CONTAINER.encode()),
        ("Contents/content.hpf", hpf.encode()),
    ]
    if variant != "missing_header":
        parts.append(("Contents/header.xml", header.encode()))
    parts.append(("Contents/section0.xml", section.encode()))
    if variant == "orphan_section":
        parts.append(("Contents/section1.xml", section.encode()))
    if variant == "mimetype_not_first":
        parts = parts[1:] + parts[:1]
    return parts, variant == "mimetype_deflated"


def zip_bytes(parts: list[tuple[str, bytes]], deflate_mimetype: bool = False) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in parts:
            info = zipfile.ZipInfo(name, DATE)
            stored = name == "mimetype" and not deflate_mimetype
            info.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
            zf.writestr(info, data)
    return buf.getvalue()


def build(variant: str = "ok", ns: str = "2011") -> bytes:
    """Return the bytes of a package: ``ok`` or one of the keys of ``EXPECTED``."""
    if variant not in EXPECTED:
        raise KeyError(f"unknown variant {variant!r}; choose from {sorted(EXPECTED)}")
    parts, deflate = parts_for(variant, ns)
    return zip_bytes(parts, deflate)
