"""Assemble the print PDF from sites/*.md and build/maps/.

    python3 pipeline/build_pdf.py [--all] [--chapters 01,05] [--fast]

A4, two columns — the revision-atlas format. The EPUB is reflowable because a
phone page is unknown; a PDF page is known, so this build sets a fixed page:
name, state, a full-column locator map, then the four anchors, with the sources
on a hairline rule beneath.

The map is given the whole column rather than a corner of it. This is a book
about where places are, and a locator too small to read a position off fails at
the only job it has — so density gives way to the map, not the other way round.

One entry fills one column, exactly, and never breaks. Entries run from about
520pt to about 930pt against a 745pt column, so something has to give, and it
is the map: it is capped at the column width and floored at MAP_MIN_MM, and it
takes whatever height the text leaves. Most entries keep the full-size locator;
the longest shrink it. See "Why the fit loop" below for the rest.

Which chapter a record is printed in, and what that chapter is called, comes
from `data/chapters.json`, not from the folder name. That file is hand-edited.

Nothing here invents content. Entries render exactly what is in the Markdown.

Why two render passes
---------------------
The contents and the two indexes print real page numbers, and a page number is
only knowable after the page has been set. Chrome records every linked `id` as a
named destination in the PDF catalog, so pass one is rendered with placeholder
folios, the destinations are read back, and pass two prints the true numbers.
Placeholders are set in a fixed-width box so substituting them cannot reflow a
line and invalidate the numbers; the loop re-checks anyway and re-renders if the
pagination moved.

Why the fit loop
----------------
A handful of entries are long enough that even the smallest map will not get
them into a column, and CSS has no way to say "then set the type smaller". Nor
can the height be predicted from the Markdown with any confidence — it depends
on where Georgia happens to break every line. So the same loop reads the render
back, finds the entries whose ink landed below the foot of the column, steps
their body type down one size and renders again. It converges in a pass or two.

Requires Pillow (maps, already built), pypdf and reportlab, plus Chrome or Edge
on PATH or in the usual place — DevTools/CDP is not used, only `--print-to-pdf`,
which works under policies that disable remote debugging.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT / "sites"
# Maps drawn for the 87 mm column this book prints them at. The screen maps are
# the fallback and carry a dot sized for a thumbnail — run `render_maps.py
# --print` before publishing.
MAPS = ROOT / "build" / "maps-print"
MAPS_FALLBACK = ROOT / "build" / "maps"
WORK = ROOT / "build" / "pdf"
OUT = ROOT / "build" / "Map Entries for History Optional.pdf"

TITLE = "Map Entries for History Optional"
SUBTITLE = "A referenced atlas of the sites in the UPSC History Optional map question"
AUTHOR = "Swet Sagar"
EDITION = "First edition"
# Where readers go to practise placing these sites. Printed at the front and
# stamped, clickable, in the foot of every page after the cover.
PRACTICE_URL = "https://www.upsckosha.in/maps"
PRACTICE_LABEL = "upsckosha.in/maps"
PRACTICE_LINE = "Practise placing every site on the map"

# --------------------------------------------------------------------------
# The page grid
#
# One entry is set to fill exactly one column. These numbers are the arithmetic
# the stylesheet and the fit loop share, so they are written once, here, and
# reach the CSS as custom properties rather than as copied literals.
# --------------------------------------------------------------------------
MM = 72.0 / 25.4
PAGE_H_MM, MARGIN_MM = 297.0, 17.0        # A4, and the head/foot margin
# 263mm of column, less a millimetre. Chrome fragments on rounded device
# pixels, and an entry a hundredth of a millimetre taller than the column it
# was cut for ejects to the next one — which would cost every page its second
# entry. The millimetre is cheaper than the risk.
COL_H_MM = PAGE_H_MM - 2 * MARGIN_MM - 1.0
CHEAD_H_MM = 27.0                         # chapter banner, plus the gap below its rule
MAP_MAX_MM = 87.5                         # the column width; a locator can be no wider
MAP_MIN_MM = 50.0                         # past this the type gives way instead of the map
FIT_STEPS = 4                             # how far body type may be stepped down to fit
HEAD_PT = 11.0                            # `.ehead h3`; the fit check finds names by it
# Landmarks in PDF user space (origin bottom left), for reading a render back.
CONTENT_TOP_PT = (PAGE_H_MM - MARGIN_MM) * MM            # head margin
OPENER_TOP_PT = CONTENT_TOP_PT - CHEAD_H_MM * MM         # under a chapter banner
ENTRY_FOOT_PT = (PAGE_H_MM - MARGIN_MM - COL_H_MM) * MM  # foot of an entry's box

# Chrome is used purely as a print engine. Edge is the same engine and is
# present on every Windows machine, so it stands in when Chrome is absent.
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "chromium", "chromium-browser", "chrome",
]

CSS = """\
/* --------------------------------------------------------------------------
   Print stylesheet. Tokens are DESIGN_SYSTEM.md's light mode; the dark mode
   half of that spec is for the EPUB and has no meaning on paper.

   One deliberate departure from the EPUB stylesheet: an entry does not reflow.
   A phone page is unknown, so the EPUB lets an entry fall where it falls; an A4
   column is known, so here the entry is cut to it and the map takes up the
   slack. `orphans` and `widows` below are what is left of the old behaviour and
   now apply only to the front and back matter.
   -------------------------------------------------------------------------- */

:root {
  --ink:      #1a1a1a;
  --muted:    #565656;
  --accent:   #b02a22;
  --rule:     #d5d5d5;
  --hairline: #e6e6e6;
}

@page       { size: A4; margin: 17mm 14mm 17mm 14mm; }
@page cover { size: A4; margin: 0; }

html { font-size: 9pt; }

body {
  margin: 0;
  font-family: Georgia, "Charis SIL", "Times New Roman", serif;
  color: var(--ink);
  line-height: 1.40;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
  orphans: 3;
  widows: 3;
}

.sans { font-family: "Helvetica Neue", Helvetica, Inter, Arial, sans-serif; }

/* ---------- cover & front matter ---------- */

