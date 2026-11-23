#!/usr/bin/env python3
"""THE WORLD — Monday 23 November 2026. A one-day newspaper front page.

Stdlib-only deterministic compositor. It pastes the photo panels and
pre-rendered text strips in assets/ onto a 1024x1024 page and writes
$MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).

Every glyph was rendered at build time by build_assets.py (DejaVu
fonts), so this program needs no fonts and no network. Run it twice:
the two files are byte-identical.
"""
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")

WIDTH, HEIGHT = 1024, 1024
PAPER = (247, 242, 231)
CREAM = (242, 236, 220)
INK = (26, 26, 26)
RED = (163, 22, 33)
NAVY = (20, 33, 61)
GREEN = (27, 107, 46)
AMBER = (146, 92, 0)
WHITE = (255, 255, 255)

# Map panel: the raw map is 2240x1120; the panel shows the crop
# (30, 40)-(2210, 824) resized to 500x180 at page position (24, 408).
MAP_POS = (24, 408)
MAP_SIZE = (500, 180)
MAP_CROP = (30, 40, 2210, 824)
MAP_RAW = (2240, 1120)
# (number, place, fx, fy, dx, dy): fractions of the raw map; dx/dy are
# small panel-pixel nudges that keep the Europe/Mediterranean cluster
# readable.
DOTS = [
    (1, "Antalya", 0.527, 0.295, 6, 8),
    (2, "Dymer", 0.520, 0.235, 10, -6),
    (3, "Benghazi", 0.513, 0.335, -4, 8),
    (4, "Bahrain", 0.585, 0.360, 0, 0),
    (5, "Johannesburg", 0.522, 0.571, 0, 0),
    (6, "Delhi", 0.696, 0.321, 0, 0),
    (7, "Seoul", 0.815, 0.290, 0, 0),
    (8, "Khartoum", 0.545, 0.455, 0, 0),
    (9, "Juba", 0.550, 0.490, 0, 0),
    (10, "Hodeida", 0.572, 0.400, 0, 0),
    (11, "Washington", 0.200, 0.300, 0, 0),
    (12, "Banten", 0.768, 0.500, 0, 0),
    (13, "Ramallah", 0.535, 0.320, -10, -2),
]
# Index stories whose confidence dot is green (CONFIRMED); the rest
# are amber (REPORTED).
CONFIRMED_INDEX = frozenset([
    16, 17, 18, 20, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 35,
    36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50,
])
LEFT_OUT_COUNT = 8    # date-check items in the left column of the box
NOT_YET_COUNT = 6     # date-check items in the lower part of the box


# ---------------------------------------------------------------- PNG I/O

def _paeth(left, up, up_left):
    pred = left + up - up_left
    pa, pb, pc = abs(pred - left), abs(pred - up), abs(pred - up_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return up_left


def read_png(path):
    """Decode an 8-bit non-interlaced PNG to (width, height, RGBA)."""
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: " + path)
    pos = 8
    idat = bytearray()
    width = height = None
    bit_depth = colour_type = None
    palette = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        name = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if name == b"IHDR":
            (width, height, bit_depth, colour_type,
             _comp, _filt, interlace) = struct.unpack(">IIBBBBB", chunk)
            if bit_depth != 8 or interlace != 0:
                raise ValueError("unsupported PNG: " + path)
        elif name == b"PLTE":
            palette = chunk
        elif name == b"IDAT":
            idat += chunk
        elif name == b"IEND":
            break
        pos += 12 + length
    if colour_type == 3 and palette is None:
        raise ValueError("palette PNG without PLTE: " + path)
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colour_type]
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    out = bytearray(width * height * 4)
    prev = bytearray(stride)
    p = 0
    for y in range(height):
        filt = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if filt == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif filt == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif filt == 3:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif filt == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(a, b, c)) & 255
        elif filt != 0:
            raise ValueError("bad PNG filter %d in %s" % (filt, path))
        prev = line
        for x in range(width):
            o = (y * width + x) * 4
            s = x * channels
            if colour_type == 6:
                out[o:o + 4] = line[s:s + 4]
            elif colour_type == 2:
                out[o:o + 3] = line[s:s + 3]
                out[o + 3] = 255
            elif colour_type == 0:
                out[o] = out[o + 1] = out[o + 2] = line[s]
                out[o + 3] = 255
            elif colour_type == 4:
                out[o] = out[o + 1] = out[o + 2] = line[s]
                out[o + 3] = line[s + 1]
            else:  # palette
                pi = line[s] * 3
                out[o:o + 3] = palette[pi:pi + 3]
                out[o + 3] = 255
    return width, height, out


