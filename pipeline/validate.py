"""Sanity-check extracted coordinates against the state named in each site's own text.

This is a gross-error detector, not a precision check. The boxes below are
deliberately loose approximations, and a site is only flagged when it falls well
outside the region its own description claims — the kind of miss that means a dot
was read from the wrong sheet or a sheet was filed in the wrong folder.

Passing here does NOT mean a coordinate is publication-accurate. Recovered dots
sit 20-60 km from truth; anything printed as a number still needs a gazetteer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOLERANCE_DEG = 1.35          # ~150 km of slack outside each box

# (lat_min, lat_max, lon_min, lon_max) — approximate, generous
BOXES = {
    "Madhya Pradesh": (21.0, 26.9, 74.0, 82.8),
    "Uttar Pradesh": (23.8, 30.4, 77.0, 84.7),
    "Maharashtra": (15.6, 22.1, 72.6, 80.9),
    "Rajasthan": (23.0, 30.2, 69.4, 78.3),
    "Gujarat": (20.1, 24.7, 68.1, 74.5),
    "Karnataka": (11.5, 18.5, 74.0, 78.6),
    "Tamil Nadu": (8.0, 13.6, 76.2, 80.4),
    "Kerala": (8.2, 12.8, 74.8, 77.4),
    "Andhra Pradesh": (12.6, 19.9, 76.7, 84.8),
    "Telangana": (15.8, 19.9, 77.2, 81.8),
    "Odisha": (17.8, 22.6, 81.3, 87.5),
    "West Bengal": (21.5, 27.2, 85.8, 89.9),
    "Bihar": (24.2, 27.5, 83.3, 88.3),
    "Jharkhand": (21.9, 25.3, 83.3, 87.9),
    "Chhattisgarh": (17.8, 24.1, 80.2, 84.4),
    "Punjab": (29.5, 32.5, 73.9, 76.9),
    "Haryana": (27.6, 30.9, 74.4, 77.6),
    "Himachal Pradesh": (30.3, 33.2, 75.6, 79.0),
    "Uttarakhand": (28.7, 31.5, 77.5, 81.0),
    "Jammu and Kashmir": (32.2, 37.1, 73.0, 80.3),
    "Ladakh": (32.2, 37.1, 75.8, 80.3),
    "Assam": (24.1, 28.0, 89.7, 96.0),
    "Goa": (14.8, 15.8, 73.6, 74.4),
    "Delhi": (28.4, 28.9, 76.8, 77.4),
    "Puducherry": (11.7, 12.1, 79.7, 79.9),
    "Pakistan": (23.6, 37.1, 60.9, 77.8),
    "Afghanistan": (29.4, 38.5, 60.5, 74.9),
    "Nepal": (26.3, 30.4, 80.0, 88.2),
    "Bangladesh": (20.7, 26.6, 88.0, 92.7),
    "Sri Lanka": (5.9, 9.8, 79.6, 81.9),
    "Myanmar": (9.8, 28.5, 92.2, 101.2),
}


def miss_distance(lat: float, lon: float, box: tuple) -> float:
    """Degrees outside the box; 0 if inside."""
    la0, la1, lo0, lo1 = box
    dlat = max(la0 - lat, lat - la1, 0.0)
    dlon = max(lo0 - lon, lon - lo1, 0.0)
    return (dlat ** 2 + dlon ** 2) ** 0.5


def main() -> int:
    records = json.loads((ROOT / "data" / "sites.json").read_text(encoding="utf-8"))
    checked = ok = 0
    flags: list[tuple[float, dict, float]] = []
    for r in records:
        if not r["coords"] or not r["state"]:
            continue
        box = BOXES.get(r["state"])
        if not box:
            continue
        checked += 1
        d = miss_distance(r["coords"][0], r["coords"][1], box)
        if d <= TOLERANCE_DEG:
            ok += 1
        else:
            flags.append((d, r, d * 111))

    flags.sort(key=lambda x: -x[0])
    pct = 100 * ok / checked if checked else 0
    print(f"checked   : {checked} sites with both a coordinate and a stated region")
    print(f"consistent: {ok}  ({pct:.0f}%)")
    print(f"flagged   : {len(flags)}")
    for d, r, km in flags[:12]:
        print(f"   {r['name'][:26]:<28} says {r['state']:<16} "
              f"dot at {r['coords'][0]:.1f}N {r['coords'][1]:.1f}E  ~{km:.0f} km outside")

    out = ["# Coordinate validation", "",
           "Cross-check of each extracted dot against the region named in the site's",
           "own description. Loose boxes, ~150 km tolerance — this catches gross",
           "errors only, not precision.", "",
           f"- Checked: **{checked}**", f"- Consistent: **{ok}** ({pct:.0f}%)",
           f"- Flagged: **{len(flags)}**", ""]
    if flags:
        out += ["| Site | Stated region | Dot | Outside by |", "|---|---|---|---:|"]
        for d, r, km in flags:
            out.append(f"| {r['name']} | {r['state']} | "
                       f"{r['coords'][0]:.2f}N {r['coords'][1]:.2f}E | {km:.0f} km |")
    (ROOT / "reports" / "validation.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