/* The art is 5:8 and the page is 1:1.41, so it is fitted rather than cropped —
   filling A4 would cut 30mm off a cover whose whole subject is a map. The page
   is painted in the cover's own paper colour, sampled from the file, so the
   band the fit leaves is not a white margin around a cream cover. */
.coverpage {
  page: cover; margin: 0; break-after: page;
  height: 297mm; width: 210mm;
  display: flex; align-items: center; justify-content: center;
}
.coverpage img { display: block; max-width: 210mm; max-height: 297mm; width: auto; height: auto; }

.titlepage { break-after: page; padding-top: 55mm; text-align: center; }
.titlepage .t {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 26pt; font-weight: 700; line-height: 1.15; margin: 0 0 6mm;
  letter-spacing: -0.01em;
}
.titlepage .rule { width: 26mm; height: 2pt; background: var(--accent); margin: 0 auto 6mm; }
.titlepage .s { font-size: 11pt; font-style: italic; color: var(--muted); margin: 0 auto 14mm; max-width: 120mm; line-height: 1.5; }
.titlepage .a { font-size: 12pt; margin: 0 0 2mm; }
.titlepage .e { font-size: 8.5pt; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
.practice {
  margin: 22mm auto 0; max-width: 120mm; padding: 5mm 6mm; text-align: center;
  border: 1pt solid var(--accent); border-radius: 2pt;
}
.practice .k {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 7.5pt; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--accent); margin: 0 0 2mm;
}
.practice p { font-size: 9.5pt; line-height: 1.45; margin: 0 0 2.5mm; }
.practice a {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 12pt; font-weight: 700; color: var(--accent); text-decoration: none;
}

.front { break-after: page; }
.front h2 {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 15pt; font-weight: 700; margin: 0 0 1mm;
}
.front .kicker {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 7.5pt; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--accent); margin: 0 0 1.5mm;
}
.front .lede { font-size: 10pt; color: var(--muted); font-style: italic; margin: 0 0 7mm;
               padding-bottom: 5mm; border-bottom: 1pt solid var(--rule); max-width: 135mm; line-height: 1.5; }
.front h3 {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 9.5pt; font-weight: 700; margin: 6mm 0 1.5mm;
}
.front p { margin: 0 0 3mm; max-width: 155mm; }
.front .note { font-size: 8.5pt; color: var(--muted); }

.anchorkey { margin: 0 0 4mm; padding: 0; list-style: none; }
.anchorkey li { margin: 0 0 2.2mm; padding-left: 30mm; text-indent: -30mm; }
.anchorkey .k {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 8pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
  display: inline-block; width: 30mm; text-indent: 0; vertical-align: top;
}

/* ---------- contents ---------- */

.toc { break-after: page; }
.toc ol { list-style: none; margin: 0; padding: 0; }
.toc li { margin: 0 0 2.4mm; }
.toc a { color: var(--ink); text-decoration: none; display: flex; align-items: baseline; gap: 2mm; }
.toc .n {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 8pt; color: var(--accent); font-weight: 700; width: 9mm; flex: 0 0 9mm;
}
.toc .t { font-size: 10.5pt; }
.toc .dots { flex: 1 1 auto; border-bottom: 0.5pt dotted var(--rule); margin: 0 1.5mm 1mm; }
.toc .c { font-size: 7.5pt; color: var(--muted); font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }
.toc .sep { margin: 6mm 0 3mm; border: 0; border-top: 1pt solid var(--rule); }

/* fixed-width folio box: a 2- and a 3-digit number occupy the same space, so
   substituting the real number in pass two cannot reflow anything. */
.pg {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 8.5pt; font-variant-numeric: tabular-nums;
  display: inline-block; min-width: 7mm; text-align: right;
}

/* ---------- chapters ---------- */

.chapter { break-before: page; }

/* Fixed height, because the two entries printed beside the banner have to be
   cut to the column it leaves them and `calc()` cannot measure a banner. Every
   chapter title sets on one line at 17pt across 182mm, so nothing here wraps. */
.chead {
  height: calc(var(--chead-h) - 4mm); box-sizing: border-box;
  margin: 0 0 4mm; padding-bottom: 2.5mm; border-bottom: 2pt solid var(--accent);
}
.chead .num {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 7.5pt; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--accent); margin: 0 0 1mm;
}
.chead h2 {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 17pt; font-weight: 700; margin: 0; line-height: 1.15; letter-spacing: -0.01em;
}
.chead .count {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 8pt; color: var(--muted); margin: 1.5mm 0 0;
}

.cols { column-count: 2; column-gap: 7mm; }

/* ---------- entry ---------- */

/* One entry, one column — the grid the book is set on.

   An entry left to the column flow breaks wherever the column happens to run
   out, and what lands at the top of the next column is one site's last bullets
   and its citation printed beneath a different site's name. That is the one
   failure a reference book cannot have, so the entry is cut to the column's
   exact height and forbidden to break.

   Something has to absorb the difference between a 520pt entry and a 930pt
   one, and it is the map: the only part of an entry that can be any size and
   still do its job. A short entry therefore still prints the full-width
   locator this layout was designed around, and a long one trades the map down
   towards MAP_MIN_MM rather than running over. Bodies too long even for the
   smallest map step the type down instead (.f2-.f4), which the fit loop in
   this file assigns by measuring the render rather than by guessing. */
.entry {
  height: var(--col-h);
  box-sizing: border-box;
  display: flex; flex-direction: column;
  break-inside: avoid;
  margin: 0;
  border-top: 0.5pt solid var(--hairline); padding-top: 4mm;
}
/* the two entries set beside a chapter banner have that much less column, and
   want no hairline of their own directly under the banner's rule */
.entry.op {
  height: calc(var(--col-h) - var(--chead-h));
  border-top: 0; padding-top: 0;
}

.ehead { flex: 0 0 auto; margin: 0; }
/* 11pt is also HEAD_PT: the fit check finds the top of an entry by looking for
   bold sans at this size, so the two move together. */
