#!/usr/bin/env python3
"""Generate the CC Decrypter DMG background image."""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path


WIDTH = 680
HEIGHT = 420
SCALE = 3


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _lerp(start: int, end: int, amount: float) -> int:
    return round(start + (end - start) * amount)


def generate(output_path: Path) -> None:
    large_width = WIDTH * SCALE
    large_height = HEIGHT * SCALE
    pixels = bytearray(large_width * large_height * 4)

    def put_pixel(x: int, y: int, red: int, green: int, blue: int) -> None:
        offset = (y * large_width + x) * 4
        pixels[offset : offset + 4] = bytes((red, green, blue, 255))

    def blend_pixel(x: int, y: int, red: int, green: int, blue: int, alpha: int) -> None:
        offset = (y * large_width + x) * 4
        amount = alpha / 255
        pixels[offset] = round(red * amount + pixels[offset] * (1 - amount))
        pixels[offset + 1] = round(green * amount + pixels[offset + 1] * (1 - amount))
        pixels[offset + 2] = round(blue * amount + pixels[offset + 2] * (1 - amount))

    for y in range(large_height):
        yy = y / (large_height - 1)
        for x in range(large_width):
            xx = x / (large_width - 1)
            diagonal = xx * 0.46 + yy * 0.54
            red = _lerp(255, 232, diagonal)
            green = _lerp(255, 236, diagonal)
            blue = _lerp(255, 241, diagonal)

            dx = (xx - 0.50) / 0.58
            dy = (yy - 0.44) / 0.68
            glow = max(0, 1 - (dx * dx + dy * dy))
            red = min(255, red + round(15 * glow))
            green = min(255, green + round(15 * glow))
            blue = min(255, blue + round(15 * glow))
            put_pixel(x, y, red, green, blue)

    for y in range(large_height):
        yy = y / (large_height - 1)
        for x in range(large_width):
            xx = x / (large_width - 1)
            edge = max(abs(xx - 0.5) / 0.5, abs(yy - 0.5) / 0.5)
            if edge > 0.68:
                alpha = round((edge - 0.68) / 0.32 * 42)
                blend_pixel(x, y, 202, 209, 219, alpha)

    downsampled = bytearray(WIDTH * HEIGHT * 4)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            red_sum = green_sum = blue_sum = alpha_sum = 0
            for yy in range(SCALE):
                for xx in range(SCALE):
                    offset = ((y * SCALE + yy) * large_width + (x * SCALE + xx)) * 4
                    red_sum += pixels[offset]
                    green_sum += pixels[offset + 1]
                    blue_sum += pixels[offset + 2]
                    alpha_sum += pixels[offset + 3]

            count = SCALE * SCALE
            offset = (y * WIDTH + x) * 4
            downsampled[offset : offset + 4] = bytes(
                (
                    red_sum // count,
                    green_sum // count,
                    blue_sum // count,
                    alpha_sum // count,
                )
            )

    raw = bytearray()
    for y in range(HEIGHT):
        raw.append(0)
        raw.extend(downsampled[y * WIDTH * 4 : (y + 1) * WIDTH * 4])

    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(png)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: scripts/generate_dmg_background.py <output.png>", file=sys.stderr)
        return 2

    generate(Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
