"""Locate a real typeface on whatever machine the build is running on.

Both cover scripts hard-coded `/System/Library/Fonts/...` paths. Off macOS every
lookup missed, PIL fell back to its built-in bitmap face, and the cover rendered
its title about ten pixels tall — legible in neither print nor thumbnail, and
silent about it. This resolves a family against the font directories of all
three platforms and says so out loud when it cannot.

Families are listed best-first. The later entries are stand-ins, not matches:
Futura has no equivalent on Windows, so a neutral grotesque carries the design
rather than failing it.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import ImageFont

# (filename, collection index). .ttc files hold several faces; index picks one.
FAMILIES: dict[str, list[tuple[str, int]]] = {
    "serif": [
        ("Baskerville.ttc", 0), ("Palatino.ttc", 0),
        ("Georgia.ttf", 0), ("georgia.ttf", 0), ("constan.ttf", 0),
        ("DejaVuSerif.ttf", 0), ("liberation/LiberationSerif-Regular.ttf", 0),
        ("times.ttf", 0),
    ],
    "sans": [
        ("Futura.ttc", 0), ("HelveticaNeue.ttc", 0), ("Helvetica.ttc", 0),
        ("arial.ttf", 0), ("Arial.ttf", 0), ("segoeui.ttf", 0),
        ("DejaVuSans.ttf", 0), ("liberation/LiberationSans-Regular.ttf", 0),
    ],
}
# the two names the Modernist cover asks for by name
FAMILIES["Georgia"] = FAMILIES["serif"][2:]
FAMILIES["Helvetica"] = FAMILIES["sans"][1:]

DIRS = [
    Path("/System/Library/Fonts/Supplemental"), Path("/System/Library/Fonts"),
    Path("/Library/Fonts"), Path.home() / "Library/Fonts",
    Path("C:/Windows/Fonts"), Path.home() / "AppData/Local/Microsoft/Windows/Fonts",
    Path("/usr/share/fonts/truetype"), Path("/usr/share/fonts"),
]

_warned: set[str] = set()


def find_font(family: str, size: int):
    """A real face at `size`, or PIL's bitmap fallback with a warning."""
    for filename, index in FAMILIES.get(family, [(f"{family}.ttf", 0)]):
        for d in DIRS:
            p = d / filename
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size, index=index)
                except Exception:
                    continue
    if family not in _warned:
        _warned.add(family)
        print(f"warning: no {family!r} face found; falling back to PIL's bitmap "
              f"font, which will render far too small to read", file=sys.stderr)
    return ImageFont.load_default()
