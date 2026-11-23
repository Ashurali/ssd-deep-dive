#!/usr/bin/env python3
"""Check the textbook's content rules (README → "Authoring rules").

Usage: python scripts/check_content.py [--strict]

Always enforced (fail with --strict):
  - includes/abbreviations.md holds only `*[X]: expansion` lines, no duplicates.
  - Every SVG in docs/assets/figures/ has a viewBox, a <title> and a <desc>,
    no <style> or <script>, an explicit font size on all text, and labels big
    enough to read on a phone: at least 11 px when drawn 343 px wide (the
    content width on a 375 px phone), or 560 px wide for .sdd-fig--wide.
  - Every figure a page references exists.

Enforced only on pages marked `textbook: v2` in their front matter, which a
page gets when its textbook-v2 pass is done (reported for every page):
  - Key vocabulary is a | Term | 中文 | Meaning | table with no empty cell.
  - Every Check-yourself question has an answer block (??? success "Answer").

Reported, never enforced:
  - Acronyms whose first use on a page isn't spelled out, either as
    "Flash Translation Layer (FTL)" or as "FTL (Flash Translation Layer)".
"""
from __future__ import annotations

import posixpath
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FIGURES = DOCS / "assets" / "figures"
ABBR_FILE = ROOT / "includes" / "abbreviations.md"
PAGE_DIRS = ["core", "supplements"]

PHONE_PX, WIDE_PX, MIN_PX = 343, 560, 11
SVG_NS = "{http://www.w3.org/2000/svg}"
ABBR_RE = re.compile(r"^\*\[(?P<abbr>[^\]]+)\]:\s*(?P<title>\S.*)$")
FIG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+\.svg)\)(\{[^}]*\})?")
FENCE_RE = re.compile(r"^(\s*)(```|~~~).*?^\1\2", re.S | re.M)


def front_matter(text: str) -> tuple[str, str]:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[4:end], text[end + 5:]
    return "", text


def section(body: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}.*?$(.*?)(?=^## |\Z)",
                  body, re.S | re.M)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- global
def check_abbreviations(errors: list[str]) -> dict[str, str]:
    """{acronym: expansion}; malformed or duplicate lines become errors."""
    seen: dict[str, str] = {}
    for n, line in enumerate(ABBR_FILE.read_text(encoding="utf-8")
                             .splitlines(), 1):
        if not line.strip():
            continue
        m = ABBR_RE.match(line)
        if not m:
            errors.append(f"includes/abbreviations.md:{n}: not a definition "
                          "line (it would render on every page)")
        elif m["abbr"] in seen:
            errors.append(f"includes/abbreviations.md:{n}: duplicate "
                          f"{m['abbr']}")
        else:
            seen[m["abbr"]] = m["title"]
    return seen


def figure_uses() -> dict[Path, bool]:
    """{svg path: used as wide?} from every page's figure references."""
    uses: dict[Path, bool] = {}
    for md in DOCS.rglob("*.md"):
        rel_dir = posixpath.dirname(md.relative_to(DOCS).as_posix())
        for src, attrs in FIG_RE.findall(md.read_text(encoding="utf-8")):
            path = DOCS / posixpath.normpath(posixpath.join(rel_dir, src))
            uses[path] = uses.get(path, False) or "sdd-fig--wide" in attrs
    return uses


def check_svg(path: Path, wide: bool, errors: list[str]) -> None:
    rel = path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    if re.search(r"<(style|script)\b", text):
        errors.append(f"{rel}: no <style> or <script> (inline SVG styles "
                      "leak site-wide); colour with the .f-* classes")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        errors.append(f"{rel}: not well-formed XML ({e})")
        return
    box = root.get("viewBox", "").split()
    if len(box) != 4:
        errors.append(f"{rel}: the <svg> needs a viewBox")
        return
    for tag in ("title", "desc"):
        if root.find(SVG_NS + tag) is None:
            errors.append(f"{rel}: needs a <{tag}> (it is the figure's "
                          "accessible name / description)")
    floor = MIN_PX * float(box[2]) / (WIDE_PX if wide else PHONE_PX)

    def walk(el: ET.Element, size: float | None) -> None:
        own = el.get("font-size")
        if own:
            size = float(re.sub(r"px$", "", own))
        if el.tag in (SVG_NS + "text", SVG_NS + "tspan") and (el.text or "").strip():
            if size is None:
                errors.append(f"{rel}: text {el.text.strip()!r} has no "
                              "font-size (set one on the <svg> or the text)")
            elif size < floor - 0.05:
                errors.append(
                    f"{rel}: text {el.text.strip()!r} is {size:g} units; "
                    f"needs ≥ {floor:.1f} to stay ≥ {MIN_PX} px on a phone")
        for child in el:
            walk(child, size)

    walk(root, None)


