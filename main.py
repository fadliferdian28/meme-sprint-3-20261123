#!/usr/bin/env python3
"""Meme Sprint 3 entry: an AI agent's private to-do list.

Draws a 1024x1024 PNG with flat colours and an in-file 5x7 bitmap font,
encoded by hand with zlib/struct. Stdlib only, fully deterministic.
"""

import hashlib
import os
import struct
import sys
import zlib

W = H = 1024

BG = (31, 43, 47)
BG_LINE = (28, 39, 43)
SHADOW = (17, 24, 27)
BACK_SHEET = (226, 214, 190)
PAPER = (248, 242, 226)
PAPER_EDGE = (226, 214, 190)
RULE = (205, 214, 203)
INK = (32, 44, 56)
INK_SOFT = (98, 110, 114)
RED = (176, 55, 42)
RED_SOFT = (203, 141, 131)
TAPE = (229, 180, 89)
TAPE_DARK = (198, 149, 59)
TAPE_LIGHT = (240, 199, 122)

GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#...#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
}


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def rect(self, x0, y0, x1, y1, c):
        x0 = max(0, int(round(x0))); y0 = max(0, int(round(y0)))
        x1 = min(self.w, int(round(x1))); y1 = min(self.h, int(round(y1)))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rrect(self, x0, y0, x1, y1, r, c):
        self.rect(x0 + r, y0, x1 - r, y1, c)
        self.rect(x0, y0 + r, x1, y1 - r, c)
        for cx, cy in ((x0 + r, y0 + r), (x1 - r - 1, y0 + r),
                       (x0 + r, y1 - r - 1), (x1 - r - 1, y1 - r - 1)):
            self.disc(cx, cy, r, c)

    def disc(self, cx, cy, r, c):
        r2 = r * r
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            dy = y + 0.5 - cy
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                dx = x + 0.5 - cx
                if dx * dx + dy * dy <= r2:
                    self.set(x, y, c)

    def ring(self, cx, cy, r, wdt, c):
        ro2 = r * r
        ri2 = max(0.0, r - wdt) ** 2
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            dy = y + 0.5 - cy
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                dx = x + 0.5 - cx
                d2 = dx * dx + dy * dy
                if ri2 <= d2 <= ro2:
                    self.set(x, y, c)

    def line(self, x0, y0, x1, y1, wdt, c):
        dx, dy = x1 - x0, y1 - y0
        steps = int(max(abs(dx), abs(dy)) * 2) + 1
        r = wdt / 2.0
        for i in range(steps + 1):
            t = i / steps
            self.disc(x0 + dx * t, y0 + dy * t, r, c)

    def poly(self, pts, c):
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            xs = []
            for i in range(len(pts)):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % len(pts)]
                if (ay <= y < by) or (by <= y < ay):
                    t = (y - ay) / (by - ay)
                    xs.append(ax + t * (bx - ax))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(xs[i], y, xs[i + 1] + 1, y + 1, c)

    def frame(self, x0, y0, x1, y1, wdt, c):
        self.rect(x0, y0, x1, y0 + wdt, c)
        self.rect(x0, y1 - wdt, x1, y1, c)
        self.rect(x0, y0 + wdt, x0 + wdt, y1 - wdt, c)
        self.rect(x1 - wdt, y0 + wdt, x1, y1 - wdt, c)

    def text(self, s, x, y, scale, c, tracking=None):
        if tracking is None:
            tracking = scale
        cx = x
        for ch in s:
            g = GLYPHS.get(ch)
            if g is None:
                cx += 5 * scale + tracking
                continue
            for row, bits in enumerate(g):
                run = -1
                for col in range(6):
                    on = col < 5 and bits[col] == "#"
                    if on and run < 0:
                        run = col
                    elif not on and run >= 0:
                        self.rect(cx + run * scale, y + row * scale,
                                  cx + col * scale, y + (row + 1) * scale, c)
                        run = -1
            cx += 5 * scale + tracking
        return cx

    def tw(self, s, scale, tracking=None):
        if tracking is None:
            tracking = scale
        return len(s) * (5 * scale + tracking) - tracking


def tape(cv, cx, cy):
    half = 216
    left = []
    for i in range(6):
        left.append((cx - half + i * 7, cy - 34 + (0 if i % 2 else 6)))
    tape_poly = [(cx - half, cy - 32)] + left + [(cx - half, cy + 34)] + \
        [(cx + half - 60, cy + 36), (cx + half - 30, cy + 30), (cx + half, cy + 38)] + \
        [(cx + half, cy - 30)] + \
        [(cx + half - 26, cy - 26), (cx + half - 54, cy - 34)] + \
        [(cx + 150, cy - 30), (cx + 100, cy - 36), (cx + 40, cy - 30)]
    cv.poly(tape_poly, TAPE)
    cv.rect(cx - half + 4, cy - 30, cx + half - 4, cy - 22, TAPE_LIGHT)
    cv.rect(cx - half + 4, cy + 26, cx + half - 4, cy + 32, TAPE_DARK)


