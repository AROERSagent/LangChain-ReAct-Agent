# -*- coding: utf-8 -*-
"""生成中文 PDF：手写 PDF 1.4 + 嵌入微软雅黑子集，只用标准库。

为什么不用 reportlab：机器上没有，而手写 PDF 的骨架也就几百行，
还能精确控制字形子集，产物体积小、文字可复制可检索。
"""
import re
import struct
import sys
import unicodedata
from pathlib import Path

FONT_REG = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")

PAGE_W, PAGE_H = 595.2756, 841.8898
MARGIN_X = 36.85
RIGHT_EDGE = 558.4
TEXT_W = RIGHT_EDGE - MARGIN_X

C_MAIN = (0.0784, 0.3137, 0.5490)
C_ACCENT = (0.1843, 0.4941, 0.8471)
C_BODY = (0.2, 0.2, 0.2)
C_GRAY = (0.35, 0.35, 0.35)


# ==================== TrueType 子集化 ====================

def read_ttc_tables(path: Path, index: int = 0) -> dict:
    data = path.read_bytes()
    if data[:4] == b"ttcf":
        num = struct.unpack(">I", data[8:12])[0]
        offs = struct.unpack(f">{num}I", data[12:12 + 4 * num])
        start = offs[index]
    else:
        start = 0
    n = struct.unpack(">H", data[start + 4:start + 6])[0]
    tables = {}
    for i in range(n):
        rec = start + 12 + 16 * i
        tag = data[rec:rec + 4]
        off, length = struct.unpack(">II", data[rec + 8:rec + 16])
        tables[tag] = data[off:off + length]
    return tables


def parse_cmap(tables: dict) -> dict:
    cmap = tables[b"cmap"]
    count = struct.unpack(">H", cmap[2:4])[0]
    best = None
    for i in range(count):
        pid, eid, off = struct.unpack(">HHI", cmap[4 + 8 * i:4 + 8 * i + 8])
        if (pid, eid) in ((3, 1), (0, 3), (0, 4), (3, 10)):
            fmt = struct.unpack(">H", cmap[off:off + 2])[0]
            score = {4: 1, 12: 2}.get(fmt, 0)
            if score and (best is None or score > best[0]):
                best = (score, off, fmt)
    mapping = {}
    if not best:
        return mapping
    _, off, fmt = best

    if fmt == 4:
        seg_x2 = struct.unpack(">H", cmap[off + 6:off + 8])[0]
        seg = seg_x2 // 2
        ends = struct.unpack(f">{seg}H", cmap[off + 14:off + 14 + seg_x2])
        p = off + 16 + seg_x2
        starts = struct.unpack(f">{seg}H", cmap[p:p + seg_x2])
        p += seg_x2
        deltas = struct.unpack(f">{seg}h", cmap[p:p + seg_x2])
        p += seg_x2
        ro_base = p
        ranges = struct.unpack(f">{seg}H", cmap[p:p + seg_x2])
        for i in range(seg):
            for c in range(starts[i], ends[i] + 1):
                if c == 0xFFFF:
                    continue
                if ranges[i] == 0:
                    gid = (c + deltas[i]) & 0xFFFF
                else:
                    gp = ro_base + i * 2 + ranges[i] + (c - starts[i]) * 2
                    if gp + 2 > len(cmap):
                        continue
                    gid = struct.unpack(">H", cmap[gp:gp + 2])[0]
                    if gid:
                        gid = (gid + deltas[i]) & 0xFFFF
                if gid:
                    mapping.setdefault(c, gid)
    elif fmt == 12:
        ngroups = struct.unpack(">I", cmap[off + 12:off + 16])[0]
        for i in range(ngroups):
            g = off + 16 + 12 * i
            sc, ec, sg = struct.unpack(">III", cmap[g:g + 12])
            for c in range(sc, min(ec, 0x10FFFF) + 1):
                mapping.setdefault(c, sg + (c - sc))
    return mapping


