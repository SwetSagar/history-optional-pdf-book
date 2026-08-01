"""Find passages in the OCR'd library that support a site's claims.

    python3 pipeline/cite.py search "Bhimbetka"      one site, ranked passages
    python3 pipeline/cite.py batch                   candidates for every site
    python3 pipeline/cite.py unsupported             sites no source mentions

This is a finding aid, not a citation generator. It surfaces real passages from
real books for a human to read and confirm. It never asserts that a passage
supports a claim, and it never invents a reference.

On page numbers: the Upinder scans carry no printed folios, so `scan_page` is a
locator into the scan, not the book's page. Citations from this corpus are
chapter-level until a paginated copy is available; `data/bibliography.json`
records which works are paginated.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
DATA = ROOT / "data"

# Words that mark a descriptive passage rather than a passing mention in a list.
DESCRIPTIVE = re.compile(
    r"\b(excavat\w*|situated|located|lies|district|valley|river|km|miles|"
    r"settlement|site of|discovered|revealed|yielded|levels?|period|phase|"
    r"radiocarbon|dated|century|bce|ce|bp)\b", re.I)

SNIPPET = 320


def fold(s: str) -> str:
    """Lowercase and strip diacritics WITHOUT changing length, so offsets survive.

    Basham writes Aśoka, your cards write Ashoka. Folding handles the accents;
    query variants below handle the sh/s spelling difference.
    """
    out = []
    for ch in s:
        d = unicodedata.normalize("NFKD", ch)
        base = "".join(c for c in d if not unicodedata.combining(c)) or ch
        out.append(base[0] if base else ch)
    return "".join(out).lower()


_ALIASES: dict[str, list[str]] | None = None


def aliases_for(name: str) -> list[str]:
    """Historical names for a place, from data/aliases.json.

    Your cards use modern names; the sources use the names current when they
    were written. Kozhikode appears nowhere in the corpus, Calicut sixteen
    times. Without this the search silently reports 'no source' for places the
    library discusses at length.
    """
    global _ALIASES
    if _ALIASES is None:
        path = DATA / "aliases.json"
        raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        table = raw.get("aliases", {})
        _ALIASES = {}
        for modern, alts in table.items():
            group = [modern] + list(alts)
            for member in group:
                _ALIASES.setdefault(fold(member), []).extend(
                    g for g in group if fold(g) != fold(member))
    out: list[str] = []
    folded = fold(name)
    for key, alts in _ALIASES.items():
        if re.search(rf"\b{re.escape(key)}\b", folded):
            out.extend(alts)
    return out


def variants(name: str) -> list[str]:
    """Plausible romanisations of a site name, longest first."""
    base = fold(name)
    base = re.sub(r"\(.*?\)", " ", base)
    base = re.sub(r"[^a-z0-9 ]", " ", base)
    base = re.sub(r"\s+", " ", base).strip()

    # drop classifier words; 'Ajanta Caves' should find 'Ajanta'
    core = re.sub(r"\b(caves?|temple|monastery|gompa|fort|city|sites?|"
                  r"inscription|port|hills?|valley|minor|re|rock|edict|pillar)\b",
                  " ", base)
    core = re.sub(r"\s+", " ", core).strip()

    seeds = {base, core}
    for alt in aliases_for(name):
        a = re.sub(r"[^a-z0-9 ]", " ", fold(alt))
        a = re.sub(r"\s+", " ", a).strip()
        if len(a) >= 4:
            seeds.add(a)
    # split alternates: 'sisupalgarh or dhauli', 'didwana nagaur'
    for s in list(seeds):
        for part in re.split(r"\bor\b|/|,", s):
            part = part.strip()
            if len(part) >= 4:
                seeds.add(part)

    out: set[str] = set()
    for s in seeds:
        if len(s) < 4:
            continue
        out.add(s)
        out.add(s.replace("sh", "s"))
        out.add(s.replace("s", "sh"))
        out.add(re.sub(r"([bcdfghjklmnpqrstvwxyz])\1", r"\1", s))   # koldihwaa -> koldihwa
        out.add(s.replace("ee", "i").replace("oo", "u"))
    return sorted({v for v in out if len(v) >= 4}, key=len, reverse=True)


# --- BM25 -----------------------------------------------------------------
# Okapi BM25 over the corpus pages. Two things it adds over raw counting:
# inverse document frequency, so a name appearing on 400 pages counts for less
# than one appearing on 4; and length normalisation, so a short page densely
# about a site outranks a long page that merely lists it.
BM25_K1 = 1.5
BM25_B = 0.75


class BM25:
    def __init__(self, pages: list["Page"]):
        self.n = len(pages)
        self.lens = [max(1, p.folded.count(" ") + 1) for p in pages]
        self.avg = sum(self.lens) / max(1, self.n)
        self.df: dict[str, int] = {}
        self.tf: list[dict[str, int]] = []
        for p in pages:
            counts: dict[str, int] = {}
            for w in re.findall(r"[a-z0-9]+", p.folded):
                counts[w] = counts.get(w, 0) + 1
            self.tf.append(counts)
            for w in counts:
                self.df[w] = self.df.get(w, 0) + 1

    def idf(self, term: str) -> float:
        import math
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def score(self, i: int, terms: list[str]) -> float:
        total = 0.0
        dl = self.lens[i]
        counts = self.tf[i]
        for t in terms:
            f = counts.get(t, 0)
            if not f:
                continue
            total += self.idf(t) * (f * (BM25_K1 + 1)) / (
                f + BM25_K1 * (1 - BM25_B + BM25_B * dl / self.avg))
        return total


_BM25: "BM25 | None" = None


def bm25_for(pages: list["Page"]) -> "BM25":
    global _BM25
    if _BM25 is None or _BM25.n != len(pages):
        _BM25 = BM25(pages)
    return _BM25


@dataclass
class Page:
    source: str
    volume: str
    page: int
    text: str
    folded: str = field(repr=False, default="")


def load_corpus() -> list[Page]:
    pages: list[Page] = []
    for src_dir in sorted(CORPUS.iterdir()) if CORPUS.is_dir() else []:
        if not src_dir.is_dir():
            continue
        for f in sorted(src_dir.glob("*.json")):
            if f.name.startswith("_"):
                continue
            for rec in json.loads(f.read_text(encoding="utf-8")):
                t = rec.get("text", "")
                if not t.strip():
                    continue
                pages.append(Page(src_dir.name, f.stem, rec["page"], t, fold(t)))
    return pages


def snippet_at(text: str, pos: int, span: int = SNIPPET) -> str:
    a = max(0, pos - span // 2)
    b = min(len(text), pos + span // 2)
    s = re.sub(r"\s+", " ", text[a:b]).strip()
    return ("…" if a > 0 else "") + s + ("…" if b < len(text) else "")


def search(pages: list[Page], name: str, top: int = 5, use_bm25: bool = True) -> list[dict]:
    vs = variants(name)
    if not vs:
        return []
    primary = vs[0]
    bm = bm25_for(pages) if use_bm25 else None
    terms = [t for t in re.findall(r"[a-z0-9]+", primary) if len(t) > 2]
    hits: list[dict] = []
    for idx, pg in enumerate(pages):
        best_pos, matched, count = -1, None, 0
        for v in vs:
            # word-boundary match so 'Ajanta' does not hit 'Ajantapura'
            for m in re.finditer(rf"\b{re.escape(v)}\b", pg.folded):
                count += 1
                if best_pos < 0:
                    best_pos, matched = m.start(), v
            if count:
                break
        if best_pos < 0:
            continue
        window = pg.folded[max(0, best_pos - 200): best_pos + 200]
        # Occurrence count is the strongest signal that a page is ABOUT the site;
        # a single mention is usually a passing comparison ("as at Burzahom…").
        # Descriptive vocabulary helps, but capped so it cannot outweigh that.
        score = 3 * count + 2 * min(len(DESCRIPTIVE.findall(window)), 3)
        if matched == primary:
            score += 2
        if re.search(rf"\b{re.escape(matched)}\b[^.]{{0,60}}\b(is|was|lies|stands)\b"
                     rf"|\b(at|near|site of)\b[^.]{{0,30}}\b{re.escape(matched)}\b",
                     window):
            score += 4          # the sentence is predicating something of the site
        if bm is not None and terms:
            score += 1.6 * bm.score(idx, terms)
        hits.append({
            "source": pg.source, "volume": pg.volume, "scan_page": pg.page,
            "matched": matched, "occurrences": count, "score": round(score, 1),
            "snippet": snippet_at(pg.text, best_pos),
        })
    hits.sort(key=lambda h: (-h["score"], h["volume"], h["scan_page"]))
    return hits[:top]


def corpus_keys() -> dict[str, str]:
    """corpus folder name -> bibliography key, via the ingest manifest."""
    path = DATA / "sources.json"
    if not path.exists():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return {w["corpus"]: w["key"] for w in manifest.get("works", [])}


def load_sites() -> list[dict]:
    return json.loads((DATA / "sites.json").read_text(encoding="utf-8"))


def cmd_search(argv: list[str]) -> int:
    if not argv:
        print("usage: cite.py search \"<site name>\"", file=sys.stderr)
        return 2
    name = " ".join(argv)
    pages = load_corpus()
    hits = search(pages, name, top=6)
    print(f"\n{name}   —   {len(pages)} pages indexed, {len(hits)} candidates\n")
    if not hits:
        print("  no source in the corpus mentions this site.")
        print("  Write it from another source, or add that source to corpus/.")
        return 0
    bib = json.loads((DATA / "bibliography.json").read_text(encoding="utf-8"))
    keys = corpus_keys()
    for i, h in enumerate(hits, 1):
        work = bib.get(keys.get(h["source"], ""), {})
        author = work.get("author", "")
        title = work.get("title", h["source"])
        print(f"[{i}] {author + ', ' if author else ''}{title[:60]}")
        print(f"    {h['volume']}")
        print(f"    scan p{h['scan_page']} · matched '{h['matched']}' "
              f"· {h['occurrences']}x · score {h['score']}")
        print(f"    {h['snippet']}\n")
    print("Confirm one by reading it, then add its key to the site's `sources`.")
    print("Note: scan_page locates the passage in the scan — it is NOT a printed page.\n")
    return 0


def cmd_batch(_argv: list[str]) -> int:
    pages = load_corpus()
    sites = load_sites()
    targets = [s for s in sites if s["status"] != "missing"]
    out: dict[str, list[dict]] = {}
    none = 0
    for i, s in enumerate(targets, 1):
        hits = search(pages, s["name"], top=4)
        out[s["name"]] = hits
        if not hits:
            none += 1
        if i % 50 == 0:
            print(f"  {i}/{len(targets)}", file=sys.stderr)
    (DATA / "candidates.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    covered = len(targets) - none
    print(f"sites searched     : {len(targets)}")
    print(f"with candidates    : {covered}  ({100*covered/len(targets):.0f}%)")
    print(f"no source mentions : {none}")
    print(f"written            : data/candidates.json")
    return 0


def cmd_unsupported(_argv: list[str]) -> int:
    """Sites carrying text that no source in the corpus mentions — where errors hide."""
    cand_path = DATA / "candidates.json"
    if not cand_path.exists():
        print("run `cite.py batch` first", file=sys.stderr)
        return 2
    cands = json.loads(cand_path.read_text(encoding="utf-8"))
    sites = {s["name"]: s for s in load_sites()}
    rows = [n for n, h in cands.items() if not h]
    lines = ["# Sites with no supporting source", "",
             "These carry a description but no work in `corpus/` mentions them.",
             "Either the claim needs a source added to the corpus, or the entry",
             "needs checking — unsupported claims are where errors hide.", "",
             f"Total: **{len(rows)}**", ""]
    from collections import defaultdict
    by = defaultdict(list)
    for n in rows:
        by[sites[n]["categories"][0] if n in sites else "?"].append(n)
    for cat in sorted(by):
        lines.append(f"## {cat} ({len(by[cat])})")
        lines += [f"- [ ] {n}" for n in sorted(by[cat])]
        lines.append("")
    (ROOT / "reports" / "unsupported.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(rows)} sites with no supporting source -> reports/unsupported.md")
    return 0


COMMANDS = {"search": cmd_search, "batch": cmd_batch, "unsupported": cmd_unsupported}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(COMMANDS[sys.argv[1]](sys.argv[2:]))
