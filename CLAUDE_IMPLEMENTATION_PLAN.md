# Implementation Plan: UPSC Site Descriptions, Grounded Drafting & Sourcing

> **Target Audience / Implementer**: AI Agent / Developer (Claude)
> **Goal**: Upgrade all 500 site entries in `sites/*.md` to exam-ready 4-anchor UPSC History Optional descriptions (~30–40 words), backed by verified citations from the local reference corpus (`corpus/`), and render formal source footers and bibliography in the final EPUB.

---

## 1. Quality Standards for UPSC Site Descriptions

Every site entry body in `sites/<nn-chapter>/<slug>.md` must strictly follow a **4-bullet standardized template**:

```markdown
---
name: Bhimbetka
categories: [Palaeolithic, Mesolithic]
state: Madhya Pradesh
coords: [22.8976, 77.3475]
coords_confidence: high
coords_provisional: true
status: sourced
sources: [upinder2008, basham1954]
---

- **Location & Setting**: Raisen district, Madhya Pradesh, situated in the Vindhyan foothills along the Narmada basin.
- **Periodization & Excavation**: Multi-layered occupation from Lower Palaeolithic to Mesolithic; major rock shelter excavations led by V.S. Wakankar.
- **Material Culture & Finds**: Quartzite Acheulian handaxes/cleavers, Auditorium Cave cupules, and Mesolithic rock art in red/green pigments depicting fauna, hunting scenes, and ritual dances.
- **Historical Significance**: Landmark evidence of continuous prehistoric human habitation, cognitive evolution, and hunter-gatherer artistic expression.
```

### The 4 Required Anchors
1. **Location & Setting**: District, State, River/Basin, Mountain Pass, or Geographical Region.
2. **Periodization & Excavator**: Archaeological phases (e.g. *Lower Palaeolithic*, *Early Harappan*, *NBPW*) + Key Excavator/Archaeologist (*V.S. Wakankar, B.B. Lal, Mortimer Wheeler, H.D. Sankalia, ASI*).
3. **Material Culture & Finds**: Pottery types (*PGW, NBPW, BRW*), tools (*Acheulian handaxes, microliths*), architecture (*stupa, chaitya, dockyard, granary*), inscriptions, or coins.
4. **Historical Significance**: Socio-economic role, trade route junction, capital city, or religious center.

---

## 2. Bibliographic Corpus Mapping

All citations in frontmatter `sources: [...]` must use official keys registered in `data/bibliography.json` and mapped from `data/sources.json`:

| Corpus Folder | Bibliography Key | Reference Work |
| :--- | :--- | :--- |
| `upinder` | `upinder2008` | Singh, Upinder (2008). *A History of Ancient and Early Medieval India* |
| `thapar` | `thapar2002` | Thapar, Romila (2002). *Early India: From the Origins to AD 1300* |
| `sharma` | `sharma2005` | Sharma, R. S. (2005). *India's Ancient Past* |
| `basham` | `basham1954` | Basham, A. L. (1954). *The Wonder That Was India* |
| `chandra1` | `chandra-medieval-1` | Chandra, Satish (1997). *Medieval India, Part I* |
| `chandra2` | `chandra-medieval-2` | Chandra, Satish (1999). *Medieval India, Part II* |
| `mehta1` | `mehta-medieval-1` | Mehta, J. L. (1979). *Advanced Study in the History of Medieval India, Vol. I* |

---

## 3. Step-by-Step Technical Implementation Tasks

### Step 1: Automated Source Linking Engine (`pipeline/link_sources.py`)
- **Purpose**: Link candidate hits from `data/candidates.json` directly into site frontmatter `sources: [...]`.
- **Implementation Logic**:
  1. Load `data/candidates.json` and `data/sources.json`.
  2. For each site in `sites/`:
     - If candidates exist with `score >= 15`, map candidate `source` folder $\rightarrow$ `bibliography_key`.
     - Update site frontmatter array: `sources: [key1, key2]`.
     - If current status is `written` or `raw`, upgrade `status: sourced`.
  3. Ensure re-running does not duplicate keys in `sources: [...]`.

### Step 2: Grounded Corpus Drafter (`pipeline/draft_corpus.py`)
- **Purpose**: Generate 4-anchor exam descriptions for the 114 missing sites and 119 thin sites (<30 words) using local corpus passages.
- **Implementation Logic**:
  1. Load `reports/gaps.md` and `data/candidates.json`.
  2. For each missing or thin site:
     - Query `corpus/` pages via `cite.py` engine to extract top 3 candidate passages.
     - Synthesize 4 bullet points according to the 4-anchor template (Location, Period/Excavator, Finds, Significance).
     - Write formatted text to `sites/<nn-chapter>/<slug>.md`.
     - Set frontmatter `status: sourced` and populate `sources: [key1, ...]`.
  3. Preserve existing user prose if present; only replace if requested or if entry is currently `missing` / `raw`.

### Step 3: Frontmatter Field Preservation (`pipeline/common.py` & `pipeline/extract.py`)
- **Purpose**: Ensure pipeline re-extraction never overwrites manually set states, gazetteer coordinates, or source lists.
- **Implementation Logic**:
  - Update `load_frontmatter()` and `dump_frontmatter()` in `pipeline/common.py` to preserve custom frontmatter attributes.
  - Update `write_markdown()` in `pipeline/extract.py` so that existing `sources`, `coords`, `state`, and `status` values are strictly preserved.

### Step 4: EPUB Source Footers & Bibliography Appendix (`pipeline/build_epub.py`)
- **Purpose**: Render formal academic citations under every site entry and append a complete Bibliography section to the EPUB.
- **Implementation Logic**:
  1. Update `body_to_html()` in `pipeline/build_epub.py` to check `meta.get("sources")`.
  2. For each key in `sources`, look up title and author in `data/bibliography.json` and append a styled HTML footer:
     ```html
     <p class="citation"><strong>Sources:</strong> Upinder Singh (2008); Romila Thapar (2002).</p>
     ```
  3. Generate a new XHTML chapter `OEBPS/bibliography.xhtml` at the end of the eBook listing all cited works formatted in standard APA/Chicago style.

---

## 4. Execution Commands for Claude

Run these commands in order to execute the implementation:

```bash
# 1. Auto-link sources from existing candidate index
python3 pipeline/link_sources.py --apply

# 2. Draft 4-anchor descriptions for missing & thin entries from local corpus
python3 pipeline/draft_corpus.py --missing --thin

# 3. Validate state and coordinate consistency
python3 pipeline/validate.py

# 4. Rebuild index and reports
python3 pipeline/extract.py

# 5. Build final EPUB with citation footers and Bibliography section
python3 pipeline/build_epub.py --all
```

---

## 5. Verification Checklist

- [ ] Every site in `sites/` adheres to the 4-bullet anchor structure (Location, Period, Finds, Significance).
- [ ] At least 75%+ of entries have non-empty `sources: [...]` lists.
- [ ] No `status: missing` entries remain in `reports/gaps.md`.
- [ ] The generated EPUB displays formatted citation footers under entries and includes a final Bibliography chapter.
