# Map Entries for History Optional

Turning 635 hand-made map sheets and 467 Anki descriptions into a referenced eBook
covering every site in the UPSC History Optional map question.

## Layout

```
Individual Map sites History Optional/   source sheets — read only, never edited
7. Optional Map Description.txt          source descriptions — read only
pipeline/                                extraction, drafting and build code
sites/<nn-chapter>/<slug>.md             CANONICAL RECORDS — edit these
corpus/                                  OCR text of the reference library — generated
data/                                    generated indices and hand-kept config
data/web-sites.json                     canonical Sarvam/web export — generated
data/exam-notes.json                    30-50 word notes per site — generated
reports/                                 generated reports — do not edit
build/                                   maps, cover, PDF and EPUB — generated, gitignored
```

**`sites/` is the source of truth.** Everything in `data/` and `reports/` is
regenerated from it plus the source folders. Re-running the pipeline never
overwrites a Markdown body, so prose you have written is safe.

Six files under `data/` are *inputs*, not outputs, and are edited by hand:
`sources.json` (which works to ingest), `bibliography.json` (how each is cited),
`aliases.json` (historical/modern name pairs for the citation search),
`gazetteer.json` (checked coordinates), `merges.json` (variant spellings of
one place that must fold into a single record — see Method notes) and
`chapters.json` (what each chapter is called in the book, and which records move
between chapters).

## Where things stand

`data/` and `reports/` are current: `extract` and `validate` were last run
against the state below.

| | |
|---|---|
| Sites | **480** (from 635 sheets; multi-period and variant-spelling sheets merged) |
| Entries with text | **480 / 480** |
| — every one hand-written in the 4-anchor format | **480** |
| — machine drafts remaining | **0** |
| `status: sourced` | **157** |
| `status: written` (not yet author-verified) | **323** |
| With a coordinate | **480 / 480** |
| Gazetteer-pinned (`coords_provisional: false`) | **308** |
| Still dot-derived and provisional | **172** |
| With a stated state | **480** |
| Coordinate cross-check | **474 / 474 consistent (100%)**, 0 flagged |
| Source corpus | 3,719 pages across 7 standard works, 9.06M chars |
| Records carrying a `sources` list | **406** |
| Source keys not in `bibliography.json` | **0** |
| Mean entry length | 247 words |
| PDF | **260 pages**, A4, two columns, 480 entries in 24 chapters, one to a column |
| Tests | 20 passing |

See `reports/coverage.md`, `reports/gaps.md`, `reports/anomalies.md`,
`reports/validation.md`, `reports/sources.md`, `reports/gazetteer.md`,
`reports/pyq.md`.

Two reports are not refreshed by `extract` and still describe an earlier state:
`sources.md` and `unsupported.md` come from `cite.py`/`link_sources.py`, and
`gazetteer.md` from `gazetteer.py`. Re-run those tools before trusting them.

### What is still outstanding

- **172 provisional coordinates.** Six pairs of unrelated sites still share a
  single dot — `adamgadh`/`adam`, `ajmer-hakra-basin`/`ajmer-sharif`,
  `kakoria`/`varanasi-…`, `kamakhya`/`pragjyotishpura`,
  `kambadahalli`/`shravanabelagol`, and Paithan's dot shared with
  `apegaon-janeshwar`. These are gazetteer mismatches, not duplicate records.
- **63 entries have no `*Sources*` line** and **74 have empty `sources:`** —
  concentrated in chapters 01 Palaeolithic and 04 Chalcolithic.
- **22 records still have no `state`.**
- **`status` is not a safe filter yet.** 157 records read `sourced`, but most of
  those flags were set by `link_sources.py` against text that has since been
  rewritten. Treat everything as `written` until you have checked it.

## Running it

Through the single entry point:

