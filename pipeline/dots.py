"""Locate the marker dot on a site sheet and convert it to a position on the map.

Every site image in this collection is the same blank UPSC outline sheet with one
dot added. Diffing against the blank recovers the dot; the sheet's own graticule
converts pixels to degrees.

Accuracy: the dots were placed by hand on a small sheet, so recovered positions
land roughly 20-60 km from truth. That is fine for drawing a dot at book scale
(2-4 px) but NOT good enough to publish as coordinates. Treat every value here as
provisional until reconciled against a gazetteer.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Sheet geometry, measured from the blank template by detecting the neat-line.
# ---------------------------------------------------------------------------
FRAME_X = (31.5, 548.0)     # pixel x of the 60E and 100E frame edges
FRAME_Y = (102.6, 626.8)    # pixel y of the top and bottom frame edges
LON_RANGE = (60.0, 100.0)

# Latitude is not labelled on the frame edges, so the scale was fitted against
# three sites of known position (Bhimbetka, Kalibangan, Ajanta) and validated at
# 23-56 km residual. Recorded explicitly so it can be re-derived or improved.
LAT_DEG_PER_PX = 0.06475
LAT_ANCHOR_PX = 338.0
LAT_ANCHOR_DEG = 22.93

DIFF_THRESHOLDS = (60, 40, 26)   # tried in order; scans vary in contrast


@dataclass
class Dot:
    x: float
    y: float
    method: str          # how it was found, for auditing
    blob_px: int
    confidence: str      # high | medium | low


def to_lonlat(x: float, y: float) -> tuple[float, float]:
    """Pixel position on the blank sheet -> (lat, lon) in degrees."""
    x0, x1 = FRAME_X
    lon = LON_RANGE[0] + (x - x0) * (LON_RANGE[1] - LON_RANGE[0]) / (x1 - x0)
    lat = LAT_ANCHOR_DEG - (y - LAT_ANCHOR_PX) * LAT_DEG_PER_PX
    return round(lat, 4), round(lon, 4)


def _centroid(diff: np.ndarray) -> tuple[float, float, int]:
    ys, xs = np.nonzero(diff)
    w = diff[ys, xs].astype(float)
    return float((xs * w).sum() / w.sum()), float((ys * w).sum() / w.sum()), int(len(xs))


def _is_dotlike(mask: np.ndarray) -> bool:
    """A marker dot is small, compact and roughly round.

    This is what separates a real dot from the sheet's printed furniture — the
    scale bar in particular diffs as an elongated, sparse smear and would
    otherwise be read as a site in the Indian Ocean.
    """
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return False
    h = ys.max() - ys.min() + 1
    w = xs.max() - xs.min() + 1
    if max(h, w) > 24 or min(h, w) < 2:
        return False
    if not (0.45 <= w / h <= 2.2):
        return False
    return len(xs) / (w * h) >= 0.5      # fills its bounding box like a disc


def _largest_blob(mask: np.ndarray) -> np.ndarray | None:
    """Keep only the largest 4-connected component. Avoids scipy."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    best: list[tuple[int, int]] = []
    idx = np.argwhere(mask)
    for sy, sx in idx:
        if seen[sy, sx]:
            continue
        stack = [(sy, sx)]
        seen[sy, sx] = True
        comp = []
        while stack:
            cy, cx = stack.pop()
            comp.append((cy, cx))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(comp) > len(best):
            best = comp
        if len(best) > 4000:      # runaway: not a dot
            return None
    if not best:
        return None
    out = np.zeros_like(mask)
    for cy, cx in best:
        out[cy, cx] = True
    return out


def build_group_blanks(paths, min_members: int = 8, sample: int = 80) -> dict:
    """Synthesise a blank template for each scan-size group.

    The collection contains more than one scan of the same sheet at different
    sizes. Rescaling the master blank to match never registers well enough to
    diff cleanly. But every sheet in a group carries its dot in a different
    place, so the per-pixel median across the group is the bare template — the
    dots are outvoted and disappear. Exact registration, no resampling.
    """
    from collections import defaultdict

    by_size: dict[tuple[int, int], list] = defaultdict(list)
    for p in paths:
        with Image.open(p) as im:
            by_size[im.size].append(p)

    blanks: dict[tuple[int, int], np.ndarray] = {}
    for size, ps in by_size.items():
        if len(ps) < min_members:
            continue
        step = max(1, len(ps) // sample)
        sel = ps[::step][:sample]
        stack = np.stack([np.asarray(Image.open(p).convert("L")) for p in sel])
        blanks[(size[1], size[0])] = np.median(stack, axis=0).astype(np.int16)
    return blanks


class SheetMatcher:
    """Holds the blank template and finds dots on sheets drawn over it."""

    def __init__(self, blank_path: Path, group_blanks: dict | None = None):
        self.blank = Image.open(blank_path).convert("L")
        self.base = np.asarray(self.blank).astype(np.int16)
        self._resized: dict[tuple[int, int], np.ndarray] = {}
        # synthesised per-scan-size templates, keyed by numpy shape (h, w)
        self.group_blanks = group_blanks or {}

    def _base_for(self, shape: tuple[int, int]) -> np.ndarray:
        if shape in self.group_blanks:
            return self.group_blanks[shape]
        if shape == self.base.shape:
            return self.base
        if shape not in self._resized:
            r = self.blank.resize((shape[1], shape[0]), Image.LANCZOS)
            self._resized[shape] = np.asarray(r).astype(np.int16)
        return self._resized[shape]

    def _registered(self, shape: tuple[int, int]) -> bool:
        """True when we have a pixel-exact template, so the diff is trustworthy."""
        return shape == self.base.shape or shape in self.group_blanks

    def find(self, path: Path) -> Dot | None:
        im = Image.open(path)
        grey = np.asarray(im.convert("L")).astype(np.int16)
        exact = self._registered(grey.shape)
        base = self._base_for(grey.shape)

        for thr in DIFF_THRESHOLDS:
            d = base - grey
            d[d < thr] = 0
            if d.sum() == 0:
                continue
            mask = d > 0
            # a registration mismatch lights up every line on the sheet; isolate the blob
            if not exact or mask.sum() > 900:
                blob = _largest_blob(mask)
                if blob is None:
                    continue
                d = np.where(blob, d, 0)
                mask = d > 0
                if d.sum() == 0:
                    continue
            if not _is_dotlike(mask):
                continue
            x, y, n = _centroid(d)
            if n < 6 or n > 3000:
                continue
            conf = "high" if (exact and thr == DIFF_THRESHOLDS[0] and 15 <= n <= 400) else \
                   ("medium" if exact else "low")
            return Dot(x, y, f"diff@{thr}{'' if exact else '+resize'}", n, conf)

        # colour marker (some sheets use a coloured pen rather than black)
        rgb = np.asarray(im.convert("RGB")).astype(np.int16)
        mx = rgb.max(axis=2)
        mn = rgb.min(axis=2)
        sat = (mx - mn) > 55
        if sat.sum() >= 6:
            blob = _largest_blob(sat)
            if blob is not None and 6 <= blob.sum() <= 3000:
                d = blob.astype(np.int16)
                x, y, n = _centroid(d)
                return Dot(x, y, "colour", n, "medium")
        return None

    def scale_to_blank(self, dot: Dot, shape: tuple[int, int]) -> tuple[float, float]:
        """Map a dot found on a differently-sized scan back onto blank-sheet pixels."""
        if shape == self.base.shape:
            return dot.x, dot.y
        sy = self.base.shape[0] / shape[0]
        sx = self.base.shape[1] / shape[1]
        return dot.x * sx, dot.y * sy
