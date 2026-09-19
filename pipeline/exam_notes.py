"""Condense each entry into the note the map question actually asks for.

    python3 pipeline/exam_notes.py             # preview the word-count spread
    python3 pipeline/exam_notes.py --write     # write data/exam-notes.json
    python3 pipeline/exam_notes.py --sample 20 # print notes to read

The book's entries run to a median of 230 words. The map question wants roughly
30-50 on each of twenty places, under time. Those are different pieces of
writing, and the second cannot be produced by printing the first in a smaller
font.

This condenses rather than writes. Every clause in a note is lifted whole from
the entry's own anchors, which are the sourced text; nothing is paraphrased and
no fact is introduced. That is a deliberate limit: a generated note can be wrong
about emphasis, but it cannot be wrong about a fact the entry did not contain.
Clauses are taken whole for the same reason — truncating mid-clause is how
"identified with Vasavasamudram, though disputed" becomes an assertion.

The notes are drafts. `review_status` in the record frontmatter, and
`model_answer_30` beside it, remain the place a human-approved answer lives; the
web export gates scored practice on those and not on anything written here.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT / "sites"
OUTPUT = ROOT / "data" / "exam-notes.json"

# What the question is worth in words. Below the floor a note is too thin to
# score; above the ceiling it costs time that the next nineteen places need.
FLOOR, CEILING = 30, 50
BUDGET_LOCATION, BUDGET_PERIOD, BUDGET_SIGNIFICANCE, BUDGET_FIND = 13, 12, 24, 16

# A full stop after an initial or an abbreviation does not end a sentence.
# Without this, "Discovered by A. Ghosh in 1951" is cut to "Discovered by A."
ABBREVIATION = re.compile(
    r"\b(?:[A-Z]|c|ca|ch|cf|approx|fig|no|vs|St|Dr|Mt|Mrs|Ms|Prof|et al|i\.e|e\.g)\.")
DATED = re.compile(
    r"\b(BCE|CE|BC|AD|century|centuries|millennium|millennia|phase|period|"
    r"Palaeolithic|Mesolithic|Neolithic|Chalcolithic|Harappan|Mauryan|Gupta|"
    r"Satavahana|Chola|Chalukya|Vijayanagara|Mughal|Sultanate)\b", re.I)
# Excavation history is real but it is not what the two and a half marks are for.
DIGRESSION = re.compile(
    r"^(excavat|explored|dug|trenched|first (?:noticed|reported|excavated)|"
    r"brought to notice|reported by|discovered by|surveyed by|the site was (?:dug|excavated))",
    re.I)
# A clause that opens on a conjunction was hanging off something already dropped.
# "and used until the seat moved to Rangpur" is not a sentence about a place.
DANGLING = re.compile(r"^(and|but|or|nor|yet|which|who|whose|whom|while|whereas|"
                      r"though|although|so that|then|is|was|are|were|has|have|had|"
                      r"with|together with|along with|including|besides|"
                      # Anaphora with nothing to refer back to. "The two are
                      # separate sites and should not be conflated" is clear in
                      # an entry and meaningless as the third sentence of a note.
                      r"the (?:two|three|four|former|latter|others?)|these|those|"
                      r"both|it|they|he|she|such)\b", re.I)


# An aside addressed to the reader about the book is editorial apparatus. It
# belongs in the atlas — Ratanpura's warning not to conflate it with Loteshwar is
# worth having — and makes no sense inside thirty words about a place.
META = re.compile(r"\b(this book|the working notes|these notes|as noted above|"
                  r"see above|see below|the entry (?:above|below)|elsewhere in this)\b",
                  re.I)


def is_fragment(clause: str) -> bool:
    """Residue of a clause whose head was dropped, rather than a clause."""
    if DANGLING.match(clause):
        return True
    if clause.count("(") != clause.count(")"):
        return True                        # "1949-66)" — the name was filtered out
    if not re.search(r"[A-Za-z]{3}", clause):
        return True                        # a bare date or number
    return False


def plain(text: str) -> str:
    """Markdown emphasis off, whitespace normalised. The note is set as plain text."""
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def sentences(text: str) -> list[str]:
    masked = ABBREVIATION.sub(lambda m: m.group(0).replace(".", "\x00"), text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(\"'])", masked)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


def clauses(text: str) -> list[str]:
    """Split on clause punctuation, but never inside brackets.

    "Excavated by Amarendra Nath (ASI, 1997-2000) and Vasant Shinde" split on the
    comma inside the bracket, and the tail "1997-2000) and Vasant Shinde (Deccan
    College" survived every filter because its brackets balanced by accident.
    """
    masked, depth = [], 0
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        masked.append("\x00" if depth and ch in ",;" else ch)
    parts = re.split(r"\s+[-–—]\s+|;\s+|,\s+", "".join(masked))
    return [p.replace("\x00", ",").strip() for p in parts if p.strip()]


def take(parts: list[str], budget: int) -> str:
    """Whole clauses up to the budget. Never returns a half-clause."""
    kept, used = [], 0
    for part in parts:
        length = len(part.split())
        if kept and used + length > budget:
            break
        kept.append(part)
        used += length
    # The budget can fall between a bracket and its close — "Punjab (Pakistan"
    # reads as a typo rather than as a trim. Give back clauses until it balances.
    while kept and "".join(kept).count("(") != "".join(kept).count(")"):
        kept.pop()
    return ", ".join(kept)


def strip_leading_name(parts: list[str], name: str) -> list[str]:
    """The heading carries the name; the Location anchor opens by repeating it."""
    if not parts:
        return parts
    key = re.sub(r"[^a-z]", "", name.lower())
    head = re.sub(r"[^a-z]", "", parts[0].lower())
    if head and (key.startswith(head) or head.startswith(key[:6])) and len(head) >= 4:
        return parts[1:]
    return parts


def usable_clauses(sentence: str) -> list[str]:
    """Drop broken openers, keep continuations.

    Filtering every clause also threw away trailing ones that only read as
    fragments in isolation — "with all three phases represented" is not a
    sentence, but it is a perfectly good tail on the clause before it.
    """
    # Whole sentence, not clause by clause. Dropping only the clause that named
    # the book turned Ratanpura's warning — "note that in the working notes,
    # Ratanpura carries the description written for Loteshwar" — into the bare
    # assertion that it does. Removing a qualifier is how a filter invents a fact.
    if META.search(sentence):
        return []
    parts = clauses(sentence)
    while parts and (DIGRESSION.match(parts[0]) or is_fragment(parts[0])):
        parts.pop(0)
    return parts


def first_usable(text: str, budget: int, prefer=None) -> str:
    """The first sentence that survives the filters, trimmed to budget."""
    for sentence in sentences(text):
        parts = usable_clauses(sentence)
        if not parts:
            continue
        if prefer is not None:
            preferred = [c for c in parts if prefer.search(c)]
            # Selecting the dated clause can promote a continuation to the head
            # of the note: "is a fortified town with NBPW" was a tail of the
            # sentence before this filter picked it out of the middle.
            while preferred and DANGLING.match(preferred[0]):
                preferred.pop(0)
            parts = preferred or parts
        trimmed = take(parts, budget)
        if trimmed:
            return trimmed
    return ""


def sentence_case(text: str) -> str:
    """A clause lifted from mid-sentence still has to open a sentence."""
    return text[:1].upper() + text[1:] if text else text


def already_said(candidate: str, parts: list[str]) -> bool:
    """Keep the note from repeating a phrase it has already used."""
    words = set(re.findall(r"[a-z]{4,}", candidate.lower()))
    if not words:
        return True
    said = set(re.findall(r"[a-z]{4,}", " ".join(parts).lower()))
    return len(words & said) / len(words) > 0.6


def compose(name: str, content: dict) -> tuple[str, list[str]]:
    """Return the note and which anchors it drew on."""
    used = []

    location_sentences = sentences(plain(content["location"]["summary"]))
    location_parts = strip_leading_name(
        usable_clauses(location_sentences[0]) if location_sentences else [], name)
    location = take(location_parts, BUDGET_LOCATION)
    if location:
        used.append("location")

    period = first_usable(plain(content["periodLevel"]["summary"]), BUDGET_PERIOD, DATED)
    if period:
        used.append("periodLevel")

    significance = first_usable(
        plain(content["keyFindsAndSignificance"]["summary"]), BUDGET_SIGNIFICANCE)
    if significance:
        used.append("keyFindsAndSignificance")

    parts = [p for p in (location, period, significance) if p]
    total = sum(len(p.split()) for p in parts)

    # Still thin — reach into the finds, which is what the question rewards and
    # what a one-line significance statement most often leaves out.
    if total < FLOOR:
        for point in content["keyFindsAndSignificance"]["points"]:
            find = first_usable(plain(point), min(BUDGET_FIND, CEILING - total))
            if find and not already_said(find, parts):
                parts.append(find)
                used.append("keyFinds")
                total += len(find.split())
                break

    # Over the ceiling, drop from the end: the significance line is the last
    # thing added and the first thing that can be shortened without the note
    # ceasing to say where the place is or when it was.
    while total > CEILING and len(parts) > 1:
        shortened = take(usable_clauses(parts[-1]), CEILING - sum(
            len(p.split()) for p in parts[:-1]))
        if shortened and len(shortened.split()) < len(parts[-1].split()):
            parts[-1] = shortened
        else:
            parts.pop()
        total = sum(len(p.split()) for p in parts)

    note = ". ".join(sentence_case(p.rstrip(" .,;:")) for p in parts)
    return (note + "." if note else ""), used


def build() -> dict:
    notes, counts = [], []
    for path in sorted(SITES.rglob("*.md")):
        meta, body = load_frontmatter(path.read_text(encoding="utf-8"))
        name = str(meta.get("name", path.stem))
        content = parse_anchors(body)
        note, used = compose(name, content)
        words = len(note.split())
        counts.append(words)
        notes.append({
            "slug": path.stem,
            "name": name,
            "stateOrRegion": meta.get("state", ""),
            "categories": meta.get("categories", []),
            "note": note,
            "words": words,
            "anchorsUsed": used,
            "withinTarget": FLOOR <= words <= CEILING,
        })

    notes.sort(key=lambda n: n["slug"])
    counts.sort()
    return {
        "schemaVersion": 1,
        "derivedFrom": "sites/**/*.md",
        "generated": "condensed from the entry anchors; clauses lifted whole, never paraphrased",
        "target": {"floorWords": FLOOR, "ceilingWords": CEILING},
        "stats": {
            "notes": len(notes),
            "withinTarget": sum(n["withinTarget"] for n in notes),
            "belowFloor": sum(1 for n in notes if n["words"] < FLOOR),
            "aboveCeiling": sum(1 for n in notes if n["words"] > CEILING),
            "medianWords": counts[len(counts) // 2] if counts else 0,
        },
        "notes": notes,
    }


def parse_anchors(body: str) -> dict:
    """The three anchors, in the shape export_web.py produces them."""
    anchors: dict[str, dict] = {}
    current: dict | None = None
    text = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    for line in text.splitlines():
        if not line.strip():
            continue
        bullet = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        if not bullet:
            continue
        depth, value = len(bullet.group(1)), bullet.group(2).strip()
        if re.match(r"^\*Sources?\*", value, flags=re.IGNORECASE):
            continue
        if depth == 0:
            labelled = re.match(r"^\*\*(.+?)\*\*\s*:?\s*(.*)$", value)
            if labelled:
                current = {"summary": labelled.group(2).strip(), "points": []}
                anchors[labelled.group(1).strip()] = current
            else:
                current = None
        elif current is not None:
            current["points"].append(value)
    empty = {"summary": "", "points": []}
    return {
        "location": anchors.get("Location", empty),
        "periodLevel": anchors.get("Period/Level", empty),
        "keyFindsAndSignificance": anchors.get("Key Finds & Significance", empty),
    }


def main() -> int:
    payload = build()
    stats = payload["stats"]
    print(f"notes={stats['notes']} within_{FLOOR}-{CEILING}={stats['withinTarget']} "
          f"below={stats['belowFloor']} above={stats['aboveCeiling']} "
          f"median={stats['medianWords']}w")

    if "--sample" in sys.argv:
        n = int(sys.argv[sys.argv.index("--sample") + 1])
        step = max(1, len(payload["notes"]) // n)
        for note in payload["notes"][::step][:n]:
            print(f"\n{note['name']} ({note['stateOrRegion']}) — {note['words']}w")
            print(f"   {note['note']}")
        return 0

    if "--write" in sys.argv or "--apply" in sys.argv:
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
    else:
        print("preview only — rerun with --write, or --sample N to read some")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
