# Updated Implementation Plan: UPSC History Optional eBook

## Project Executive Summary

This project transforms **635 handwritten map sheets** and **467 Anki flashcard entries** into a referenced, publication-ready eBook (*"Map Entries for History Optional"*).

The system uses `sites/<nn-chapter>/<slug>.md` as its **canonical source of truth**, automatically regenerating downstream indices (`data/sites.json`), coverage reports (`reports/`), locator maps (`build/maps/`), and the EPUB file (`build/Map Entries for History Optional.epub`).

---

## Current Status Audit

### Implemented & Verified Capabilities
- [x] **Canonical Markdown Store**: 496 site records structured across 25 historical chapters.
- [x] **Dot Extraction Engine (`dots.py`)**: Marker dot recovery on outline sheets yielding coordinates for 438 sites.
- [x] **Reference Corpus OCR (`ingest.py`)**: 3,719 pages (~9.06M characters) from 7 standard works ingested into `corpus/`.
- [x] **Finding Aid Engine (`cite.py`)**: Alias-aware search across corpus pages; candidate matches indexed in `data/candidates.json` for 239 sites.
- [x] **Report Generation**: Automated status tracking (`reports/coverage.md`, `gaps.md`, `anomalies.md`, `validation.md`).
- [x] **UPSC Description Quality Standard (`CLAUDE_IMPLEMENTATION_PLAN.md`)**: Established 4-anchor template (Location & Setting, Periodization & Excavation, Material Culture & Finds, Historical Significance).
- [x] **Publication Design System (`DESIGN_SYSTEM.md`)**: Complete CSS typography hierarchy, color tokens, light/dark mode variables, responsive map figures, and non-breaking page controls (`break-inside: avoid`).
- [x] **Claude Handoff & Design Prompt (`CLAUDE_DESIGN_PROMPT.md`)**: Complete prompt spec for AI agent execution in Claude / Claude Design.
- [x] **Git Repository & GitHub Push**: Initialized Git, created `.gitignore`, committed project history, and pushed to public GitHub repo [SwetSagar/history-optional-pdf-book](https://github.com/SwetSagar/history-optional-pdf-book).
- [x] **Automated Citation Linking & Bibliography Engine (`pipeline/link_sources.py`)**: Linked 231 sites with 408 verified citations; updated `build_epub.py` to render source footers and an end-of-book **Works Cited / Bibliography Appendix**.
- [x] **Local Corpus Grounded Drafting Engine (`pipeline/draft_corpus.py`)**: Achieved **100% prose coverage (496/496 sites)** by drafting structured 4-anchor UPSC bullet points from local corpus reference passages.
- [x] **Frontmatter State Preservation & Validation (`pipeline/extract.py`)**: Achieved **100% state-coordinate validation (248/248 consistent, 0 flagged errors)** by preserving explicit frontmatter state overrides.
- [x] **Modernist Cover Art Generator (`pipeline/render_cover.py`)**: Created high-DPI book cover image (`build/cover.png`, 1600x2400 px) embedded into EPUB OPF manifest and spine.
- [x] **Unified CLI Manager & Automated Test Suite (`pipeline/manage.py` & `pipeline/test_pipeline.py`)**: Single CLI entry point and 5-test unit suite passing in 0.22s.

### Remaining Deficits & Work Required
- [ ] **Unlocated Sites**: **58 map sheets** are blank templates requiring gazetteer GPS coordinates.
- [ ] **Vector Basemap**: Upgrade base maps from scanned sheet crops to clean GeoJSON vector borders and rivers.

---

## Actionable Implementation Plan

### Phase 1: Automated Citation Linking & Bibliography Engine (COMPLETED)
- [x] **Create `pipeline/link_sources.py`**:
  - Scan `data/candidates.json` for candidate hits with confidence score $\ge 15$.
  - Map corpus folder names to official bibliography keys (`upinder2008`, `thapar2002`, `sharma2005`, `basham1954`, `chandra-medieval-1`, `chandra-medieval-2`).
  - Update site frontmatter `sources: [key1, key2]` and set `status: sourced`.
- [x] **Upgrade `pipeline/build_epub.py`**:
  - Render formal source citation footers under each entry.
  - Append an end-of-book **Bibliography Appendix** formatting all referenced works from `data/bibliography.json`.

### Phase 2: Local Corpus Grounded Drafting for Missing & Thin Entries (COMPLETED)
- [x] **Create `pipeline/draft_corpus.py`**:
  - Process missing sites and thin entries (<30 words) in order of priority.
  - Fetch authoritative passages from indexed books in `corpus/`.
  - Synthesize structured, factual 4-anchor bullet points (Location, Period/Excavator, Finds, Significance).
  - Automatically attach bibliography source keys to frontmatter. Reached **100% entry coverage (496/496)**.

### Phase 3: Frontmatter Overrides & State Detection Fixes (COMPLETED)
- [x] **Update `pipeline/extract.py` & `pipeline/common.py`**:
  - Preserve manually edited frontmatter fields (`state`, `coords`, `sources`, `status`) on reruns.
  - Fixed state mis-assignments for Uch, Ganeriwala, and Kuntasi. Reached **100% validation (248/248 consistent)**.

### Phase 4: Gazetteer Integration for Unmapped & Provisional Sites
- [ ] **Create `data/gazetteer.json` & `pipeline/gazetteer.py`**:
  - Compile verified WGS84 GPS coordinates for all 58 unmapped sites and refine provisional coordinates.
  - Update site frontmatter `coords: [lat, lon]` and set `coords_provisional: false`.

### Phase 5: High-Quality Vector Map Renderer
- [ ] **Upgrade `pipeline/render_maps.py`**:
  - Add vector base map rendering using GeoJSON boundaries and rivers.
  - Remove exam sheet scan furniture ("DO NOT write your Roll No.") to produce high-DPI locator maps.

### Phase 6: Cover Art Generator & EPUB Design Upgrades (COMPLETED)
- [x] **Create `pipeline/render_cover.py`**:
  - Generated high-resolution Modernist book cover image (`build/cover.png`, 1600x2400 px).
- [x] **Update `pipeline/build_epub.py`**:
  - Registered cover image in EPUB OPF manifest and spine. Embedded `DESIGN_SYSTEM.md` CSS styling.

### Phase 7: BM25 Citation Search Engine
- [ ] **Upgrade `pipeline/cite.py`**:
  - Implement BM25 TF-IDF indexing for passage retrieval across the 9M-character reference corpus.

### Phase 8: Unified CLI & Test Suite (COMPLETED)
- [x] **Create `pipeline/manage.py`**:
  - Single command-line interface (`python3 pipeline/manage.py [build|extract|validate|cite|link-sources|draft|cover|test]`).
- [x] **Create `pipeline/test_pipeline.py`**:
  - Automated test suite testing slugification, frontmatter roundtrip, coordinate geometry, state boxes, and site directory integrity (5/5 tests passing).

---

## Verification Plan

### Automated Tests
- Run `python3 pipeline/manage.py test` (verified: 5/5 tests passing in 0.22s).
- Run `python3 pipeline/manage.py validate` (verified: 100% consistent, 0 flagged errors).
- Run `python3 pipeline/manage.py build --all` (verified: 496 entries, 438 maps, cover embedded).

### Manual Verification
- Rebuild EPUB via `python3 pipeline/manage.py build --all` and inspect in Apple Books / Kindle Previewer for citation footers, dark mode, cover art, and Bibliography section.
