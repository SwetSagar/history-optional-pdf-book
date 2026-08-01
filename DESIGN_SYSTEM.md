# Design System & Styling Specification: UPSC History Optional eBook

> **Target Audience**: AI Agent / Developer (Claude)  
> **Document Scope**: Complete visual styling, typography, color tokens, layout hierarchy, and CSS specification for generating the published EPUB and PDF eBook (*"Map Entries for History Optional"*).

---

## 1. Design Philosophy & Vision

The eBook must look like an **authoritative, high-end cartographic atlas & academic reference book**. It should feel clean, elegant, and effortless to read on e-ink devices (Kindle, Kobo) as well as tablets and smartphones (Apple Books, Calibre, mobile screens).

### Core Layout Principles
1. **Zero Awkward Page Breaks**: A site title, location subtitle, locator map, and 4-anchor bullet description must stay glued together as a **single visual unit** (`break-inside: avoid`). The reader should never turn a page between a site's name and its map.
2. **Typography-First Hierarchy**: Classical serif body text for readability, crisp sans-serif labels for metadata, and clean monospaced/italic styling for citation footers.
3. **Responsive Cartography**: Locator maps must scale to full screen width on phones and cap gracefully on tablets without going soft or pixelated.
4. **E-Reader & Dark Mode Native**: High contrast in light mode; soft dark slate in dark mode with no hard white map borders or harsh glare.

---

## 2. Color Palette & Typography Tokens

### Color Palette

| Token Name | Light Mode Hex | Dark Mode Hex | Usage |
| :--- | :--- | :--- | :--- |
| `--color-bg` | `#FFFFFF` | `#121212` | Background |
| `--color-text-main` | `#1A1A1A` | `#E0E0E0` | Primary prose text & headings |
| `--color-text-muted` | `#555555` | `#A0A0A0` | Subtitles, location tags, metadata |
| `--color-accent-red` | `#B02A22` | `#FF6B6B` | Primary marker red (matches map dot) |
| `--color-border` | `#E2E2E2` | `#2D2D2D` | Divider lines & card borders |
| `--color-draft-bg` | `#FFF5F5` | `#2C1E1E` | Draft entry warning box background |
| `--color-draft-border` | `#A03028` | `#FF6B6B` | Draft entry border |

### Typography Hierarchy

- **Primary Serif Stack**: `"Georgia", "Charis SIL", "Times New Roman", serif`
- **Metadata Sans-Serif Stack**: `"Helvetica Neue", "Inter", "Arial", sans-serif`

| Element | Font Size | Weight | Line Height | Case / Style |
| :--- | :--- | :--- | :--- | :--- |
| **Book Title** | `2.2em` (`35px`) | Bold (700) | `1.2` | Title Case |
| **Chapter Heading (H1)** | `1.6em` (`26px`) | Bold (700) | `1.25` | Title Case |
| **Site Name (H2)** | `1.25em` (`20px`) | Semi-Bold (600) | `1.3` | Title Case |
| **Location Subtitle** | `0.9em` (`14px`) | Normal (400) | `1.4` | Italic |
| **Tags / Cross-Ref** | `0.8em` (`13px`) | Normal (400) | `1.3` | UPPERCASE / Tracked `0.05em` |
| **Body / Bullets** | `1.0em` (`16px`) | Normal (400) | `1.5` | Sentence case |
| **Citation Footer** | `0.85em` (`13.5px`)| Normal (400) | `1.4` | Italic / Small Caps key |

---

## 3. Component Design Specifications

### Component A: Site Entry Header & Location Line
- **Site Name (H2)**: Top margin `1.4em`, bottom margin `0.1em`. `break-after: avoid`.
- **Location Subtitle (`.loc`)**: Displays State and Region in italicized muted gray. `margin-bottom: 0.2em`.

```html
<h2 id="bhimbetka">Bhimbetka</h2>
<p class="loc">Madhya Pradesh — Raisen District, Narmada Basin</p>
<p class="tags">Also listed under: Mesolithic, Rockcut Caves</p>
```

### Component B: Responsive Locator Map Figure
- **Container (`figure`)**: `margin: 0.4em 0 0.8em 0; text-align: center; break-inside: avoid;`
- **Image (`figure img`)**: Width `100%`, `max-width: 100%`, `border-radius: 4px`, subtle border `1px solid var(--color-border)`.

```html
<figure>
  <img src="images/bhimbetka.png" alt="Location map for Bhimbetka" />
</figure>
```

### Component C: 4-Anchor Bullet Facts List (`ul.facts`)
- **Structure**: Clean list with `0.4em` spacing between bullets. Bold label prefix for each anchor.

```html
<ul class="facts">
  <li><strong>Location &amp; Setting:</strong> Raisen district, Madhya Pradesh, in the Vindhyan foothills along the Narmada basin.</li>
  <li><strong>Periodization &amp; Excavation:</strong> Multi-layered occupation from Lower Palaeolithic to Mesolithic; major excavations by V.S. Wakankar.</li>
  <li><strong>Material Culture &amp; Finds:</strong> Quartzite Acheulian handaxes, Auditorium Cave cupules, and Mesolithic rock art in red/green pigments.</li>
  <li><strong>Historical Significance:</strong> Landmark evidence of continuous prehistoric human settlement and early artistic expression.</li>
</ul>
```