.ehead h3 {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 11pt; font-weight: 700; margin: 0 0 0.8mm; line-height: 1.15;
  letter-spacing: -0.005em;
}
.ehead .state { font-size: 8.5pt; font-style: italic; color: var(--muted); margin: 0; }
.ehead .also {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 6.8pt; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--muted); margin: 1mm 0 0;
}
/* flex-basis 0, so the map's height is the column's free space and nothing
   else — grown to the column width where the text leaves room, shrunk towards
   the floor where it does not. The artwork is square, so the cap is the column
   width; height drives the sizing and the width follows it. */
.emap {
  flex: 1 1 0;
  min-height: var(--map-min); max-height: var(--map-max);
  margin: 2mm 0 0;
  text-align: center;
}
.emap img {
  display: inline-block; vertical-align: top;
  height: 100%; width: auto; max-width: 100%;
  /* border-box, or the rule is added to the width rather than drawn inside it:
     100% of a 247.9pt column plus two 0.5pt edges is 248.9pt, and the map — the
     widest thing on the page — became the one element in the book hanging past
     the text edge into the margin. */
  box-sizing: border-box;
  border: 0.5pt solid var(--rule); border-radius: 1pt;
}

/* The four anchors and the citation. Never shrinks to fit — the map does that
   — but the fit loop may step the whole block down a size where an entry is
   long enough that even the smallest map will not save it. Everything inside
   is sized in em so one class moves all of it together. */
.ebody { flex: 0 0 auto; margin-top: 2.5mm; font-size: 9pt;   line-height: 1.40; }
.ebody.f2 {                                   font-size: 8.6pt; line-height: 1.36; }
.ebody.f3 {                                   font-size: 8.2pt; line-height: 1.32; }
.ebody.f4 {                                   font-size: 7.8pt; line-height: 1.28; }

ul.facts { margin: 0; padding: 0; list-style: none; }
ul.facts > li { margin: 0 0 1.6mm; }
ul.facts .lab {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 0.82em; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--ink);
}
ul.facts .lab::after { content: " "; }

ul.subs { margin: 1.2mm 0 0; padding: 0 0 0 3mm; list-style: none; }
ul.subs li { margin: 0 0 1.2mm; position: relative; padding-left: 2.6mm; }
ul.subs li::before {
  content: "\\2022"; position: absolute; left: 0; color: var(--accent);
}

/* No `break-before: avoid` any more: the entry that used to break underneath a
   citation cannot break at all now, so there is nothing to strand it from. */
.src {
  font-size: 0.845em; color: var(--muted); font-style: italic;
  border-top: 0.5pt dashed var(--rule); padding-top: 1.2mm; margin: 2mm 0 0;
}
.src .lab {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-style: normal; font-size: 0.895em; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink);
}
.src .lab::after { content: " "; }

/* ---------- back matter ---------- */

.back { break-before: page; }
.back h2 {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 17pt; font-weight: 700; margin: 0 0 2.5mm;
  padding-bottom: 2.5mm; border-bottom: 2pt solid var(--accent);
}
.back .lede { font-size: 9pt; color: var(--muted); font-style: italic; margin: 0 0 5mm; max-width: 155mm; }

ul.bib { list-style: none; margin: 0; padding: 0; column-count: 2; column-gap: 7mm; font-size: 8.5pt; }
ul.bib li { margin: 0 0 2.5mm; padding-left: 4mm; text-indent: -4mm; break-inside: avoid; }

.index { column-count: 3; column-gap: 6mm; font-size: 7.8pt; }
.index .grp {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 7.5pt; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--accent); margin: 3mm 0 1.2mm; break-after: avoid;
}
.index .grp:first-child { margin-top: 0; }
.index p.ix { margin: 0 0 0.9mm; display: flex; align-items: baseline; break-inside: avoid; }
.index p.ix a { color: var(--ink); text-decoration: none; }
.index p.ix .dots { flex: 1 1 auto; border-bottom: 0.5pt dotted var(--hairline); margin: 0 1mm 0.8mm; }
.index p.ix .pg { font-size: 7.6pt; min-width: 5mm; }
.index .ch {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 6.4pt; color: var(--muted); margin-left: 1mm;
}
"""


# --------------------------------------------------------------------------
# markdown -> html
# --------------------------------------------------------------------------

def geometry_css() -> str:
    """The page grid as custom properties, written from the constants above.

    The stylesheet and `overflow_entries` have to agree about where the foot of
    a column is, or the fit loop chases an overflow the CSS does not have. One
    source, two readers.
    """
    return (":root {\n"
            f"  --col-h:   {COL_H_MM:g}mm;\n"
            f"  --chead-h: {CHEAD_H_MM:g}mm;\n"
            f"  --map-max: {MAP_MAX_MM:g}mm;\n"
            f"  --map-min: {MAP_MIN_MM:g}mm;\n"
            "}\n")


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def inline(s: str) -> str:
    """The inline subset the bodies actually use: **bold** and *italic*.

    Escaped first, so a stray < or & in a body can never become markup.
    """
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", s)
    return s


def parse_body(body: str) -> tuple[list[dict], str]:
    """Body markdown -> ([{label, text, subs}], sources_line).

    Every record is the same shape — three labelled top-level bullets, each with
    optional sub-bullets, and a final `*Sources*` sub-bullet where one has been
    written. The sources line is lifted out and set as the entry's footer.
    """
    text = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    items: list[dict] = []
    sources = ""
    for line in text.split("\n"):
        if not line.strip():
            continue
        m = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        if not m:                       # no such line in the corpus; keep it rather than drop it
            if items:
                items[-1]["text"] += " " + line.strip()
            continue
        depth, content = len(m.group(1)), m.group(2).strip()
        src = re.match(r"^\*Sources?\*\s*:?\s*(.*)$", content, flags=re.I)
        if src:
            sources = src.group(1).strip().rstrip(".")
            continue
        if depth == 0:
            lab = re.match(r"^\*\*(.+?)\*\*\s*:?\s*(.*)$", content)
            if lab:
                items.append({"label": lab.group(1).strip(), "text": lab.group(2).strip(), "subs": []})
            else:
                items.append({"label": "", "text": content, "subs": []})
        elif items:
            items[-1]["subs"].append(content)
    return items, sources


def cite_label(ref: str, bib: dict) -> str:
    """'upinder2008#4. Harappan Civilization@69' -> a readable chapter citation.

    Deliberately no page number: the scans carry no printed folios, so a locator
    would point into a scan rather than into the book. Same rule as the EPUB.
    """
    key, _, rest = ref.partition("#")
    chapter = rest.split("@")[0].strip()
    w = bib.get(key, {})
    who = str(w.get("author", key)).rstrip(".")
    if "," in who:                                   # "Singh, Upinder" -> "Upinder Singh"
        last, _, first = who.partition(",")
        who = f"{first.strip()} {last.strip()}".strip()
    out = f"{esc(who)}, <em>{esc(w.get('title', key))}</em>"
    if chapter:
        out += f", {esc(chapter)}"
    return out


# --------------------------------------------------------------------------
# records
# --------------------------------------------------------------------------

def load_chapter_config() -> dict:
    path = ROOT / "data" / "chapters.json"
    if not path.exists():
        return {"titles": {}, "merge_into": {}, "move_sites": {}}
    cfg = json.loads(path.read_text(encoding="utf-8"))
    return {"titles": cfg.get("titles", {}),
            "merge_into": cfg.get("merge_into", {}),
            "move_sites": cfg.get("move_sites", {})}


CHAPTERS = load_chapter_config()


def chapter_title(folder: str) -> str:
    """The printed name. data/chapters.json wins; the folder is the fallback."""
    if folder in CHAPTERS["titles"]:
        return CHAPTERS["titles"][folder]
    name = re.sub(r"^\d+-", "", folder).replace("-", " ")
    fixed = {"pgw": "PGW", "nbpw": "NBPW", "ocp": "OCP", "and": "and", "of": "of"}
    words = [fixed.get(w.lower(), w.capitalize() if w.islower() else w) for w in name.split()]
    return " ".join(words)


def folder_number(folder: str) -> str:
    """The number in the folder name — the sites/ tree's own ordering."""
    m = re.match(r"^(\d+)-", folder)
    return m.group(1) if m else "--"


