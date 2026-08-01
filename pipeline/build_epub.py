"""Assemble the eBook from sites/*.md and build/maps/.

    python3 pipeline/build_epub.py [--all]

Produces a reflowable EPUB 3. Reflowable rather than fixed-layout because each
entry is self-contained, so it stays readable on a phone — fixed-layout would
lock the page and ruin that.

By default only sites that have BOTH text and a coordinate are included, which
is the edition-one scope. --all includes every site carrying text.

Nothing here invents content: entries render exactly what is in the Markdown,
and an entry still carrying imported bullets is marked in the proof so an
unrewritten entry cannot slip into a published file unnoticed.
"""
from __future__ import annotations

import html
import json
import re
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT / "sites"
MAPS = ROOT / "build" / "maps"
OUT = ROOT / "build" / "Map Entries for History Optional.epub"

TITLE = "Map Entries for History Optional"
SUBTITLE = "A referenced atlas of the sites in the UPSC History Optional map question"
AUTHOR = "Swet Sagar"
LANG = "en"
UUID = "urn:uuid:8f4e2c10-1d3a-4b77-9c21-0a6b5e9d4f31"

CSS = """\
/* --------------------------------------------------------------------------
   Production stylesheet, from DESIGN_SYSTEM.md.

   One deviation from that spec: `break-inside: avoid` is applied to the entry
   HEADER (name + map + location) rather than to the whole entry. A complete
   entry — a full-width square map plus four bullets and a citation — is taller
   than a phone page, and an unbreakable block taller than the page makes
   readers eject it to the next page, leaving exactly the large gap this
   project already fixed once. Binding the header keeps a site glued to its map,
   which is the actual requirement, without the blank-page risk.
   -------------------------------------------------------------------------- */

:root {
  --color-bg: #ffffff;
  --color-text-main: #1a1a1a;
  --color-text-muted: #555555;
  --color-accent-red: #b02a22;
  --color-border: #e2e2e2;
  --color-draft-bg: #fff5f5;
  --color-draft-border: #a03028;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #121212;
    --color-text-main: #e0e0e0;
    --color-text-muted: #a0a0a0;
    --color-accent-red: #ff6b6b;
    --color-border: #2d2d2d;
    --color-draft-bg: #2c1e1e;
    --color-draft-border: #ff6b6b;
  }
}

html { font-size: 100%; background-color: var(--color-bg); color: var(--color-text-main); }

body {
  margin: 0 4%;
  line-height: 1.5;
  font-family: "Georgia", "Charis SIL", "Times New Roman", serif;
  font-weight: 400;
}

h1 {
  font-family: "Helvetica Neue", "Inter", "Arial", sans-serif;
  font-size: 1.6em; font-weight: 700; margin: 1.4em 0 0.2em;
  color: var(--color-text-main);
  border-bottom: 2px solid var(--color-accent-red);
  padding-bottom: 0.2em;
}

h2 {
  font-family: "Helvetica Neue", "Inter", "Arial", sans-serif;
  font-size: 1.25em; font-weight: 600; margin: 1.5em 0 0.05em;
  color: var(--color-text-main);
  page-break-after: avoid; break-after: avoid;
}

.chapter-range {
  font-family: "Helvetica Neue", "Inter", sans-serif;
  font-size: 0.8em; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--color-text-muted); margin: 0 0 1.2em;
}

.loc {
  font-size: 0.9em; color: var(--color-text-muted); margin: 0 0 0.15em;
  font-style: italic; page-break-after: avoid; break-after: avoid;
}

.tags {
  font-family: "Helvetica Neue", "Inter", sans-serif;
  font-size: 0.75em; color: var(--color-text-muted); letter-spacing: 0.04em;
  margin: 0 0 0.3em; page-break-after: avoid; break-after: avoid;
}

.site-entry { margin-bottom: 1.8em; }

/* name + map + location travel together; see note above */
.entry-head { page-break-inside: avoid; break-inside: avoid; }

figure {
  margin: 0.4em 0 0.7em; text-align: center;
  page-break-inside: avoid; break-inside: avoid;
  page-break-before: avoid; break-before: avoid;
  page-break-after: avoid; break-after: avoid;
}

figure img {
  width: 100%; max-width: 100%; height: auto;
  border-radius: 4px; border: 1px solid var(--color-border);
}

ul.facts { margin: 0.4em 0 0.6em; padding-left: 1.2em; }
ul.facts li { margin-bottom: 0.35em; line-height: 1.48; }
ul.facts li strong {
  font-family: "Helvetica Neue", "Inter", sans-serif;
  font-size: 0.88em; color: var(--color-text-main); letter-spacing: 0.01em;
}

.citation {
  font-size: 0.82em; color: var(--color-text-muted);
  border-top: 1px dashed var(--color-border);
  padding-top: 0.4em; margin-top: 0.6em; font-style: italic;
}
.citation strong {
  font-style: normal;
  font-family: "Helvetica Neue", "Inter", sans-serif;
  font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.05em;
}

.draft {
  font-family: "Helvetica Neue", "Inter", sans-serif;
  font-size: 0.75em; color: var(--color-draft-border);
  background-color: var(--color-draft-bg);
  border: 1px solid var(--color-draft-border);
  border-radius: 3px; padding: 0.3em 0.6em; margin: 0.5em 0;
}

.coverpage { margin: 0; padding: 0; text-align: center; }
.coverpage img { width: 100%; max-width: 100%; height: auto; border: 0; border-radius: 0; }
.front p { margin: 0.8em 0; }
.front .title { font-size: 2.2em; line-height: 1.2; margin: 2em 0 0.2em; font-weight: 700; }
.front .sub { font-size: 1em; color: var(--color-text-muted); font-style: italic; }
.bib { font-size: 0.9em; padding-left: 0; }
.bib li { margin-bottom: 0.6em; padding-left: 1.2em; text-indent: -1.2em; list-style: none; }

hr { border: 0; border-top: 1px solid var(--color-border); margin: 2em 0; }
"""


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def xhtml(title: str, body: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" lang="%s" xml:lang="%s">\n'
        '<head><meta charset="utf-8"/><title>%s</title>'
        '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
        '<body>\n%s\n</body>\n</html>\n' % (LANG, LANG, esc(title), body)
    )


