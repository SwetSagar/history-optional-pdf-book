"""Assemble the evidence needed to write one chapter's entries.

    python3 pipeline/evidence.py 01            evidence pack for chapter 01
    python3 pipeline/evidence.py 01 --from 20  resume partway through

For each site it prints the imported bullets and the best supporting passages
from the corpus, so an entry can be written from the author's own notes and
their own books — and from nothing else.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT / "sites"
DATA = ROOT / "data"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    prefix = sys.argv[1]
    start = 0
    if "--from" in sys.argv:
        start = int(sys.argv[sys.argv.index("--from") + 1])
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 999

    folders = sorted(p for p in SITES.iterdir() if p.is_dir() and p.name.startswith(prefix))
    if not folders:
        print(f"no chapter matching {prefix!r}", file=sys.stderr)
        return 1
    cands = json.loads((DATA / "candidates.json").read_text(encoding="utf-8"))
    srcmap = {w["corpus"]: w["key"] for w in
              json.loads((DATA / "sources.json").read_text(encoding="utf-8"))["works"]}

    files = sorted(f for folder in folders for f in folder.glob("*.md"))
    shown = 0
    for i, md in enumerate(files):
        if i < start or shown >= limit:
            continue
        meta, body = load_frontmatter(md.read_text(encoding="utf-8"))
        name = meta.get("name", md.stem)
        if meta.get("status") not in ("raw", "missing"):
            continue
        shown += 1
        print(f"\n{'='*72}\n[{i}] {name}   <{md.relative_to(ROOT)}>")
        print(f"    state={meta.get('state') or '—'}  categories={meta.get('categories')}")
        bullets = [ln[2:].strip() for ln in body.splitlines() if ln.strip().startswith("- ")]
        if bullets:
            print("  NOTES:")
            for b in bullets:
                print(f"    · {b}")
        else:
            print("  NOTES: (none — entry has no text)")
        hits = cands.get(name, [])[:2]
        if hits:
            print("  SOURCES:")
            for h in hits:
                print(f"    [{srcmap.get(h['source'], h['source'])}] {h['volume'][:44]} "
                      f"p{h['scan_page']} (score {h['score']})")
                print(f"      {h['snippet'][:420]}")
        else:
            print("  SOURCES: none in corpus")
    print(f"\n{'='*72}\nshown {shown} of {len(files)} in chapter {prefix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
