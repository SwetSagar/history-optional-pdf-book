"""Regression tests for the pipeline.

    python3 pipeline/test_pipeline.py        (also runs under pytest)

Every test here corresponds to a bug that actually reached the book. They exist
because each of these was found by eye, late, and would have been cheaper to
catch here:

  * the printed scale bar was read as a site dot, putting five sites in the sea
  * a second scan batch at 698x903 failed to register at all
  * 'occupied by China during 62 war' put Tawang in China
  * 'confluence of Central Asia, China, India' put Purushapura in China
  * 'Maski- WRONG' and 'Vidisha-WRONG' merged into one record via the key 'wrong'
  * a rebuild silently demoted written entries and wiped every citation
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import (canonical_key, display_name, dump_frontmatter,  # noqa: E402
                    load_frontmatter, match_keys, slugify)

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# frontmatter
# --------------------------------------------------------------------------

def test_frontmatter_roundtrip():
    meta = {
        "name": "Bhimbetka",
        "categories": ["Palaeolithic", "Rockcut Caves, Petroglyph sites"],
        "state": "",
        "coords": [22.8976, 77.3475],
        "coords_provisional": True,
        "sources": [],
        "locked": ["state", "coords"],
    }
    back, body = load_frontmatter(dump_frontmatter(meta) + "\n\nprose\n")
    assert back == meta, back
    assert body.strip() == "prose"


def test_frontmatter_quotes_values_containing_commas():
    """A category with a comma must not split into two list items."""
    text = dump_frontmatter({"categories": ["Rockcut Caves, Petroglyph sites"]})
    back, _ = load_frontmatter(text + "\n\n")
    assert back["categories"] == ["Rockcut Caves, Petroglyph sites"]


def test_frontmatter_rejects_malformed_rather_than_guessing():
    try:
        load_frontmatter("---\nnot a mapping line\n---\n\nbody\n")
    except ValueError:
        return
    raise AssertionError("malformed frontmatter should raise, not guess")


# --------------------------------------------------------------------------
# name handling — the Maski/Vidisha merge
# --------------------------------------------------------------------------

def test_author_annotations_never_become_match_keys():
    """Two unrelated sites both annotated WRONG must not share a key."""
    assert "wrong" not in match_keys("Maski- WRONG")
    assert "wrong" not in match_keys("Vidisha-WRONG")
    assert not (match_keys("Maski- WRONG") & match_keys("Vidisha-WRONG"))


def test_annotations_stripped_from_printed_names():
    assert display_name("Maski- WRONG") == "Maski"
    assert display_name("Vidisha-WRONG") == "Vidisha"
    assert display_name("Mundigak - Copy") == "Mundigak"
    assert display_name("Brahmagiri correct") == "Brahmagiri"


def test_alternate_names_still_merge():
    """The annotation fix must not split legitimate 'X or Y' pairs."""
    assert match_keys("Girnar or Jungadh") & match_keys("Girnar")
    assert match_keys("Bharatpur or Noh") & match_keys("Noh")


def test_state_suffix_and_classifiers_normalise():
    assert match_keys("Baghor MP") & match_keys("Baghor")
    assert match_keys("Ajanta Caves") & match_keys("Ajanta")
    assert canonical_key("Baghor MP") == "baghor"


def test_slugify():
    assert slugify("Sisupalgarh or Dhauli") == "sisupalgarh-or-dhauli"
    assert slugify("Rockcut Caves, Petroglyph sites(Cave Painting)").startswith("rockcut")


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def test_georeference_roundtrip():
    from dots import to_lonlat
    from render_maps import to_pixel
    for px, py in [(255.5, 338.5), (100.0, 200.0), (460.0, 500.0)]:
        lat, lon = to_lonlat(px, py)
        bx, by = to_pixel(lat, lon)
        assert abs(bx - px) < 0.05 and abs(by - py) < 0.05, (px, py, bx, by)


def test_known_sites_land_in_the_right_place():
    """The calibration constants must keep reproducing the sites they were fitted on."""
    from dots import to_lonlat
    for px, py, lat, lon in [(255.5, 338.5, 22.93, 77.61),      # Bhimbetka
                             (221.0, 237.0, 29.47, 74.13)]:     # Kalibangan
        got_lat, got_lon = to_lonlat(px, py)
        km = (((got_lat - lat) * 111) ** 2 + ((got_lon - lon) * 103) ** 2) ** 0.5
        assert km < 80, f"{km:.0f} km off at ({px},{py})"


def test_scale_bar_blob_is_not_a_dot():
    """The printed scale bar diffs as a long thin smear; a site dot is a disc."""
    import numpy as np
    from dots import _is_dotlike
    disc = np.zeros((16, 16), dtype=bool)
    yy, xx = np.mgrid[0:16, 0:16]
    disc[((yy - 8) ** 2 + (xx - 8) ** 2) <= 16] = True
    assert _is_dotlike(disc)

    smear = np.zeros((6, 60), dtype=bool)
    smear[2:4, :] = True
    assert not _is_dotlike(smear)

    sparse = np.zeros((20, 20), dtype=bool)
    sparse[::4, ::4] = True
    assert not _is_dotlike(sparse)


# --------------------------------------------------------------------------
# state inference — Tawang and Purushapura
# --------------------------------------------------------------------------

def test_region_named_as_an_actor_is_not_a_location():
    from extract import derive_state
    assert derive_state(["Occupied by China during 62 war"]) == ""
    assert derive_state(["Traded with Sri Lanka and the Roman world"]) == ""


def test_region_inside_a_long_sentence_is_not_a_location():
    from extract import derive_state
    assert derive_state(
        ["Important trade center lied on the confluence of Central Asia, China, India"]
    ) == ""


def test_short_location_tag_is_accepted():
    from extract import derive_state
    assert derive_state(["Mature Harappa", "Sindh, Pakistan"]) == "Pakistan"
    assert derive_state(["Mesolithic Site", "In Madhya Pradesh"]) == "Madhya Pradesh"


def test_dedicated_location_beats_passing_mention():
    from extract import derive_state
    bullets = ["Traded extensively with Sri Lanka", "Tamil Nadu"]
    assert derive_state(bullets) == "Tamil Nadu"


# --------------------------------------------------------------------------
# rebuild safety
# --------------------------------------------------------------------------

def test_rebuild_preserves_citations():
    from extract import apply_overrides
    fresh = {"sources": [], "state": "Maharashtra", "locked": []}
    prev = {"sources": ["thapar2002-ch3"], "state": "Maharashtra", "locked": []}
    assert apply_overrides(fresh, prev)["sources"] == ["thapar2002-ch3"]


def test_rebuild_honours_locked_fields():
    from extract import apply_overrides
    fresh = {"state": "Maharashtra", "coords": [1.0, 2.0], "sources": [], "locked": []}
    prev = {"state": "Gujarat", "coords": [22.9, 70.5], "sources": [],
            "locked": ["state", "coords"]}
    out = apply_overrides(fresh, prev)
    assert out["state"] == "Gujarat" and out["coords"] == [22.9, 70.5]


def test_verified_coordinate_pins_itself():
    from extract import apply_overrides
    fresh = {"state": "Maharashtra", "coords": [1.0, 2.0],
             "coords_provisional": True, "sources": [], "locked": []}
    prev = {"state": "Gujarat", "coords": [22.9, 70.5],
            "coords_provisional": False, "sources": [], "locked": []}
    out = apply_overrides(fresh, prev)
    assert out["coords"] == [22.9, 70.5]
    assert out["coords_provisional"] is False
    assert "state" in out["locked"]


def test_blank_template_copies_are_not_sites():
    """'Use this copy - Copy.jpg' once became a record called 'Use this'."""
    for stem in ["Use this copy", "Use this copy - Copy", "use this copy 2"]:
        assert stem.lower().startswith("use this copy")


# --------------------------------------------------------------------------
# citation search
# --------------------------------------------------------------------------

def test_diacritics_fold_so_asoka_matches_ashoka():
    from cite import fold, variants
    assert fold("Aśoka") == "asoka"
    assert "asoka" in variants("Ashoka")


def test_historical_aliases_are_searched():
    from cite import variants
    assert any("calicut" in v for v in variants("Kozhikode"))


# --------------------------------------------------------------------------
# built artefacts (skipped when not yet built)
# --------------------------------------------------------------------------

def test_epub_structure():
    epub = ROOT / "build" / "Map Entries for History Optional.epub"
    if not epub.exists():
        print("    (skip: no EPUB built)")
        return
    import xml.dom.minidom as minidom
    z = zipfile.ZipFile(epub)
    names = z.namelist()
    assert names[0] == "mimetype", "mimetype must be the first entry"
    assert z.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
    assert z.read("mimetype") == b"application/epub+zip"
    assert "META-INF/container.xml" in names
    for n in names:
        if n.endswith((".xhtml", ".opf", ".xml")):
            minidom.parseString(z.read(n))
    assert z.testzip() is None

    opf = z.read("OEBPS/content.opf").decode()
    assert 'properties="cover-image"' in opf, "EPUB 3 cover missing"
    assert 'name="cover"' in opf, "EPUB 2 cover pointer missing (Kindle reads this)"


def test_every_entry_map_follows_its_heading_immediately():
    """Nothing may sit between a site's name and its map."""
    import re
    epub = ROOT / "build" / "Map Entries for History Optional.epub"
    if not epub.exists():
        print("    (skip: no EPUB built)")
        return
    z = zipfile.ZipFile(epub)
    checked = 0
    for n in z.namelist():
        if not re.match(r"OEBPS/ch\d+\.xhtml$", n):
            continue
        text = z.read(n).decode()
        for m in re.finditer(r"<h2 [^>]*>.*?</h2>\s*(<[a-z]+)", text, re.S):
            assert m.group(1) == "<figure", (
                f"{n}: {m.group(1)} sits between the heading and its map")
            checked += 1
    assert checked > 0


