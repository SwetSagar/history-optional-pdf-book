# Claude Prompt: Implement eBook Visual Design System & CSS

Copy and paste the prompt below to instruct Claude (or any AI coding agent) to implement the visual design system for the **UPSC History Optional eBook**.

---

### 📋 COPY-PASTE PROMPT FOR CLAUDE

```text
Hi Claude! Please implement the visual design system and EPUB styling for our project "Map Entries for History Optional" based on the specification in `DESIGN_SYSTEM.md` and `CLAUDE_IMPLEMENTATION_PLAN.md`.

### Project Context:
We are building a published eBook (EPUB 3 format) containing 500 historical site entries across 25 chapters. Each site entry consists of:
1. Site Name (H2 Heading)
2. Location Subtitle (State, District, River Basin)
3. Categories / Cross-reference Tags
4. Responsive Locator Map Image
5. 4-Anchor Bullet Facts List (Location & Setting, Periodization & Excavation, Material Culture & Finds, Historical Significance)
6. Citation Footer (Sources referenced from bibliography)

### Your Specific Tasks:

1. UPDATE `pipeline/build_epub.py` CSS STYLESHEET:
   - Replace the legacy CSS with the production CSS token system specified in `DESIGN_SYSTEM.md`.
   - Ensure support for both Light Mode and Dark Mode via `@media (prefers-color-scheme: dark)`.
   - Apply the serif font stack (`"Georgia", "Charis SIL", "Times New Roman", serif`) for body text and sans-serif stack (`"Helvetica Neue", "Inter", "Arial", sans-serif`) for metadata and headings.

2. ENFORCE PAGE-BREAK CONTROLS:
   - Wrap each site entry inside a `<div class="site-entry">` container with `page-break-inside: avoid; break-inside: avoid;`.
   - Set `page-break-after: avoid; break-after: avoid;` on H2 headings, location subtitles, tags, and map figures so e-Readers NEVER turn a page between a site's title and its locator map.

3. STRUCTURE 4-ANCHOR BULLETS & CITATIONS:
   - Format the body bullet points as `<ul class="facts">` with bold label prefixes (`<strong>Location & Setting:</strong>`, `<strong>Periodization & Excavation:</strong>`, etc.).
   - Check `meta.get("sources")` for each site entry. If present, render a citation footer:
     `<div class="citation"><strong>Sources:</strong> Upinder Singh (2008); Romila Thapar (2002).</div>`
   - At the end of the EPUB, generate a dedicated `OEBPS/bibliography.xhtml` chapter rendering all works cited from `data/bibliography.json` in clean academic format.

4. AUTOMATED EBOOK COVER GENERATOR (`pipeline/render_cover.py`):
   - Create a Python script `pipeline/render_cover.py` using Pillow (or SVG) to generate a high-DPI book cover image (`build/cover.png`, 1600x2400 px) featuring:
     - Main Title: "Map Entries for History Optional"
     - Subtitle: "A referenced atlas of the sites in the UPSC History Optional map question"
     - Author: "Swet Sagar"
     - A clean minimalist map graphic or subtle graticule background.
   - Register the cover image in `build_epub.py` under the EPUB OPF manifest (`<item id="cover-image" href="images/cover.png" properties="cover-image"/>`).

5. VERIFICATION:
   - Run `python3 pipeline/build_epub.py --all` to build the updated eBook.
   - Confirm that the output `build/Map Entries for History Optional.epub` validates cleanly and displays beautiful typography, map figures, citation footers, dark mode styling, and cover art.

Please implement these changes now!
```
