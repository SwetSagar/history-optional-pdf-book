"""Automated Unit Test Suite for the UPSC History Optional eBook Pipeline."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT / "sites"
DATA = ROOT / "data"

import sys
sys.path.insert(0, str(ROOT / "pipeline"))

import json
import re

import build_pdf
from build_pdf import CHAPTERS, inline, numbering, parse_body, roman
from common import canonical_key, display_name, dump_frontmatter, load_frontmatter, match_keys, slugify
from dots import to_lonlat
from export_web import OUTPUT as WEB_OUTPUT, build_export
from extract import apply_overrides
from render_maps import base_image, render
from validate import miss_distance, BOXES


class TestPipeline(unittest.TestCase):

    def test_slugify(self):
        self.assertEqual(slugify("Bhimbetka Caves"), "bhimbetka-caves")
        self.assertEqual(slugify("Sanchi Stupa No. 1"), "sanchi-stupa-no-1")
        self.assertEqual(slugify("Lothal / Harappan Port"), "lothal-harappan-port")

    def test_frontmatter_roundtrip(self):
        meta = {
            "name": "Bhimbetka",
            "categories": ["Palaeolithic", "Mesolithic"],
            "state": "Madhya Pradesh",
            "coords": [22.8976, 77.3475],
            "coords_provisional": True,
            "sources": ["upinder2008"],
            "status": "sourced",
        }
        text = dump_frontmatter(meta) + "\n\nTest body paragraph."
        parsed_meta, parsed_body = load_frontmatter(text)

        self.assertEqual(parsed_meta["name"], "Bhimbetka")
        self.assertEqual(parsed_meta["state"], "Madhya Pradesh")
        self.assertEqual(parsed_meta["coords"], [22.8976, 77.3475])
        self.assertEqual(parsed_meta["sources"], ["upinder2008"])
        self.assertEqual(parsed_meta["status"], "sourced")
        self.assertIn("Test body paragraph.", parsed_body)

    def test_coordinate_conversion(self):
        # Frame anchor coordinates: (x=255.5, y=338.0) -> lat ~ 22.93, lon ~ 77.38
        lat, lon = to_lonlat(255.5, 338.0)
        self.assertAlmostEqual(lat, 22.93, delta=0.5)
        self.assertAlmostEqual(lon, 77.38, delta=0.5)

    def test_state_validation_boxes(self):
        mp_box = BOXES["Madhya Pradesh"]
        # Bhimbetka (22.8976 N, 77.3475 E) should be inside MP box (distance 0)
        dist = miss_distance(22.8976, 77.3475, mp_box)
        self.assertEqual(dist, 0.0)

    def test_screen_locator_keeps_red_marker(self):
        """Palette reduction must not turn the small red marker grey."""
        image = render(base_image(), 22.8976, 77.3475).convert("RGB")
        colours = image.getcolors(maxcolors=256) or []
        self.assertTrue(
            any(r > 120 and r > g * 1.5 and r > b * 1.5 for _, (r, g, b) in colours),
            "screen locator contains no visibly red palette entry",
        )

    def test_pdf_entry_is_cut_to_the_column_it_is_printed_in(self):
        """The print grid is one entry to one column, and three things enforce it.

        The stylesheet has to receive the geometry rather than repeat it, or the
        fit check ends up looking for a foot line the CSS never drew. The entry
        has to be a flex column with the map as its only elastic member, or a
        long body pushes the citation into the next site's column — which is
        what this whole arrangement exists to stop. And the two entries beside a
        chapter banner have to be marked short, or they do not fit the page the
        banner leaves them and the opening spread comes out blank.
        """
        css = build_pdf.geometry_css()
        self.assertIn(f"--col-h:   {build_pdf.COL_H_MM:g}mm", css)
        self.assertIn(f"--map-min: {build_pdf.MAP_MIN_MM:g}mm", css)
        # a millimetre of slack, or a rounding error costs the page an entry
        self.assertLess(build_pdf.COL_H_MM, 297.0 - 2 * 17.0)
        self.assertGreater(build_pdf.COL_H_MM, 297.0 - 2 * 17.0 - 2.0)
        # the fit check finds the top of an entry by this size; the CSS sets it
        self.assertIn(f"font-size: {build_pdf.HEAD_PT:g}pt", build_pdf.CSS)

        entry = {"slug": "bhimbetka", "name": "Bhimbetka", "meta": {"state": "Madhya Pradesh"},
                 "facts": [{"label": "Location", "text": "Raisen district.", "subs": []}],
                 "sources": "Upinder Singh, ch. 3"}
        plain = build_pdf.entry_html(entry, {})
        self.assertIn('class="entry"', plain)
        self.assertIn('class="ebody"', plain)
        # the map is a sibling of the head, not a child: only a direct flex
        # child of the entry can take up the slack the text leaves
        self.assertLess(plain.index("</div>"), plain.index('class="ebody"'))

        opener = build_pdf.entry_html(entry, {}, opener=True, fit=3)
        self.assertIn('class="entry op"', opener)
        self.assertIn('class="ebody f3"', opener)

    def test_web_export_uses_canonical_markdown(self):
        payload, _ = build_export()
        exported = {site["slug"]: site for site in payload["sites"]}
        markdown = list(SITES.rglob("*.md"))
        self.assertEqual(len(exported), len(markdown))

        for path in markdown:
            meta, _ = load_frontmatter(path.read_text(encoding="utf-8"))
            site = exported[path.stem]
            self.assertEqual(site["name"], meta["name"])
            self.assertEqual(
                site["location"]["verified"],
                meta.get("coords_provisional") is False,
            )
            self.assertEqual(
                [source["ref"] for source in site["sources"]],
                meta.get("sources", []),
            )
            if site["editorial"]["practiceReady"]:
                self.assertEqual(site["editorial"]["issues"], [])

        self.assertEqual(exported["thanjavur"]["pyq"]["frequency"], 4)
        self.assertEqual(
            exported["thanjavur"]["pyq"]["resolvedLabels"],
            [{"label": "Tanjore", "count": 4}],
        )
        self.assertEqual(exported["khambat"]["pyq"]["frequency"], 3)
        self.assertNotIn(
            "Muziris",
            [
                item["label"]
                for item in exported["kodungallur-or-mahodayapuram"]["pyq"]["resolvedLabels"]
            ],
        )
        self.assertIn(
            "location_type_review_required",
            exported["nirppeyarru"]["editorial"]["issues"],
        )

        # A frequency is only defensible if it can be taken back to a page. Any
        # route that adds a count without adding an occurrence — a spelling
        # counted once as a match and again as an alias — breaks this.
        for site in payload["sites"]:
            self.assertEqual(
                site["pyq"]["frequency"], len(site["pyq"]["occurrences"]),
                f"{site['slug']} frequency is not backed by occurrences",
            )
            self.assertEqual(
                site["pyq"]["years"],
                sorted({item["year"] for item in site["pyq"]["occurrences"]}),
            )
        madurai = exported["madurai"]["pyq"]
        self.assertEqual(madurai["frequency"], 4)
        # Madura and Madurai are two spellings on four different pages, so four
        # appearances — not one pair counted twice.
        self.assertEqual(len({item["page"] for item in madurai["occurrences"]}), 4)

        if WEB_OUTPUT.exists():
            self.assertEqual(
                json.loads(WEB_OUTPUT.read_text(encoding="utf-8")),
                payload,
                "data/web-sites.json is stale; run manage.py web --write",
            )

    def test_exam_notes_are_whole_sentences_of_the_right_length(self):
        """A condensed note must read as prose, not as a clause that lost its head.

        Every defect guarded here was one the condenser actually produced:
        "Discovered by A." from splitting on an initial, "1949-66)" from splitting
        inside a bracket, "Is a fortified town" from promoting a continuation to
        the front, and — the one that mattered — "Ratanpura carries the
        description written for Loteshwar", where dropping the clause that named
        the book turned a warning into an assertion.
        """
        import exam_notes

        payload = exam_notes.build()
        self.assertEqual(payload["stats"]["notes"], len(list(SITES.rglob("*.md"))))
        self.assertEqual(payload["stats"]["aboveCeiling"], 0)

        broken = re.compile(
            r"^(And|But|Or|Which|Is|Was|Were|Has|Have|With|Then|These|Those|Both|"
            r"It|They|The (?:two|three|former|latter))\b")
        for note in payload["notes"]:
            text = note["note"]
            self.assertTrue(text.endswith("."), f"{note['slug']}: note does not end a sentence")
            self.assertEqual(text.count("("), text.count(")"), f"{note['slug']}: bracket left open")
            self.assertIsNone(exam_notes.META.search(text),
                              f"{note['slug']}: an aside about the book reached the note")
            for sentence in text.split(". "):
                self.assertIsNone(broken.match(sentence.strip()),
                                  f"{note['slug']}: sentence opens on a fragment — {sentence[:40]!r}")
            self.assertLessEqual(note["words"], exam_notes.CEILING, note["slug"])

        stored = ROOT / "data" / "exam-notes.json"
        if stored.exists():
            self.assertEqual(
                json.loads(stored.read_text(encoding="utf-8"))["notes"], payload["notes"],
                "data/exam-notes.json is stale; run manage.py notes --write")

    def test_no_neat_line_survives_the_crop(self):
        """The sheet's frame is not map, and at cover size it reads as damage.

        Cropping alone did not remove it: the rule sits just outside the crop and
        both renderers resample before cropping, so LANCZOS carried it back in,
        while the graticule ticks point inward and were inside the crop already.
        """
        import numpy as np
        from PIL import Image
        from render_maps import BASEMAP, CROP, INK_THRESHOLD, without_frame

        raw = np.asarray(Image.open(BASEMAP).convert("L")).astype(np.uint8)
        cleaned = without_frame(np.where(raw < INK_THRESHOLD, 0, 255).astype(np.uint8))
        ink = cleaned == 0

        inside = ink[CROP[1]:CROP[3], CROP[0]:CROP[2]].sum()
        self.assertEqual(int(ink.sum() - inside), 0, "ink survives outside the crop and will bleed in")
        self.assertGreater(int(inside), 4000, "the cleanup ate the map")
        # the one coastline that reaches the left edge must survive column 0 going
        self.assertTrue(ink[CROP[1] + 182, CROP[0] + 1])

        locator = np.asarray(render(base_image(), 22.8976, 77.3475).convert("L"))
        self.assertEqual(int((locator[:8] < 128).sum()), 0, "frame rule along the top of the locator")

    def test_coordinate_gate_follows_provenance_not_the_read_confidence(self):
        """`coords_confidence` grades the dot read, not the location.

        Burzahom is labelled `high` and sits 139 km from Burzahom; Pattadakal is
        labelled `none` and is exact. Gating on the adjective rejected the good
        coordinates and accepted the bad ones, so the gate is `coords_provisional`.
        """
        payload, _ = build_export()
        exported = {site["slug"]: site for site in payload["sites"]}

        burzahom = exported["burzahom"]["location"]
        self.assertEqual(burzahom["readConfidence"], "high")
        self.assertFalse(burzahom["scorable"])
        self.assertIsNone(burzahom["acceptedRadiusKm"])

        pattadakal = exported["pattadakal"]["location"]
        self.assertEqual(pattadakal["readConfidence"], "none")
        self.assertTrue(pattadakal["scorable"])
        self.assertEqual(pattadakal["acceptedRadiusKm"], 25)

        for site in payload["sites"]:
            location = site["location"]
            self.assertEqual(location["scorable"],
                             location["verified"] and location["coordinates"] is not None)
            if not location["verified"]:
                self.assertIn("coordinate_unverified", site["editorial"]["issues"])
                self.assertIsNone(location["acceptedRadiusKm"])

    def test_index_coordinates_match_the_canonical_markdown(self):
        """The maps and the cover are drawn from records, the export from Markdown.

        They agree today. Nothing asserted it, and the names have already drifted
        apart once — thirteen of them — so a corrected coordinate could leave a
        locator pinned at the old place with no test to notice.
        """
        index = {record["slug"]: record
                 for record in json.loads((DATA / "sites.json").read_text(encoding="utf-8"))}
        for md in SITES.rglob("*.md"):
            meta, _ = load_frontmatter(md.read_text(encoding="utf-8"))
            self.assertIn(md.stem, index, f"{md.stem} is missing from data/sites.json")
            self.assertEqual(
                list(index[md.stem].get("coords") or []),
                list(meta.get("coords") or []),
                f"{md.stem}: data/sites.json coordinate differs from the Markdown",
            )
        self.assertEqual(len(index), len(list(SITES.rglob("*.md"))))

    def test_editorial_frontmatter_survives_a_rebuild(self):
        """The fields the web gate demands are hand-written and derived by nothing."""
        fresh = {"name": "X", "categories": [], "state": "", "coords": [],
                 "coords_confidence": "none", "coords_from": "", "coords_provisional": True,
                 "dot_px": [], "images": [], "status": "raw", "sources": [], "locked": []}
        prev = dict(fresh, state="Kerala", sources=["upinder2008"],
                    review_status="reviewed", model_answer_30="A thirty-word note.",
                    recall_points=["pit dwellings"], location_type="area")

        out = apply_overrides(fresh, prev)
        for field in ("review_status", "model_answer_30", "recall_points", "location_type"):
            self.assertEqual(out[field], prev[field], f"{field} was wiped by a rebuild")
        self.assertEqual(out["sources"], ["upinder2008"])
        self.assertEqual(out["state"], "Kerala")

    def test_body_parses_into_anchors_and_sources(self):
        body = (
            "- **Location**: Bhilwara district, Rajasthan.\n"
            "- **Period/Level**: Three phases excavated by V. N. Misra.\n"
            "- **Key Finds & Significance**: The richest microlithic assemblage.\n"
            "  - Some fifty thousand microliths were recovered.\n"
            "  - *Sources*: Upinder Singh, ch. 2; R. S. Sharma.\n"
        )
        facts, sources = parse_body(body)
        self.assertEqual([f["label"] for f in facts],
                         ["Location", "Period/Level", "Key Finds & Significance"])
        self.assertEqual(facts[2]["subs"], ["Some fifty thousand microliths were recovered."])
        # the sources sub-bullet is lifted out rather than left in the list
        self.assertEqual(sources, "Upinder Singh, ch. 2; R. S. Sharma")
        self.assertEqual(facts[0]["subs"], [])

    def test_inline_escapes_before_marking_up(self):
        # a stray angle bracket or ampersand must never become markup
        self.assertEqual(inline("Ashoka & <b>Devanampiya</b>"),
                         "Ashoka &amp; &lt;b&gt;Devanampiya&lt;/b&gt;")
        self.assertEqual(inline("the *teri* industry"), "the <em>teri</em> industry")
        self.assertEqual(inline("**Location**: x"), "<strong>Location</strong>: x")
        # 5 * 3 * 2 is arithmetic, not emphasis
        self.assertEqual(inline("5 * 3 * 2"), "5 * 3 * 2")

    def test_chapter_config_points_at_real_folders(self):
        """A typo in chapters.json would silently file entries into a ghost chapter."""
        folders = {p.name for p in SITES.iterdir() if p.is_dir()}
        for src, dest in CHAPTERS["merge_into"].items():
            self.assertIn(src, folders, f"merge_into source {src!r} is not a chapter")
            self.assertIn(dest, folders, f"merge_into target {dest!r} is not a chapter")
        slugs = {p.stem for p in SITES.rglob("*.md")}
        for slug, dest in CHAPTERS["move_sites"].items():
            self.assertIn(slug, slugs, f"move_sites slug {slug!r} is not a record")
            self.assertIn(dest, folders, f"move_sites target {dest!r} is not a chapter")
        for folder in folders:
            self.assertIn(folder, CHAPTERS["titles"], f"{folder} has no printed title")

    def test_printed_chapter_numbers_have_no_gaps(self):
        nums = numbering({"01-a": [], "05-b": [], "23-c": []})
        self.assertEqual(list(nums.values()), ["01", "02", "03"])

    def test_roman_folios(self):
        self.assertEqual([roman(n) for n in (1, 2, 4, 9, 14)],
                         ["i", "ii", "iv", "ix", "xiv"])

    def test_every_entry_has_the_four_anchors(self):
        """The PDF is set on the assumption that every body has this shape."""
        expected = ["Location", "Period/Level", "Key Finds & Significance"]
        for md in SITES.rglob("*.md"):
            meta, body = load_frontmatter(md.read_text(encoding="utf-8"))
            if meta.get("status") == "missing":
                continue
            facts, _ = parse_body(body)
            self.assertEqual([f["label"] for f in facts], expected,
                             f"{md.relative_to(ROOT)} is not in the 4-anchor format")

    def test_sites_directory_integrity(self):
        md_files = list(SITES.rglob("*.md"))
        self.assertGreater(len(md_files), 450, "Expected at least 450 site markdown files")
        for md in md_files:
            text = md.read_text(encoding="utf-8")
            meta, body = load_frontmatter(text)
            self.assertIn("name", meta, f"Missing name in {md}")
            self.assertIn("status", meta, f"Missing status in {md}")


if __name__ == "__main__":
    unittest.main()
