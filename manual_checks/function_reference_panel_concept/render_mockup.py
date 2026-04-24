from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "editor_function_reference_panel_concept.png"

WIDTH = 1600
HEIGHT = 980


FONT_5X7 = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00100", "00100"),
    ",": ("00000", "00000", "00000", "00000", "00100", "00100", "01000"),
    ":": ("00000", "00100", "00100", "00000", "00100", "00100", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "=": ("00000", "01110", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "/": ("00001", "00010", "00100", "01000", "10000", "00000", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
}


def rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


class Canvas:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 3)

    def set_pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        index = (y * self.width + x) * 3
        self.pixels[index:index + 3] = bytes(color)

    def blend_pixel(self, x: int, y: int, color: tuple[int, int, int], alpha: float) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        index = (y * self.width + x) * 3
        existing = self.pixels[index:index + 3]
        blended = [
            int(existing[i] * (1.0 - alpha) + color[i] * alpha)
            for i in range(3)
        ]
        self.pixels[index:index + 3] = bytes(blended)

    def fill_rect(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        row = bytes(color) * max(0, x1 - x0)
        for yy in range(y0, y1):
            start = (yy * self.width + x0) * 3
            end = start + len(row)
            self.pixels[start:end] = row

    def stroke_rect(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int], thickness: int = 1) -> None:
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int], thickness: int = 1) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.fill_rect(x0 - thickness // 2, y0 - thickness // 2, thickness, thickness, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def draw_circle(self, cx: int, cy: int, radius: int, color: tuple[int, int, int], fill: bool = False) -> None:
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                dist = math.hypot(x - cx, y - cy)
                if fill:
                    if dist <= radius:
                        self.set_pixel(x, y, color)
                else:
                    if radius - 1.2 <= dist <= radius + 0.4:
                        self.set_pixel(x, y, color)

    def draw_text(
        self,
        text: str,
        x: int,
        y: int,
        color: tuple[int, int, int],
        scale: int = 3,
        tracking: int = 1,
    ) -> None:
        cursor_x = x
        for char in text.upper():
            glyph = FONT_5X7.get(char, FONT_5X7[" "])
            for row_index, row in enumerate(glyph):
                for col_index, bit in enumerate(row):
                    if bit != "1":
                        continue
                    self.fill_rect(
                        cursor_x + col_index * scale,
                        y + row_index * scale,
                        scale,
                        scale,
                        color,
                    )
            cursor_x += (5 + tracking) * scale

    def save_png(self, path: Path) -> None:
        raw = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            raw.append(0)
            start = y * stride
            raw.extend(self.pixels[start:start + stride])

        compressed = zlib.compress(bytes(raw), level=9)

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + tag
                + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            )

        png = bytearray(b"\x89PNG\r\n\x1a\n")
        png.extend(
            chunk(
                b"IHDR",
                struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0),
            )
        )
        png.extend(chunk(b"IDAT", compressed))
        png.extend(chunk(b"IEND", b""))
        path.write_bytes(png)