def write_png(path, width, height, rgba):
    """Encode RGBA bytes as a deterministic PNG (filter 0, zlib 9)."""
    def chunk(name, payload):
        blob = struct.pack(">I", len(payload)) + name + payload
        return blob + struct.pack(">I", zlib.crc32(name + payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    scan = bytearray()
    stride = width * 4
    for y in range(height):
        scan.append(0)
        scan += rgba[y * stride:(y + 1) * stride]
    blob = b"\x89PNG\r\n\x1a\n"
    blob += chunk(b"IHDR", ihdr)
    blob += chunk(b"IDAT", zlib.compress(bytes(scan), 9))
    blob += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(blob)


# ---------------------------------------------------------------- canvas

class Page:
    """An RGB page buffer with rect, disc, frame and paste helpers."""

    def __init__(self):
        self.buf = bytearray(PAPER) * (WIDTH * HEIGHT)

    def _set(self, x, y, r, g, b):
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            o = (y * WIDTH + x) * 3
            self.buf[o:o + 3] = bytes((r, g, b))

    def fill_rect(self, x, y, w, h, color):
        r, g, b = color
        for yy in range(y, y + h):
            if yy < 0 or yy >= HEIGHT:
                continue
            left = max(x, 0)
            span = min(x + w, WIDTH) - left
            if span > 0:
                base = (yy * WIDTH + left) * 3
                self.buf[base:base + span * 3] = bytes((r, g, b)) * span

    def hline(self, y, color=INK, thick=2):
        self.fill_rect(24, y, WIDTH - 48, thick, color)

    def frame(self, x, y, w, h, color=INK):
        self.fill_rect(x, y, w, 1, color)
        self.fill_rect(x, y + h - 1, w, 1, color)
        self.fill_rect(x, y, 1, h, color)
        self.fill_rect(x + w - 1, y, 1, h, color)

    def disc(self, cx, cy, rad, color, ring=None):
        r, g, b = color
        for dy in range(-rad, rad + 1):
            dx = int((rad * rad - dy * dy) ** 0.5)
            for x in range(cx - dx, cx + dx + 1):
                on_edge = abs(x - cx) >= dx - 1 or abs(dy) >= rad - 1
                if ring is not None and on_edge:
                    self._set(x, cy + dy, *ring)
                else:
                    self._set(x, cy + dy, r, g, b)

    def paste(self, rel, x, y):
        w, h, px = read_png(os.path.join(ROOT, rel))
        for yy in range(h):
            py = y + yy
            if py < 0 or py >= HEIGHT:
                continue
            for xx in range(w):
                pxx = x + xx
                if pxx < 0 or pxx >= WIDTH:
                    continue
                s = (yy * w + xx) * 4
                a = px[s + 3]
                if a == 0:
                    continue
                o = (py * WIDTH + pxx) * 3
                if a == 255:
                    self.buf[o:o + 3] = px[s:s + 3]
                else:
                    for k in range(3):
                        self.buf[o + k] = (px[s + k] * a +
                                           self.buf[o + k] * (255 - a)) // 255

    def text(self, name, x, y):
        self.paste(os.path.join("assets", "text", name), x, y)

    def photo(self, name, x, y):
        self.paste(os.path.join("assets", name), x, y)


# ---------------------------------------------------------------- layout

def build():
    pg = Page()

    # Masthead
    pg.text("mast_date.png", 24, 8)
    pg.text("mast_title.png", 24, 24)
    pg.text("mast_tag.png", 24, 80)
    pg.hline(94)

    # UTC timeline band
    pg.fill_rect(24, 98, 976, 34, NAVY)
    pg.text("tl_label.png", 34, 109)
    for i in range(8):
        row, col = divmod(i, 4)
        pg.text("tl_%d.png" % i, 150 + col * 215, 102 + row * 16)

    # Leads: one wide story on the left, two stacked on the right
    pg.photo("lead1.png", 24, 136)
    pg.frame(24, 136, 500, 140)
    pg.text("lead1_kicker.png", 24, 280)
    pg.text("lead1_head.png", 24, 293)
    pg.text("lead1_deck.png", 24, 337)
    pg.text("lead1_tag.png", 24, 373)
    for n, y0 in ((2, 136), (3, 264)):
        pg.photo("lead%d.png" % n, 536, y0)
        pg.frame(536, y0, 168, 120)
        pg.text("lead%d_kicker.png" % n, 712, y0 + 2)
        pg.text("lead%d_head.png" % n, 712, y0 + 14)
        pg.text("lead%d_deck.png" % n, 712, y0 + 54)
        pg.text("lead%d_tag.png" % n, 712, y0 + 100)
    pg.hline(388)

    # World map + numbered dots
    pg.text("map_title.png", 24, 392)
    pg.photo("map.png", MAP_POS[0], MAP_POS[1])
    pg.frame(MAP_POS[0], MAP_POS[1], MAP_SIZE[0], MAP_SIZE[1])
    cx0, cy0, cx1, cy1 = MAP_CROP
    for _num, _place, fx, fy, dx, dy in DOTS:
        px = int(MAP_POS[0] + (fx * MAP_RAW[0] - cx0) *
                 MAP_SIZE[0] / (cx1 - cx0)) + dx
        py = int(MAP_POS[1] + (fy * MAP_RAW[1] - cy0) *
                 MAP_SIZE[1] / (cy1 - cy0)) + dy
        pg.disc(px, py, 4, RED, ring=WHITE)
    pg.text("map_key.png", 24, 590)

    # Date-check box (right of the map)
    pg.fill_rect(536, 392, 464, 216, CREAM)
    pg.fill_rect(536, 392, 464, 22, INK)
    pg.fill_rect(536, 392, 464, 1, INK)
    pg.fill_rect(536, 607, 464, 1, INK)
    pg.fill_rect(536, 392, 1, 216, INK)
    pg.fill_rect(999, 392, 1, 216, INK)
    pg.text("dc_title.png", 544, 397)
    y = 418
    pg.text("dc_left_h.png", 544, y)
    y += 13
    for i in range(LEFT_OUT_COUNT):
        pg.text("dc_left_%d.png" % i, 544, y)
        y += 11
    pg.text("dc_yet_h.png", 544, y)
    y += 13
    for i in range(NOT_YET_COUNT):
        pg.text("dc_yet_%d.png" % i, 544, y)
        y += 11
    pg.hline(616)

    # Minis: 3 columns x 4 rows
    for i in range(12):
        n = i + 4
        row, col = divmod(i, 3)
        x = 24 + col * 329
        y = 620 + row * 52
        pg.photo("mini%02d.png" % n, x, y)
        pg.frame(x, y, 96, 52)
        pg.text("mini%02d_head.png" % n, x + 104, y)
        pg.text("mini%02d_deck.png" % n, x + 104, y + 30)
        pg.text("mini%02d_kicker.png" % n, x + 104, y + 42)
    pg.hline(832)

    # Index: 3 columns x 12 lines, green/amber confidence dots
    pg.text("idx_title.png", 24, 836)
    for i in range(36):
        num = i + 16
        col, row = divmod(i, 12)
        x = 24 + col * 318
        y = 852 + row * 10
        pg.disc(x + 3, y + 4, 3,
                GREEN if num in CONFIRMED_INDEX else AMBER)
        pg.text("idx_%02d.png" % num, x + 10, y)

    # Markets + footer
    pg.text("markets.png", 24, 976)
    pg.text("footer.png", 24, 994)

    rgba = bytearray(WIDTH * HEIGHT * 4)
    for i in range(WIDTH * HEIGHT):
        rgba[i * 4:i * 4 + 3] = pg.buf[i * 3:i * 3 + 3]
        rgba[i * 4 + 3] = 255
    return rgba


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "entry.png")
    rgba = build()
    write_png(out, WIDTH, HEIGHT, rgba)
    print("wrote %s (%d bytes)" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    main()
