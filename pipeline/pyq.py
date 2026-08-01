"""Mine the past papers for what the map question has actually asked.

    python3 pipeline/pyq.py

Two eras, two formats:

  older papers  name the places outright — "Mark any fifteen of the following
                places on the map: (i) Agra (ii) Ahmadnagar …". These give real
                per-site frequencies.
  newer papers  give only locational hints — "(i) A Mesolithic site" — because
                the places are marked on a separate sheet handed to the
                candidate, which is not in the PDF. These give category weights.

Both are useful: the first says which sites to write first, the second says
which chapters carry the most marks.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import match_keys  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PYQ = ROOT / "corpus_pyq"

MAP_Q = re.compile(r"(?:marked on the map|places on the map|on the map supplied)", re.I)
# The roman numeral and its text are not always on one line: newer papers print
# the Devanagari first and the English hint on the line below. Capture a small
# window after the numeral and pick the English out of it.
ITEM = re.compile(r"\(\s*([ivxlcIVXLC]{1,6})\s*\)([^(]{2,160})")
ENGLISH = re.compile(r"[A-Za-z][A-Za-z .'’\-/&]{3,}")
YEAR = re.compile(r"\b(19[7-9]\d|20[0-2]\d)\b")

# hint phrases used by the newer papers, mapped to the book's chapters
HINTS = [
    (r"palaeolithic|paleolithic", "Palaeolithic"),
    (r"mesolithic", "Mesolithic"),
    (r"neolithic", "Neolithic"),
    (r"chalcolithic", "Chalcolithic"),
    (r"harappan|indus", "Harappa"),
    (r"megalith", "Megalith"),
    (r"copper hoard|ochre", "Copper Hoards and OCP"),
    (r"painted grey|pgw", "PGW"),
    (r"black polished|nbpw|mahajanapada", "NBPW"),
    (r"buddhist", "Buddhist Sites"),
    (r"ashokan|asokan|edict", "Ashokan Inscriptions"),
    (r"inscription", "Non Ashokan Inscription"),
    (r"temple", "Temple Sites"),
    (r"jain", "Jain sites and caves"),
    (r"cave|rock.cut|rock shelter|painting", "Rockcut Caves"),
    (r"port|harbour", "Ancient Ports"),
    (r"capital|city|town|urban", "Ancient Capitals and trade cities"),
    (r"fort|fortified", "Forts"),
    (r"saint|sufi|bhakti", "Bhakti and other saints"),
    (r"trade|silk", "Silk Route sites"),
    (r"educational|university|learning", "Cultural and Educational Centers"),
]

# Match a whole item, not its first word: the hint items legitimately begin
# "A Mesolithic site", and an article-prefix rule silently discarded every one.
NOISE_EXACT = {"and", "or", "the", "a", "an", "section", "marks", "mark", "note",
               "notes", "about", "each", "following", "places", "place", "map",
               "answer", "question", "write", "identify", "given", "below", "of",
               "on", "in", "to", "supplied", "seriatim", "booklet"}
NOISE_LIKE = re.compile(r"^(www\.|http|page\b|\d+$)", re.I)


def is_noise(item: str) -> bool:
    return item.lower().strip() in NOISE_EXACT or bool(NOISE_LIKE.match(item))


def blocks(text: str) -> list[str]:
    out = []
    for m in MAP_Q.finditer(text):
        out.append(text[m.end(): m.end() + 2600])
    return out


def main() -> int:
    if not PYQ.is_dir():
        print("no corpus_pyq/ — ingest the papers first", file=sys.stderr)
        return 1

    named: Counter[str] = Counter()
    cats: Counter[str] = Counter()
    named_years: dict[str, set] = {}
    blocks_named = blocks_hint = 0

    for f in sorted(PYQ.glob("*.json")):
        pages = json.loads(f.read_text(encoding="utf-8"))
        ystem = YEAR.findall(f.stem)
        for p in pages:
            text = p["text"]
            page_year = (YEAR.findall(text) or ystem or ["?"])[0]
            for blk in blocks(text):
                items = []
                for _, chunk in ITEM.findall(blk):
                    words = ENGLISH.findall(chunk)
                    if not words:
                        continue
                    # longest run of Latin text is the place name or the hint
                    items.append(max(words, key=len).strip(" .:;—-"))
                items = [i for i in items if i and not is_noise(i)]
                if not items:
                    continue
                # a hint block describes kinds of site; a named block lists places
                hinty = sum(1 for i in items
                            if re.search(r"^\s*(a|an|the)\b|site|remains", i, re.I))
                if hinty >= max(2, len(items) * 0.6):
                    blocks_hint += 1
                    for i in items:
                        for pat, chapter in HINTS:
                            if re.search(pat, i, re.I):
                                cats[chapter] += 1
                                break
                else:
                    blocks_named += 1
                    for i in items:
                        nm = re.sub(r"\s+", " ", i).strip()
                        if 3 <= len(nm) <= 40 and re.match(r"^[A-Z]", nm):
                            named[nm] += 1
                            named_years.setdefault(nm, set()).add(page_year)

    print(f"map-question blocks found : {blocks_named} named, {blocks_hint} hint-only")
    print(f"distinct places named     : {len(named)}")
    print(f"category hints counted    : {sum(cats.values())}")

    # match named places against the book's records
    sites = json.loads((ROOT / "data" / "sites.json").read_text(encoding="utf-8"))
    keys = {s["slug"]: match_keys(s["name"]) for s in sites}
    by_slug = {s["slug"]: s for s in sites}

    asked: dict[str, int] = {}
    unmatched = []
    for place, n in named.items():
        pk = match_keys(place)
        hit = next((slug for slug, k in keys.items() if pk & k), None)
        if hit:
            asked[hit] = asked.get(hit, 0) + n
        else:
            unmatched.append((place, n))

    covered = [s for s in asked if by_slug[s].get("status") != "missing"]
    missing = [s for s in asked if by_slug[s].get("status") == "missing"]
    print(f"\nnamed places matched to records : {len(asked)}")
    print(f"  already written               : {len(covered)}")
    print(f"  MISSING but historically asked: {len(missing)}")

    out = {
        "named_frequency": {k: v for k, v in named.most_common()},
        "named_years": {k: sorted(v) for k, v in named_years.items()},
        "by_slug": asked,
        "category_weight": dict(cats.most_common()),
        "unmatched": dict(sorted(unmatched, key=lambda x: -x[1])[:80]),
    }
    (ROOT / "data" / "pyq.json").write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                            encoding="utf-8")

    lines = ["# What the map question has actually asked", "",
             "Mined from the past papers in `corpus_pyq/`. Older papers name the",
             "places; newer ones give only locational hints, so those contribute",
             "chapter weights rather than site names.", "",
             f"- Map-question blocks: **{blocks_named}** naming places, "
             f"**{blocks_hint}** hint-only",
             f"- Distinct places named: **{len(named)}**",
             f"- Matched to records: **{len(asked)}**", "",
             "> **Year attribution is unreliable.** The 1979-2012 compendium prints",
             "> many papers per page, so the year shown is the first one found on",
             "> the page, not necessarily the paper the question came from. Treat",
             "> the counts as trustworthy and the years as indicative.", ""]

    if missing:
        lines += ["## Priority — asked before, still unwritten", "",
                  "Write these first.", "",
                  "| Site | Times asked | Years |", "|---|---:|---|"]
        for slug in sorted(missing, key=lambda s: -asked[s]):
            nm = by_slug[slug]["name"]
            yrs = ", ".join(sorted(named_years.get(nm, []))[:6]) or "—"
            lines.append(f"| {nm} | {asked[slug]} | {yrs} |")
        lines.append("")

    lines += ["## Chapter weight from the hint-only papers", "",
              "| Chapter | Hints |", "|---|---:|"]
    for chapter, n in cats.most_common():
        lines.append(f"| {chapter} | {n} |")

    lines += ["", "## Most-asked places overall", "", "| Place | Times |", "|---|---:|"]
    for place, n in named.most_common(30):
        lines.append(f"| {place} | {n} |")

    (ROOT / "reports" / "pyq.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  -> reports/pyq.md, data/pyq.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
