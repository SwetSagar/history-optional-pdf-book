"""Assemble the revision booklet: one locator and one 30-50 word note per site.

    python3 pipeline/build_exam_pdf.py

The atlas prints the whole entry — a median of 230 words — because a reference
book should. The map question gives you twenty places and about 30-50 words
each, under time, and revising for that out of the atlas means reading six times
what you can write. This is the same corpus set for the other job: three columns,
a locator, and the note.

Notes come from data/exam-notes.json, so the booklet cannot drift from the
condenser. Run `pipeline/exam_notes.py --write` first; this refuses to build from
a stale file rather than printing yesterday's wording.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_pdf import CHAPTERS, chapter_title, esc, find_browser, render  # noqa: E402
from common import load_frontmatter  # noqa: E402
from exam_notes import build as build_notes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT / "sites"
NOTES = ROOT / "data" / "exam-notes.json"
MAPS = ROOT / "build" / "maps-print"
MAPS_FALLBACK = ROOT / "build" / "maps"
WORK = ROOT / "build" / "pdf"
OUT = ROOT / "build" / "Exam Notes for History Optional.pdf"

TITLE = "Exam Notes for History Optional"
SUBTITLE = "Every site in the map question, in the words you have time to write"

CSS = """\
:root { --ink:#1a1a1a; --muted:#565656; --accent:#b02a22; --rule:#d5d5d5; --hairline:#ececec; }

@page { size: A4; margin: 15mm 14mm 16mm 14mm; }

html { font-size: 9pt; }
body {
  margin: 0; font-family: Georgia, "Charis SIL", "Times New Roman", serif;
  color: var(--ink); line-height: 1.34; orphans: 2; widows: 2;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.sans { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }

/* ---------- front ---------- */
.title { break-after: page; padding-top: 60mm; text-align: center; }
.title h1 {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 25pt; font-weight: 700; margin: 0 0 5mm; line-height: 1.15;
}
.title .rule { width: 26mm; height: 2pt; background: var(--accent); margin: 0 auto 5mm; }
.title .s { font-size: 11pt; font-style: italic; color: var(--muted); max-width: 120mm;
            margin: 0 auto 12mm; line-height: 1.5; }
.title .meta { font-size: 8.5pt; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }

.howto { break-after: page; }
.howto h2 { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 15pt; font-weight: 700; margin: 0 0 3mm; }
.howto p { margin: 0 0 3.5mm; max-width: 150mm; }
.howto .warn { border-left: 2pt solid var(--accent); padding-left: 4mm; color: var(--muted); }

/* ---------- chapters ---------- */
.chapter { break-before: page; }
.chead { margin: 0 0 4mm; padding-bottom: 2mm; border-bottom: 2pt solid var(--accent); }
.chead .num { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
              font-size: 7pt; font-weight: 700; letter-spacing: 0.16em;
              text-transform: uppercase; color: var(--accent); margin: 0 0 1mm; }
.chead h2 { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 15pt; font-weight: 700; margin: 0; line-height: 1.15; }

/* Four columns, not three. At three the map is 56mm, a card is about 95mm, and
   three of them do not fit the 267mm text height — so each column took two and
   a third of every page was white. Four puts the map at 42mm, the card at about
   77mm, and three to a column: twelve cards a page instead of six. The dot is
   still placeable against a state boundary at that size, which is the only job
   the locator has here; the atlas is where a map gets a full column. */
.cols { column-count: 4; column-gap: 5mm; }

/* ---------- card ----------
   The whole card is unbreakable, which the atlas could not afford: there an
   entry was taller than half a column, so binding it whole ejected it and left
   the gap the layout existed to avoid. A card here is about a third of a
   column, so it can be kept together and never splits a note from its map. */
.card { break-inside: avoid; margin: 0 0 3.5mm; padding-bottom: 3mm;
        border-bottom: 0.5pt solid var(--hairline); }
.card img {
  display: block; width: 100%; height: auto; box-sizing: border-box;
  border: 0.5pt solid var(--rule); border-radius: 1pt; margin: 0 0 1.2mm;
}
.card h3 { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
           font-size: 8.6pt; font-weight: 700; margin: 0; line-height: 1.18; }
.card .where { font-size: 6.6pt; font-style: italic; color: var(--muted); margin: 0.3mm 0 1.1mm; }
.card .note { font-size: 7pt; line-height: 1.3; margin: 0; text-align: left; hyphens: auto; }
.card .pyq { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
             font-size: 6pt; font-weight: 700; letter-spacing: 0.06em;
             text-transform: uppercase; color: var(--accent); margin: 1mm 0 0; }
"""


def map_for(slug: str) -> Path | None:
    for folder in (MAPS, MAPS_FALLBACK):
        candidate = folder / f"{slug}.png"
        if candidate.exists():
            return candidate
    return None


def collect() -> tuple[dict, dict]:
    """Cards grouped by printed chapter, and the PYQ frequency per slug."""
    payload = build_notes()
    if NOTES.exists():
        on_disk = json.loads(NOTES.read_text(encoding="utf-8"))
        if on_disk.get("notes") != payload["notes"]:
            raise SystemExit(
                "data/exam-notes.json is stale — run `python3 pipeline/exam_notes.py --write`")

    frequency = {}
    web = ROOT / "data" / "web-sites.json"
    if web.exists():
        for site in json.loads(web.read_text(encoding="utf-8"))["sites"]:
            frequency[site["slug"]] = site["pyq"]["frequency"]

    by_slug = {n["slug"]: n for n in payload["notes"]}
    chapters: dict[str, list[dict]] = {}
    for path in sorted(SITES.rglob("*.md")):
        note = by_slug.get(path.stem)
        if not note or not note["note"]:
            continue
        folder = CHAPTERS.get("move_sites", {}).get(path.stem, path.parent.name)
        folder = CHAPTERS.get("merge_into", {}).get(folder, folder)
        chapters.setdefault(folder, []).append(note)
    for entries in chapters.values():
        entries.sort(key=lambda n: n["name"].casefold())
    return dict(sorted(chapters.items())), frequency


def card_html(note: dict, frequency: dict) -> str:
    image = map_for(note["slug"])
    parts = ['<article class="card">']
    if image:
        parts.append(f'<img src="{image.as_uri()}" alt="">')
    parts.append(f'<h3>{esc(note["name"])}</h3>')
    where = " · ".join(x for x in [note.get("stateOrRegion") or "",
                                   ", ".join(note.get("categories") or [])] if x)
    if where:
        parts.append(f'<p class="where">{esc(where)}</p>')
    parts.append(f'<p class="note">{esc(note["note"])}</p>')
    asked = frequency.get(note["slug"], 0)
    if asked:
        parts.append(f'<p class="pyq">Asked {asked}&times;</p>')
    parts.append("</article>")
    return "".join(parts)


def build_html(chapters: dict, frequency: dict) -> str:
    total = sum(len(v) for v in chapters.values())
    out = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        f"<title>{esc(TITLE)}</title><style>{CSS}</style></head><body>",
        '<section class="title">',
        f"<h1>{esc(TITLE)}</h1><div class=\"rule\"></div>",
        f'<p class="s">{esc(SUBTITLE)}</p>',
        f'<p class="meta">{total} sites &nbsp;·&nbsp; {len(chapters)} chapters '
        f'&nbsp;·&nbsp; {date.today():%B %Y}</p>',
        "</section>",
        '<section class="howto"><h2>How to use this</h2>',
        "<p>One card to a site: the locator, the name, where it is, and a note of "
        "roughly thirty to fifty words — the length the map question actually "
        "leaves you time to write. Cover the note, look at the dot, say the place; "
        "then cover the map, read the name, and place it.</p>",
        "<p>Cards carry <span class=\"pyq\">Asked N&times;</span> where the place has "
        "appeared in a past map question. That count is mined from the papers in "
        "<code>corpus_pyq/</code> and each occurrence records the page it came from.</p>",
        '<p class="warn">These notes are condensed from the full entries in the atlas, '
        'clause by clause — nothing here is paraphrased and no fact has been added. '
        'They are drafts for revision, not a substitute for reading the entry, and '
        'they have not been through an editorial pass. Where a note reads thin, the '
        'atlas has the whole of it.</p>',
        "</section>",
    ]
    for folder, entries in chapters.items():
        out.append('<section class="chapter"><div class="chead">')
        out.append(f'<p class="num">{esc(folder.split("-")[0])} &nbsp;·&nbsp; '
                   f'{len(entries)} sites</p>')
        out.append(f"<h2>{esc(chapter_title(folder))}</h2></div>")
        out.append('<div class="cols">')
        out.extend(card_html(n, frequency) for n in entries)
        out.append("</div></section>")
    out.append("</body></html>")
    return "".join(out)


def stamp_folios(src: Path, dst: Path, heads: dict[int, str]) -> None:
    """Folio on the outer edge, chapter name opposite. Two pages of front matter
    carry neither — a number on a title page is furniture nobody reads."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    W, H = A4
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    reader = PdfReader(str(src))
    for i in range(len(reader.pages)):
        if i >= 2:
            recto = i % 2 == 0
            x = W - 40 if recto else 40
            c.setFont("Helvetica", 7.5)
            c.setFillColorRGB(0.34, 0.34, 0.34)
            c.drawRightString(x, 26, str(i - 1)) if recto else c.drawString(x, 26, str(i - 1))
            head = heads.get(i, "")
            if head:
                c.setFont("Helvetica", 7)
                c.setFillColorRGB(0.55, 0.55, 0.55)
                if recto:
                    c.drawRightString(W - 40, H - 30, head)
                else:
                    c.drawString(40, H - 30, head)
        c.showPage()
    c.save()
    buf.seek(0)

    overlay = PdfReader(buf)
    writer = PdfWriter()
    for page, extra in zip(reader.pages, overlay.pages):
        page.merge_page(extra)
        writer.add_page(page)
    with open(dst, "wb") as fh:
        writer.write(fh)


def running_heads(pdf: Path, chapters: dict) -> dict[int, str]:
    """Which chapter each page belongs to, read back off the rendered pages."""
    import pymupdf
    titles = {chapter_title(folder) for folder in chapters}
    doc = pymupdf.open(pdf)
    heads, current = {}, ""
    for i, page in enumerate(doc):
        text = page.get_text()
        for title in titles:
            if title in text[:400]:
                current = title
                break
        heads[i] = current
    doc.close()
    return heads


def main() -> int:
    chapters, frequency = collect()
    total = sum(len(v) for v in chapters.values())
    if not total:
        raise SystemExit("no notes — run `python3 pipeline/exam_notes.py --write` first")

    WORK.mkdir(parents=True, exist_ok=True)
    html_path = WORK / "exam-notes.html"
    html_path.write_text(build_html(chapters, frequency), encoding="utf-8", newline="\n")

    browser = find_browser()
    print(f"engine   : {Path(browser).name}")
    print(f"cards    : {total} in {len(chapters)} chapters")

    raw = WORK / "exam-notes-raw.pdf"
    render(browser, html_path, raw)
    heads = running_heads(raw, chapters)
    stamp_folios(raw, OUT, heads)

    import pymupdf
    doc = pymupdf.open(OUT)
    print(f"pages    : {doc.page_count}")
    doc.close()
    print(f"output   : {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