def numbering(chapters: dict[str, list[dict]]) -> dict[str, str]:
    """Printed chapter numbers: sequential, so a removed chapter leaves no gap.

    The folder keeps its own number — it matches the author's source folders and
    nothing should disturb that — but a book whose chapters run 21, 23, 24 reads
    as a mistake, so the printed number is assigned in order of appearance.
    """
    return {folder: f"{i:02d}" for i, folder in enumerate(chapters, 1)}


def read_entries(include_all: bool, only: set[str] | None) -> dict[str, list[dict]]:
    index = {s["slug"]: s for s in
             json.loads((ROOT / "data" / "sites.json").read_text(encoding="utf-8"))}
    chapters: dict[str, list[dict]] = {}
    seen: dict[str, str] = {}
    for md in sorted(SITES.rglob("*.md")):
        meta, body = load_frontmatter(md.read_text(encoding="utf-8"))
        slug = md.stem
        if meta.get("status") == "missing":
            continue
        if not include_all and not meta.get("coords"):
            continue
        # a record is filed where the book wants it, which is not always where
        # extract.py put it: a single site can be moved, a whole folder folded.
        folder = md.parent.name
        folder = CHAPTERS["move_sites"].get(slug, folder)
        folder = CHAPTERS["merge_into"].get(folder, folder)
        if only and folder_number(folder) not in only:
            continue
        if slug in seen:                 # anchors must be unique or the index lies
            print(f"warning: duplicate slug {slug!r} in {folder} and {seen[slug]}", file=sys.stderr)
            continue
        seen[slug] = folder
        facts, sources = parse_body(body)
        chapters.setdefault(folder, []).append({
            "slug": slug,
            "name": str(meta.get("name", slug)),
            "meta": meta,
            "facts": facts,
            "sources": sources,
            "order": index.get(slug, {}).get("order", 999),
        })
    for v in chapters.values():
        v.sort(key=lambda e: e["name"].lower())
    return dict(sorted(chapters.items()))


# --------------------------------------------------------------------------
# html
# --------------------------------------------------------------------------

