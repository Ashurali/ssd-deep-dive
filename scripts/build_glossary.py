#!/usr/bin/env python3
"""Build docs/reference/glossary.md from every page's Key-vocabulary table,
plus the site-wide acronym list (includes/abbreviations.md).

Vocabulary table formats. The header names decide each column's role, so old
and new tables can coexist while pages are being converted:
  - | Term | 中文 | Meaning |     textbook-v2 format (every page, eventually)
  - | 中文 | English |            legacy chapter format (translation pairs)
  - | Term | Meaning |            legacy supplement format (definitions)

Output: one entry per term, grouped under A–Z headings with a jump bar. Each
entry is an `###` heading with a stable anchor, followed by the 中文 term(s),
the meaning(s) and the source link(s). One entry per heading keeps Material's
search previews short; a single whole-glossary table used to preview as about
ten phone screens. Identical terms are merged and their sources accumulate;
genuinely different glosses are kept side by side.

Acronyms: every acronym in the site-wide list gets an entry. It joins the
entry that names it, when there is one ("solid-state drive (SSD)", a 中文 cell
reading "基地址寄存器 (BAR)", or a list such as "SLC / MLC / TLC"); otherwise
it becomes an entry of its own, with its expansion as the meaning.
hooks/acronym_links.py calls acronym_targets() to link each acronym on every
page to that entry, and `mkdocs build --strict` checks those links.

Links inside a cell are written relative to their own page, e.g.
`→ [§4.3.2](#432-write-amplification)`. This script re-points them so they
work from reference/glossary.md, and the strict build checks them.

Run it manually after editing vocabulary or the acronym list, and in CI before
`mkdocs build`.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "reference" / "glossary.md"
ABBR_FILE = ROOT / "includes" / "abbreviations.md"

SOURCE_DIRS = ["core", "supplements"]
VOCAB_HEADING_RE = re.compile(r"^##\s+(Key vocabulary.*?)\s*$")
CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")  # don't split on escaped \|
LINK_TARGET_RE = re.compile(r"\]\(([^)\s]+)\)")
ABBR_RE = re.compile(r"^\*\[(?P<abbr>[^\]]+)\]:\s*(?P<title>.+?)\s*$")
ACRONYM_PART_RE = re.compile(r"[A-Za-z0-9-]*[A-Z][A-Za-z0-9-]*")


def toc_slug(text: str) -> str:
    """Replicate python-markdown's default toc slugify (ASCII-only)."""
    text = unicodedata.normalize("NFKD", text).encode(
        "ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def plain(text: str) -> str:
    """Strip markdown emphasis/code markup."""
    return re.sub(r"[*`_]", "", text).strip()


def sort_key(term: str) -> str:
    """Alphabetize ignoring markdown markup and leading non-alphanumerics."""
    t = re.sub(r"^[^0-9A-Za-z一-鿿]+", "", plain(term))
    return t.casefold()


def group_of(key: str) -> tuple[str, str]:
    """(label, anchor) of the A–Z group a sort key belongs to."""
    c = key[:1]
    if c.isascii() and c.isalpha():
        return c.upper(), f"letter-{c}"
    if c.isdigit():
        return "0–9", "letter-digits"
    return "Other", "letter-other"


def parse_front_matter_title(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    m = re.search(r'^title:\s*"?([^"\n]+)"?\s*$', text[4:end], re.M)
    return m.group(1).strip() if m else None


def column_roles(header: list[str]) -> dict[str, int] | None:
    """Map 'term' / 'zh' / 'meaning' to column indexes, by header name."""
    roles: dict[str, int] = {}
    for i, name in enumerate(header):
        n = name.strip().strip("*").strip().casefold()
        if n.startswith("中文"):
            roles.setdefault("zh", i)
        elif n in ("term", "english"):
            roles.setdefault("term", i)
        elif n in ("meaning", "definition"):
            roles.setdefault("meaning", i)
    return roles if "term" in roles else None


def repoint_links(cell: str, dirname: str, stem: str) -> str:
    """Rewrite page-relative link targets so they resolve from reference/."""
    def fix(m: re.Match) -> str:
        target = m.group(1)
        if target.startswith(("http://", "https://", "mailto:", "../", "/")):
            return m.group(0)  # sibling dirs of reference/ resolve the same
        if target.startswith("#"):
            return f"](../{dirname}/{stem}.md{target})"
        return f"](../{dirname}/{target})"
    return LINK_TARGET_RE.sub(fix, cell)


def extract_vocab(path: Path, dirname: str
                  ) -> tuple[str, list[tuple[str, str, str]]] | None:
    """Return (section_anchor, rows) where rows are (term, zh, meaning)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    heading_idx = anchor = None
    for i, line in enumerate(lines):
        m = VOCAB_HEADING_RE.match(line)
        if m:
            heading_idx, anchor = i, toc_slug(m.group(1))
            break
    if heading_idx is None:
        return None

    stem = path.name.removesuffix(".md")
    rows: list[tuple[str, str, str]] = []
    roles: dict[str, int] | None = None
    for line in lines[heading_idx + 1:]:
        s = line.strip()
        if s.startswith("## ") or (s.startswith("# ") and rows):
            break  # next section
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in CELL_SPLIT_RE.split(s.strip("|"))]
        if len(cells) < 2:
            continue
        if roles is None:
            roles = column_roles(cells)
            if roles is None:
                print(f"  WARN: unrecognized vocabulary header in "
                      f"{path.name}: {cells}", file=sys.stderr)
                return None
            continue
        if set(cells[0]) <= {"-", ":", " "}:
            continue  # separator row

        def cell(role: str) -> str:
            i = roles.get(role)
            if i is None or i >= len(cells):
                return ""
            return repoint_links(cells[i], dirname, stem)

        term = cell("term")
        if term:
            rows.append((term, cell("zh"), cell("meaning")))
    return (anchor, rows) if rows else None


def read_abbreviations() -> dict[str, str]:
    """{acronym: expansion} from the site-wide acronym list."""
    abbrs: dict[str, str] = {}
    if ABBR_FILE.exists():
        for line in ABBR_FILE.read_text(encoding="utf-8").splitlines():
            m = ABBR_RE.match(line.strip())
            if m:
                abbrs[m["abbr"]] = m["title"]
    return abbrs


def collect_entries(quiet: bool = False) -> tuple[dict[str, dict], int]:
    """Merge every page's vocabulary rows into {sort key: entry}."""
    entries: dict[str, dict] = {}
    n_sources = 0
    for dirname in SOURCE_DIRS:
        for path in sorted((DOCS / dirname).glob("*.md")):
            result = extract_vocab(path, dirname)
            if result is None:
                if not quiet:
                    print(f"  WARN: no vocabulary table in {path.name}",
                          file=sys.stderr)
                continue
            anchor, rows = result
            title = parse_front_matter_title(
                path.read_text(encoding="utf-8")) or path.stem
            link = f"../{dirname}/{path.name.removesuffix('.md')}.md#{anchor}"
            source_md = f"[{title}]({link})"
            n_sources += 1

            for term, zh, meaning in rows:
                key = sort_key(term)
                e = entries.setdefault(
                    key, {"term": term, "zh": [], "meanings": [],
                          "sources": [], "acronyms": []})
                if zh and zh not in e["zh"]:
                    e["zh"].append(zh)
                if meaning and meaning not in e["meanings"]:
                    e["meanings"].append(meaning)
                if source_md not in e["sources"]:
                    e["sources"].append(source_md)
    return entries, n_sources


def owner_rank(acr: str, entry: dict) -> int | None:
    """How clearly an entry names an acronym (lower = clearer), or None."""
    term = plain(entry["term"])
    a = re.escape(acr)
    word = r"(?<![\w-])" + a + r"(?![\w-])"
    if re.fullmatch(a + "#?", term):
        return 0  # "UFS", "CLKREQ#"
    if (re.search(r"\(\s*" + a + r"\s*\)", term)
            or re.match(a + r"\s*[(,/]", term)
            or re.fullmatch(a + r"\s+[a-z]+", term)):
        return 1  # "solid-state drive (SSD)", "PHY / physical layer", "BCH code"
    if re.search(r"\([^)]*" + word + r"[^)]*\)", term):
        return 2  # "raw-flash FS (JFFS2/UBIFS)"
    if any(re.search(r"\(\s*" + a + r"\s*\)", zh) for zh in entry["zh"]):
        return 3  # 中文 cell "提交隊列 (SQ)"
    parts = [p.strip() for p in term.split("/")]
    if (len(parts) > 1 and acr in parts
            and all(ACRONYM_PART_RE.fullmatch(p) for p in parts)):
        return 4  # "SLC / MLC / TLC"
    return None


def attach_acronyms(entries: dict[str, dict],
                    abbrs: dict[str, str]) -> dict[str, str]:
    """Give every acronym an entry; return {acronym: entry sort key}."""
    targets: dict[str, str] = {}
    singular_first = sorted(abbrs, key=lambda a: (a.endswith("s"), a))
    for acr in singular_first:
        if acr.endswith("s") and acr[:-1] in targets:
            targets[acr] = targets[acr[:-1]]  # "SSDs" → the SSD entry
            continue
        ranked = [(rank, len(plain(e["term"])), key)
                  for key, e in entries.items()
                  if (rank := owner_rank(acr, e)) is not None]
        if ranked:
            key = min(ranked)[2]
        else:
            key = sort_key(acr)
            if key not in entries:
                entries[key] = {"term": acr, "zh": [], "meanings": [],
                                "sources": [], "acronyms": []}
        entries[key]["acronyms"].append((acr, abbrs[acr]))
        targets[acr] = key
    return targets


def assign_ids(entries: dict[str, dict]) -> dict[str, str]:
    """{sort key: anchor id}, unique and stable for a given set of terms."""
    ids: dict[str, str] = {}
    used: set[str] = set()
    for key in sorted(entries, key=str):
        base = "term-" + (toc_slug(plain(entries[key]["term"])) or "x")
        tid, n = base, 2
        while tid in used:
            tid, n = f"{base}-{n}", n + 1
        used.add(tid)
        ids[key] = tid
    return ids


def build(quiet: bool = False) -> tuple[list[str], dict[str, str], int]:
    """Return (glossary lines, {acronym: anchor id}, number of entries)."""
    entries, n_sources = collect_entries(quiet)
    acr_keys = attach_acronyms(entries, read_abbreviations())
    ids = assign_ids(entries)

    keys = sorted(entries, key=str)
    groups: dict[tuple[str, str], list[str]] = {}
    for key in keys:
        groups.setdefault(group_of(key), []).append(key)

    jump = " · ".join(f"[{label}](#{gid})" for label, gid in groups)
    lines = [
        "---",
        'title: "Glossary"',
        "hide:",
        "  - toc",
        "---",
        "",
        "<!-- AUTO-GENERATED by scripts/build_glossary.py — do not edit by "
        "hand. Re-run the script after editing a page's vocabulary or "
        "includes/abbreviations.md. -->",
        "",
        "# Master glossary",
        "",
        f"Every term from the Key-vocabulary tables of all {n_sources} "
        "chapters and supplements, plus every acronym the site uses: "
        f"{len(entries)} entries, merged and alphabetized. Each entry gives "
        "the 中文 term, a short meaning where one exists, and a link to the "
        "page it comes from. Tap any acronym on any page to jump here.",
        "",
        f"**Jump to:** {jump}",
        "",
    ]

    for (label, gid), group_keys in groups.items():
        lines += [f"## {label} {{ #{gid} }}", ""]
        for key in group_keys:
            e = entries[key]
            head = []
            if e["zh"]:
                head.append("**" + "；".join(e["zh"]) + "**")
            if e["meanings"]:
                head.append("; ".join(e["meanings"]))
            elif e["acronyms"]:
                head.append("; ".join(
                    exp if plain(e["term"]) == acr else f"{acr} = {exp}"
                    for acr, exp in e["acronyms"]))
            source = (" · ".join(e["sources"]) if e["sources"]
                      else "the site-wide acronym list")
            lines += [f"### {e['term']} {{ #{ids[key]} .sdd-term }}", ""]
            if head:
                lines.append(" — ".join(head) + "  ")
            lines += [f"<small>From: {source}</small>", ""]

    targets = {acr: ids[key] for acr, key in acr_keys.items()}
    return lines, targets, len(entries)


def acronym_targets() -> dict[str, str]:
    """{acronym: glossary anchor id}, for hooks/acronym_links.py."""
    return build(quiet=True)[1]


def main() -> int:
    lines, targets, n_entries = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {n_entries} entries "
          f"({len(targets)} acronyms linked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