def read_sites(include_all: bool) -> dict[str, list[dict]]:
    """Load records from Markdown, grouped by chapter, in roadmap order."""
    index = {s["slug"]: s for s in
             json.loads((ROOT / "data" / "sites.json").read_text(encoding="utf-8"))}
    chapters: dict[str, list[dict]] = {}
    for md in sorted(SITES.rglob("*.md")):
        meta, body = load_frontmatter(md.read_text(encoding="utf-8"))
        slug = md.stem
        rec = index.get(slug, {})
        if meta.get("status") == "missing":
            continue
        if not include_all and not meta.get("coords"):
            continue
        chapter = md.parent.name
        chapters.setdefault(chapter, []).append({
            "slug": slug, "meta": meta, "body": body,
            "name": meta.get("name", slug),
            "order": rec.get("order", 999),
        })
    for v in chapters.values():
        v.sort(key=lambda e: e["name"].lower())
    return dict(sorted(chapters.items()))


def body_to_html(body: str) -> tuple[str, bool]:
    """Markdown body -> XHTML. Returns (html, still_has_imported_bullets)."""
    imported = "IMPORTED FROM YOUR CARDS" in body
    text = re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()
    paras: list[str] = []
    bullets: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            bullets.append(line[2:].strip())
        else:
            paras.append(line)
    out = "".join(f"<p>{esc(p)}</p>\n" for p in paras)
    if bullets:
        out += ('<ul class="facts">\n'
                + "".join(f"  <li>{esc(b)}</li>\n" for b in bullets)
                + "</ul>\n")
    return out, imported


def chapter_title(folder: str) -> str:
    return re.sub(r"^\d+-", "", folder).replace("-", " ").title()


def cite_label(ref: str, bib: dict) -> str:
    """'upinder2008#4. Harappan Civilization@69' -> a readable chapter citation.

    Deliberately no page number: these scans carry no printed folios, so the
    locator would be a page in a scan rather than in the book.
    """
    key, _, rest = ref.partition("#")
    chapter = rest.split("@")[0].strip()
    w = bib.get(key, {})
    who = w.get("author", key)
    title = w.get("title", "")
    out = f"{esc(who)}, <em>{esc(title)}</em>"
    if chapter:
        out += f", {esc(chapter)}"
    return out