def cover_background(path: Path) -> str:
    """The cover's own paper colour, read from its corner."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            r, g, b = im.convert("RGB").getpixel((2, 2))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return "#ffffff"


def folio_box(anchor: str, folios: dict[str, str] | None) -> str:
    """Page number for an anchor, or a same-width placeholder on the first pass."""
    val = (folios or {}).get(anchor, "000")
    return f'<span class="pg">{esc(val)}</span>'


def entry_html(e: dict, bib: dict, opener: bool = False, fit: int = 1) -> str:
    """One entry, as the three flex children the grid is built from.

    `opener` marks the two entries that share their page with a chapter banner
    and so are cut to a shorter column; `fit` is the body type size the fit
    loop settled on, 1 being the full 9pt.
    """
    meta = e["meta"]
    cls = "entry op" if opener else "entry"
    parts = [f'<article class="{cls}" id="{esc(e["slug"])}">']

    parts.append('<div class="ehead">')
    parts.append(f'<h3>{esc(e["name"])}</h3>')
    state = meta.get("state") or ""
    if state:
        parts.append(f'<p class="state">{esc(state)}</p>')
    cats = meta.get("categories") or []
    if isinstance(cats, str):
        cats = [cats]
    if len(cats) > 1:
        parts.append(f'<p class="also">Also: {esc(", ".join(str(c) for c in cats[1:]))}</p>')
    parts.append('</div>')

    # A sibling of the head, not a child of it: the map is the flexible member
    # of the entry and can only take up the slack if the flex box can see it.
    if (MAPS / f"{e['slug']}.png").exists():
        parts.append(f'<figure class="emap"><img src="../{esc(MAPS.name)}/{esc(e["slug"])}.png" '
                     f'alt="Location of {esc(e["name"])}"/></figure>')

    parts.append(f'<div class="ebody{"" if fit <= 1 else f" f{fit}"}">')
    parts.append('<ul class="facts">')
    for f in e["facts"]:
        parts.append('<li>')
        if f["label"]:
            parts.append(f'<span class="lab">{esc(f["label"])}</span>')
        if f["text"]:
            parts.append(inline(f["text"]))
        if f["subs"]:
            parts.append('<ul class="subs">')
            parts.extend(f'<li>{inline(s)}</li>' for s in f["subs"])
            parts.append('</ul>')
        parts.append('</li>')
    parts.append('</ul>')

    # The written *Sources* line is the author's own and is preferred. Where one
    # was never written, fall back to the frontmatter keys so the entry is not
    # silently unattributed.
    src = e["sources"]
    if src:
        parts.append(f'<p class="src"><span class="lab">Sources</span>{inline(src)}</p>')
    else:
        keys = meta.get("sources") or []
        if isinstance(keys, str):
            keys = [keys]
        if keys:
            parts.append('<p class="src"><span class="lab">Sources</span>'
                         + "; ".join(cite_label(str(k), bib) for k in keys) + '</p>')
    parts.append('</div>')
    parts.append('</article>')
    return "\n".join(parts)


def practice_html() -> str:
    """The front-of-book pointer to the practice map. The exam booklet reuses it."""
    return ('<div class="practice">'
            '<p class="k">Practise on the map</p>'
            '<p>Reading where a place is and placing it yourself are different skills. '
            'Test yourself on every site in this book on the interactive map &mdash; '
            'click where you think it lies and see how close you were.</p>'
            f'<a href="{esc(PRACTICE_URL)}">{esc(PRACTICE_LABEL)}</a>'
            '</div>')


def stamp_practice(c, width: float, y: float) -> None:
    """A clickable practice line, centred in the foot margin between the folios."""
    text_a, text_b = f"{PRACTICE_LINE}  ·  ", PRACTICE_LABEL
    wa = c.stringWidth(text_a, "Helvetica", 7)
    wb = c.stringWidth(text_b, "Helvetica-Bold", 7)
    x = (width - wa - wb) / 2
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.34, 0.34, 0.34)
    c.drawString(x, y, text_a)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0.69, 0.16, 0.13)          # --accent
    c.drawString(x + wa, y, text_b)
    c.linkURL(PRACTICE_URL, (x - 2, y - 3, x + wa + wb + 2, y + 8), relative=0)


def build_html(chapters: dict[str, list[dict]], bib: dict,
               folios: dict[str, str] | None, cover: Path | None,
               fits: dict[str, int] | None = None) -> str:
    total = sum(len(v) for v in chapters.values())
    nums = numbering(chapters)
    fits = fits or {}
    out: list[str] = [
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>',
        f'<title>{esc(TITLE)}</title><style>\n{geometry_css()}{CSS}</style></head><body>',
    ]

    if cover and cover.exists():
        out.append(f'<section class="coverpage" style="background:{cover_background(cover)}">'
                   f'<img src="{esc(cover.name)}" alt="{esc(TITLE)}"/></section>')

    out.append(
        '<section class="titlepage">'
        f'<p class="t">{esc(TITLE)}</p>'
        '<div class="rule"></div>'
        f'<p class="s">{esc(SUBTITLE)}</p>'
        f'<p class="a">{esc(AUTHOR)}</p>'
        f'<p class="e">{esc(EDITION)} &middot; {total} sites &middot; '
        f'{date.today().strftime("%B %Y")}</p>'
        f'{practice_html()}'
        '</section>'
    )

    out.append(f'''<section class="front" id="how-to-use">
<p class="kicker">Front matter</p>
<h2>How this book is arranged</h2>
<p class="lede">Every site the UPSC History Optional map question has drawn on, set out
once, in the chapter where it belongs, with the place shown on a locator map and the
answer-worthy content beneath it.</p>

<h3>The four anchors</h3>
<p>Each entry is written to the shape a map answer is marked on. The labels are the
same in all {total} entries, so the eye learns where to look.</p>
<ul class="anchorkey">
  <li><span class="k">Location</span>Where the site is, and anything odd about that.</li>
  <li><span class="k">Period/Level</span>Material, date, stratigraphy, excavator.</li>
  <li><span class="k">Key&nbsp;Finds</span>The exam-answerable content, one argument to a bullet.</li>
  <li><span class="k">Sources</span>Where the claims come from, by chapter.</li>
</ul>

<h3>The locator maps</h3>
<p>The map beside each name carries one red dot. It answers the question the examiner
is really asking — <em>where in India is this</em> — and nothing more. It is not a
survey map, and distances on it should not be measured.</p>
<p class="note">Positions come from the author&rsquo;s own marked map sheets, resolved
against a gazetteer where one was available. Roughly a third remain as marked by hand
and sit some tens of kilometres from truth: invisible at this scale, but the reason no
entry in this edition prints a coordinate as a number.</p>

<h3>The citations</h3>
<p>Sources are cited by chapter rather than by page. The reference library was scanned
without printed folios, so a page number would locate a passage in a scan and not in the
book; a chapter is the finest locator that is honest. Works cited in full at the back.</p>
<p class="note">Entries carrying no source line draw on the author&rsquo;s own notes and
are marked for sourcing in a later edition.</p>
</section>''')

    # ---- contents ----
    toc = ['<section class="toc" id="contents">',
           '<p class="kicker" style="font-family:Helvetica,Arial,sans-serif;font-size:7.5pt;'
           'letter-spacing:.14em;text-transform:uppercase;color:#b02a22;margin:0 0 1.5mm">'
           'Contents</p>',
           '<h2 style="font-family:Helvetica,Arial,sans-serif;font-size:17pt;margin:0 0 2.5mm;'
           'padding-bottom:2.5mm;border-bottom:2pt solid #b02a22">Contents</h2>',
           '<ol>']
    toc.append('<li><a href="#how-to-use"><span class="n"></span>'
               '<span class="t">How this book is arranged</span>'
               f'<span class="dots"></span>{folio_box("how-to-use", folios)}</a></li>')
    for folder, entries in chapters.items():
        num, ctitle = nums[folder], chapter_title(folder)
        anchor = f"ch-{num}"
        toc.append(
            f'<li><a href="#{anchor}"><span class="n">{esc(num)}</span>'
            f'<span class="t">{esc(ctitle)} <span class="c">{len(entries)} sites</span></span>'
            f'<span class="dots"></span>{folio_box(anchor, folios)}</a></li>')
    toc.append('<hr class="sep"/>')
    for anchor, label in (("works-cited", "Works Cited"),
                          ("index-sites", "Index of Sites"),
                          ("index-states", "Sites by State")):
        toc.append(f'<li><a href="#{anchor}"><span class="n"></span>'
                   f'<span class="t">{esc(label)}</span><span class="dots"></span>'
                   f'{folio_box(anchor, folios)}</a></li>')
    toc.append('</ol></section>')
    out.append("\n".join(toc))

    # ---- chapters ----
    for folder, entries in chapters.items():
        num, ctitle = nums[folder], chapter_title(folder)
        out.append(f'<section class="chapter" id="ch-{esc(num)}">')
        out.append(f'<header class="chead"><p class="num">Chapter {esc(num)}</p>'
                   f'<h2>{esc(ctitle)}</h2>'
                   f'<p class="count">{len(entries)} '
                   f'{"site" if len(entries) == 1 else "sites"}</p></header>')
        out.append('<div class="cols">')
        # the first two share the banner's page, so they get the short column
        out.extend(entry_html(e, bib, opener=i < 2, fit=fits.get(e["slug"], 1))
                   for i, e in enumerate(entries))
        out.append('</div></section>')

    # ---- works cited ----
    cited: set[str] = set()
    for entries in chapters.values():
        for e in entries:
            keys = e["meta"].get("sources") or []
            if isinstance(keys, str):
                keys = [keys]
            cited.update(str(k).split("#")[0] for k in keys)
    items = []
    for key in sorted(cited):
        w = bib.get(key)
        if not w:
            continue
        bits = [f"{esc(str(w.get('author', '')).rstrip('.'))}. <em>{esc(w['title'])}</em>."]
        place, pub, yr = w.get("place"), w.get("publisher"), w.get("year")
        if place and pub:
            bits.append(f"{esc(place)}: {esc(pub)}{',' if yr else '.'}")
        if yr:
            bits.append(f"{yr}.")
        items.append("<li>" + " ".join(bits) + "</li>")
    out.append('<section class="back" id="works-cited"><h2>Works Cited</h2>'
               '<p class="lede">Works from which entries in this book are sourced. '
               'Cited by chapter throughout; see the note in the front matter.</p>'
               '<ul class="bib">' + "\n".join(items) + '</ul></section>')

    # ---- index of sites ----
    flat = [(e, nums[f]) for f, v in chapters.items() for e in v]
    out.append('<section class="back" id="index-sites"><h2>Index of Sites</h2>'
               '<p class="lede">Every site in the book, alphabetically, with the chapter '
               'it is filed under.</p><div class="index">')
    letter = ""
    for e, num in sorted(flat, key=lambda t: t[0]["name"].lower()):
        first = e["name"][:1].upper()
        if first != letter:
            letter = first
            out.append(f'<p class="grp">{esc(letter)}</p>')
        out.append(f'<p class="ix"><a href="#{esc(e["slug"])}">{esc(e["name"])}</a>'
                   f'<span class="ch">{esc(num)}</span><span class="dots"></span>'
                   f'{folio_box(e["slug"], folios)}</p>')
    out.append('</div></section>')

    # ---- sites by state ----
    by_state: dict[str, list[tuple[dict, str]]] = {}
    for e, num in flat:
        by_state.setdefault(str(e["meta"].get("state") or "Not stated"), []).append((e, num))
    out.append('<section class="back" id="index-states"><h2>Sites by State</h2>'
               '<p class="lede">The same sites grouped by modern state — the way the map '
               'question is usually revised.</p><div class="index">')
    for state in sorted(by_state, key=lambda s: (s == "Not stated", s)):
        out.append(f'<p class="grp">{esc(state)} <span style="color:#565656">'
                   f'{len(by_state[state])}</span></p>')
        for e, num in sorted(by_state[state], key=lambda t: t[0]["name"].lower()):
            out.append(f'<p class="ix"><a href="#{esc(e["slug"])}">{esc(e["name"])}</a>'
                       f'<span class="dots"></span>{folio_box(e["slug"], folios)}</p>')
    out.append('</div></section>')

    out.append('</body></html>')
    return "\n".join(out)


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------

def find_browser() -> str:
    for cand in BROWSERS:
        if Path(cand).is_file():
            return cand
        found = shutil.which(cand)
        if found:
            return found
    raise SystemExit("no Chrome or Edge found — install one, or add it to PATH")


def render(browser: str, html_path: Path, pdf_path: Path) -> None:
    """HTML -> PDF through headless Chrome.

    A throwaway --user-data-dir is essential: without it the run attaches to the
    signed-in profile and fails outright when a Chrome window is already open.
    """
    if pdf_path.exists():
        pdf_path.unlink()
    with tempfile.TemporaryDirectory(prefix="mapbook-chrome-") as profile:
        cmd = [
            browser, "--headless", "--disable-gpu", "--disable-extensions",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            "--virtual-time-budget=120000",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if not pdf_path.exists():
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(f"{Path(browser).name} produced no PDF")


# --------------------------------------------------------------------------
# fitting
# --------------------------------------------------------------------------

def overflow_entries(pdf: Path, order: list[str], dests: dict[str, int]) -> set[str]:
    """Slugs whose entry did not fit the column it was cut for.

    `break-inside: avoid` is a request, not a guarantee: faced with a box
    taller than any column it could go in, Chrome breaks it anyway. So the
    symptom is not ink spilling below the foot of the box — that only happens
    where there is no next column to escape into — it is a second column
    whose first ink is not its own entry's name.

    Both are checked. A column is sound when its topmost ink is the 11pt name
    that heads it; anything above that line arrived from the entry before.
    The chapter banner is ink above the name too, so on the pages that carry
    one the banner's band is cut away first.

    Two entries to a page, left column first, is what turns a page and an x
    back into a slug. That holds because none is short enough for two to
    share a column.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(pdf))

    # every entry's slot, in reading order
    slots: list[tuple[str, int, int]] = []
    filled: dict[int, int] = {}
    for slug in order:
        page = dests.get(slug)
        if page is None:
            continue
        col = filled.get(page, 0)
        filled[page] = col + 1
        slots.append((slug, page, col))

    openers = {p for a, p in dests.items() if re.fullmatch(r"ch-\d+", a)}
    head_y: dict[tuple[int, int], float] = {}
    ink_y: dict[tuple[int, int], float] = {}
    below: set[tuple[int, int]] = set()

    for page_no in sorted({p for _, p, _ in slots} | {p + 1 for _, p, _ in slots}):
        if page_no >= len(reader.pages):
            continue
        page = reader.pages[page_no]
        middle = float(page.mediabox.width) / 2
        ceiling = OPENER_TOP_PT if page_no in openers else float("inf")

        def visit(text, cm, tm, font, size, pg=page_no, mid=middle, top=ceiling):
            if not text.strip():
                return
            # text-space origin through the CTM, i.e. where it sits on the page
            x = cm[0] * tm[4] + cm[2] * tm[5] + cm[4]
            y = cm[1] * tm[4] + cm[3] * tm[5] + cm[5]
            if y > top:                      # the chapter banner, not an entry
                return
            key = (pg, 0 if x < mid else 1)
            ink_y[key] = max(ink_y.get(key, -1e9), y)
            if y < ENTRY_FOOT_PT:
                below.add(key)
            name = str(font.get("/BaseFont", "")) if hasattr(font, "get") else ""
            if "Arial-Bold" in name and abs(size * abs(cm[3]) - HEAD_PT) < 0.3:
                head_y[key] = max(head_y.get(key, -1e9), y)

        page.extract_text(visitor_text=visit)

    entry_pages = {p for _, p, _ in slots}
    last_page = max(entry_pages, default=-1)

    over: set[str] = set()
    for slug, page, col in slots:
        if (page, col) in below:             # nowhere to break to, so it spilled
            over.add(slug)
        nxt = (page, 1) if col == 0 else (page + 1, 0)
        # past the last entry the ink is the back matter, which heads itself
        if nxt[0] > last_page:
            continue
        if nxt not in ink_y:                 # nothing follows it in that column
            continue
        head = head_y.get(nxt)
        if head is None or ink_y[nxt] > head + 2:
            over.add(slug)
    return over


