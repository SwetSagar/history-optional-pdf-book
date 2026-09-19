"""Render one clean locator map per site from its coordinate.

    python3 pipeline/render_maps.py [--force] [--print]

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

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from common import load_frontmatter  # noqa: E402
from dots import FRAME_X, FRAME_Y, LAT_ANCHOR_DEG, LAT_ANCHOR_PX, LAT_DEG_PER_PX, LON_RANGE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASEMAP = ROOT / "Individual Map sites History Optional" / "Use this copy.jpg"
OUT = ROOT / "build" / "maps"
PRINT_OUT = ROOT / "build" / "maps-print"

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
# just inside the neat-line (x=31.5, y=102.6) — which is not by itself enough to
# be rid of the frame, for the two reasons set out above without_frame().
CROP = (34, 107, 505, 583)

# --- print variant -------------------------------------------------------
# The PDF prints a locator at a full column, about 87 mm. This is a book about
# where places are, so the map is the argument and the dot is only a pointer
# into it: the dot is 1.3 mm, roughly 1.5% of the map's width, small enough to
# resolve a site against a state boundary rather than cover one.
#
# At 87 mm the 2x base is reproduced near 1:1, so there is no downsampling to
# dissolve a line and no dilation is wanted — proofing at size, one pass of
# dilation already thickens the coastline into a rope. What the scan does need
# is the grey pulled out of it, which is what the floor does.
PRINT_W = 950                 # ~280 dpi at 87 mm; the 2x base is 942 px wide
PRINT_DILATE = 0              # passes of MinFilter(3) at 2x, before resampling
PRINT_FLOOR = 150             # greys at or below this are pulled to solid black
PRINT_DOT = 0.009             # dot radius as a fraction of image width (~1.6mm)
PRINT_HALO = 0.45             # white ring around the dot, as a fraction of it
SS = 4                        # supersampling for the dot alone


def to_pixel(lat: float, lon: float) -> tuple[float, float]:
    """Inverse of dots.to_lonlat — degrees back to blank-sheet pixels."""
    x0, x1 = FRAME_X
    x = x0 + (lon - LON_RANGE[0]) * (x1 - x0) / (LON_RANGE[1] - LON_RANGE[0])
    y = LAT_ANCHOR_PX + (LAT_ANCHOR_DEG - lat) / LAT_DEG_PER_PX
    return x, y


# Cropping alone does not get rid of the sheet's neat-line, for two reasons.
#
# The frame is thick and sits immediately outside the crop — 5 px of rule down
# columns 29-33, 8 rows of it across 99-106 — and both renderers resample the
# whole sheet *before* cropping, so LANCZOS carries that ink back across the
# boundary. Blanking everything outside the crop removes the source; nothing is
# lost, since it was going to be cropped away regardless.
#
# The graticule ticks then point inward, so part of the frame is genuinely
# inside the crop: a rule along its first row and four ticks hanging eleven rows
# below it at the 60/70/80/90° meridians. Measured off the sheet, row 12 down is
# clean, and the one coastline that reaches the left edge does so in column 1,
# so column 0 can go whole.
#
# At locator size this was a few grey specks. At cover size it reads as damage.
FRAME_TOP_ROWS = 12
FRAME_LEFT_COLS = 1


def without_frame(bw: np.ndarray) -> np.ndarray:
    """Keep the map inside the crop and nothing else, in basemap pixels."""
    top, left = CROP[1] + FRAME_TOP_ROWS, CROP[0] + FRAME_LEFT_COLS
    out = np.full_like(bw, 255)
    out[top:CROP[3], left:CROP[2]] = bw[top:CROP[3], left:CROP[2]]
    return out


def base_image() -> Image.Image:
    src = Image.open(BASEMAP).convert("L")
    arr = np.asarray(src).astype(np.uint8)
    bw = without_frame(np.where(arr < INK_THRESHOLD, 0, 255).astype(np.uint8))
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
    # An adaptive palette is chosen by pixel count.  A locator dot is too small
    # to win a colour slot, so MEDIANCUT silently turned every screen marker
    # grey.  Use the same reserved palette as the print renderer.
    return im.quantize(palette=print_palette(), dither=Image.Dither.NONE)


def print_palette() -> Image.Image:
    """A fixed 16-colour palette that reserves slots for the dot.

    MEDIANCUT chooses its palette by pixel count. It was safe while the dot was
    6% of the image, and silently wrong once the dot shrank to 1.5%: too few red
    pixels to win a slot, so the marker quantised to grey and every locator in
    the book lost its colour. Reserving the red — and four steps of it towards
    white, so the antialiased rim survives — makes the palette independent of
    how large the dot happens to be.
    """
    cols = [(g, g, g) for g in (round(i * 255 / 9) for i in range(10))]
    cols += [tuple(round(c + (255 - c) * t) for c in DOT_RGB)
             for t in (0.0, 0.25, 0.5, 0.75, 0.9)]
    cols += [(255, 255, 255)]
    pal = Image.new("P", (1, 1))
    flat = [v for c in cols for v in c]
    pal.putpalette(flat + [0] * (768 - len(flat)))
    return pal


def print_base() -> Image.Image:
    """The base map set for reproduction at ~31 mm: dilated, resampled, re-inked."""
    im = base_image().convert("L")
    for _ in range(PRINT_DILATE):
        im = im.filter(ImageFilter.MinFilter(3))   # on greyscale, min = grow the ink
    im = im.crop(tuple(c * SCALE for c in CROP))
    w, h = im.size
    im = im.resize((PRINT_W, round(h * PRINT_W / w)), Image.LANCZOS)
    lut = [0 if p < PRINT_FLOOR else min(255, round((p - PRINT_FLOOR) * 255 / (255 - PRINT_FLOOR)))
           for p in range(256)]
    return im.point(lut).convert("RGB")


def render_print(base: Image.Image, lat: float, lon: float) -> Image.Image:
    """Locator for the PDF. The dot is supersampled so its edge stays smooth."""
    im = base.copy()
    px, py = to_pixel(lat, lon)
    span = CROP[2] - CROP[0]
    x = (px - CROP[0]) * PRINT_W / span
    y = (py - CROP[1]) * PRINT_W / span
    r = PRINT_W * PRINT_DOT
    outer = r * (1 + PRINT_HALO)

    box = round(outer * 2) + 2
    patch = Image.new("RGBA", (box * SS, box * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(patch)
    c = box * SS / 2
    d.ellipse([c - outer * SS, c - outer * SS, c + outer * SS, c + outer * SS],
              fill=(255, 255, 255, 255))
    d.ellipse([c - r * SS, c - r * SS, c + r * SS, c + r * SS], fill=(*DOT_RGB, 255))
    patch = patch.resize((box, box), Image.LANCZOS)
    im.paste(patch, (round(x - box / 2), round(y - box / 2)), patch)
    return im.quantize(palette=print_palette(), dither=Image.Dither.NONE)


def render_fingerprint(for_print: bool) -> str:
    """Hash every input that can change a rendered locator.

    Previously an existing PNG was reused forever unless the operator happened
    to remember ``--force``.  A corrected coordinate or renderer could therefore
    leave a stale map in the book.  The per-directory manifest makes reuse
    content-addressed while retaining the fast no-op path.
    """
    h = hashlib.sha256()
    h.update(Path(__file__).read_bytes())
    h.update(BASEMAP.read_bytes())
    h.update(b"print" if for_print else b"screen")
    return h.hexdigest()


def located_sites() -> list[dict]:
    """Every record with a coordinate, from the Markdown that is the source of truth.

    This read data/sites.json, a rebuilt index. The two agree on coordinates
    today and have already disagreed on thirteen names, so a corrected
    coordinate could have left a locator pinned at the old place.
    """
    sites = []
    for md in sorted((ROOT / "sites").rglob("*.md")):
        meta, _ = load_frontmatter(md.read_text(encoding="utf-8"))
        coords = meta.get("coords")
        if isinstance(coords, list) and len(coords) == 2:
            sites.append({"slug": md.stem, "coords": [float(coords[0]), float(coords[1])]})
    return sites


def main() -> int:
    force = "--force" in sys.argv
    for_print = "--print" in sys.argv
    sites = located_sites()
    out = PRINT_OUT if for_print else OUT
    out.mkdir(parents=True, exist_ok=True)
    base = print_base() if for_print else base_image()
    draw = render_print if for_print else render
    manifest_path = out / ".render-manifest.json"
    try:
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        previous_manifest = {}
    renderer_hash = render_fingerprint(for_print)
    next_manifest: dict[str, str] = {}

    made = skipped = 0
    for s in sites:
        if not s["coords"]:
            continue
        dest = out / f"{s['slug']}.png"
        site_hash = hashlib.sha256(
            json.dumps(
                [renderer_hash, s["slug"], s["coords"]],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        next_manifest[s["slug"]] = site_hash
        if dest.exists() and not force and previous_manifest.get(s["slug"]) == site_hash:
            skipped += 1
            continue
        draw(base, s["coords"][0], s["coords"][1]).save(dest, optimize=True)
        made += 1

    # A renamed or deleted record used to leave its locator behind forever, and
    # a stale map is worse than a missing one: the book would print it.
    removed = 0
    for stale in out.glob("*.png"):
        if stale.stem not in next_manifest:
            stale.unlink()
            removed += 1

    manifest_path.write_text(
        json.dumps(next_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )

    total = sum(p.stat().st_size for p in out.glob("*.png"))
    print(f"rendered {made}, reused {skipped}, removed {removed}"
          f"{'  (print variant)' if for_print else ''}")
    print(f"maps on disk: {len(list(out.glob('*.png')))}  ({total/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