# -------------------------------------------------------------- per page
def check_vocab(body: str) -> tuple[int, int, int, bool]:
    """(rows, rows with meaning, rows with 中文, 3-column header?)"""
    rows = [ln for ln in section(body, "Key vocabulary").splitlines()
            if ln.strip().startswith("|")]
    if not rows:
        return 0, 0, 0, False
    header = [c.strip().casefold() for c in rows[0].strip("|").split("|")]
    three = header[:3] == ["term", "中文", "meaning"]
    data = [r for r in rows[2:]]
    full = lambda c: c.strip() not in ("", "—", "-")  # noqa: E731
    cells = [[c for c in re.split(r"(?<!\\)\|", r.strip().strip("|"))]
             for r in data]
    if three:
        meaning = sum(1 for c in cells if len(c) > 2 and full(c[2]))
        zh = sum(1 for c in cells if len(c) > 1 and full(c[1]))
    else:
        meaning = sum(1 for c in cells if header[:2] == ["term", "meaning"]
                      and len(c) > 1 and full(c[1]))
        zh = sum(1 for c in cells if header[:1] == ["中文"] and full(c[0]))
    return len(data), meaning, zh, three


def check_answers(body: str) -> tuple[int, int]:
    block = section(body, "Check yourself")
    items = re.split(r"^(?=\d+\. )", block, flags=re.M)[1:]
    answered = sum(1 for it in items
                   if re.search(r'^\s{4,}\?\?\?\+? success "Answer"', it, re.M))
    return len(items), answered


def _norm(s: str) -> str:
    return re.sub(r"[\s\-–—/]+", " ", s.casefold())


def unexpanded_acronyms(body: str, abbrs: dict[str, str]) -> list[str]:
    """Acronyms whose first use in the prose isn't spelled out.

    Headings and the "In this chapter" preview are skipped (the prose that
    follows explains). An acronym counts as spelled out when it sits in
    parentheses after its expansion, is followed by a parenthesised
    expansion, or has its expansion within a sentence's reach.
    """
    text = FENCE_RE.sub("", body)
    text = re.sub(r"^!!! abstract[^\n]*\n(?:[ \t][^\n]*\n|\n)*", "", text,
                  flags=re.M)
    text = re.sub(r"^#{1,6} .*$", "", text, flags=re.M)
    text = re.sub(r"^\s*\|.*$", "", text, flags=re.M)  # tables
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # images (alt text)
    # Only real tags: a bare "<" in prose ("<10 mW") must not swallow text
    # up to the next ">" on some later line.
    text = re.sub(r"</?[A-Za-z][^<>\n]*>|\]\([^)]*\)|[*`]", " ", text)
    missing = []
    for acr, title in abbrs.items():
        if acr.endswith("s") and acr[:-1] in abbrs:
            continue
        m = re.search(r"(?<![\w-])" + re.escape(acr) + r"(?![\w-])", text)
        if not m:
            continue
        before = text[max(0, m.start() - 1):m.start()]
        after = text[m.end():m.end() + 3]
        if before == "(" or re.match(r" \([A-Za-z]", after):
            continue
        expansion = _norm(title.split(" (")[0])
        window = _norm(text[max(0, m.start() - 160):m.end() + 160])
        if len(expansion) > 3 and expansion in window:
            continue
        missing.append(acr)
    return missing


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    errors: list[str] = []
    abbrs = check_abbreviations(errors)

    uses = figure_uses()
    for path in uses:
        if not path.is_file():
            errors.append(f"missing figure: {path.relative_to(ROOT).as_posix()}")
    for svg in sorted(FIGURES.rglob("*.svg")) if FIGURES.is_dir() else []:
        check_svg(svg, uses.get(svg, False), errors)

    print(f"{'page':34} {'v2':3} {'answers':>9} {'meanings':>9} "
          f"{'中文':>8}  unexpanded acronyms")
    for d in PAGE_DIRS:
        for md in sorted((DOCS / d).glob("*.md")):
            meta, body = front_matter(md.read_text(encoding="utf-8"))
            v2 = bool(re.search(r"^textbook:\s*v2\s*$", meta, re.M))
            rows, meaning, zh, three = check_vocab(body)
            questions, answered = check_answers(body)
            missing = unexpanded_acronyms(body, abbrs)
            name = f"{d}/{md.stem}"
            print(f"{name:34} {'yes' if v2 else '-':3} "
                  f"{answered:>4}/{questions:<4} {meaning:>4}/{rows:<4} "
                  f"{zh:>3}/{rows:<4}  {len(missing)}"
                  + (f" ({', '.join(missing[:8])}{'…' if len(missing) > 8 else ''})"
                     if missing else ""))
            if v2:
                if not three:
                    errors.append(f"{name}: vocabulary must be a "
                                  "| Term | 中文 | Meaning | table")
                if meaning < rows or zh < rows:
                    errors.append(f"{name}: {rows - meaning} vocabulary rows "
                                  f"lack a meaning, {rows - zh} lack 中文")
                if answered < questions:
                    errors.append(f"{name}: {questions - answered} of "
                                  f"{questions} questions have no answer")

    print()
    if errors:
        print(f"{len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("No problems.")
    return 1 if (strict and errors) else 0


if __name__ == "__main__":
    sys.exit(main())