# --------------------------------------------------------------------------
# page numbers, folios, bookmarks
# --------------------------------------------------------------------------

ROMAN = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
         (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]


def roman(n: int) -> str:
    out = ""
    for v, s in ROMAN:
        while n >= v:
            out += s
            n -= v
    return out


def read_destinations(pdf: Path) -> dict[str, int]:
    """anchor -> zero-based PDF page index, from the catalog's named destinations."""
    from pypdf import PdfReader
    r = PdfReader(str(pdf))
    pages = {p.indirect_reference.idnum: i for i, p in enumerate(r.pages)}
    dests: dict[str, int] = {}

    def resolve(name: str, value) -> None:
        try:
            arr = value.dest_array if hasattr(value, "dest_array") else value
            ref = arr[0]
            idx = pages.get(getattr(ref, "idnum", None))
            if idx is None:                      # already a resolved page object
                idx = pages.get(getattr(getattr(ref, "indirect_reference", None), "idnum", None))
            if idx is not None:
                dests[str(name).lstrip("/")] = idx
        except Exception:
            pass

    root = r.trailer["/Root"]
    direct = root.get("/Dests")
    if direct:
        for k, v in direct.get_object().items():
            resolve(k, v)
    try:
        for k, v in (r.named_destinations or {}).items():
            resolve(k, v)
    except Exception:
        pass
    return dests


