# Map Entries for History Optional

Turning 635 hand-made map sheets and 467 Anki descriptions into a referenced eBook
covering every site in the UPSC History Optional map question.

## Layout

```
Individual Map sites History Optional/   source sheets — read only, never edited
7. Optional Map Description.txt          source descriptions — read only
pipeline/                                extraction and validation code
sites/<nn-chapter>/<slug>.md             CANONICAL RECORDS — edit these
data/sites.json                          generated index — do not edit
reports/                                 generated reports — do not edit
```

**`sites/` is the source of truth.** Everything in `data/` and `reports/` is
regenerated from it plus the source folders. Re-running the pipeline never
overwrites a Markdown body, so prose you have written is safe.

## Running it

```sh
python3 pipeline/extract.py            # rebuild records from the source folders
python3 pipeline/validate.py           # cross-check coordinates against stated regions

python3 pipeline/ingest.py             # OCR/extract library works into corpus/
python3 pipeline/cite.py search "Sanchi"   # ranked source passages for one site
python3 pipeline/cite.py batch             # candidates for every entry
python3 pipeline/cite.py unsupported       # entries no source mentions

python3 pipeline/render_maps.py        # one locator map per site
python3 pipeline/make_cover.py         # cover art, from the site data itself
python3 pipeline/build_epub.py         # assemble the eBook

python3 pipeline/test_pipeline.py      # regression tests (25, no dependencies)
```

Or through the single entry point:

```sh
python3 pipeline/manage.py status      # where the book stands
python3 pipeline/manage.py all         # extract + validate + maps + cover + epub
python3 pipeline/manage.py sources propose
python3 pipeline/manage.py gazetteer build
python3 pipeline/manage.py pyq
```

Requires Python 3.10+, Pillow and NumPy. OCR additionally needs Swift, which
ships with macOS — build once with
`swiftc -O pipeline/ocr/ocr.swift -o pipeline/ocr/ocr`.

## Where things stand

| | |
|---|---|
| Sites | **496** (from 635 sheets; multi-period sheets merged) |
| Entries written | **386** — all rewritten from the author's notes |
| Needing text written | **114** (deferred to the next release) |
| With a coordinate | **438** |
| Needing a gazetteer coordinate | **58** (sheets that were never marked) |
| Coordinate cross-check | 245/248 consistent (99%) |
| Source corpus | 3,719 pages across 7 standard works, 9.06M chars |
| Entries with a substantive source | **122 / 384 (32%)** — see note below |
| **Edition one scope** | **379** entries (text + coordinate) |
| Proof eBook | 25 chapters, 375 entries, cover, 10.7 MB |
| Tests | 25 passing |

See `reports/coverage.md`, `reports/gaps.md`, `reports/anomalies.md`,
`reports/validation.md`.

## How a record works

```markdown
---
name: Bhimbetka
categories: [Palaeolithic, Mesolithic, "Rockcut Caves, Petroglyph sites"]
state: Madhya Pradesh
coords: [22.8976, 77.3475]
coords_confidence: high
coords_provisional: true
dot_px: [255.5, 338.5]
images: [...]
status: raw
sources: []
---

Prose goes here.
```

### Keeping your corrections

A rebuild re-derives most frontmatter from the source folders. Three things
survive it, so hand corrections are not silently undone:

- **`sources`** — always preserved. Nothing derives citations.
- **`locked: [state, coords]`** — an explicit, auditable list of fields the
  pipeline must not touch.
- **`coords_provisional: false`** — declares the coordinate checked against a
  gazetteer, and pins `coords` and `state` automatically.

Before this, correcting a state by hand survived exactly until the next run.

`status` tracks the writing pipeline:

- `missing` — no description exists; write from sources
- `raw` — bullets imported from your cards; **must be rewritten in your own words**
- `written` — rewritten, not yet sourced
- `sourced` — every dated or attributed claim has an entry in `sources`
- `final` — checked and ready

## Citing sources

`corpus/` holds text extracted from your own library; `data/sources.json` says
what is ingested and `data/bibliography.json` how each work is cited. Coaching
notes are deliberately excluded — useful for finding a fact, never citable.

`cite.py` is a **finding aid, not a citation generator**. It surfaces real
passages for you to read and confirm. It never asserts that a passage supports a
claim and never invents a reference.

Two things it has to work around:

- **No printed page numbers.** The scans are cropped without folios — of 991
  Upinder pages, 5 carry anything folio-like and those are OCR noise. So
  `scan_page` locates a passage *in the scan*, not in the book. Cite by chapter
  until a paginated copy is available; `bibliography.json` records which works
  are paginated (ASI's *IAR* is).
- **Coverage is the real ceiling.** 239 entries return a candidate passage, but
  only **122 (32%)** are substantive: 12 are district-name coincidences (the
  "Bagalkot" hit is about Badami's temples) and 105 are single passing mentions.
  No ranking algorithm creates sources that do not exist.
- **Historical names.** The sources use the names current when they were
  written: Kozhikode appears 0 times, Calicut 16; Khambat 0, Cambay 36.
  `data/aliases.json` bridges this and **is worth reviewing** — a wrong
  equivalence silently attaches the wrong passage to a site.

## Two cautions that are easy to forget

**Coordinates are provisional.** They come from dots placed by hand on a small
sheet and sit roughly 20–60 km from truth. That is invisible at book scale (2–4 px)
but they must not be printed as numbers. Anything published as a coordinate needs
a gazetteer. Hence `coords_provisional: true` on every record.

**Imported bullets are not publishable.** Text under `status: raw` came from notes
made while studying from standard works, and is likely close to its source wording.
Rewriting it is both the legal fix and the actual authorship of the book.

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
(`Ajanta Caves` vs `Ajanta`). This is why 635 sheets reduce to 498 sites, and why
Bhimbetka carries three categories rather than appearing three times.
