"""Render one clean locator map per site from its coordinate.

    python3 pipeline/render_maps.py [--force]

The base map is currently derived from the scanned exam sheet: thresholded to
pure black-and-white to kill the scan grey, then resampled. That is good enough
to read a proof on a device, and it is a large improvement on the raw scans.

It is NOT what should ship. Before publication the base map must be redrawn
from open geodata, for two reasons: the scan is an exam answer sheet and carries
its furniture ('DO NOT write your Roll No.'), and a published map of India must
depict boundaries as officially defined. BASEMAP below is the single seam where
that swap happens — everything downstream works off coordinates, so replacing it
re-renders all 439 maps with no other change.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from dots import FRAME_X, FRAME_Y, LAT_ANCHOR_DEG, LAT_ANCHOR_PX, LAT_DEG_PER_PX, LON_RANGE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASEMAP = ROOT / "Individual Map sites History Optional" / "Use this copy.jpg"
OUT = ROOT / "build" / "maps"

SCALE = 2                     # 598x774 -> 1196x1548 before cropping
TARGET_W = 900                # full-bleed on a tablet without going soft
INK_THRESHOLD = 170
DOT_RGB = (176, 42, 34)
# Crop to the region the sites actually occupy (dots span x 58-460, y 140-556)
# plus a margin. This drops the exam header, the roll-number notice and the
# printed scale bar — none of which belong in a published book — and removes
# empty ocean that was making every map needlessly tall on the page.
# Sri Lanka's southern tip ends at y~580 and the printed scale bar begins at
# y=585, so 583 keeps every site and drops the exam furniture. Left and top sit
# just inside the neat-line (x=31.5, y=102.6) so no frame remnant survives.
CROP = (34, 107, 505, 583)


def to_pixel(lat: float, lon: float) -> tuple[float, float]:
    """Inverse of dots.to_lonlat — degrees back to blank-sheet pixels."""
    x0, x1 = FRAME_X
    x = x0 + (lon - LON_RANGE[0]) * (x1 - x0) / (LON_RANGE[1] - LON_RANGE[0])
    y = LAT_ANCHOR_PX + (LAT_ANCHOR_DEG - lat) / LAT_DEG_PER_PX
    return x, y


def base_image() -> Image.Image:
    src = Image.open(BASEMAP).convert("L")
    arr = np.asarray(src).astype(np.uint8)
    bw = np.where(arr < INK_THRESHOLD, 0, 255).astype(np.uint8)
    im = Image.fromarray(bw).resize((src.width * SCALE, src.height * SCALE), Image.LANCZOS)
    return im.point(lambda p: 0 if p < 160 else 255).convert("RGB")


def render(base: Image.Image, lat: float, lon: float) -> Image.Image:
    im = base.copy()
    d = ImageDraw.Draw(im)
    px, py = to_pixel(lat, lon)
    x, y = px * SCALE, py * SCALE
    r = 7
    # white halo keeps the dot legible where it lands on a boundary line
    d.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3], fill=(255, 255, 255))
    d.ellipse([x - r, y - r, x + r, y + r], fill=DOT_RGB)
    im = im.crop(tuple(c * SCALE for c in CROP))
    w, h = im.size
    im = im.resize((TARGET_W, round(h * TARGET_W / w)), Image.LANCZOS)
    return im.quantize(colors=16, method=Image.MEDIANCUT)


def main() -> int:
    force = "--force" in sys.argv
    sites = json.loads((ROOT / "data" / "sites.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    base = base_image()

    made = skipped = 0
    for s in sites:
        if not s["coords"]:
            continue
        dest = OUT / f"{s['slug']}.png"
        if dest.exists() and not force:
            skipped += 1
            continue
        render(base, s["coords"][0], s["coords"][1]).save(dest, optimize=True)
        made += 1

    total = sum(p.stat().st_size for p in OUT.glob("*.png"))
    print(f"rendered {made}, reused {skipped}")
    print(f"maps on disk: {len(list(OUT.glob('*.png')))}  ({total/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