def build(include_all: bool) -> int:
    if not MAPS.is_dir():
        print("run pipeline/render_maps.py first", file=sys.stderr)
        return 1
    chapters = read_sites(include_all)
    if not chapters:
        print("no entries to build", file=sys.stderr)
        return 1

    files: dict[str, bytes] = {}
    manifest: list[str] = []
    spine: list[str] = []
    nav: list[str] = []
    used_maps: set[str] = set()
    cited: set[str] = set()
    bib = json.loads((ROOT / "data" / "bibliography.json").read_text(encoding="utf-8"))
    total = drafts = 0

    # cover. Reading systems fall back to a grey placeholder without one, and
    # KDP will not accept a book that has none.
    cover_png = ROOT / "build" / "cover.png"
    has_cover = cover_png.exists()
    if has_cover:
        files["OEBPS/cover.png"] = cover_png.read_bytes()
        manifest.append('<item id="cover-image" href="cover.png" media-type="image/png" '
                        'properties="cover-image"/>')
        cover_doc = ('<section epub:type="cover" class="coverpage">\n'
                     f'<img src="cover.png" alt="{esc(TITLE)}"/>\n</section>\n')
        files["OEBPS/cover.xhtml"] = xhtml(TITLE, cover_doc).encode()
        manifest.append('<item id="cover" href="cover.xhtml" '
                        'media-type="application/xhtml+xml"/>')
        spine.append('<itemref idref="cover" linear="no"/>')
    else:
        print("warning: build/cover.png missing — run pipeline/make_cover.py",
              file=sys.stderr)

    # front matter
    front = (
        '<section class="front" epub:type="titlepage">\n'
        f'<p class="title">{esc(TITLE)}</p>\n'
        f'<p class="sub">{esc(SUBTITLE)}</p>\n'
        f'<p>{esc(AUTHOR)}</p>\n<hr/>\n'
        f'<p>Proof generated {date.today().isoformat()}.</p>\n'
        '<p>Locator maps are generated from positions recorded on the author’s '
        'own map sheets. Positions are approximate and are intended to show where '
        'a site lies, not to serve as survey coordinates.</p>\n'
        '</section>\n'
    )
    files["OEBPS/title.xhtml"] = xhtml(TITLE, front).encode()
    manifest.append('<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>')
    spine.append('<itemref idref="title"/>')
    nav.append(f'<li><a href="title.xhtml">{esc(TITLE)}</a></li>')

    for i, (folder, entries) in enumerate(chapters.items(), 1):
        cid = f"ch{i:02d}"
        ctitle = chapter_title(folder)
        parts = [f"<h1>{esc(ctitle)}</h1>",
                 f'<p class="chapter-range">{len(entries)} entries</p>']
        for e in entries:
            total += 1
            meta = e["meta"]
            # Name then map, with nothing between them. The state and
            # cross-reference lines follow the map: putting them in between
            # separated a site from its own map and made the pairing ambiguous
            # when several entries fell on one screen.
            parts.append('<div class="site-entry">')
            parts.append('<div class="entry-head">')
            parts.append(f'<h2 id="{esc(e["slug"])}">{esc(e["name"])}</h2>')
            cats = meta.get("categories") or []
            if isinstance(cats, str):
                cats = [cats]
            png = MAPS / f"{e['slug']}.png"
            if png.exists():
                used_maps.add(e["slug"])
                parts.append(
                    f'<figure><img src="images/{esc(e["slug"])}.png" '
                    f'alt="Map showing the location of {esc(e["name"])}"/></figure>')
            state = meta.get("state") or ""
            if state:
                parts.append(f'<p class="loc">{esc(str(state))}</p>')
            if len(cats) > 1:
                parts.append(f'<p class="tags">Also listed under: '
                             f'{esc(", ".join(str(c) for c in cats[1:]))}</p>')
            parts.append('</div>')          # close .entry-head
            srcs = meta.get("sources") or []
            if isinstance(srcs, str):
                srcs = [srcs]
            inner, imported = body_to_html(e["body"])
            if imported:
                drafts += 1
                parts.append('<p class="draft">DRAFT — imported notes, not yet '
                             'rewritten or sourced. Not for publication.</p>')
            parts.append(inner)
            if srcs:
                cited.update(str(x).split("#")[0] for x in srcs)
                parts.append('<p class="citation"><strong>Source</strong> '
                             + "; ".join(cite_label(str(x), bib) for x in srcs)
                             + "</p>")
            parts.append('</div>')          # close .site-entry
        files[f"OEBPS/{cid}.xhtml"] = xhtml(ctitle, "\n".join(parts)).encode()
        manifest.append(f'<item id="{cid}" href="{cid}.xhtml" '
                        f'media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="{cid}"/>')
        nav.append(f'<li><a href="{cid}.xhtml">{esc(ctitle)}</a></li>')

    for slug in sorted(used_maps):
        data = (MAPS / f"{slug}.png").read_bytes()
        files[f"OEBPS/images/{slug}.png"] = data
        manifest.append(f'<item id="img-{slug}" href="images/{slug}.png" '
                        f'media-type="image/png"/>')

    files["OEBPS/style.css"] = CSS.encode()
    manifest.append('<item id="css" href="style.css" media-type="text/css"/>')

    if cited:
        items = []
        for key in sorted(cited):
            w = bib.get(key)
            if not w:
                continue
            author = str(w.get("author", "")).rstrip(".")   # "R. S." already ends in one
            bits = [f"{esc(author)}. <em>{esc(w['title'])}</em>."]
            place, pub, yr = w.get("place"), w.get("publisher"), w.get("year")
            if place and pub:
                bits.append(f"{esc(place)}: {esc(pub)}{',' if yr else '.'}")
            if yr:
                bits.append(f"{yr}.")
            items.append("<li>" + " ".join(bits) + "</li>")
        body_ = ("<h1>Works Cited</h1>\n"
                 "<p>Works from which entries in this book are sourced. Entries "
                 "without a citation draw on the author's own notes and are marked "
                 "for sourcing in a later edition.</p>\n"
                 '<ul class="bib">\n' + "\n".join(items) + "\n</ul>\n")
        files["OEBPS/bibliography.xhtml"] = xhtml("Works Cited", body_).encode()
        manifest.append('<item id="bibliography" href="bibliography.xhtml" '
                        'media-type="application/xhtml+xml"/>')
        spine.append('<itemref idref="bibliography"/>')
        nav.append('<li><a href="bibliography.xhtml">Works Cited</a></li>')

    nav_doc = ('<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>\n'
               + "\n".join(f"  {n}" for n in nav) + "\n</ol></nav>\n")
    files["OEBPS/nav.xhtml"] = xhtml("Contents", nav_doc).encode()
    manifest.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
                    'properties="nav"/>')

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="bookid">\n'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f'  <dc:identifier id="bookid">{UUID}</dc:identifier>\n'
        f'  <dc:title>{esc(TITLE)}</dc:title>\n'
        f'  <dc:creator>{esc(AUTHOR)}</dc:creator>\n'
        f'  <dc:language>{LANG}</dc:language>\n'
        f'  <dc:date>{date.today().isoformat()}</dc:date>\n'
        f'  <meta property="dcterms:modified">{stamp}</meta>\n'
        # EPUB2-style pointer as well: it is what Kindle actually reads
        + ('  <meta name="cover" content="cover-image"/>\n' if has_cover else '')
        + '</metadata>\n<manifest>\n'
        + "\n".join(f"  {m}" for m in manifest)
        + '\n</manifest>\n<spine>\n'
        + "\n".join(f"  {s}" for s in spine)
        + '\n</spine>\n</package>\n'
    )
    files["OEBPS/content.opf"] = opf.encode()
    files["META-INF/container.xml"] = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '  <rootfiles><rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/></rootfiles>\n'
        '</container>\n').encode()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w") as z:
        # mimetype must be first and stored uncompressed
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                   compress_type=zipfile.ZIP_STORED)
        for name, data in files.items():
            z.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)

    print(f"chapters : {len(chapters)}")
    print(f"entries  : {total}")
    print(f"maps     : {len(used_maps)}")
    print(f"drafts   : {drafts}  (imported bullets, not yet rewritten)")
    print(f"output   : {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(build("--all" in sys.argv))