def page_labels(n_pages: int, body_start: int, cover: bool) -> list[str]:
    """Printed folio for every page: cover blank, front matter roman, body arabic."""
    labels = []
    for i in range(n_pages):
        if cover and i == 0:
            labels.append("")
        elif i < body_start:
            labels.append(roman(i if cover else i + 1))
        else:
            labels.append(str(i - body_start + 1))
    return labels


def stamp(src: Path, dst: Path, labels: list[str], heads: dict[int, str],
          outline: list[tuple[str, int, list[tuple[str, int]]]], no_folio: set[int],
          no_footer: set[int] = frozenset()) -> None:
    """Merge running heads and folios into the margins, then write bookmarks."""
    from io import BytesIO
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    W, H = A4
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for i, label in enumerate(labels):
        if i not in no_footer:
            stamp_practice(c, W, 28.3)
        if i not in no_folio:
            # The cover is leaf one and sits on the right, so even indexes are
            # rectos and the folio belongs on the outer — right — edge.
            recto = (i % 2 == 0)
            x = W - 39.7 if recto else 39.7  # 14mm margins
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(0.34, 0.34, 0.34)
            if recto:
                c.drawRightString(x, 28.3, label)
            else:
                c.drawString(x, 28.3, label)
            head = heads.get(i, "")
            if head:
                c.setFont("Helvetica", 7)
                c.setFillColorRGB(0.55, 0.55, 0.55)
                if recto:
                    c.drawRightString(x, H - 33, head)
                else:
                    c.drawString(x, H - 33, head)
        c.showPage()
    c.save()
    buf.seek(0)

    marks = PdfReader(buf)
    # Clone, do not rebuild. A fresh PdfWriter starts with an empty catalog, and
    # the /Dests name tree lives there — dropping it turns every `/Dest /ch-01`
    # link annotation into a dangling name, so the contents and both indexes
    # render as clickable text that goes nowhere while the bookmarks, which
    # carry explicit page references, keep working and hide the breakage.
    writer = PdfWriter(clone_from=str(src))
    for i, page in enumerate(writer.pages):
        if i < len(marks.pages):
            page.merge_page(marks.pages[i])

    writer.add_metadata({
        "/Title": TITLE, "/Author": AUTHOR, "/Subject": SUBTITLE,
        "/Creator": "pipeline/build_pdf.py", "/Keywords":
        "UPSC, History Optional, map question, archaeology, India",
    })
    for title, page, children in outline:
        parent = writer.add_outline_item(title, min(page, len(writer.pages) - 1))
        for ctitle, cpage in children:
            writer.add_outline_item(ctitle, min(cpage, len(writer.pages) - 1), parent=parent)

    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "wb") as fh:
        writer.write(fh)


