#!/usr/bin/env python3
"""THE WORLD -- Monday 23 November 2026.

A deterministic compositor for the make.fun news-image-20261123 entry.
It lays pre-rendered photo panels and text strips from assets/ onto a
1024x1024 newspaper front page and writes the result as a PNG.

Standard library only, no network, no timestamps: two runs of this file
produce byte-identical output.

Layout (all coordinates measured from the approved design):
  masthead  -- THE WORLD, Monday 23 November 2026, with a counts tagline
  timeline  -- a navy UTC strip with 8 timed events of the day
  leads     -- 3 lead stories with photos (COP31, Dymer, Merkury)
  map       -- world map with 13 numbered dots + printed key
  date check -- the audit: 8 stories LEFT OUT, 6 NOT YET
  minis     -- 12 illustrated stories in a 3 x 4 grid
  index     -- the rest of the day: 36 one-line stories, 16..51
  markets + footer
"""

import os
import struct
import zlib

# ---------------------------------------------------------------------------
# Page and palette
# ---------------------------------------------------------------------------

PAGE_W = 1024
PAGE_H = 1024

PAPER = (247, 242, 231)    # page background
INK = (26, 26, 26)        # rules, borders, title band
NAVY = (20, 33, 61)       # UTC timeline band
BOX_BG = (242, 236, 220)  # DATE CHECK panel background
MAP_RED = (163, 22, 33)   # numbered dots on the world map
DOT_GREEN = (27, 107, 46)   # CONFIRMED index dot
DOT_AMBER = (146, 92, 0)    # REPORTED index dot

# Encoder settings (fixed, so the output is deterministic).
PNG_FILTER = 0
ZLIB_LEVEL = 9

# A dot is a filled disc of radius 3.5 px: a pixel belongs to it when the
# squared distance from the centre is under 3.5**2.
DOT_R2 = 12.25


# ---------------------------------------------------------------------------
# Minimal PNG codec (8-bit, colour types 2 and 6, non-interlaced)
# ---------------------------------------------------------------------------

