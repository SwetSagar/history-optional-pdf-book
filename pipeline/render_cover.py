"""Generate a high-DPI Modernist book cover image (1600x2400 px) for the eBook.

    python3 pipeline/render_cover.py

Creates `build/cover.png` with clean serif/sans typography, graticule lines,
and red-on-white cartographic aesthetic specified in DESIGN_SYSTEM.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from fonts import find_font  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "cover.png"

WIDTH, HEIGHT = 1600, 2400
BG_RGB = (255, 255, 255)
TEXT_MAIN = (26, 26, 26)
TEXT_MUTED = (85, 85, 85)
ACCENT_RED = (176, 42, 34)
LINE_LIGHT = (226, 226, 226)


def font_or_default(name: str, size: int):
    return find_font(name, size)


def strapline() -> str:
    """Derived from the records, so the cover cannot outlive its own numbers."""
    sites = json.loads((ROOT / "data" / "sites.json").read_text(encoding="utf-8"))
    n = sum(1 for s in sites if s.get("coords"))
    chapters = len({p.parent.name for p in (ROOT / "sites").rglob("*.md")})
    return f"{n} SITES  ·  {chapters} CHAPTERS  ·  CITED BY CHAPTER"


def main() -> int:
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_RGB)
    draw = ImageDraw.Draw(im)

    # 1. Subtle Cartographic Graticule Background Grid
    for x in range(100, WIDTH, 150):
        draw.line([(x, 100), (x, HEIGHT - 100)], fill=LINE_LIGHT, width=2)
    for y in range(100, HEIGHT, 150):
        draw.line([(100, y), (WIDTH - 100, y)], fill=LINE_LIGHT, width=2)

    # Outer Neatline Border
    draw.rectangle([80, 80, WIDTH - 80, HEIGHT - 80], outline=TEXT_MAIN, width=6)
    draw.rectangle([92, 92, WIDTH - 92, HEIGHT - 92], outline=ACCENT_RED, width=2)

    # Load Fonts
    font_title = font_or_default("Georgia", 92)
    font_sub = font_or_default("Helvetica", 42)
    font_author = font_or_default("Helvetica", 48)
    font_meta = font_or_default("Helvetica", 32)

    # 2. Header Accent Bar
    draw.rectangle([140, 180, WIDTH - 140, 196], fill=ACCENT_RED)

    # 3. Main Title & Subtitle (Flush Left Margin)
    x_margin = 140
    y = 280

    title_lines = ["Map Entries for", "History Optional"]
    for line in title_lines:
        draw.text((x_margin, y), line, fill=TEXT_MAIN, font=font_title)
        y += 115

    y += 40
    draw.line([(x_margin, y), (x_margin + 240, y)], fill=ACCENT_RED, width=8)
    y += 60

    sub_lines = [
        "A referenced atlas of the sites in the",
        "UPSC History Optional map question"
    ]
    for line in sub_lines:
        draw.text((x_margin, y), line, fill=TEXT_MUTED, font=font_sub)
        y += 55

    # 4. Central Decorative Compass / Graticule Motif
    cx, cy = WIDTH // 2, HEIGHT // 2 + 100
    r = 220
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT_RED, width=3)
    draw.ellipse([cx - r + 30, cy - r + 30, cx + r - 30, cy + r - 30], outline=TEXT_MAIN, width=1)
    draw.line([(cx - r - 40, cy), (cx + r + 40, cy)], fill=ACCENT_RED, width=2)
    draw.line([(cx, cy - r - 40), (cx, cy + r + 40)], fill=ACCENT_RED, width=2)
    draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=ACCENT_RED)

    # 5. Author & Edition Footer
    y_footer = HEIGHT - 360
    draw.line([(x_margin, y_footer), (WIDTH - x_margin, y_footer)], fill=LINE_LIGHT, width=2)

    y_footer += 50
    draw.text((x_margin, y_footer), "SWET SAGAR", fill=TEXT_MAIN, font=font_author)

    y_footer += 75
    draw.text((x_margin, y_footer), strapline(), fill=TEXT_MUTED, font=font_meta)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, quality=95)
    print(f"cover rendered : {OUT}  ({OUT.stat().st_size / 1e3:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