# --------------------------------------------------------------------------

def main() -> int:
    argv = sys.argv[1:]
    include_all = "--all" in argv
    fast = "--fast" in argv
    only: set[str] | None = None
    if "--chapters" in argv:
        only = {c.strip().zfill(2) for c in argv[argv.index("--chapters") + 1].split(",")}

    if not MAPS.is_dir():
        print("run pipeline/render_maps.py first", file=sys.stderr)
        return 1
    chapters = read_entries(include_all, only)
    if not chapters:
        print("no entries to build", file=sys.stderr)
        return 1
    bib = json.loads((ROOT / "data" / "bibliography.json").read_text(encoding="utf-8"))
    nums = numbering(chapters)          # the same mapping build_html anchors on

    WORK.mkdir(parents=True, exist_ok=True)
    cover_src = ROOT / "build" / "cover.png"
    cover = WORK / "cover.png"
    if cover_src.exists():
        if not cover.exists() or cover_src.stat().st_mtime > cover.stat().st_mtime:
            shutil.copyfile(cover_src, cover)
    else:
        cover = None
        print("warning: build/cover.png missing — run pipeline/render_cover.py", file=sys.stderr)

    browser = find_browser()
    html_path, raw = WORK / "book.html", WORK / "book-raw.pdf"
    total = sum(len(v) for v in chapters.values())
    print(f"engine   : {Path(browser).name}")
    print(f"entries  : {total} in {len(chapters)} chapters")

    # Pass one sets the book with placeholder folios and reads back where every
    # anchor landed; pass two prints the real numbers. Repeated until the
    # pagination stops moving, which in practice is immediately.
    #
    # The same loop does the fitting. An entry is cut to the column's height,
    # so one whose body will not go prints out of the bottom of its box; the
    # render is read back for exactly that and the offenders come round again
    # a type size smaller. In practice a handful of entries need one step and
    # the loop is clean on the second pass.
    folios: dict[str, str] | None = None
    fits: dict[str, int] = {}
    order = [e["slug"] for entries in chapters.values() for e in entries]
    dests: dict[str, int] = {}
    labels: list[str] = []
    for attempt in range(1 if fast else 3 + FIT_STEPS):
        html_path.write_text(build_html(chapters, bib, folios, cover, fits), encoding="utf-8")
        render(browser, html_path, raw)
        dests = read_destinations(raw)
        from pypdf import PdfReader
        n_pages = len(PdfReader(str(raw)).pages)
        first_chapter = min((dests[f"ch-{nums[f]}"] for f in chapters
                             if f"ch-{nums[f]}" in dests), default=1)
        labels = page_labels(n_pages, first_chapter, cover is not None)
        new = {a: labels[i] for a, i in dests.items() if i < len(labels)}

        over = overflow_entries(raw, order, dests)
        bumped = {s: fits.get(s, 1) + 1 for s in over if fits.get(s, 1) < FIT_STEPS}
        note = f", {len(over)} overflowing" if over else ""
        print(f"pass {attempt + 1}    : {n_pages} pages, {len(dests)} anchors located{note}")
        if bumped:                       # refitting moves the type, so it moves the pages
            fits.update(bumped)
            folios = new
            continue
        if over:
            print(f"warning: {len(over)} entries still overrun the column at the "
                  f"smallest size: {', '.join(sorted(over))}", file=sys.stderr)
        if new == folios:
            break
        folios = new
    else:
        if not fast:
            print("note: pagination still shifting; numbers are from the last render",
                  file=sys.stderr)
    if fits:
        steps = ", ".join(f"f{n}×{sum(1 for v in fits.values() if v == n)}"
                          for n in sorted(set(fits.values())))
        print(f"refitted : {len(fits)} entries stepped down ({steps})")

    # running heads, and a bookmark tree of chapter -> site
    heads: dict[int, str] = {}
    outline: list[tuple[str, int, list[tuple[str, int]]]] = []
    if "how-to-use" in dests:
        outline.append(("How this book is arranged", dests["how-to-use"], []))
    if "contents" in dests:
        outline.append(("Contents", dests["contents"], []))
    chapter_starts = sorted(
        ((dests[f"ch-{nums[f]}"], f) for f in chapters if f"ch-{nums[f]}" in dests))
    back = sorted((dests[a], t) for a, t in (("works-cited", "Works Cited"),
                                             ("index-sites", "Index of Sites"),
                                             ("index-states", "Sites by State")) if a in dests)
    bounds = [p for p, _ in chapter_starts] + [back[0][0] if back else len(labels)]
    for n, (start, folder) in enumerate(chapter_starts):
        # ASCII only: a bookmark label is written in the PDF's own string
        # encoding and readers disagree about anything outside it.
        title = f"{nums[folder]}  {chapter_title(folder)}"
        for p in range(start, bounds[n + 1]):
            heads[p] = chapter_title(folder)
        kids = [(e["name"], dests[e["slug"]]) for e in chapters[folder] if e["slug"] in dests]
        outline.append((title, start, kids))
    for n, (start, title) in enumerate(back):
        end = back[n + 1][0] if n + 1 < len(back) else len(labels)
        for p in range(start, end):
            heads[p] = title
        outline.append((title, start, []))

    no_folio = {i for i, l in enumerate(labels) if not l}
    if cover is not None:
        no_folio.add(0)
        no_folio.add(1)                     # title page carries no printed folio
    for start, _ in chapter_starts:
        heads.pop(start, None)              # a chapter opener is its own heading
    for start, _ in back:
        heads.pop(start, None)

    stamp(raw, OUT, labels, heads, outline, no_folio,
          no_footer={0} if cover is not None else set())

    body_pages = len(labels) - (min(p for p, _ in chapter_starts) if chapter_starts else 0)
    print(f"pages    : {len(labels)}  ({body_pages} numbered)")
    print(f"bookmarks: {len(outline)} sections, "
          f"{sum(len(k) for _, _, k in outline)} sites")
    print(f"output   : {OUT.relative_to(ROOT)}  ({OUT.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
