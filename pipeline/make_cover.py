"""Generate the eBook cover.

    python3 pipeline/make_cover.py [--show]

KDP will not accept a book without a cover, and Books and Kindle fall back to a
grey placeholder when the EPUB declares none.

The artwork is the book's own data: every located site plotted at once. It says
what the book contains without a word of marketing, and it regenerates as the
data changes. Output is 1600x2560 — KDP's recommended eBook size and ratio.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from render_maps import BASEMAP, CROP, INK_THRESHOLD, to_pixel  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "cover.png"

W, H = 1600, 2560
INK = (18, 22, 26)
PAPER = (243, 241, 236)
DOT = (176, 42, 34)
RULE = (150, 146, 138)

TITLE = "Map Entries"
TITLE2 = "for History Optional"
SUBTITLE = "A referenced atlas of the sites in the\nUPSC History Optional map question"
AUTHOR = "Swet Sagar"

FONTS = {
    "serif": ["/System/Library/Fonts/Supplemental/Baskerville.ttc",
              "/System/Library/Fonts/Palatino.ttc",
              "/System/Library/Fonts/Supplemental/Georgia.ttf"],
    "sans": ["/System/Library/Fonts/Supplemental/Futura.ttc",
             "/System/Library/Fonts/Helvetica.ttc",
             "/System/Library/Fonts/Supplemental/Georgia.ttf"],
}


def font(kind: str, size: int, index: int = 0):
    for path in FONTS[kind]:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size, index=index)
            except Exception:
                continue
    return ImageFont.load_default()


def map_layer(width: int) -> Image.Image:
    """The outline with every located site marked, as a transparent overlay."""
    src = Image.open(BASEMAP).convert("L")
    arr = np.asarray(src).astype(np.uint8)
    bw = np.where(arr < INK_THRESHOLD, 0, 255).astype(np.uint8)

    scale = 4
    big = Image.fromarray(bw).resize((src.width * scale, src.height * scale), Image.LANCZOS)
    big = big.point(lambda p: 0 if p < 165 else 255).convert("L")

    canvas = Image.new("RGBA", big.size, (0, 0, 0, 0))
    # ink where the outline is, transparent elsewhere
    mask = big.point(lambda p: 255 if p < 128 else 0)
    canvas.paste(Image.new("RGBA", big.size, INK + (255,)), (0, 0), mask)

    d = ImageDraw.Draw(canvas)
    sites = json.loads((ROOT / "data" / "sites.json").read_text(encoding="utf-8"))
    plotted = 0
    for s in sites:
        if not s.get("coords"):
            continue
        px, py = to_pixel(s["coords"][0], s["coords"][1])
        x, y = px * scale, py * scale
        r = 9
        d.ellipse([x - r, y - r, x + r, y + r], fill=DOT + (235,))
        plotted += 1

    canvas = canvas.crop(tuple(c * scale for c in CROP))
    w, h = canvas.size
    canvas = canvas.resize((width, round(h * width / w)), Image.LANCZOS)
    print(f"  sites plotted on cover: {plotted}")
    return canvas


def centred(d: ImageDraw.ImageDraw, y: int, text: str, f, fill, spacing: int = 0):
    for line in text.split("\n"):
        w = d.textbbox((0, 0), line, font=f)[2]
        d.text(((W - w) // 2, y), line, font=f, fill=fill)
        y += (f.size + spacing) if hasattr(f, "size") else 40
    return y


def main() -> int:
    cover = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(cover)

    # --- type block, top third ---
    d.line([(180, 300), (W - 180, 300)], fill=INK, width=5)
    centred(d, 340, "UPSC CIVIL SERVICES  ·  HISTORY OPTIONAL", font("sans", 42), RULE)

    f_title = font("serif", 175, index=1)
    y = centred(d, 430, TITLE, f_title, INK, spacing=-14)
    centred(d, y, TITLE2, font("serif", 118, index=1), INK)

    centred(d, 800, SUBTITLE, font("serif", 52, index=2), (86, 84, 80), spacing=18)

    n = sum(1 for s in json.loads((ROOT / "data" / "sites.json").read_text(encoding="utf-8"))
            if s.get("coords"))
    centred(d, 960, f"{n} SITES  ·  25 CHAPTERS", font("sans", 40), RULE)

    # --- map, occupying the lower half only, so no type sits over it ---
    MAP_TOP, MAP_BOTTOM = 1070, H - 330
    layer = map_layer(int(W * 0.78))
    if layer.size[1] > MAP_BOTTOM - MAP_TOP:            # fit to the free band
        s = (MAP_BOTTOM - MAP_TOP) / layer.size[1]
        layer = layer.resize((int(layer.size[0] * s), MAP_BOTTOM - MAP_TOP), Image.LANCZOS)
    alpha = layer.split()[3].point(lambda p: int(p * 0.62))
    layer.putalpha(alpha)
    cover.paste(layer, ((W - layer.size[0]) // 2, MAP_TOP), layer)

    d.line([(180, H - 250), (W - 180, H - 250)], fill=INK, width=3)
    centred(d, H - 195, AUTHOR, font("serif", 62, index=1), INK)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    cover.save(OUT, optimize=True)
    print(f"  cover: {OUT.relative_to(ROOT)}  {cover.size[0]}x{cover.size[1]}  "
          f"{OUT.stat().st_size/1e6:.2f} MB")
    if "--show" in sys.argv:
        cover.copy().resize((W // 3, H // 3)).save(OUT.with_name("cover_preview.png"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
