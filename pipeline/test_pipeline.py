"""Automated Unit Test Suite for the UPSC History Optional eBook Pipeline."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT / "sites"
DATA = ROOT / "data"

import sys
sys.path.insert(0, str(ROOT / "pipeline"))

from common import canonical_key, display_name, dump_frontmatter, load_frontmatter, match_keys, slugify
from dots import to_lonlat
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