### Component D: Citation Footer (`.citation`)
- **Structure**: Positioned directly below the bullet list with a subtle top border or light tint.

```html
<div class="citation">
  <strong>Sources:</strong> Upinder Singh (2008), <em>A History of Ancient and Early Medieval India</em>; A.L. Basham (1954).
</div>
```

---

## 4. Production CSS Code for `build_epub.py`

This complete CSS stylesheet must be embedded into `OEBPS/style.css` during the EPUB compilation:

```css
/* --------------------------------------------------------------------------
   UPSC History Optional eBook - Production Design System Stylesheet
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

html {
  font-size: 100%;
  background-color: var(--color-bg);
  color: var(--color-text-main);
}

body {
  margin: 0 4%;
  line-height: 1.5;
  font-family: "Georgia", "Charis SIL", "Times New Roman", serif;
  font-weight: 400;
}

/* Headings & Structure */
h1 {
  font-family: "Helvetica Neue", "Inter", "Arial", sans-serif;
  font-size: 1.6em;
  font-weight: 700;
  margin: 1.4em 0 0.2em;
  color: var(--color-text-main);
  border-bottom: 2px solid var(--color-accent-red);
  padding-bottom: 0.2em;
}

h2 {
  font-family: "Helvetica Neue", "Inter", "Arial", sans-serif;
  font-size: 1.25em;
  font-weight: 600;
  margin: 1.5em 0 0.05em;
  color: var(--color-text-main);
  page-break-after: avoid;
  break-after: avoid;
}

.chapter-range {
  font-family: "Helvetica Neue", "Inter", sans-serif;
  font-size: 0.8em;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  margin: 0 0 1.2em;
}

.loc {
  font-size: 0.9em;
  color: var(--color-text-muted);
  margin: 0 0 0.15em;
  font-style: italic;
  page-break-after: avoid;
  break-after: avoid;
}

.tags {
  font-family: "Helvetica Neue", "Inter", sans-serif;
  font-size: 0.75em;
  color: var(--color-text-muted);
  letter-spacing: 0.04em;
  margin: 0 0 0.3em;
  page-break-after: avoid;
  break-after: avoid;
}

/* Page Break Container */
.site-entry {
  page-break-inside: avoid;
  break-inside: avoid;
  margin-bottom: 1.8em;
}

/* Map Figures */
figure {
  margin: 0.4em 0 0.7em;
  text-align: center;
  page-break-inside: avoid;
  break-inside: avoid;
  page-break-before: avoid;
  break-before: avoid;
}

figure img {
  width: 100%;
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  border: 1px solid var(--color-border);
}

/* 4-Anchor Bullet List */
ul.facts {
  margin: 0.4em 0 0.6em;
  padding-left: 1.2em;
}

ul.facts li {
  margin-bottom: 0.35em;
  line-height: 1.48;
}

ul.facts li strong {
  font-family: "Helvetica Neue", "Inter", sans-serif;
  font-size: 0.88em;
  color: var(--color-text-main);
  letter-spacing: 0.01em;
}

/* Citations & Footers */
.citation {
  font-size: 0.82em;
  color: var(--color-text-muted);
  border-top: 1px dashed var(--color-border);
  padding-top: 0.4em;
  margin-top: 0.6em;
  font-style: italic;
}

.citation strong {
  font-style: normal;
  font-family: "Helvetica Neue", "Inter", sans-serif;
  font-size: 0.85em;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Warning & Draft Badges */
.draft {
  font-family: "Helvetica Neue", "Inter", sans-serif;
  font-size: 0.75em;
  color: var(--color-draft-border);
  background-color: var(--color-draft-bg);
  border: 1px solid var(--color-draft-border);
  border-radius: 3px;
  padding: 0.3em 0.6em;
  margin: 0.5em 0;
}

hr {
  border: 0;
  border-top: 1px solid var(--color-border);
  margin: 2em 0;
}
```

---

## 5. What Is Required From Your Side

To execute this design system seamlessly, **almost everything is automated** inside the Python scripts. Here are the only minor inputs needed from your end:

### 1. Book Cover Preference (Optional)
- **Do you have a preferred cover image?**
  - If yes, place a high-resolution PNG/JPG file (`1600x2400 px`) at `assets/cover.jpg`.
  - If no, `build_epub.py` will automatically render an elegant minimal SVG title cover.

### 2. Embedded Fonts (Optional)
- By default, the CSS uses clean system serif/sans fonts (`Georgia`, `Helvetica Neue`, `Inter`) which render beautifully across Apple Books, Kindle, and Android.
- If you want custom embedded fonts (e.g. *Charis SIL* or *Lora* `.ttf` files), let me know and we can drop them into `assets/fonts/`.

### 3. Review & Approval
- Review `DESIGN_SYSTEM.md` and confirm if you'd like any custom brand colors or styling adjustments!
