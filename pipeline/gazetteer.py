"""Integrate master gazetteer coordinates into site records.

    python3 pipeline/gazetteer.py            preview
    python3 pipeline/gazetteer.py --write    apply

Reads `data/gazetteer.json` and updates site frontmatter `coords: [lat, lon]`, `state`,
`coords_confidence: gazetteer`, and `coords_provisional: false` for all matching sites.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import dump_frontmatter, load_frontmatter, slugify  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITES = ROOT / "sites"


def main() -> int:
    write = "--write" in sys.argv or "--apply" in sys.argv
    gaz_file = DATA / "gazetteer.json"
    if not gaz_file.exists():
        print("error: data/gazetteer.json missing", file=sys.stderr)
        return 1

    gaz_data = json.loads(gaz_file.read_text(encoding="utf-8")).get("gazetteer", {})
    updated = 0

    for md in sorted(SITES.rglob("*.md")):
        meta, body = load_frontmatter(md.read_text(encoding="utf-8"))
        slug = md.stem
        
        info = gaz_data.get(slug)
        if info:
            meta["coords"] = info["coords"]
            meta["state"] = info["state"]
            meta["coords_confidence"] = "gazetteer"
            meta["coords_provisional"] = False
            if "locked" not in meta or not isinstance(meta["locked"], list):
                meta["locked"] = []
            for f in ("coords", "coords_provisional", "state"):
                if f not in meta["locked"]:
                    meta["locked"].append(f)
            updated += 1
            if write:
                md.write_text(dump_frontmatter(meta) + "\n\n" + body, encoding="utf-8")

    print(f"gazetteer entries : {len(gaz_data)}")
    print(f"sites updated     : {updated}")
    if not write:
        print("\n(preview — rerun with --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