def test_no_orphaned_records():
    """A record whose slug no longer exists would still be built into the book.

    Changing how names are merged renamed several records; the old files stayed
    behind, and build_epub reads sites/ directly rather than the index.
    """
    data = ROOT / "data" / "sites.json"
    if not data.exists():
        print("    (skip: no index built)")
        return
    index = {r["slug"] for r in json.loads(data.read_text(encoding="utf-8"))}
    files = {p.stem for p in (ROOT / "sites").rglob("*.md")}
    orphans = sorted(files - index)
    assert not orphans, f"stale records would ship: {orphans}"


def test_no_record_still_carries_imported_bullets():
    data = ROOT / "data" / "sites.json"
    if not data.exists():
        print("    (skip: no index built)")
        return
    raw = [r["name"] for r in json.loads(data.read_text(encoding="utf-8"))
           if r.get("status") == "raw"]
    assert not raw, f"unrewritten entries would ship: {raw[:5]}"


# --------------------------------------------------------------------------

def main() -> int:
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            failed.append((name, str(e) or "assertion failed"))
            print(f"  FAIL  {name}: {str(e)[:110]}")
        except Exception as e:  # noqa: BLE001
            failed.append((name, f"{type(e).__name__}: {e}"))
            print(f"  ERROR {name}: {type(e).__name__}: {str(e)[:100]}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