def parse_advances(tables: dict) -> list:
    num = struct.unpack(">H", tables[b"hhea"][34:36])[0]
    hmtx = tables[b"hmtx"]
    return [struct.unpack(">H", hmtx[4 * i:4 * i + 2])[0] for i in range(num)]


def build_cmap_format4(pairs: list) -> bytes:
    segs = []
    for u, g in pairs:
        if segs and u == segs[-1][1] + 1 and g == segs[-1][2] + (u - segs[-1][0]):
            segs[-1][1] = u
        else:
            segs.append([u, u, g])
    segs.append([0xFFFF, 0xFFFF, 0])

    n = len(segs)
    pow2 = 2 ** (n.bit_length() - 1)
    sel = pow2.bit_length() - 1

    body = bytearray()
    body += struct.pack(">HHHH", n * 2, pow2 * 2, sel, n * 2 - pow2 * 2)
    body += b"".join(struct.pack(">H", s[1]) for s in segs)
    body += b"\0\0"
    body += b"".join(struct.pack(">H", s[0]) for s in segs)
    body += b"".join(struct.pack(">H", (s[2] - s[0]) & 0xFFFF) for s in segs)
    body += b"\0\0" * n

    sub = bytearray(struct.pack(">HHH", 4, 0, 0)) + body
    struct.pack_into(">H", sub, 2, len(sub))

    return struct.pack(">HHHHI", 0, 1, 3, 1, 12) + bytes(sub)


def checksum(blob: bytes) -> int:
    blob = blob + b"\0" * ((-len(blob)) % 4)
    return sum(struct.unpack(f">{len(blob) // 4}I", blob)) & 0xFFFFFFFF


def serialize_sfnt(tables: dict) -> bytes:
    tags = sorted(tables)
    n = len(tags)
    pow2 = 2 ** (n.bit_length() - 1)
    head = struct.pack(">IHHHH", 0x00010000, n, pow2 * 16,
                       pow2.bit_length() - 1, n * 16 - pow2 * 16)
    offset = 12 + 16 * n
    dirs, bodies = b"", b""
    for tag in tags:
        blob = tables[tag]
        pad = (-len(blob)) % 4
        dirs += tag + struct.pack(">III", checksum(blob), offset, len(blob))
        bodies += blob + b"\0" * pad
        offset += len(blob) + pad
    return head + dirs + bodies


