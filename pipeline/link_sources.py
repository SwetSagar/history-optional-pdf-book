"""Attach bibliography keys to site records.

    python3 pipeline/link_sources.py propose        write sources_proposed
    python3 pipeline/link_sources.py confirm SLUG N  promote proposal N to sources
    python3 pipeline/link_sources.py report          what is proposed vs confirmed

Proposals go to `sources_proposed`, never to `sources`, and never set
`status: sourced`.

The reason is measured, not cautious by temperament. At a score threshold of 15,
122 sites acquire a citation — but 8 of those top hits match only a district name
(the "Chittoor" passage is about somewhere else in Chittoor district) and 19 are a
single passing mention. That is roughly a fifth of the citations pointing at
something that does not support the claim. A book whose selling point is being
referenced cannot carry those, and `status: sourced` would assert a check that
nobody performed.

So: the machine proposes, a human confirms, and only then does it become a
citation.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cite import corpus_keys  # noqa: E402
from common import dump_frontmatter, load_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT / "sites"

# Recalibrated for BM25 scoring. The previous threshold of 18 was set against
# raw counts; BM25 shifted the distribution so 70% of hits cleared it and
# "strong" stopped meaning anything. Measured over 936 hits: median 22, p75 28.
STRONG_SCORE = 22          # median — paired with a repeat mention
VERY_STRONG_SCORE = 40     # top decile — stands on its own
STRONG_OCCURRENCES = 2


def tier(hit: dict) -> str:
    """How much the passage is worth, before a human looks at it."""
    snippet = hit.get("snippet", "").lower()
    matched = hit.get("matched", "").lower()
    if matched and re.search(rf"{re.escape(matched)}\s+(district|taluk|tehsil)", snippet):
        return "rejected"          # names a region, not the site
    occ = hit.get("occurrences", 0)
    sc = hit.get("score", 0)
    if sc >= VERY_STRONG_SCORE or (occ >= STRONG_OCCURRENCES and sc >= STRONG_SCORE):
        return "strong"
    return "weak"                  # a single glancing mention


def records() -> dict[str, Path]:
    return {p.stem: p for p in SITES.rglob("*.md")}


def load_candidates() -> dict[str, list[dict]]:
    """Candidates are keyed by name in one file and by slug in the other."""
    out: dict[str, list[dict]] = {}
    idx = json.loads((ROOT / "data" / "sites.json").read_text(encoding="utf-8"))
    by_name = {s["name"]: s["slug"] for s in idx}

    p = ROOT / "data" / "candidates.json"
    if p.exists():
        for name, hits in json.loads(p.read_text(encoding="utf-8")).items():
            slug = by_name.get(name)
            if slug:
                out.setdefault(slug, []).extend(hits)
    p = ROOT / "data" / "candidates_missing.json"
    if p.exists():
        for slug, hits in json.loads(p.read_text(encoding="utf-8")).items():
            out.setdefault(slug, []).extend(hits)
    return out


def propose() -> int:
    keys = corpus_keys()
    cands = load_candidates()
    recs = records()
    counts = {"strong": 0, "weak": 0, "rejected": 0}
    touched = 0

    for slug, hits in cands.items():
        p = recs.get(slug)
        if not p:
            continue
        proposals = []
        for h in hits:
            t = tier(h)
            counts[t] += 1
            if t == "rejected":
                continue
            key = keys.get(h["source"], h["source"])
            # chapter-level: these scans carry no printed folios, so the scan
            # page is a locator, not a citable page number
            proposals.append(f"{key}#{h['volume'][:38]}@{h['scan_page']}:{t}")
        if not proposals:
            continue
        meta, body = load_frontmatter(p.read_text(encoding="utf-8"))
        meta["sources_proposed"] = proposals[:4]
        p.write_text(dump_frontmatter(meta) + "\n\n" + body.rstrip() + "\n",
                     encoding="utf-8")
        touched += 1

    print(f"records given proposals : {touched}")
    print(f"  strong passages       : {counts['strong']}")
    print(f"  weak (single mention) : {counts['weak']}")
    print(f"  rejected (district)   : {counts['rejected']}")
    print("\nNothing was written to `sources` and no status changed.")
    print("Confirm one with:  link_sources.py confirm <slug> <n>")
    return report()


def confirm(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: link_sources.py confirm <slug> <n>", file=sys.stderr)
        return 2
    slug, n = argv[0], int(argv[1])
    p = records().get(slug)
    if not p:
        print(f"no record {slug!r}", file=sys.stderr)
        return 1
    meta, body = load_frontmatter(p.read_text(encoding="utf-8"))
    props = meta.get("sources_proposed") or []
    if not 1 <= n <= len(props):
        print(f"{slug} has {len(props)} proposals", file=sys.stderr)
        return 1
    chosen = props[n - 1].rsplit(":", 1)[0]          # drop the tier marker
    sources = list(meta.get("sources") or [])
    if chosen not in sources:
        sources.append(chosen)
    meta["sources"] = sources
    meta["status"] = "sourced"
    p.write_text(dump_frontmatter(meta) + "\n\n" + body.rstrip() + "\n", encoding="utf-8")
    print(f"{slug}: confirmed {chosen}  (status -> sourced)")
    return 0


def report() -> int:
    strong = weak = confirmed = none = 0
    rows = []
    for p in sorted(SITES.rglob("*.md")):
        meta, _ = load_frontmatter(p.read_text(encoding="utf-8"))
        if meta.get("status") == "missing":
            continue
        props = meta.get("sources_proposed") or []
        if meta.get("sources"):
            confirmed += 1
        elif any(x.endswith(":strong") for x in props):
            strong += 1
            rows.append((meta.get("name", p.stem), props[0]))
        elif props:
            weak += 1
        else:
            none += 1

    total = strong + weak + confirmed + none
    print(f"\nwritten entries        : {total}")
    print(f"  citation confirmed   : {confirmed}")
    print(f"  strong proposal      : {strong}   <- review these")
    print(f"  weak proposal only   : {weak}")
    print(f"  nothing in the corpus: {none}")

    lines = ["# Source linking", "",
             "Proposals are machine-generated and unverified. They live in",
             "`sources_proposed`; only a confirmed proposal becomes a `sources`",
             "entry and moves an entry to `status: sourced`.", "",
             f"- Confirmed: **{confirmed}**",
             f"- Strong proposal awaiting review: **{strong}**",
             f"- Weak proposal only: **{weak}**",
             f"- No corpus passage: **{none}**", "",
             "## Strong proposals to review", "",
             "| Site | Top proposal |", "|---|---|"]
    for name, prop in sorted(rows):
        lines.append(f"| {name} | `{prop}` |")
    (ROOT / "reports" / "sources.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  -> reports/sources.md")
    return 0


COMMANDS = {"propose": lambda a: propose(), "confirm": confirm,
            "report": lambda a: report()}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(COMMANDS[sys.argv[1]](sys.argv[2:]))
