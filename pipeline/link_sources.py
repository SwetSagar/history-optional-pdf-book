"""Automatically link candidate reference citations into site frontmatter.

    python3 pipeline/link_sources.py            preview
    python3 pipeline/link_sources.py --write    apply

Reads `data/candidates.json` and maps corpus match folders to bibliography keys
in `data/bibliography.json`. Populates `sources: [...]` and updates `status` to `sourced`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import dump_frontmatter, load_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITES = ROOT / "sites"
MIN_SCORE = 15


def corpus_to_bib_map() -> dict[str, str]:
    sources_file = DATA / "sources.json"
    if not sources_file.exists():
        return {}
    manifest = json.loads(sources_file.read_text(encoding="utf-8"))
    return {w["corpus"]: w["key"] for w in manifest.get("works", [])}


def main() -> int:
    write = "--write" or "--apply" in sys.argv
    cand_file = DATA / "candidates.json"
    if not cand_file.exists():
        print("error: data/candidates.json not found. Run `python3 pipeline/cite.py batch` first.", file=sys.stderr)
        return 1

    cands = json.loads(cand_file.read_text(encoding="utf-8"))
    c2bib = corpus_to_bib_map()
    bib = json.loads((DATA / "bibliography.json").read_text(encoding="utf-8"))

    updated = 0
    total_sources = 0

    for md in sorted(SITES.rglob("*.md")):
        meta, body = load_frontmatter(md.read_text(encoding="utf-8"))
        name = meta.get("name", md.stem)
        hits = cands.get(name, [])

        # Filter hits with high confidence score
        valid_keys = []
        for h in hits:
            if h.get("score", 0) >= MIN_SCORE:
                corpus_id = h.get("source")
                bib_key = c2bib.get(corpus_id)
                if bib_key and bib_key in bib and bib_key not in valid_keys:
                    valid_keys.append(bib_key)

        existing_sources = meta.get("sources", [])
        if isinstance(existing_sources, str):
            existing_sources = [existing_sources]

        combined = list(dict.fromkeys(existing_sources + valid_keys))

        if combined != meta.get("sources", []):
            updated += 1
            meta["sources"] = combined
            if meta.get("status") in ("raw", "written"):
                meta["status"] = "sourced"
            total_sources += len(combined)

            if write:
                md.write_text(dump_frontmatter(meta) + "\n\n" + body, encoding="utf-8")

    print(f"sites evaluated : {len(cands)}")
    print(f"sites updated   : {updated}")
    print(f"total sources linked: {total_sources}")
    if not write:
        print("\n(preview — rerun with --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