```sh
python pipeline/manage.py extract         # rebuild records and indices from the source sheets
python pipeline/manage.py validate        # cross-check coordinates against state boxes
python pipeline/manage.py link-sources    # attach candidate corpus citations (writes by default)
python pipeline/manage.py draft           # draft 4-anchor entries for thin records (writes by default)
python pipeline/manage.py maps [--print]  # one locator map per site
python pipeline/manage.py web [--write]   # preview/write the canonical Sarvam export
python pipeline/manage.py cover           # render build/cover.png
python pipeline/manage.py pdf [--all]     # assemble the A4 PDF
python pipeline/manage.py build [--all]   # assemble the EPUB
python pipeline/manage.py test            # unit tests
```

From a clean checkout, a PDF is three commands in this order:

```sh
python pipeline/manage.py maps --print    # locators drawn for 31mm of paper
python pipeline/manage.py cover
python pipeline/manage.py pdf
```

`manage.py` covers the common path only. The rest of the pipeline is run
directly:

| Script | What it does |
|---|---|
| `extract.py` | rebuild `sites/` and `data/sites.json` from the sheets and descriptions |
| `dots.py` | recover each sheet's dot and convert pixels to degrees |
| `validate.py` | flag coordinates inconsistent with the region the entry names |
| `gazetteer.py [--write]` | apply `data/gazetteer.json` coordinates; pins and locks the record |
| `ingest.py [--list]` | OCR/extract the library works into `corpus/` |
| `cite.py search "Sanchi"` | ranked source passages for one site |
| `cite.py batch` | candidate passages for every entry |
| `cite.py unsupported` | entries no source mentions |
| `link_sources.py [--write]` | turn candidates into `sources_proposed` / `sources` |
| `evidence.py 01 [--from 20]` | evidence pack for writing one chapter by hand |
| `draft_corpus.py [--write] [--all]` | draft entries from the corpus |
| `apply_prose.py <file.py>` | write a `PROSE = {slug: text}` file into the records |
| `apply_aliases.py [--write]` | weave historical/modern name pairs into the prose |
| `reformat.py [--write]` | restructure a prose block into lead + bullets |
| `pyq.py` | mine past papers for what the map question has actually asked; every occurrence carries the paper and page it was read from |
| `render_maps.py [--force] [--print]` | one locator map per site into `build/maps/`; `--print` writes the heavier `build/maps-print/`; deletes locators whose record is gone |
| `export_web.py [--write] [--check]` | build/check `data/web-sites.json` and the web-readiness report from canonical Markdown |
| `make_cover.py [--show]` | the cover: every located site the book prints, plotted at once from the same records the pages are set from (`manage.py cover` uses this) |
| `render_cover.py` | alternative cover: Modernist typographic, no map on it |
| `exam_notes.py [--write] [--sample N]` | condense every entry to a 30-50 word note into `data/exam-notes.json` |
| `build_exam_pdf.py` | assemble `build/Exam Notes for History Optional.pdf`, the revision booklet |
| `build_pdf.py [--all] [--chapters 02,07] [--fast]` | assemble `build/Map Entries for History Optional.pdf` |
| `build_epub.py [--all]` | assemble `build/Map Entries for History Optional.epub` |

### Sarvam / web export

The interactive map application must consume `data/web-sites.json`, not the
older extraction index `data/sites.json`. The web export is rebuilt directly
from the canonical Markdown records and joins their descriptions, coordinate
quality, aliases, bibliography metadata, chapter labels and available PYQ
frequency data.

```sh
python pipeline/manage.py web             # readiness preview; writes nothing
python pipeline/manage.py web --write     # regenerate JSON and report
python pipeline/manage.py web --check     # CI check; fails when either is stale
```

`referenceReady` means that an entry has text and a coordinate. The stricter
`practiceReady` flag additionally requires a verified coordinate, explicit
`review_status: reviewed`, source metadata and `model_answer_30`. This prevents
an unverified record from entering scored map practice merely because its older
`status` says `sourced`. See `reports/web-readiness.md` for the current blockers
and exact records requiring manual review.

Each record's `location` carries the one field a trainer should branch on:

