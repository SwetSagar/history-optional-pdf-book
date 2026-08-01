# Updated Implementation Plan: UPSC History Optional eBook

## Project Executive Summary

This project transforms **635 handwritten map sheets** and **467 Anki flashcard entries** into a referenced, publication-ready eBook (*"Map Entries for History Optional"*).

The system uses `sites/<nn-chapter>/<slug>.md` as its **canonical source of truth**, automatically regenerating downstream indices (`data/sites.json`), coverage reports (`reports/`), locator maps (`build/maps/`), and the EPUB file (`build/Map Entries for History Optional.epub`).

---

## Current Status Audit

### Implemented & Verified Capabilities
- [x] **Canonical Markdown Store**: 500 site records structured across 25 historical chapters.
- [x] **Dot Extraction Engine (`dots.py`)**: Marker dot recovery on outline sheets yielding coordinates for 439 sites.
- [x] **Reference Corpus OCR (`ingest.py`)**: 3,719 pages (~9.06M characters) from 7 standard works ingested into `corpus/`.
- [x] **Finding Aid Engine (`cite.py`)**: Alias-aware search across corpus pages; candidate matches indexed in `data/candidates.json` for 239 sites.
- [x] **Report Generation**: Automated status tracking (`reports/coverage.md`, `gaps.md`, `anomalies.md`, `validation.md`).
- [x] **UPSC Description Quality Standard (`CLAUDE_IMPLEMENTATION_PLAN.md`)**: Established 4-anchor template (Location & Setting, Periodization & Excavation, Material Culture & Finds, Historical Significance).
- [x] **Publication Design System (`DESIGN_SYSTEM.md`)**: Complete CSS typography hierarchy, color tokens, light/dark mode variables, responsive map figures, and non-breaking page controls (`break-inside: avoid`).
- [x] **Claude Handoff & Design Prompt (`CLAUDE_DESIGN_PROMPT.md`)**: Complete prompt spec for AI agent execution in Claude / Claude Design.
- [x] **Git Repository & GitHub Push**: Initialized Git, created `.gitignore`, committed project history, and pushed to public GitHub repo [SwetSagar/history-optional-pdf-book](https://github.com/SwetSagar/history-optional-pdf-book).

### Remaining Deficits & Work Required
- [ ] **Sources Attached**: **0 / 500 sites** currently have citation sources linked in `sources: []` frontmatter.
- [ ] **Missing Entries**: **114 sites** have no text written (`status: missing`).
- [ ] **Thin Entries**: **119 sites** have under 30 words (some single-sentence summaries).
- [ ] **Unlocated Sites**: **58 map sheets** are blank templates requiring gazetteer GPS coordinates.
- [ ] **State Mis-assignments**: 3 state-location mismatches (Uch, Ganeriwala, Kuntasi) caused by passing mentions in text.
- [ ] **EPUB CSS & Cover Integration**: Upgrade `build_epub.py` with `DESIGN_SYSTEM.md` stylesheet, cover generator (`render_cover.py`), citation footers, and Bibliography chapter.

---

## Actionable Implementation Plan

### Phase 1: Automated Citation Linking & Bibliography Engine
- [ ] **Create `pipeline/link_sources.py`**:
  - Scan `data/candidates.json` for candidate hits with confidence score $\ge 15$.
  - Map corpus folder names (`upinder`, `thapar`, `sharma`, `basham`, `chandra1`, `chandra2`) to official bibliography keys (`upinder2008`, `thapar2002`, `sharma2005`, `basham1954`, `chandra-medieval-1`, `chandra-medieval-2`).
  - Update site frontmatter `sources: [key1, key2]` and set `status: sourced`.
- [ ] **Upgrade `pipeline/build_epub.py`**:
  - Render formal source citation footers under each entry.
  - Append an end-of-book **Bibliography Appendix** formatting all referenced works from `data/bibliography.json`.

### Phase 2: Local Corpus Grounded Drafting for Missing & Thin Entries
- [ ] **Create `pipeline/draft_corpus.py`**:
  - Process the 114 missing sites and 119 thin entries (<30 words) in order of priority.
  - Fetch authoritative passages from indexed books in `corpus/`.
  - Synthesize structured, factual 4-anchor bullet points (Location, Period/Excavator, Finds, Significance).
  - Automatically attach bibliography source keys to frontmatter.

### Phase 3: Frontmatter Overrides & State Detection Fixes
- [ ] **Update `pipeline/extract.py` & `pipeline/common.py`**:
  - Preserve manually edited frontmatter fields (`state`, `coords`, `sources`, `status`) on reruns.
  - Fix state mis-assignments for Uch, Ganeriwala, and Kuntasi by respecting explicit frontmatter `state` overrides.

### Phase 4: Gazetteer Integration for Unmapped & Provisional Sites
- [ ] **Create `data/gazetteer.json` & `pipeline/gazetteer.py`**:
  - Compile verified WGS84 GPS coordinates for all 58 unmapped sites and refine provisional coordinates.
  - Update site frontmatter `coords: [lat, lon]` and set `coords_provisional: false`.

### Phase 5: High-Quality Vector Map Renderer
- [ ] **Upgrade `pipeline/render_maps.py`**:
  - Add vector base map rendering using GeoJSON boundaries and rivers.
  - Remove exam sheet scan furniture ("DO NOT write your Roll No.") to produce high-DPI locator maps.

### Phase 6: Cover Art Generator & EPUB Design Upgrades
- [ ] **Create `pipeline/render_cover.py`**:
  - Generate high-resolution Modernist book cover image (`build/cover.png`, 1600x2400 px).
- [ ] **Update `pipeline/build_epub.py`**:
  - Inject CSS stylesheet from `DESIGN_SYSTEM.md`.
  - Wrap site entries in `<div class="site-entry">` to prevent ugly e-Reader page breaks.
  - Register cover image in EPUB OPF manifest.

### Phase 7: BM25 Citation Search Engine
- [ ] **Upgrade `pipeline/cite.py`**:
  - Implement BM25 TF-IDF indexing for passage retrieval across the 9M-character reference corpus.

### Phase 8: Unified CLI & Test Suite
- [ ] **Create `pipeline/manage.py`**:
  - Single command-line interface (`python3 pipeline/manage.py [build|extract|validate|cite|link-sources|draft]`).
- [ ] **Create `pipeline/test_pipeline.py`**:
  - Automated test suite for frontmatter parsing, coordinate geometry, citation mapping, and EPUB validity.

---

## Verification Plan

### Automated Tests
- Run `python3 pipeline/link_sources.py` and verify `sources: [...]` populated across sites.
- Run `python3 pipeline/validate.py` to verify state consistency.
- Run `pytest pipeline/test_pipeline.py` to confirm pipeline stability.

### Manual Verification
- Rebuild EPUB via `python3 pipeline/build_epub.py` and inspect in Apple Books / Kindle Previewer for citation footers, dark mode, cover art, and Bibliography section.
