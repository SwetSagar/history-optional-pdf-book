"""Resolve site coordinates against Wikidata, cross-checked with the map sheets.

    python3 pipeline/gazetteer.py build      query Wikidata, write data/gazetteer.json
    python3 pipeline/gazetteer.py report     summarise what was resolved
    python3 pipeline/gazetteer.py apply      write confident results into sites/

Never trusts a single source. A search for "Maski" returns a Kraków literary
magazine first and a Quebec municipality second; the Karnataka town is third.
So a candidate is only accepted when it is inside South Asia AND agrees with the
position the author marked on their own sheet. Two independent sources agreeing
is evidence; one search result is not.

Where they agree, Wikidata's coordinate is taken — it is exact, while a dot
placed by hand on a small outline sheet is not. Where they disagree, or where
there is no dot to check against, the candidate is recorded for review and
nothing is written.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import dump_frontmatter, load_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "gazetteer.json"
CACHE = ROOT / "data" / ".wikidata_cache.json"

UA = "HistoryOptionalAtlas/0.1 (personal research project; contact via repository)"
# The map sheet spans 60-100E; allow a margin and the full latitude range it covers.
BBOX = (4.0, 39.0, 59.0, 101.0)          # lat_min, lat_max, lon_min, lon_max
AGREE_KM = 150                            # dot and Wikidata counted as agreeing
PAUSE = 1.1
# The query service is currently rate-limiting to 1 request/minute during an
# outage, so resolve in batches of labels rather than one request per site:
# 496 names becomes ~10 queries instead of ~1000.
BATCH = 50
SPARQL_PAUSE = 64.0

GOOD_DESC = ("archaeolog", "village", "town", "city", "district", "site",
             "temple", "fort", "cave", "monastery", "stupa", "river", "port",
             "human settlement", "india", "pakistan", "nepal", "bangladesh",
             "sri lanka", "afghanistan", "ruins", "heritage")
BAD_DESC = ("magazine", "album", "film", "band", "song", "surname", "given name",
            "municipality in", "commune in", "quebec", "belarus", "poland",
            "encyclopedia article", "wikimedia", "disambiguation")


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    return (((a[0] - b[0]) * 111.0) ** 2 + ((a[1] - b[1]) * 103.0) ** 2) ** 0.5


class Wikidata:
    def __init__(self):
        self.cache: dict = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        self.calls = 0

    def _get(self, url: str) -> dict:
        """Fetch with backoff. Raises if it never succeeds — the caller must NOT
        cache a failure, or a rate-limited run poisons the cache with empty
        results that look like genuine misses on the next run."""
        delay = PAUSE
        last = None
        for attempt in range(5):
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            self.calls += 1
            time.sleep(delay)
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode())
            except Exception as e:                   # noqa: BLE001
                last = e
                code = getattr(e, "code", None)
                if code == 429 or code is None or code >= 500:
                    delay = min(delay * 3 + 1.0, 30.0)
                    continue
                raise
        raise RuntimeError(f"gave up after retries: {last}")

    def search(self, name: str) -> list[dict]:
        key = f"s:{name}"
        if key in self.cache:
            return self.cache[key]
        u = ("https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json"
             "&language=en&uselang=en&type=item&limit=8&search="
             + urllib.parse.quote(name))
        hits = [{"qid": h["id"], "label": h.get("label", ""),
                 "desc": h.get("description", "")}
                for h in self._get(u).get("search", [])]
        self.cache[key] = hits                       # only reached on success
        return hits

    def coords(self, qids: list[str]) -> dict[str, tuple[float, float]]:
        want = [q for q in qids if f"c:{q}" not in self.cache]
        for i in range(0, len(want), 45):
            batch = want[i:i + 45]
            u = ("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json"
                 "&props=claims&ids=" + "|".join(batch))
            ents = self._get(u).get("entities", {})
            for q in batch:
                val = None
                claims = ents.get(q, {}).get("claims", {}).get("P625")
                if claims:
                    v = claims[0]["mainsnak"].get("datavalue", {}).get("value", {})
                    if "latitude" in v:
                        val = [v["latitude"], v["longitude"]]
                self.cache[f"c:{q}"] = val
        return {q: tuple(self.cache[f"c:{q}"]) for q in qids
                if self.cache.get(f"c:{q}")}

    def save(self):
        CACHE.write_text(json.dumps(self.cache), encoding="utf-8")


def score(hit: dict, pos: tuple[float, float], dot) -> tuple[float, str]:
    d = hit["desc"].lower()
    if any(b in d for b in BAD_DESC):
        return -100, "description rules it out"
    s = sum(2 for g in GOOD_DESC if g in d)
    note = ""
    if dot:
        dist = km(pos, tuple(dot))
        note = f"{dist:.0f} km from sheet dot"
        s += 12 if dist <= AGREE_KM else -8
    return s, note


def sparql(names: list[str]) -> dict[str, list[dict]]:
    """Resolve many labels in one query.

    Matching rdfs:label OR skos:altLabel and *requiring* a coordinate is far more
    precise than free-text search: it returns the Raichur Maski directly instead
    of a Krakow literary magazine, because magazines have no coordinates.
    """
    values = " ".join('"%s"@en' % n.replace('\\', '').replace('"', '') for n in names)
    q = ("SELECT ?l ?item ?coord ?desc WHERE { VALUES ?l { " + values + " } "
         "{ ?item rdfs:label ?l } UNION { ?item skos:altLabel ?l } "
         "?item wdt:P625 ?coord . "
         'OPTIONAL { ?item schema:description ?desc . FILTER(LANG(?desc)="en") } }')
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())

    out: dict[str, list[dict]] = {}
    for b in data["results"]["bindings"]:
        raw = b["coord"]["value"]
        if not raw.startswith("Point("):
            continue                      # globe URI or novalue, not a position
        pt = raw.replace("Point(", "").replace(")", "").split()
        if len(pt) != 2:
            continue
        try:
            lat, lon = float(pt[1]), float(pt[0])
        except ValueError:
            continue
        out.setdefault(b["l"]["value"], []).append({
            "qid": b["item"]["value"].rsplit("/", 1)[-1],
            "label": b["l"]["value"],
            "desc": b.get("desc", {}).get("value", ""),
            "coords": [round(lat, 5), round(lon, 5)],
        })
    return out


def build() -> int:
    sites = json.loads((ROOT / "data" / "sites.json").read_text(encoding="utf-8"))
    cache: dict = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    out: dict[str, dict] = {}

    todo = [s["name"] for s in sites if f"q:{s['name']}" not in cache]
    print(f"{len(sites)} sites, {len(todo)} still to resolve "
          f"({(len(todo) + BATCH - 1)//BATCH} queries at ~{SPARQL_PAUSE:.0f}s each)")
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        try:
            got = sparql(chunk)
        except Exception as e:                       # noqa: BLE001
            print(f"    batch failed ({e}); retrying once after backoff",
                  file=sys.stderr)
            time.sleep(SPARQL_PAUSE * 2)
            try:
                got = sparql(chunk)
            except Exception as e2:                  # noqa: BLE001
                print(f"    batch failed again: {e2}", file=sys.stderr)
                continue
        for n in chunk:
            cache[f"q:{n}"] = got.get(n, [])
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        print(f"  {min(i+BATCH, len(todo))}/{len(todo)} resolved", flush=True)
        if i + BATCH < len(todo):
            time.sleep(SPARQL_PAUSE)

    try:
        for i, s in enumerate(sites, 1):
            name = s["name"]
            hits = cache.get(f"q:{name}", [])
            cands = []
            for h in hits:
                pos = tuple(h["coords"])
                if not (BBOX[0] <= pos[0] <= BBOX[1] and BBOX[2] <= pos[1] <= BBOX[3]):
                    continue                          # outside the sheet's world
                sc, note = score(h, pos, s.get("coords"))
                cands.append({**h, "score": sc, "note": note})
            cands.sort(key=lambda c: -c["score"])

            verdict, chosen = "unresolved", None
            if cands:
                best = cands[0]
                if s.get("coords") and km(tuple(best["coords"]), tuple(s["coords"])) <= AGREE_KM:
                    verdict, chosen = "confirmed", best
                elif best["score"] > 0:
                    verdict, chosen = "review", best
                else:
                    verdict, chosen = "review", best
            out[s["slug"]] = {"name": name, "verdict": verdict,
                              "chosen": chosen, "candidates": cands[:4],
                              "sheet_dot": s.get("coords")}
    finally:
        CACHE.write_text(json.dumps(cache), encoding="utf-8")

    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    report()
    return 0


def report() -> int:
    if not OUT.exists():
        print("run `gazetteer.py build` first", file=sys.stderr)
        return 2
    g = json.loads(OUT.read_text(encoding="utf-8"))
    from collections import Counter
    c = Counter(v["verdict"] for v in g.values())
    print(f"sites            : {len(g)}")
    print(f"  confirmed      : {c['confirmed']}   (Wikidata agrees with the sheet dot)")
    print(f"  needs review   : {c['review']}")
    print(f"  unresolved     : {c['unresolved']}   (nothing plausible in South Asia)")

    lines = ["# Gazetteer", "",
             "Wikidata coordinates cross-checked against the position marked on the",
             "author's own map sheet. Only agreement between the two is treated as",
             "confirmation; a lone search result is not.", "",
             f"- Confirmed: **{c['confirmed']}**",
             f"- Needs review: **{c['review']}**",
             f"- Unresolved: **{c['unresolved']}**", "",
             "## Needs review", "",
             "| Site | Wikidata | Coordinates | Note |", "|---|---|---|---|"]
    for v in sorted(g.values(), key=lambda x: x["name"]):
        if v["verdict"] != "review" or not v["chosen"]:
            continue
        ch = v["chosen"]
        lines.append(f"| {v['name']} | {ch['label']} — {ch['desc'][:44]} | "
                     f"{ch['coords'][0]:.3f}, {ch['coords'][1]:.3f} | {ch['note'] or '—'} |")
    unres = [v["name"] for v in g.values() if v["verdict"] == "unresolved"]
    lines += ["", f"## Unresolved ({len(unres)})", ""]
    lines += [f"- [ ] {n}" for n in sorted(unres)]
    (ROOT / "reports" / "gazetteer.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  -> reports/gazetteer.md")
    return 0


def apply() -> int:
    """Write only the confirmed coordinates, and pin them so a rebuild keeps them."""
    g = json.loads(OUT.read_text(encoding="utf-8"))
    index = {p.stem: p for p in (ROOT / "sites").rglob("*.md")}
    n = 0
    for slug, v in g.items():
        if v["verdict"] != "confirmed" or slug not in index:
            continue
        p = index[slug]
        meta, body = load_frontmatter(p.read_text(encoding="utf-8"))
        meta["coords"] = v["chosen"]["coords"]
        meta["coords_confidence"] = "gazetteer"
        meta["coords_from"] = v["chosen"]["qid"]
        meta["coords_provisional"] = False       # auto-locks coords and state
        # lock the provenance too, or a rebuild relabels a gazetteer coordinate
        # as "high" (meaning a well-detected dot), losing where it actually came from
        locked = set(meta.get("locked") or []) | {
            "coords", "coords_provisional", "coords_confidence", "coords_from"}
        meta["locked"] = sorted(locked)
        p.write_text(dump_frontmatter(meta) + "\n\n" + body.rstrip() + "\n", encoding="utf-8")
        n += 1
    print(f"applied {n} confirmed coordinates (pinned against rebuild)")
    return 0


COMMANDS = {"build": build, "report": report, "apply": apply}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(COMMANDS[sys.argv[1]]())
