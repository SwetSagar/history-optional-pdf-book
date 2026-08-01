"""Shared helpers: name normalisation, slugs, and the tiny frontmatter format.

The canonical store for this project is one Markdown file per site under sites/.
Frontmatter is deliberately restricted to flat scalars and simple lists so it can
be parsed without a YAML dependency. Anything more complex belongs in the body.
"""
from __future__ import annotations

import html
import re
import unicodedata

# Words that appear in filenames/descriptions as classifiers rather than as part
# of the place name. Stripped only when generating match keys, never from display names.
CLASSIFIERS = {
    "site", "sites", "cave", "caves", "temple", "temples", "monastery", "gompa",
    "fort", "city", "cities", "inscription", "inscriptions", "port", "ports",
    "the", "of", "near", "at", "and",
}

# Trailing state/qualifier tokens people append to disambiguate files.
STATE_TOKENS = {
    "mp", "up", "ap", "tn", "hp", "jk", "wb", "mah", "raj", "guj", "kar", "ker",
    "tel", "ori", "odisha", "orissa", "bihar", "punjab", "haryana", "assam", "goa",
}

# Working annotations the author left in filenames ('Maski- WRONG', 'Brahmagiri
# correct'). They must never contribute a match key: two unrelated sites both
# annotated WRONG would otherwise share the key 'wrong' and be merged into one
# record — which is exactly what happened to Maski and Vidisha.
ANNOTATIONS = {"wrong", "correct", "copy", "new", "old", "final", "edit", "dup",
               "duplicate", "same", "check"}


def strip_html(s: str) -> str:
    """HTML fragment -> plain text, preserving nothing but the words."""
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def display_name(s: str) -> str:
    """Clean a raw filename stem or card field into a presentable site name."""
    s = strip_html(s)
    s = re.sub(r"\s*\(\d+\)\s*$", "", s)          # trailing "(2)"
    s = re.sub(r"^\s*\d+[.)]\s*", "", s)          # leading "12. "
    # working annotations belong in the author's filenames, not on a printed page
    s = re.sub(r"[\s\-–—,]*\b(" + "|".join(ANNOTATIONS) + r")\b\s*$", "", s, flags=re.I)
    s = re.sub(r"[\s\-–—,]*\b(" + "|".join(ANNOTATIONS) + r")\b\s*$", "", s, flags=re.I)
    # "Neolithic Site - Kile Gile Mohammed" -> "Kile Gile Mohammed"
    m = re.match(r"^[A-Za-z ]{3,30}\s+-\s+(.{3,})$", s)
    if m and re.search(r"\b(site|sites|temple|fort|cave|caves|remains|painting)\b", m.group(1), re.I) is None:
        head = s[: m.start(1)].lower()
        if re.search(r"\b(site|sites|temple|fort|cave|caves|remains|painting|paleao|palaeo)\b", head):
            s = m.group(1)
    return s.strip(" -,")


def match_keys(s: str) -> set[str]:
    """Every plausible lookup key for a label, for joining images to descriptions.

    Handles the real variation in this corpus: trailing state codes ("Baghor MP"),
    alternates ("Sisupalgarh or Dhauli"), compound labels ("Mirabai - Kurki"),
    and classifier words ("Ajanta Caves" vs "Ajanta").
    """
    s = strip_html(s).lower()
    s = re.sub(r"\(\d+\)", " ", s)
    s = re.sub(r"[^a-z0-9 \-/,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    parts = [s] + [p.strip() for p in re.split(r"\s*[-/,]\s*|\bor\b", s)]
    keys: set[str] = set()
    for p in parts:
        if not p:
            continue
        p = re.sub(r"\b\d{3,5}\s*-?\s*\d{0,4}\b", " ", p)     # years
        toks = [t for t in p.split() if t and t not in ANNOTATIONS]
        if not toks:
            continue
        # full form, minus classifiers
        core = [t for t in toks if t not in CLASSIFIERS]
        if core:
            keys.add("".join(core))
        # minus trailing state qualifier
        trimmed = [t for t in core if t not in STATE_TOKENS]
        if trimmed:
            keys.add("".join(trimmed))
        keys.add("".join(toks))
    return {k for k in keys if len(k) >= 3}


def canonical_key(s: str) -> str:
    """The single key a record is merged on.

    Taking the shortest of match_keys() is wrong: a short incidental token can be
    shared by unrelated sites. This derives one key from the whole name instead,
    with annotations and classifiers removed.
    """
    t = strip_html(s).lower()
    t = re.sub(r"\(\d+\)", " ", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\b\d{3,5}\s*-?\s*\d{0,4}\b", " ", t)
    toks = [w for w in t.split()
            if w not in ANNOTATIONS and w not in CLASSIFIERS and w not in STATE_TOKENS]
    if not toks:
        toks = [w for w in t.split() if w not in ANNOTATIONS] or t.split()
    return "".join(toks)


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", strip_html(s))
    s = s.encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return re.sub(r"-{2,}", "-", s) or "unnamed"


# --------------------------------------------------------------------------
# frontmatter
# --------------------------------------------------------------------------

def _fmt(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_fmt(x) for x in v) + "]"
    s = str(v)
    # quote anything that would confuse the reader: list/flow punctuation, leading
    # or trailing space, or an empty value
    if s == "" or re.search(r'[,\[\]{}"\']|^[>|#*&!%@`]|: |#|\n|^\s|\s$', s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def dump_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {_fmt(v)}")
    lines.append("---")
    return "\n".join(lines)


def _parse_scalar(s: str):
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x) for x in re.split(r",\s*(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", inner)]
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return s[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if s in ("true", "false"):
        return s == "true"
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d*\.\d+", s):
        return float(s)
    return s


def load_frontmatter(text: str) -> tuple[dict, str]:
    """Parse '---' delimited frontmatter. Raises on malformed input rather than guessing."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("unterminated frontmatter")
    head = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    meta: dict = {}
    for i, line in enumerate(head.split("\n"), start=2):
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"frontmatter line {i}: expected 'key: value', got {line!r}")
        k, _, v = line.partition(":")
        meta[k.strip()] = _parse_scalar(v)
    return meta, body
