"""Restructure entries as a short lead paragraph followed by bullet points.

    python3 pipeline/reformat.py            preview
    python3 pipeline/reformat.py --write    apply

A solid block of prose is hard to revise from. The lead sentence carries what the
site is and where; everything after it is a discrete fact and reads better as a
scannable list.

Short entries are left as plain prose — two sentences do not need a bullet list.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import dump_frontmatter, load_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MIN_SENTENCES = 3        # below this, keep it as a paragraph

# Abbreviations whose full stop does not end a sentence.
ABBREV = (r"c|ca|approx|no|nos|vs|St|Mt|Dr|Mr|Mrs|Ms|Ltd|Co|ed|eds|vol|p|pp|"
          r"A\.D|B\.C|A\.H|i\.e|e\.g|cf|fl|r|d|b")


def split_sentences(text: str) -> list[str]:
    """Sentence split that survives 'c. 249 BCE' and 'A.D. 634'."""
    protected = re.sub(rf"\b({ABBREV})\.", r"\1<DOT>", text)
    protected = re.sub(r"\b([A-Z])\.", r"\1<DOT>", protected)     # initials
    parts = re.split(r"(?<=[.;])\s+(?=[A-Z“\"'])", protected)
    out = []
    for s in parts:
        s = s.replace("<DOT>", ".").strip()
        if s:
            out.append(s)
    return out


def restructure(body: str) -> str | None:
    text = " ".join(re.sub(r"<!--.*?-->", "", body, flags=re.S).split())
    if not text or text.lstrip().startswith("-"):
        return None                                   # already bulleted
    sentences = split_sentences(text)
    if len(sentences) < MIN_SENTENCES:
        return None                                   # too short to be worth it

    lede, rest = sentences[0], sentences[1:]
    # A bare opening clause ('A Mesolithic site in Rajasthan.') is not a lead —
    # pull the next sentence up so the paragraph says something.
    if len(lede.split()) < 9 and rest:
        lede += " " + rest.pop(0)
    if not rest:
        return None

    bullets = []
    for s in rest:
        s = s.strip()
        # a trailing semicolon clause reads oddly as its own bullet
        s = re.sub(r";$", ".", s)
        if not s.endswith((".", "!", "?")):
            s += "."
        bullets.append(s)
    return lede + "\n\n" + "\n".join(f"- {b}" for b in bullets)


def main() -> int:
    write = "--write" in sys.argv
    changed = kept = 0
    samples = []
    for p in sorted((ROOT / "sites").rglob("*.md")):
        meta, body = load_frontmatter(p.read_text(encoding="utf-8"))
        if meta.get("status") != "written":
            continue
        new = restructure(body)
        if new is None:
            kept += 1
            continue
        changed += 1
        if len(samples) < 2:
            samples.append((meta.get("name"), new))
        if write:
            p.write_text(dump_frontmatter(meta) + "\n\n" + new + "\n", encoding="utf-8")

    print(f"restructured  : {changed}")
    print(f"left as prose : {kept}  (too short to bullet)")
    for name, new in samples:
        print(f"\n--- {name} ---\n{new}")
    if not write:
        print("\n(preview — rerun with --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