```
"provenance": "gazetteer" | "checked" | "scan-dot",
"verified": true,          // coords_provisional is false
"scorable": true,          // verified and has a coordinate
"acceptedRadiusKm": 25,    // null when unverified — do not score it
"readConfidence": "none"   // coords_confidence, kept for audit, not for gating
```

308 of 480 are scorable. The rest are fine to show on a reference map and unfit
to mark a student's click against; see the coordinate note at the end of this file.

Scripts that write take `--write` (or `--apply`); without it they preview.
`build_epub.py` includes only entries with **both** text and a coordinate —
edition-one scope — unless you pass `--all`; since every record now has a
coordinate, that is everything except the one `missing`.

One exception to the preview rule: `link_sources.py` tests its flag as
`"--write" or "--apply" in sys.argv`, which is always true, so it **writes
whether or not you pass a flag**. Commit before running it.

## The revision booklet

The atlas prints the whole entry, a median of 230 words, because a reference book
should. The map question gives twenty places and about 30-50 words each, under
time. Revising for that out of the atlas means reading six times what you can
write, so the same corpus is also set for the other job:

```sh
python3 pipeline/manage.py notes --write   # data/exam-notes.json
python3 pipeline/manage.py exam            # build/Exam Notes for History Optional.pdf
```

**54 pages against the atlas's 276** — four columns, twelve cards to a page, each
a 42 mm locator, the name, where it is, and the note. Cards carry `ASKED N×` from
the PYQ occurrence data, so the places the question keeps returning to are
visible while revising.

The notes are **condensed, not written**. Every clause is lifted whole from the
entry's own anchors; nothing is paraphrased and no fact is introduced. Clauses
are taken whole for the same reason — truncating mid-clause is how "identified
with Vasavasamudram, though disputed" becomes an assertion, and how Ratanpura's
warning that it is *not* Loteshwar became the claim that it is. 471 of 480 land
in 30-50 words, none run over, and the nine under the floor are 25-29 and read
cleanly.

They are drafts. `review_status` and `model_answer_30` in the record frontmatter
remain where a human-approved answer lives, and the web export still gates scored
practice on those and on nothing generated here.

## The PDF edition

`build_pdf.py` sets the whole book as an A4 two-column revision atlas —
**260 pages**, all 480 entries in 24 chapters, two to a page, each under a
locator map that runs the full column. Front matter, contents, works cited, an
alphabetical index and a sites-by-state index; PDF bookmarks for every chapter
and every site; running heads and folios in the margins.

The map is given the whole column, about 87 mm, with a 1.6 mm dot. That is the
layout's one extravagance and it is deliberate: this is a book about where
places are, and a locator too small to read a position off fails at the only job
it has.

**One entry, one column, and it never breaks.** An entry left to the column flow
breaks wherever the column runs out, and what lands at the top of the next
column is one site's last bullets and its citation printed under a different
site's name. So the entry is cut to the column's exact height and forbidden to
break. Entries run from about 520 pt to about 930 pt against a 745 pt column, so
something has to absorb the difference, and it is the map: capped at the column
width, floored at 50 mm, taking whatever height the text leaves. 351 of the 480
entries still print the full 87 mm map and the mean is 83 mm; five sit on the
floor. Seven entries are long enough that even the smallest map will not save
them, and they are set a type size down — see the fit loop below.

Five things are worth knowing before changing it:

- **Chrome is the print engine.** Not CDP — only the `--print-to-pdf` flag, which
  keeps working on machines where policy disables remote debugging. Edge is the
  same engine and stands in automatically. `pypdf` and `reportlab` add the
  folios, running heads and bookmarks afterwards.
- **It renders twice.** The contents and both indexes print real page numbers,
  and a page number is only knowable once the page is set. Pass one uses
  placeholder folios in a fixed-width box, reads back where every anchor landed
  from the PDF's named destinations, and pass two prints the true numbers. The
  loop re-checks and re-renders if pagination moved; `--fast` renders once, with
  `000` in place of every number.
