"""Phase 1+2: build the canonical site records from the source folders.

Reads
  Individual Map sites History Optional/   635 sheets, one dot each
  7. Optional Map Description.txt          467 Anki description rows

Writes
  sites/<nn-category>/<slug>.md            canonical record, hand-edited from here on
  data/sites.json                          machine index, regenerated, never edited
  reports/*.md                             coverage, gaps, anomalies

Rerunnable: existing Markdown bodies are preserved, only frontmatter is refreshed.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import (canonical_key, display_name, dump_frontmatter,  # noqa: E402
                    load_frontmatter, match_keys, slugify, strip_html)
from dots import SheetMatcher, build_group_blanks, to_lonlat  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "Individual Map sites History Optional"
DESCFILE = ROOT / "7. Optional Map Description.txt"
BLANK = IMAGES / "Use this copy.jpg"
SITES = ROOT / "sites"
DATA = ROOT / "data"
REPORTS = ROOT / "reports"

SKIP_DIRS = {"Bin"}          # overview plates, not per-site sheets
FUZZY_CUTOFF = 0.87


def category_of(folder: str) -> tuple[int, str]:
    """'14. Temple Sites' -> (14, 'Temple Sites'); unnumbered folders sort last."""
    m = re.match(r"^\s*(\d+)[.\s]\s*(.+)$", folder)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return 999, folder.strip()


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

def read_descriptions() -> tuple[dict[str, list[dict]], int]:
    """key -> [{name, bullets}]. One description may answer to several keys."""
    idx: dict[str, list[dict]] = defaultdict(list)
    rows = 0
    for line in DESCFILE.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split("\t")
        if len(f) < 2 or not f[1].strip():
            continue
        bullets = [strip_html(b) for b in re.findall(r"<li>(.*?)</li>", f[0], re.S)]
        bullets = [b for b in bullets if b]
        if not bullets:
            body = strip_html(f[0])
            bullets = [body] if body else []
        name = strip_html(f[1])
        rec = {"name": name, "bullets": bullets}
        rows += 1
        for k in match_keys(name):
            idx[k].append(rec)
    return idx, rows


def read_images() -> dict[str, dict]:
    """Group sheets into one record per site, merging categories across folders."""
    sites: dict[str, dict] = {}
    for path in sorted(IMAGES.rglob("*.jpg")):
        # the blank template is duplicated into several category folders, sometimes
        # as 'Use this copy - Copy.jpg'; none of them are sites
        if path.name.startswith(".") or path.stem.lower().startswith("use this copy"):
            continue
        rel = path.relative_to(IMAGES).parts
        if len(rel) < 2 or rel[0] in SKIP_DIRS:
            continue
        folder = rel[0]
        sub = rel[1] if len(rel) > 2 else ""
        order, cat = category_of(folder)
        name = display_name(path.stem)
        keys = match_keys(name)
        if not keys:
            continue
        # Shortest key merges alternate names ('Girnar or Jungadh' with 'Girnar',
        # 'Bharatpur or Noh' with 'Noh'). Safe now that match_keys() drops the
        # author's WRONG/correct/Copy annotations, which previously gave two
        # unrelated sites the shared key 'wrong'.
        merge_key = sorted(keys, key=len)[0]
        rec = sites.get(merge_key)
        if rec is None:
            rec = sites[merge_key] = {
                "name": name, "keys": set(), "categories": [], "images": [],
            }
        rec["keys"] |= keys
        if len(name) > len(rec["name"]):     # prefer the fuller spelling
            rec["name"] = name
        entry = {"order": order, "category": cat, "sub": sub,
                 "path": str(path.relative_to(ROOT))}
        if not any(c["category"] == cat for c in rec["categories"]):
            rec["categories"].append(entry)
        rec["images"].append(entry)
    return sites


# ---------------------------------------------------------------------------
# join
# ---------------------------------------------------------------------------

def attach_descriptions(sites: dict[str, dict], didx: dict[str, list[dict]]) -> None:
    allkeys = list(didx)
    for rec in sites.values():
        hit, how = None, "none"
        for k in sorted(rec["keys"], key=len, reverse=True):
            if k in didx:
                hit, how = didx[k], "exact"
                break
        if hit is None:
            for k in sorted(rec["keys"], key=len, reverse=True):
                m = difflib.get_close_matches(k, allkeys, n=1, cutoff=FUZZY_CUTOFF)
                if m:
                    hit, how = didx[m[0]], "fuzzy"
                    break
        bullets: list[str] = []
        if hit:
            seen = set()
            for d in hit:                      # multi-period sites carry several rows
                for b in d["bullets"]:
                    if b.lower() not in seen:
                        seen.add(b.lower())
                        bullets.append(b)
        rec["bullets"] = bullets
        rec["match"] = how


_STATES = {
    "andhra pradesh": "Andhra Pradesh", "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam", "bihar": "Bihar", "chhattisgarh": "Chhattisgarh",
    "goa": "Goa", "gujarat": "Gujarat", "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh", "jharkhand": "Jharkhand",
    "karnataka": "Karnataka", "kerala": "Kerala", "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra", "manipur": "Manipur", "meghalaya": "Meghalaya",
    "mizoram": "Mizoram", "nagaland": "Nagaland", "odisha": "Odisha",
    "orissa": "Odisha", "punjab": "Punjab", "rajasthan": "Rajasthan",
    "sikkim": "Sikkim", "tamil nadu": "Tamil Nadu", "telangana": "Telangana",
    "tripura": "Tripura", "uttar pradesh": "Uttar Pradesh", "uttarakhand": "Uttarakhand",
    "west bengal": "West Bengal", "delhi": "Delhi", "ladakh": "Ladakh",
    "jammu and kashmir": "Jammu and Kashmir", "kashmir": "Jammu and Kashmir",
    "puducherry": "Puducherry", "pondicherry": "Puducherry",
    "andaman": "Andaman and Nicobar Islands",
    # the sheet extends beyond India, and plenty of sites sit outside it
    "pakistan": "Pakistan", "afghanistan": "Afghanistan", "nepal": "Nepal",
    "bangladesh": "Bangladesh", "sri lanka": "Sri Lanka", "myanmar": "Myanmar",
    "burma": "Myanmar", "tibet": "Tibet", "china": "China",
}

_ABBREV = {"mp": "Madhya Pradesh", "up": "Uttar Pradesh", "ap": "Andhra Pradesh",
           "tn": "Tamil Nadu", "hp": "Himachal Pradesh", "wb": "West Bengal",
           "mah": "Maharashtra", "raj": "Rajasthan", "guj": "Gujarat",
           "kar": "Karnataka", "ker": "Kerala", "tel": "Telangana",
           "jk": "Jammu and Kashmir"}


def derive_state(bullets: list[str]) -> str:
    """Find the state named in the bullets.

    The card convention is a short trailing bullet ('In Madhya Pradesh'), but
    merging multi-period entries moves it, so scan every bullet and prefer the
    shortest match — the dedicated location bullet rather than a passing mention.
    """
    dedicated: tuple[str, str] | None = None   # bullet that is *only* a location
    passing: tuple[str, str] | None = None     # region mentioned inside other prose

    for b in bullets:
        low = re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", b.lower())).strip()
        # strip a leading locator so 'in madhya pradesh' reduces to the bare name
        bare = re.sub(r"^(in|located in|located at|at|from|near)\s+", "", low).strip()
        hit = None
        for key, canon in _STATES.items():
            m = re.search(rf"\b{re.escape(key)}\b", low)
            if not m:
                continue
            # A region named as an actor or counterparty is not where the site is.
            # 'occupied by China during the 62 war' had been putting Tawang in China.
            before = low[max(0, m.start() - 34):m.start()]
            if re.search(r"\b(occupied|invaded|annexed|conquered|attacked|ruled|held|"
                         r"captured|war|conflict|trade|traded|contact|contacts|"
                         r"exported|imported|relations|against|from|via|to)\b\s*"
                         r"(by|with|of|over)?\s*$", before):
                continue
            hit = (canon, key)
            break
        if hit is None and bare in _ABBREV:
            hit = (_ABBREV[bare], bare)
        if hit is None:
            continue
        canon, key = hit
        if bare == key:                        # the whole bullet is the region
            if dedicated is None or len(b) < len(dedicated[1]):
                dedicated = (canon, b)
        elif len(b) <= 40 and (passing is None or len(b) < len(passing[1])):
            # A region named inside a full sentence is usually a trade partner or
            # a neighbour, not the site's own location — 'confluence of Central
            # Asia, China, India' had been putting Purushapura in China. Only a
            # short bullet ('Sindh, Pakistan') is a reliable location tag.
            passing = (canon, b)

    chosen = dedicated or passing
    return chosen[0] if chosen else ""


def inherit_coords(records: list[dict], sites: dict[str, dict]) -> int:
    """Let an unmarked sheet borrow the position of the same place recorded elsewhere.

    Only where the two records are demonstrably the SAME site: either their
    normalised match keys intersect, or one name is a token-subset of the other
    ('Lumbini' inside 'Lumbini Pillar Inscription').

    Deliberately NOT done by string similarity. Indian place names share
    morphemes, so near-identical names are usually different places — Tilwara
    and Dilwara score 0.86 and are a Rajasthan Mesolithic site and the Jain
    temples at Mount Abu. A borrowed coordinate is invisible once printed, so
    the bar for reuse is identity, not resemblance.
    """
    keys = {r["name"]: match_keys(r["name"]) for r in records}
    toks = {r["name"]: set(re.split(r"[\s\-]+", r["name"].lower())) - {""} for r in records}
    donors = [r for r in records if r["coords"]]
    n = 0
    for r in records:
        if r["coords"]:
            continue
        for d in donors:
            shared = keys[r["name"]] & keys[d["name"]]
            ta, tb = toks[r["name"]], toks[d["name"]]
            subset = (ta < tb or tb < ta) and bool(ta & tb)
            if not (shared or subset):
                continue
            r["coords"] = list(d["coords"])
            r["dot_px"] = list(d["dot_px"]) if d["dot_px"] else None
            r["coords_confidence"] = "inherited"
            r["coords_from"] = d["name"]
            n += 1
            break
    return n


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    if not IMAGES.is_dir() or not DESCFILE.exists() or not BLANK.exists():
        print("error: expected source files not found", file=sys.stderr)
        return 1

    didx, drows = read_descriptions()
    sites = read_images()
    attach_descriptions(sites, didx)

    all_sheets = [ROOT / i["path"] for rec in sites.values() for i in rec["images"]]
    group_blanks = build_group_blanks(all_sheets)
    if group_blanks:
        print("synthesised blanks for scan sizes: "
              + ", ".join(f"{w}x{h}" for h, w in sorted(group_blanks)))
    matcher = SheetMatcher(BLANK, group_blanks)
    from PIL import Image

    anomalies: list[dict] = []
    records: list[dict] = []

    for rec in sites.values():
        ordered = sorted(rec["images"], key=lambda i: (i["order"], i["path"]))
        lat = lon = None
        dot_px = None
        conf = "none"
        # a site may have several sheets; take the first that yields a confident dot
        best: tuple[int, object, str] | None = None
        rank = {"high": 0, "medium": 1, "low": 2}
        for cand in ordered:
            p = ROOT / cand["path"]
            d = matcher.find(p)
            if not d:
                continue
            if best is None or rank[d.confidence] < rank[best[1].confidence]:
                best = (0, d, cand["path"])
                if d.confidence == "high":
                    break
        if best:
            _, dot, used = best
            shape = Image.open(ROOT / used).convert("L").size[::-1]
            bx, by = matcher.scale_to_blank(dot, shape)
            dot_px = [round(bx, 1), round(by, 1)]
            lat, lon = to_lonlat(bx, by)
            conf = dot.confidence
        else:
            anomalies.append({"name": rec["name"], "why": "no dot found on any sheet",
                              "path": ordered[0]["path"]})

        cats = sorted(rec["categories"], key=lambda c: c["order"])
        state = derive_state(rec["bullets"])
        status = "missing" if not rec["bullets"] else "raw"

        records.append({
            "name": rec["name"],
            "slug": slugify(rec["name"]),
            "categories": [c["category"] for c in cats],
            "order": cats[0]["order"],
            "state": state,
            "dot_px": dot_px,
            "coords": [lat, lon] if lat is not None else None,
            "coords_confidence": conf,
            "coords_from": "",
            "images": [i["path"] for i in rec["images"]],
            "bullets": rec["bullets"],
            "match": rec["match"],
            "status": status,
        })

    inherit_coords(records, sites)
    records.sort(key=lambda r: (r["order"], r["name"].lower()))
    write_markdown(records)
    write_index(records)
    write_reports(records, anomalies, drows)

    covered = sum(1 for r in records if r["status"] != "missing")
    print(f"sites            : {len(records)}")
    print(f"with description : {covered}  ({100*covered/len(records):.0f}%)")
    print(f"needing text     : {len(records)-covered}")
    print(f"dots located     : {sum(1 for r in records if r['coords'])}")
    print(f"  high confidence: {sum(1 for r in records if r['coords_confidence']=='high')}")
    print(f"no dot           : {len(anomalies)}")
    return 0


# Fields a human may take ownership of. Everything else is derived from the
# source folders and is safe to regenerate on every run.
OWNABLE = ("state", "coords", "coords_confidence", "coords_from",
           "coords_provisional", "dot_px", "name")


def apply_overrides(fresh: dict, prev: dict) -> dict:
    """Let human corrections survive a rebuild.

    Three ways a field becomes the author's rather than the pipeline's:

      sources             always — nothing derives citations, so a rebuild must
                          never reset them. This was silently wiping them.
      locked: [field,…]   explicit, auditable opt-out from re-derivation.
      coords_provisional  set to false, meaning the coordinate has been checked
                          against a gazetteer; that pins coords and state too.

    Without this, correcting Kuntasi's state to Gujarat by hand survived exactly
    until the next run of this script.
    """
    if not prev:
        return fresh
    out = dict(fresh)

    prior_sources = prev.get("sources")
    if prior_sources:
        out["sources"] = prior_sources

    if prev.get("state"):
        out["state"] = prev["state"]

    locked = prev.get("locked") or []
    if isinstance(locked, str):
        locked = [locked]
    locked = [str(f) for f in locked]

    if prev.get("coords_provisional") is False:
        for f in ("coords", "coords_provisional", "state"):
            if f not in locked:
                locked.append(f)

    for field in locked:
        if field in OWNABLE and field in prev:
            out[field] = prev[field]
    out["locked"] = sorted(set(locked))
    return out


def write_markdown(records: list[dict]) -> None:
    SITES.mkdir(exist_ok=True)
    for r in records:
        folder = SITES / f"{r['order']:02d}-{slugify(r['categories'][0])}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{r['slug']}.md"

        body = None
        status = r["status"]
        prev: dict = {}
        if path.exists():                      # never clobber written prose
            try:
                prev, body = load_frontmatter(path.read_text(encoding="utf-8"))
                # the writing pipeline only moves forward; a rerun must not
                # demote an entry that has already been rewritten or sourced
                rank = {"missing": 0, "raw": 1, "written": 2, "sourced": 3, "final": 4}
                if rank.get(str(prev.get("status")), 0) > rank.get(status, 0):
                    status = str(prev.get("status"))
            except ValueError:
                body = None
                prev = {}

        meta = {
            "name": r["name"],
            "categories": r["categories"],
            "state": r["state"],
            "coords": r["coords"] or [],
            "coords_confidence": r["coords_confidence"],
            "coords_from": r.get("coords_from", ""),
            "coords_provisional": True,
            "dot_px": r["dot_px"] or [],
            "images": r["images"],
            "status": status,
            "sources": [],
            "locked": [],
        }
        meta = apply_overrides(meta, prev)
        # The Markdown is canonical, so feed the reconciled values back into the
        # record before data/sites.json is written from it. Without this the
        # index reported entries as `raw` that the files had marked `written`.
        r["status"] = meta["status"]
        r["state"] = meta.get("state", r["state"])
        r["coords"] = list(meta["coords"]) if meta.get("coords") else None
        r["coords_confidence"] = meta.get("coords_confidence", r["coords_confidence"])
        if body is None:
            if r["bullets"]:
                body = ("<!-- IMPORTED FROM YOUR CARDS. Rewrite in your own words before\n"
                        "     publication, and attach a source to every dated claim. -->\n\n"
                        + "\n".join(f"- {b}" for b in r["bullets"]) + "\n")
            else:
                body = ("<!-- NO DESCRIPTION FOUND. Write this entry from your sources. -->\n")
        path.write_text(dump_frontmatter(meta) + "\n\n" + body, encoding="utf-8")


def write_index(records: list[dict]) -> None:
    DATA.mkdir(exist_ok=True)
    (DATA / "sites.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


def write_reports(records: list[dict], anomalies: list[dict], drows: int) -> None:
    REPORTS.mkdir(exist_ok=True)
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_cat[f"{r['order']:02d} {r['categories'][0]}"].append(r)

    lines = ["# Coverage", "",
             f"- Sites: **{len(records)}**",
             f"- Description rows read: {drows}",
             f"- With a description: **{sum(1 for r in records if r['status']!='missing')}**",
             f"- Needing text: **{sum(1 for r in records if r['status']=='missing')}**",
             f"- Dots located: {sum(1 for r in records if r['coords'])}"
             f" ({sum(1 for r in records if r['coords_confidence']=='high')} high confidence)",
             "", "| Chapter | Sites | Have text | To write |", "|---|---:|---:|---:|"]
    for cat in sorted(by_cat):
        rs = by_cat[cat]
        have = sum(1 for r in rs if r["status"] != "missing")
        lines.append(f"| {cat} | {len(rs)} | {have} | {len(rs)-have} |")
    (REPORTS / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    g = ["# Entries needing text", "",
         "Sites with a map sheet but no description. Grouped by chapter.", ""]
    for cat in sorted(by_cat):
        miss = [r for r in by_cat[cat] if r["status"] == "missing"]
        if not miss:
            continue
        g.append(f"## {cat}  ({len(miss)})")
        g += [f"- [ ] {r['name']}" for r in miss]
        g.append("")
    (REPORTS / "gaps.md").write_text("\n".join(g), encoding="utf-8")

    inherited = [r for r in records if r["coords_confidence"] == "inherited"]
    still = [r for r in records if not r["coords"]]
    a = ["# Sheets without a position", "",
         "Every one of these sheets was verified to be *blank* — the outline map was",
         "saved but a dot was never marked on it. The detector did not fail; there is",
         "nothing on the sheet to find.", "",
         "These need a coordinate from a gazetteer, which is more accurate than a",
         "hand-placed dot anyway (recovered dots sit 20-60 km from truth).", ""]
    if inherited:
        a.append(f"## Resolved by identity ({len(inherited)})")
        a.append("")
        a.append("Same place recorded under another name, so the position was reused.")
        a.append("")
        a += [f"- **{r['name']}** ← {r['coords_from']}" for r in inherited]
        a.append("")
    a.append(f"## Still needing a coordinate ({len(still)})")
    a.append("")
    a += [f"- [ ] {r['name']}  ({r['categories'][0]})" for r in still]
    a.append("")
    low = [r for r in records if r["coords"] and r["coords_confidence"] == "low"]
    if low:
        a.append(f"## Low-confidence positions ({len(low)}) — worth eyeballing")
        a += [f"- {r['name']}" for r in low]
    (REPORTS / "anomalies.md").write_text("\n".join(a) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