def draw_gradient_background(canvas: Canvas, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    for y in range(canvas.height):
        t = y / max(1, canvas.height - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        canvas.fill_rect(0, y, canvas.width, 1, color)


def add_background_pattern(canvas: Canvas) -> None:
    dot = rgb("#A8B5C6")
    for y in range(40, canvas.height, 48):
        for x in range(44, canvas.width, 48):
            canvas.blend_pixel(x, y, dot, 0.10)


def draw_panel_block(
    canvas: Canvas,
    x: int,
    y: int,
    w: int,
    h: int,
    title: str,
    body_lines: list[str],
    *,
    accent: tuple[int, int, int],
    fill: tuple[int, int, int],
    title_color: tuple[int, int, int],
    body_color: tuple[int, int, int],
) -> None:
    canvas.fill_rect(x + 8, y + 10, w, h, rgb("#D9E2EC"))
    canvas.fill_rect(x, y, w, h, fill)
    canvas.stroke_rect(x, y, w, h, rgb("#D6DEE7"), 2)
    canvas.fill_rect(x, y, 10, h, accent)
    canvas.draw_text(title, x + 26, y + 18, title_color, scale=3, tracking=1)

    body_y = y + 56
    for line in body_lines:
        canvas.draw_text(line, x + 26, body_y, body_color, scale=2, tracking=1)
        body_y += 24


def main() -> None:
    slate_900 = rgb("#0F172A")
    slate_800 = rgb("#16233A")
    slate_700 = rgb("#23324A")
    ink = rgb("#EAF0F6")
    soft_ink = rgb("#BFCADA")
    paper = rgb("#F8F5EE")
    paper_shadow = rgb("#E4DDD1")
    line = rgb("#D9DEE7")
    dark_text = rgb("#162033")
    muted_text = rgb("#586174")
    blue = rgb("#3B82F6")
    teal = rgb("#14B8A6")
    orange = rgb("#F97316")
    green = rgb("#22C55E")
    yellow = rgb("#FACC15")
    red = rgb("#FB7185")

    canvas = Canvas(WIDTH, HEIGHT)
    draw_gradient_background(canvas, rgb("#E8EDF3"), rgb("#DDE6F0"))
    add_background_pattern(canvas)

    canvas.fill_rect(84, 72, 1432, 828, rgb("#CBD5E1"))
    canvas.fill_rect(64, 52, 1432, 828, rgb("#F5F7FB"))
    canvas.stroke_rect(64, 52, 1432, 828, rgb("#C9D4E3"), 3)

    canvas.draw_text("RIGHT SIDE FUNCTION REFERENCE PANEL", 92, 84, dark_text, scale=4, tracking=1)
    canvas.draw_text("EDITOR FIRST, DOCS ALWAYS VISIBLE", 94, 126, muted_text, scale=2, tracking=1)

    editor_x, editor_y, editor_w, editor_h = 102, 172, 930, 660
    panel_x, panel_y, panel_w, panel_h = 1064, 172, 384, 660

    canvas.fill_rect(editor_x + 10, editor_y + 14, editor_w, editor_h, rgb("#0B1220"))
    canvas.fill_rect(editor_x, editor_y, editor_w, editor_h, slate_900)
    canvas.stroke_rect(editor_x, editor_y, editor_w, editor_h, rgb("#243246"), 2)

    canvas.fill_rect(editor_x, editor_y, editor_w, 56, slate_800)
    canvas.draw_text("MAIN SCRIPT", editor_x + 24, editor_y + 18, ink, scale=3, tracking=1)
    canvas.draw_text("LIVE PREVIEW", editor_x + 610, editor_y + 18, soft_ink, scale=2, tracking=1)

    gutter_x = editor_x + 18
    code_x = editor_x + 84
    for offset in range(0, 540, 48):
        canvas.draw_line(editor_x, editor_y + 92 + offset, editor_x + editor_w, editor_y + 92 + offset, slate_700, 1)

    canvas.fill_rect(editor_x + 18, editor_y + 186, editor_w - 36, 56, rgb("#12243D"))
    canvas.fill_rect(editor_x + 12, editor_y + 186, 8, 56, blue)
    canvas.stroke_rect(editor_x + 18, editor_y + 186, editor_w - 36, 56, rgb("#27456C"), 1)

    code_lines = [
        ("1", "DEF MAIN():", soft_ink),
        ("2", "SET TCP(P[0,0,0.12,0,0,0])", soft_ink),
        ("3", "MOVEL(..., A=0.5, V=0.05)", ink),
        ("4", "TARGET = POSE TRANS(FEATURE, LOCAL TARGET)", soft_ink),
        ("5", "TEXTMSG(DONE)", soft_ink),
    ]

    y = editor_y + 106
    for number, content, color in code_lines:
        canvas.draw_text(number, gutter_x, y, rgb("#64748B"), scale=2, tracking=1)
        canvas.draw_text(content, code_x, y, color, scale=2, tracking=1)
        y += 48

    canvas.fill_rect(editor_x + 110, editor_y + 206, 338, 12, rgb("#1E3A5F"))
    canvas.fill_rect(editor_x + 656, editor_y + 206, 76, 12, blue)
    canvas.fill_rect(editor_x + 790, editor_y + 206, 76, 12, teal)

    canvas.draw_circle(editor_x + 720, editor_y + 212, 22, yellow, fill=False)
    canvas.draw_line(editor_x + 742, editor_y + 212, panel_x - 34, panel_y + 300, yellow, 3)
    canvas.draw_circle(panel_x - 34, panel_y + 300, 8, yellow, fill=True)

    canvas.fill_rect(panel_x + 10, panel_y + 14, panel_w, panel_h, paper_shadow)
    canvas.fill_rect(panel_x, panel_y, panel_w, panel_h, paper)
    canvas.stroke_rect(panel_x, panel_y, panel_w, panel_h, rgb("#D7D1C6"), 2)
    canvas.fill_rect(panel_x, panel_y, panel_w, 62, rgb("#F1ECE2"))
    canvas.fill_rect(panel_x, panel_y, 12, panel_h, orange)
    canvas.draw_text("FUNCTION REFERENCE", panel_x + 28, panel_y + 18, dark_text, scale=3, tracking=1)
    canvas.draw_text("FOLLOWS CURSOR", panel_x + 30, panel_y + 42, muted_text, scale=2, tracking=1)

    draw_panel_block(
        canvas,
        panel_x + 24,
        panel_y + 86,
        panel_w - 48,
        104,
        "SYMBOL",
        ["MOVEL", "MOTION COMMAND"],
        accent=blue,
        fill=rgb("#FFFFFF"),
        title_color=dark_text,
        body_color=muted_text,
    )
    draw_panel_block(
        canvas,
        panel_x + 24,
        panel_y + 210,
        panel_w - 48,
        128,
        "SIGNATURE",
        ["MOVEL(POSE, A=1.2,", "V=0.25, T=0, R=0)"],
        accent=teal,
        fill=rgb("#FFFFFF"),
        title_color=dark_text,
        body_color=dark_text,
    )
    draw_panel_block(
        canvas,
        panel_x + 24,
        panel_y + 358,
        panel_w - 48,
        128,
        "CURRENT ARG",
        ["A", "CARTESIAN ACCEL", "DEFAULT 1.2"],
        accent=yellow,
        fill=rgb("#FFFBEA"),
        title_color=dark_text,
        body_color=dark_text,
    )
    draw_panel_block(
        canvas,
        panel_x + 24,
        panel_y + 506,
        panel_w - 48,
        120,
        "NOTES",
        ["POSE IS AXIS ANGLE", "T OVERRIDES SPEED PLAN"],
        accent=red,
        fill=rgb("#FFF7F7"),
        title_color=dark_text,
        body_color=dark_text,
    )

    draw_panel_block(
        canvas,
        panel_x + 24,
        panel_y + 634,
        panel_w - 48,
        78,
        "RELATED",
        ["MOVEJ   MOVEP   MOVEC"],
        accent=green,
        fill=rgb("#F5FFF9"),
        title_color=dark_text,
        body_color=dark_text,
    )

    canvas.fill_rect(64, 880, 1432, 18, slate_700)
    canvas.fill_rect(64, 898, 1432, 26, slate_900)
    canvas.draw_text("STATUS  MOVEL  ARG 2  A", 88, 904, soft_ink, scale=2, tracking=1)
    canvas.draw_text("SYSTEM STATUS STAYS BELOW", 1184, 904, soft_ink, scale=2, tracking=1)

    canvas.save_png(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