- **The same loop fits the entries.** `break-inside: avoid` is a request, not a
  guarantee: given a box taller than any column could hold, Chrome breaks it
  anyway. And the height cannot be predicted from the Markdown — it depends on
  where Georgia happens to break every line. So each render is read back with
  `pypdf`, and a column whose first ink is not its own 11 pt name is an entry
  that spilled from the one before; those entries come round again a type size
  smaller. It converges in two or three passes and reports what it moved.
  `--fast` skips it, so a fast preview can still show a split entry.
- **The stamping step clones the document.** Those same named destinations are
  what the contents and indexes link through, and they live in the PDF catalog —
  so building a fresh `PdfWriter` to stamp the folios onto silently drops the
  lot, leaving 988 links that highlight and go nowhere. The bookmarks carry
  explicit page references and keep working, which is what hides it. Clone from
  the source and merge into the clone.
- **Print maps are a separate render.** `render_maps.py --print` draws for the
  size the page reproduces them at and sizes the dot as a fraction of the image,
  not in pixels. It also quantises against a fixed palette rather than an
  adaptive one: a median-cut palette is chosen by pixel count, so once the dot
  shrank below about 2% of the image there were too few red pixels to win a slot
  and every marker in the book quantised to grey. The PDF falls back to
  `build/maps/` if `build/maps-print/` is absent, and looks worse for it.
- **Chapters are configured, not derived.** `data/chapters.json` holds each
  chapter's printed title and any records that move between chapters. Two
  chapters are folded away there rather than in the tree: `22 Early Medieval
  Capital cities` (one record, Kalyani) merges into the medieval cities chapter,
  and `999 Missed recent PYQ` empties into the chapters its two records belong
  to — Kupgal to rock-cut and petroglyph, Thapli to PGW. A chapter left with no
  entries is not printed. The canonical tree under `sites/` is untouched, so
  `extract.py` will not undo any of it, and chapter numbers are printed
  sequentially so a folded chapter leaves no gap.

Citations in the PDF come from the body's written `*Sources*` line where there
is one — 417 entries — and fall back to the frontmatter `sources:` keys rendered
through `bibliography.json` for another 33. **30 entries print no citation at
all.**

Still to do in a second edition: the base map is the scanned exam sheet, which
is fine for a proof and is *not* publishable — see the note at the top of
`render_maps.py`. Those 30 unattributed entries. And nothing in the PDF yet
distinguishes a gazetteer-pinned site from a hand-placed one.

### Requirements

Python 3.10+, plus **Pillow** and **NumPy** (needed by `dots.py`, `extract.py`,
`render_maps.py` and both cover scripts, and therefore by the test suite):

```sh
pip install pillow numpy
```

The PDF build additionally needs **pypdf** and **reportlab**, plus Chrome or
Edge:

```sh
pip install pypdf reportlab
```

Two things assume the machine this was authored on:

- **OCR needs Swift**, which ships with macOS. Build once with
  `swiftc -O pipeline/ocr/ocr.swift -o pipeline/ocr/ocr`. `corpus/` is already
  populated and committed, so ingestion only matters when adding a new work.
- **`data/sources.json` holds an absolute macOS `library_root`**
  (`/Users/swetsagar/Downloads/...`). Point it at the local library before
  re-running `ingest.py` anywhere else.

Everything downstream of `corpus/` — extract, validate, draft, maps, cover,
EPUB — is pure Python and runs anywhere. On macOS and Linux use `python3`.

## How a record works

```markdown
---
name: Allahabad
categories: [Ashokan Inscriptions, Non Ashokan Inscription]
state: Uttar Pradesh
coords: [25.45, 81.85]
coords_confidence: gazetteer
coords_from: Q162442
coords_provisional: false
dot_px: [298.5, 303.5]
images: [Individual Map sites History Optional/12 Ashokan Inscriptions/Allahabad.jpg, ...]
status: sourced
sources: [upinder2008, chandra-medieval-2, sharma2005]
locked: [coords, coords_confidence, coords_from, coords_provisional, state]
---

- **Location**: where it is, and anything odd about that — the Allahabad pillar
  was not made for the spot it stands in.
- **Period/Level**: material, date, stratigraphy, what is inscribed.
- **Key Finds & Significance**: the exam-answerable content, as sub-bullets.
  - One argument per sub-bullet.
  - *Sources*: Upinder Singh, ch. 7 and 9; D. C. Sircar, *Select Inscriptions*.
```