class Font:
    def __init__(self, path: Path, name: str):
        self.name = name
        self.tables = read_ttc_tables(path)
        self.cmap = parse_cmap(self.tables)
        self.advances = parse_advances(self.tables)
        self.units = struct.unpack(">H", self.tables[b"head"][18:20])[0]
        self.used = {}

    def use(self, text: str):
        for ch in text:
            u = ord(ch)
            if u not in self.used:
                gid = self.cmap.get(u)
                if gid:
                    self.used[u] = gid

    def advance(self, ch: str) -> int:
        gid = self.cmap.get(ord(ch))
        if not gid:
            return self.units // 2
        return self.advances[min(gid, len(self.advances) - 1)]

    def width(self, text: str, size: float) -> float:
        return sum(self.advance(c) for c in text) / self.units * size

    def subset(self) -> tuple:
        tables = self.tables
        num_glyphs = struct.unpack(">H", tables[b"maxp"][4:6])[0]
        loca_fmt = struct.unpack(">h", tables[b"head"][50:52])[0]
        raw = tables[b"loca"]
        if loca_fmt == 0:
            loca = [v * 2 for v in struct.unpack(f">{num_glyphs + 1}H", raw[:2 * (num_glyphs + 1)])]
        else:
            loca = list(struct.unpack(f">{num_glyphs + 1}I", raw[:4 * (num_glyphs + 1)]))

        order = [0] + [g for g in dict.fromkeys(self.used.values()) if g != 0]
        remap = {old: new for new, old in enumerate(order)}

        glyf = tables[b"glyf"]
        new_glyf = bytearray()
        new_loca = [0]
        for old in order:
            new_glyf += glyf[loca[old]:loca[old + 1]]
            while len(new_glyf) % 4:
                new_glyf += b"\0"
            new_loca.append(len(new_glyf))

        new_hmtx = bytearray()
        for old in order:
            gid = min(old, len(self.advances) - 1)
            new_hmtx += struct.pack(">Hh", self.advances[gid], 0)

        new_head = bytearray(tables[b"head"])
        struct.pack_into(">H", new_head, 50, 1)
        new_maxp = bytearray(tables[b"maxp"])
        struct.pack_into(">H", new_maxp, 4, len(order))
        new_hhea = bytearray(tables[b"hhea"])
        struct.pack_into(">H", new_hhea, 34, len(order))

        pairs = sorted((u, remap[g]) for u, g in self.used.items() if g in remap)
        out = {
            b"head": bytes(new_head),
            b"hhea": bytes(new_hhea),
            b"maxp": bytes(new_maxp),
            b"hmtx": bytes(new_hmtx),
            b"loca": b"".join(struct.pack(">I", v) for v in new_loca),
            b"glyf": bytes(new_glyf),
            b"cmap": build_cmap_format4(pairs),
        }
        for tag in (b"cvt ", b"fpgm", b"prep", b"name", b"post", b"OS/2"):
            if tag in tables:
                out[tag] = tables[tag]

        self.new_gid = {u: remap[g] for u, g in self.used.items()}
        return serialize_sfnt(out)


# ==================== PDF 写出 ====================