def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png(path):
    """Decode a PNG. Returns (width, height, channels, pixels).

    Pixels is a bytearray of raw channel bytes, row-major, filter bytes
    removed. Only 8-bit non-interlaced RGB and RGBA files are supported,
    which covers every asset this entry ships.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    pos = 8
    width = height = bit_depth = colour = interlace = None
    idat = bytearray()
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if ctype == b"IHDR":
            width, height, bit_depth, colour, _cm, _fm, interlace = (
                struct.unpack(">IIBBBBB", chunk))
        elif ctype == b"IDAT":
            idat += chunk
        elif ctype == b"IEND":
            break
        pos += 12 + length
    if bit_depth != 8 or interlace != 0:
        raise ValueError(
            "unsupported PNG %s (depth %s, interlace %s)"
            % (path, bit_depth, interlace))
    if colour == 2:
        channels = 3
    elif colour == 6:
        channels = 4
    else:
        raise ValueError(
            "unsupported colour type %s in %s" % (colour, path))
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    pixels = bytearray(width * height * channels)
    prev = bytearray(stride)
    off = 0
    for y in range(height):
        ftype = raw[off]
        line = bytearray(raw[off + 1:off + 1 + stride])
        off += 1 + stride
        if ftype == 0:
            pass
        elif ftype == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(a, b, c)) & 0xFF
        else:
            raise ValueError("bad filter %d in %s" % (ftype, path))
        pixels[y * stride:(y + 1) * stride] = line
        prev = line
    return width, height, channels, pixels


def _chunk(ctype, cdata):
    crc = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
    return struct.pack(">I", len(cdata)) + ctype + cdata + struct.pack(">I", crc)


def encode_png(width, height, rgb):
    """Encode 24-bit RGB pixels as a PNG with a fixed filter and level."""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(PNG_FILTER)
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), ZLIB_LEVEL))
        + _chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

class Page:
    """A 1024x1024 RGB canvas backed by a bytearray."""

    def __init__(self):
        self.pixels = bytearray(PAGE_W * PAGE_H * 3)
        self.fill(PAPER)

    def fill(self, colour):
        r, g, b = colour
        self.pixels[:] = bytes((r, g, b)) * (PAGE_W * PAGE_H)

    def rect(self, x, y, w, h, colour):
        """Solid rectangle."""
        r, g, b = colour
        row = bytes((r, g, b)) * w
        for yy in range(y, y + h):
            off = (yy * PAGE_W + x) * 3
            self.pixels[off:off + w * 3] = row

    def paste(self, img, dx, dy):
        """Paste an opaque RGB image at (dx, dy)."""
        w, h, _ch, px = img
        stride = w * 3
        for yy in range(h):
            src = yy * stride
            dst = ((dy + yy) * PAGE_W + dx) * 3
            self.pixels[dst:dst + stride] = px[src:src + stride]

    def paste_alpha(self, img, dx, dy):
        """Paste an RGBA strip, alpha-blending it over the page.

        Only the strip's ink bounding box is walked, so the mostly
        transparent strips stay cheap.
        """
        w, h, _ch, px = img
        min_x, max_x, min_y, max_y = w, -1, h, -1
        for yy in range(h):
            row = yy * w * 4
            for xx in range(w):
                if px[row + xx * 4 + 3]:
                    if xx < min_x:
                        min_x = xx
                    if xx > max_x:
                        max_x = xx
                    if yy < min_y:
                        min_y = yy
                    if yy > max_y:
                        max_y = yy
        if max_x < 0:
            return
        for yy in range(min_y, max_y + 1):
            for xx in range(min_x, max_x + 1):
                base = (yy * w + xx) * 4
                a = px[base + 3]
                if a == 0:
                    continue
                off = ((dy + yy) * PAGE_W + dx + xx) * 3
                if a == 255:
                    self.pixels[off:off + 3] = px[base:base + 3]
                else:
                    # Round to nearest (the +127): this is the blend the
                    # reference render uses, verified on 828 edge pixels.
                    ia = 255 - a
                    for c in range(3):
                        s = px[base + c]
                        d = self.pixels[off + c]
                        self.pixels[off + c] = (s * a + d * ia + 127) // 255

    def disc(self, cx, cy, colour, r2=DOT_R2):
        """Filled disc (map dots and index dots).

        A pixel belongs to the disc when the squared distance from the
        centre is under r2: 12.25 for the 3.5 px dots, 18.5 for the white
        halo drawn behind the dots on the map.
        """
        r, g, b = colour
        rad = int(r2 ** 0.5)
        for dy in range(-rad, rad + 1):
            half = 0
            while (half + 1) * (half + 1) + dy * dy < r2:
                half += 1
            yy = cy + dy
            off = (yy * PAGE_W + cx - half) * 3
            self.pixels[off:off + (2 * half + 1) * 3] = (
                bytes((r, g, b)) * (2 * half + 1))


# ---------------------------------------------------------------------------
# Layout data
# ---------------------------------------------------------------------------

BASE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    return decode_png(os.path.join(BASE, "assets", name))


def _load_text(name):
    return decode_png(os.path.join(BASE, "assets", "text", name))


# World-map dots: (story number, centre x, centre y), measured on the page.
MAP_DOTS = [
    (1, 293, 482), (2, 294, 453), (3, 276, 492), (4, 317, 491),
    (5, 285, 545), (6, 374, 481), (7, 435, 473), (8, 297, 515),
    (9, 299, 524), (10, 310, 501), (11, 119, 475), (12, 411, 527),
    (13, 281, 479),
]

# Index confidence flags for stories 16..51, in order:
# C = CONFIRMED (green dot), R = REPORTED (amber dot).
INDEX_FLAGS = "CCCRCRRCCCCCCCCCCRCCCCCCCCCCCRCCCCCR"

# Mini grid: 3 columns x 4 rows. Photo 96x52; text starts 8 px right of it.
MINI_COLS_X = (24, 353, 682)
MINI_ROWS_Y = (620, 672, 724, 776)

# Index grid: 3 columns of 12, pitch 10 px down, 318 px across.
INDEX_COLS_X = (34, 352, 670)
INDEX_FIRST_Y = 852
INDEX_PITCH_Y = 10


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def build_page():
    """Compose the front page and return the finished PNG bytes."""
    page = Page()

    # --- horizontal rules: 2 px, ink, full content width ----------------
    for rule_y in (94, 388, 616, 832):
        page.rect(24, rule_y, 976, 2, INK)

    # --- masthead ---------------------------------------------------------
    page.paste_alpha(_load_text("mast_date.png"), 24, 8)
    page.paste_alpha(_load_text("mast_title.png"), 24, 24)
    page.paste_alpha(_load_text("mast_tag.png"), 24, 80)

    # --- UTC timeline band ------------------------------------------------
    page.rect(24, 98, 976, 34, NAVY)
    page.paste_alpha(_load_text("tl_label.png"), 34, 109)
    tl_xy = [(150, 102), (365, 102), (580, 102), (795, 102),
             (150, 118), (365, 118), (580, 118), (795, 118)]
    for i, (tx, ty) in enumerate(tl_xy):
        page.paste_alpha(_load_text("tl_%d.png" % i), tx, ty)

    # --- lead story 1 (left column, photo on top) -------------------------
    page.paste(_load("lead1.png"), 24, 136)
    page.paste_alpha(_load_text("lead1_kicker.png"), 24, 280)
    page.paste_alpha(_load_text("lead1_head.png"), 24, 293)
    page.paste_alpha(_load_text("lead1_deck.png"), 24, 337)
    page.paste_alpha(_load_text("lead1_tag.png"), 24, 373)

    # --- lead stories 2 and 3 (right column, photo left, text right) ------
    for n, photo_y in ((2, 136), (3, 264)):
        page.paste(_load("lead%d.png" % n), 536, photo_y)
        page.paste_alpha(_load_text("lead%d_kicker.png" % n), 712, photo_y + 2)
        page.paste_alpha(_load_text("lead%d_head.png" % n), 712, photo_y + 14)
        page.paste_alpha(_load_text("lead%d_deck.png" % n), 712, photo_y + 54)
        page.paste_alpha(_load_text("lead%d_tag.png" % n), 712, photo_y + 100)

    # --- world map ---------------------------------------------------------
    page.paste_alpha(_load_text("map_title.png"), 24, 392)
    page.paste(_load("map.png"), 24, 408)
    for _n, dx, dy in MAP_DOTS:
        page.disc(dx, dy, (255, 255, 255), r2=18.5)
        page.disc(dx, dy, MAP_RED)
    page.paste_alpha(_load_text("map_key.png"), 24, 590)

    # --- DATE CHECK panel (right of the map) ------------------------------
    page.rect(537, 414, 462, 193, BOX_BG)
    page.rect(536, 392, 464, 22, INK)
    page.rect(536, 392, 1, 216, INK)
    page.rect(999, 392, 1, 216, INK)
    page.rect(536, 607, 464, 1, INK)
    page.paste_alpha(_load_text("dc_title.png"), 544, 397)
    page.paste_alpha(_load_text("dc_left_h.png"), 544, 418)
    for i in range(8):
        page.paste_alpha(_load_text("dc_left_%d.png" % i), 544, 431 + 11 * i)
    page.paste_alpha(_load_text("dc_yet_h.png"), 544, 519)
    for i in range(6):
        page.paste_alpha(_load_text("dc_yet_%d.png" % i), 544, 532 + 11 * i)

    # --- 12 minis -----------------------------------------------------------
    for row, my in enumerate(MINI_ROWS_Y):
        for col, mx in enumerate(MINI_COLS_X):
            n = 4 + col + 3 * row
            page.paste(_load("mini%02d.png" % n), mx, my)
            tx = mx + 104
            page.paste_alpha(_load_text("mini%02d_head.png" % n), tx, my)
            page.paste_alpha(_load_text("mini%02d_deck.png" % n), tx, my + 30)
            page.paste_alpha(_load_text("mini%02d_kicker.png" % n), tx, my + 42)

    # --- the rest of the day: index 16..51 ---------------------------------
    page.paste_alpha(_load_text("idx_title.png"), 24, 836)
    for col, ix in enumerate(INDEX_COLS_X):
        for row in range(12):
            n = 16 + col * 12 + row
            iy = INDEX_FIRST_Y + INDEX_PITCH_Y * row
            flag = INDEX_FLAGS[n - 16]
            dot = DOT_GREEN if flag == "C" else DOT_AMBER
            page.disc(ix - 7, iy + 4, dot)
            page.paste_alpha(_load_text("idx_%d.png" % n), ix, iy)

    # --- markets strip and footer -------------------------------------------
    page.paste_alpha(_load_text("markets.png"), 24, 976)
    page.paste_alpha(_load_text("footer.png"), 24, 994)

    return encode_png(PAGE_W, PAGE_H, page.pixels)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "entry.png"), "wb") as fh:
        fh.write(build_page())


if __name__ == "__main__":
    main()