Bodies follow a **4-anchor format**, because that is the shape a map answer is
marked on. All 480 are now in the hand-written set — *Location · Period/Level ·
Key Finds & Significance · *Sources**, the last as a final sub-bullet. 417 carry
that sources line; the other 63 fall back to the `sources:` keys in frontmatter.

`draft_corpus.py`'s template set — *Location & Setting · Periodization &
Excavation · Material Culture & Finds · Historical Significance* — is scaffolding
to write over, not prose, and none survives in the tree. Rewriting one means
replacing the body with the hand-written anchors.

`coords_confidence` is one of `high`, `medium`, `inherited` (dot-derived) or
`gazetteer` (looked up); `coords_from` records the Wikidata QID when it was.

**`coords_confidence` is not a quality score.** It grades how cleanly the dot was
read off the scanned sheet, not how close the reading landed. Burzahom is
labelled `high` and sits 139 km from Burzahom; Pattadakal is labelled `none` and
is exact. Anything deciding whether a coordinate can be trusted — the web export
does — must read `coords_provisional`, which records whether a human checked it.

### Keeping your corrections

A rebuild re-derives most frontmatter from the source folders. Four things
survive it, so hand corrections are not silently undone:

- **`sources`** — always preserved. Nothing derives citations.
- **`locked: [state, coords]`** — an explicit, auditable list of fields the
  pipeline must not touch.
- **`coords_provisional: false`** — declares the coordinate checked against a
  gazetteer, and pins `coords` and `state` automatically.
- **any key the pipeline does not itself write** — `review_status`,
  `model_answer_30`, `recall_points`, `location_type` and whatever comes next.
  These are hand-written and derived by nothing, so a rebuild carries them
  through untouched rather than needing to be told about each one.

Before this, correcting a state by hand survived exactly until the next run.

`status` tracks the writing pipeline:

- `missing` — no description exists; write from sources
- `raw` — bullets imported from your cards; **must be rewritten in your own words**
- `written` — rewritten, not yet sourced
- `sourced` — every dated or attributed claim has an entry in `sources`
- `final` — checked and ready

Two caveats on what `status` currently tells you. No record is `raw` any more,
but that does not mean everything has been written — `written` and `sourced`
both include machine drafts, so `status` alone no longer separates authored
prose from template output. And the one remaining `missing` is mislabelled
rather than empty, which means `build_epub.py` drops an entry that has text.

## Citing sources

`corpus/` holds text extracted from your own library; `data/sources.json` says
what is ingested and `data/bibliography.json` how each work is cited. Coaching
notes are deliberately excluded — useful for finding a fact, never citable.

`cite.py` is a **finding aid, not a citation generator**. It surfaces real
passages for you to read and confirm. It never asserts that a passage supports a
claim and never invents a reference. `link_sources.py` writes machine proposals
into `sources_proposed`; only a confirmed proposal should become a `sources`
entry.

Three things it has to work around:

- **No printed page numbers.** The scans are cropped without folios — of 991
  Upinder pages, 5 carry anything folio-like and those are OCR noise. So
  `scan_page` locates a passage *in the scan*, not in the book. Cite by chapter
  until a paginated copy is available; `bibliography.json` records which works
  are paginated (ASI's *IAR* is).
- **Coverage is the real ceiling.** Roughly a third of entries have a
  substantive corpus passage behind them; the rest return a district-name
  coincidence (the "Bagalkot" hit is about Badami's temples) or a single passing
  mention. No ranking algorithm creates sources that do not exist — which is why
  entries cite works outside the corpus by hand.
- **Historical names.** The sources use the names current when they were
  written: Kozhikode appears 0 times, Calicut 16; Khambat 0, Cambay 36.
  `data/aliases.json` bridges this and **is worth reviewing** — a wrong
  equivalence silently attaches the wrong passage to a site.

## Two cautions that are easy to forget

**172 coordinates are still provisional.** They come from dots placed by hand on
a small sheet. Hand-checking three of them against published coordinates put
Mohenjodaro 18 km out, Bhimbetka 28 km and Burzahom 139 km — further than the
20–60 km this once claimed, and far enough that the state itself can be wrong.
That is invisible at book scale (2–4 px) but they must not be printed as numbers
— neither edition does — and they must not be scored in a map trainer, which is
why `data/web-sites.json` exports them with `scorable: false` and no radius.

The other 308 have been resolved against a gazetteer and carry
`coords_provisional: false`. Measured against the unambiguous entries in
`data/.wikidata_cache.json` that fall inside the sheet's frame, they run to a
median of 0.0 km and a p90 of 2.2 km (n=123), which is what the exported 25 km
accepted radius is built on. Check the flag, not the presence of a coordinate
and not `coords_confidence`.

**`status` no longer separates authored prose from machine output.** It once
did: `status: raw` meant imported bullets close to their source wording, and
`build_epub.py` marked those in the proof so an unrewritten entry could not ship
unnoticed. No record is `raw` now, and both builds skip only `status: missing`,
so nothing in the pipeline would stop a template entry from being published.

What makes that safe at present is the tree itself rather than any safeguard:
all 480 bodies are in the hand-written anchor set (*Location · Period/Level ·
Key Finds & Significance · Sources*), none carry `draft_corpus.py`'s
*Location & Setting* template, and none carry the old imported-bullet marker.
`test_pipeline.py` asserts this, so a regression fails the suite rather than
reaching a reader. The anchor names remain the test — an entry reading
*Location & Setting* has not been written yet.

## Method notes

Every sheet is the same blank template with one dot added, so the dot is recovered
by diffing against `Use this copy.jpg`. Candidate blobs are rejected unless they are
small, compact and round — without that test the printed scale bar diffs as a false
dot and five sites landed in the Indian Ocean.

Pixels convert to degrees using the sheet's own graticule: longitude from the
labelled 60°E–100°E frame edges, latitude from a scale fitted to three sites of
known position and validated at 23–56 km residual. Both constants live at the top
of `pipeline/dots.py`.

Sites are merged across category folders by a normalised match key that handles the
real variation in the corpus — trailing state codes (`Baghor MP`), alternates
(`Sisupalgarh or Dhauli`), compound labels (`Mirabai - Kurki`) and classifier words
(`Ajanta Caves` vs `Ajanta`). This is why 635 sheets reduce to 480 sites, and why
Bhimbetka carries three categories rather than appearing three times.

That normalisation cannot bridge everything. `Sudergarh`/`Sundargarh`,
`Runnindei`/`Lumbini`, `Kile Gile Mohammed`/`Kili Gul Mohammad` are one place
under two spellings, and the author's later sheets sometimes carry a descriptive
label — `Famous Fort - Fort St George`. `data/merges.json` maps those variant
keys onto a canonical one and pins the display name, because the "prefer the
fuller spelling" rule above would otherwise title the record *Famous Fort - Fort
St George*. Its keys are derived from the **sheet filename**, not from a
record's `name:` field. Sixteen pairs are mapped there; without it the book
counts sixteen places twice.

A merged record is written to the directory of its **lowest-numbered** category,
so a site merged across chapters appears once, in the earlier chapter —
Mahabalipuram carries both `Temple Sites` and `Ancient Ports` and lives in
chapter 14. Its body has to cover both, or the merge silently loses half the
entry.

The EPUB is reflowable rather than fixed-layout because each entry is
self-contained, so it stays readable on a phone. The production stylesheet lives
in `build_epub.py` and follows `DESIGN_SYSTEM.md`, with one documented deviation:
`break-inside: avoid` binds the entry *header* (name + map + location) rather
than the whole entry, which would be taller than a phone page.