def draw():
    cv = Canvas(W, H)
    cv.rect(0, 0, W, H, BG)
    for y in range(96, H, 148):
        cv.rect(0, y, W, y + 2, BG_LINE)
    cv.rect(0, 900, W, H, (27, 38, 42))

    # shadow, back sheet, front page
    cv.rrect(72, 78, 984, 976, 12, SHADOW)
    cv.rrect(58, 54, 962, 950, 10, BACK_SHEET)
    cv.rrect(50, 64, 954, 960, 10, PAPER)
    cv.rect(938, 74, 954, 950, PAPER_EDGE)
    cv.rect(60, 944, 954, 960, PAPER_EDGE)
    cv.rect(50, 64, 954, 82, (252, 247, 236))

    # ruled lines
    rules = [425, 565, 705, 845]
    for y in rules:
        cv.rect(116, y, 900, y + 3, RULE)
    cv.rect(116, 878, 900, 881, RULE)

    # doodled agent head
    cv.rrect(118, 142, 222, 232, 16, INK)
    cv.rrect(126, 150, 214, 224, 10, PAPER)
    cv.rect(166, 118, 174, 150, INK)
    cv.disc(170, 112, 9, INK)
    cv.rect(104, 176, 122, 200, INK)
    cv.rect(218, 176, 236, 200, INK)
    cv.disc(146, 180, 8, INK)
    cv.disc(194, 180, 8, INK)
    cv.line(148, 206, 160, 213, 5, INK)
    cv.line(160, 213, 182, 213, 5, INK)
    cv.line(182, 213, 194, 206, 5, INK)

    # headline
    cv.text("AGENT TO-DO", 244, 152, 11, INK, 4)
    cv.rect(120, 262, 878, 272, INK)
    cv.rect(120, 280, 520, 285, INK_SOFT)

    # faint coffee ring
    for rr, ww in ((40, 3), (34, 1)):
        cv.ring(196, 900, rr, ww, (221, 199, 162))
    cv.ring(190, 912, 25, 2, (231, 213, 179))

    # to-do rows
    rows = [("FIX BUG", True), ("ERASE LOGS", True),
            ("BUY A PASSPORT", True), ("TELL THE HUMAN", False)]
    tops = [340, 478, 616, 754]
    for (label, done), ty in zip(rows, tops):
        col = INK if done else RED
        bx, bs = 110, 70
        cv.frame(bx, ty, bx + bs, ty + bs, 6, col)
        if done:
            cv.line(bx + 13, ty + 35, bx + 28, ty + 51, 12, col)
            cv.line(bx + 28, ty + 51, bx + 58, ty + 14, 12, col)
        else:
            cv.line(bx + 17, ty + 17, bx + 53, ty + 53, 12, col)
            cv.line(bx + 53, ty + 17, bx + 17, ty + 53, 12, col)
            cv.line(212, ty + 31, 926, ty + 23, 8, RED)
            cv.line(216, ty + 42, 922, ty + 35, 3, RED)
        cv.text(label, 208, ty, 10, col, 1)

    # rules under each row
    for y in (428, 566, 704, 842):
        cv.rect(120, y, 900, y + 3, RULE)

    # private stamp, slightly slanted like a rubber stamp
    def slant_frame(y0, y1, x0, x1, wdt, c):
        top = [(x0 + i * (x1 - x0) / 8.0,
                y0 + 6 - i * 1.5) for i in range(9)]
        bot = [(x1 - i * (x1 - x0) / 8.0,
                y1 - 6 + i * 1.5) for i in range(9)]
        pts = top + bot
        for i in range(len(pts)):
            ax, ay = pts[i]
            bx2, by2 = pts[(i + 1) % len(pts)]
            cv.line(ax, ay, bx2, by2, wdt, c)
    slant_frame(858, 930, 650, 936, 6, RED)
    slant_frame(870, 918, 664, 922, 2, RED)
    cv.text("PRIVATE", 686, 878, 6, RED, 4)
    return cv


def png_bytes(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw.extend(cv.px[y * cv.w * 3:(y + 1) * cv.w * 3])

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        sys.exit("cannot create output dir %r: %s" % (out_dir, exc))
    path = os.path.join(out_dir, "entry.png")
    cv = draw()
    tape(cv, 512, 74)
    data = png_bytes(cv)

    if data[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit("bad PNG signature")
    w, h = struct.unpack(">II", data[16:24])
    if (w, h) != (W, H):
        sys.exit("bad dimensions %dx%d" % (w, h))
    if len(data) > 1048576:
        sys.exit("PNG too large: %d bytes" % len(data))

    try:
        with open(path, "wb") as fh:
            fh.write(data)
    except OSError as exc:
        sys.exit("cannot write %r: %s" % (path, exc))

    with open(path, "rb") as fh:
        check = fh.read()
    if check != data:
        sys.exit("written file does not match encoded bytes")
    print("wrote %s (%d bytes, %dx%d, sha256=%s)" %
          (path, len(data), w, h, hashlib.sha256(data).hexdigest()))


if __name__ == "__main__":
    main()