class PDF:
    def __init__(self):
        self.fonts = []
        self.ops = []
        self.pages = []
        self.texts = []
        self.images = []

    def image(self, x, y, w, h, jpeg_bytes: bytes, px_w: int, px_h: int, name: str):
        """放置一张 JPEG：DCTDecode 直接内嵌原始数据，不做重编码。"""
        self.images.append((name, jpeg_bytes, px_w, px_h))
        self.ops.append(f"q\n{w:.3f} 0 0 {h:.3f} {x:.3f} {y:.3f} cm\n/{name} Do\nQ\n")

    def text(self, x, y, s, font, size, color, right=None):
        if not s:
            return x
        if right is not None:
            x = right - font.width(s, size)
        w = font.width(s, size)
        font.use(s)
        r, g, b = color
        # 用 Unicode 码点书写，save() 时再换成子集字形编号
        hexed = "".join(f"{ord(c):04X}" for c in s)
        marker = f"@{len(self.texts)}@"
        self.texts.append((font, s))
        self.ops.append(
            f"BT\n1 0 0 1 {x:.3f} {y:.3f} Tm\n/{font.name} {size} Tf\n"
            f"{r:.4f} {g:.4f} {b:.4f} rg\n<{marker}> Tj\nET\n"
        )
        return x + w

    def rect(self, x, y, w, h, color):
        r, g, b = color
        self.ops.append(f"{r:.4f} {g:.4f} {b:.4f} rg {x:.3f} {y:.3f} {w:.3f} {h:.3f} re f\n")

    def page_break(self):
        self.pages.append("".join(self.ops))
        self.ops = []

    def save(self, path: Path):
        if self.ops:
            self.pages.append("".join(self.ops))
            self.ops = []

        objs = []

        def add(blob: bytes) -> int:
            objs.append(blob)
            return len(objs)

        # 图片：JPEG 原始流直接内嵌
        image_refs = {}
        for name, data, px_w, px_h in self.images:
            image_refs[name] = add((
                f"<< /Type /XObject /Subtype /Image /Width {px_w} /Height {px_h} "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                f"/Length {len(data)} >>\nstream\n"
            ).encode() + data + b"\nendstream")

        font_refs = {}
        for font in self.fonts:
            data = font.subset()
            ffile = add(b"<< /Length %d /Length1 %d >>\nstream\n" % (len(data), len(data))
                        + data + b"\nendstream")
            descriptor = add((
                f"<< /Type /FontDescriptor /FontName /{font.name}-Subset /Flags 4 "
                f"/FontBBox [0 -300 1200 950] /ItalicAngle 0 /Ascent 950 /Descent -300 "
                f"/CapHeight 700 /StemV 80 /FontFile2 {ffile} 0 R >>"
            ).encode())
            widths = b"[" + b" ".join(
                b"%d [%d]" % (g, round(font.advance(chr(u)) / font.units * 1000))
                for u, g in sorted(font.new_gid.items())) + b"]"
            cid = add((
                f"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /{font.name}-Subset "
                f"/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
                f"/FontDescriptor {descriptor} 0 R /DW 1000 /W {widths.decode()} "
                f"/CIDToGIDMap /Identity >>"
            ).encode())
            tu_data = self._tounicode(font)
            tu = add(b"<< /Length %d >>\nstream\n" % len(tu_data) + tu_data + b"\nendstream")
            font_refs[font.name] = add((
                f"<< /Type /Font /Subtype /Type0 /BaseFont /{font.name}-Subset "
                f"/Encoding /Identity-H /DescendantFonts [{cid} 0 R] /ToUnicode {tu} 0 R >>"
            ).encode())

        xobj = ""
        if image_refs:
            xobj = "/XObject << " + " ".join(f"/{n} {o} 0 R" for n, o in image_refs.items()) + " >> "

        page_objs = []
        for content in self.pages:
            content = self._resolve(content)
            data = content.encode("latin-1")
            cid = add(b"<< /Length %d >>\nstream\n" % len(data) + data + b"\nendstream")
            page_objs.append(add((
                f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {PAGE_W:.4f} {PAGE_H:.4f}] "
                f"/Contents {cid} 0 R /Resources << /Font << "
                + " ".join(f"/{n} {o} 0 R" for n, o in font_refs.items())
                + " >> " + xobj + ">> >>"
            ).encode()))

        pages_num = add(("<< /Type /Pages /Kids ["
                         + " ".join(f"{p} 0 R" for p in page_objs)
                         + f"] /Count {len(page_objs)} >>").encode())
        for p in page_objs:
            objs[p - 1] = objs[p - 1].replace(b"/Parent 0 0 R", b"/Parent %d 0 R" % pages_num)
        catalog = add(f"<< /Type /Catalog /Pages {pages_num} 0 R >>".encode())

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, blob in enumerate(objs):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % (i + 1) + blob + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        for off in offsets:
            out += b"%010d 00000 n \n" % off
        out += (b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
                % (len(objs) + 1, catalog, xref))
        path.write_bytes(bytes(out))

    def _resolve(self, content: str) -> str:
        """把 @n@ 占位换成子集后的字形编号。"""
        def repl(m):
            font, s = self.texts[int(m.group(1))]
            return "".join(f"{font.new_gid[ord(c)]:04X}" for c in s)
        return re.sub(r"@(\d+)@", repl, content)

    @staticmethod
    def _tounicode(font: Font) -> bytes:
        lines = [
            "/CIDInit /ProcSet findresource begin",
            "12 dict begin",
            "begincmap",
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
            "/CMapName /Adobe-Identity-UCS def",
            "/CMapType 2 def",
            "1 begincodespacerange",
            "<0000> <FFFF>",
            "endcodespacerange",
        ]
        pairs = sorted(font.new_gid.items(), key=lambda kv: kv[1])
        for i in range(0, len(pairs), 100):
            chunk = pairs[i:i + 100]
            lines.append(f"{len(chunk)} beginbfchar")
            lines += [f"<{g:04X}> <{u:04X}>" for u, g in chunk]
            lines.append("endbfchar")
        lines += ["endcmap", "CMapName currentdict /CMap defineresource pop", "end", "end"]
        return "\n".join(lines).encode("ascii")
