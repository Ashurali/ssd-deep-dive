#!/usr/bin/env python3
"""Build docs/reference/visual-index.md: every figure and animation on the
site, by page and by concept.

Figures are the original SVG drawings written into chapter and supplement
pages as `![alt](../assets/figures/<page>/<name>.svg){ .sdd-fig }` followed by
a `/// figure-caption` block. Animations are the iframes that embed
`animations/files/<name>.html`; their titles and one-line summaries come from
the wrapper pages in docs/animations/.

By page: one `###` entry per picture, under its page, so each search hit
previews one picture. The entry names the section the picture sits in and
links to it. By concept: one alphabetical table of the same pictures, keyed by
what each one shows (its caption's first clause, or the animation's title).

Pages are listed in nav order (mkdocs.yml). Links inside captions are written
relative to their own page; they are re-pointed to work from reference/, and
`mkdocs build --strict` checks every link and anchor. Run it after adding or
re-captioning a figure, and in CI before `mkdocs build`.
"""
from __future__ import annotations

import posixpath
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "reference" / "visual-index.md"
OUT_DIR = "reference"

FIG_RE = re.compile(r"^\s*!\[(?P<alt>.*?)\]\((?P<src>[^)\s]*assets/figures/[^)\s]+\.svg)\)")
ANIM_RE = re.compile(r'<iframe src="[./]*animations/files/(?P<name>[\w\-]+\.html)"')
HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")
ATTR_ID_RE = re.compile(r"\{[^}]*#(?P<id>[\w\-]+)[^}]*\}\s*$")
LINK_RE = re.compile(r"(?<!!)\[(?P<text>[^\]]*)\]\((?P<target>[^)\s]+)\)")


def toc_slug(text: str) -> str:
    """Replicate python-markdown's default toc slugify (ASCII-only)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def plain(text: str) -> str:
    """Heading text as the toc extension sees it (markup stripped)."""
    text = re.sub(r"\{[^}]*\}\s*$", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\*\*|__|(?<!\w)[*_]|[*_](?!\w)", "", text)
    return text.strip()


def display(text: str) -> str:
    """Heading text for a link label: markup and star signposts removed, and
    a § before a section number ('3.4.2 Read Retry' -> '§3.4.2 Read Retry')."""
    text = re.sub(r"\s*⭐+\s*", " ", plain(text)).strip()
    return re.sub(r"^(?=(?:\d+|[A-I])\.\d)", "§", text)


def nav_pages() -> list[str]:
    """Chapter and supplement pages in nav order, as docs-relative paths."""
    seen: list[str] = []
    for m in re.finditer(r"((?:core|supplements)/[\w\-]+\.md)",
                         (ROOT / "mkdocs.yml").read_text(encoding="utf-8")):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def front_matter(text: str) -> tuple[str, str]:
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return (m.group(1), text[m.end():]) if m else ("", text)


def title_of(meta: str, body: str) -> str:
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', meta, re.M)
    if m:
        return m.group(1)
    m = re.search(r"^#\s+(.+)$", body, re.M)
    return plain(m.group(1)) if m else "?"


def repoint(text: str, page: str) -> str:
    """Rewrite links relative to `page` (docs-relative) so they work from OUT_DIR."""
    base = posixpath.dirname(page)

    def fix(m: re.Match) -> str:
        target = m.group("target")
        if re.match(r"[a-z]+:|/", target):
            return m.group(0)
        if target.startswith("#"):
            new = posixpath.relpath(page, OUT_DIR) + target
        else:
            path, _, frag = target.partition("#")
            new = posixpath.relpath(posixpath.normpath(posixpath.join(base, path)), OUT_DIR)
            new += ("#" + frag) if frag else ""
        return f"[{m.group('text')}]({new})"

    return LINK_RE.sub(fix, text)


def label_of(caption: str) -> str:
    """What a figure shows: its caption's first sentence, cut at a clause
    break when long, without the closing full stop."""
    first = re.split(r"(?<=[.!?])\s", caption.strip(), maxsplit=1)[0]
    first = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", first)
    if len(first) > 64:                          # main clause only
        first = re.split(r"[:;]\s|\s—\s", first, maxsplit=1)[0]
    if len(first) > 64:                          # drop asides
        first = re.sub(r"\s*\([^)]*\)", "", first)
    if len(first) > 64:                          # then at the first comma
        first = first.split(", ", 1)[0]
    return first.rstrip(" .")


def short(title: str) -> str:
    """'Chapter 3 — NAND flash: …' -> 'Chapter 3', for the jump bar."""
    m = re.match(r"(Chapter \d+|Supplement [A-Z])", title)
    return m.group(1) if m else title.split(" — ")[0].split(":")[0]


def sort_key(label: str) -> str:
    return re.sub(r"^(a|an|the|one|two|three|four|five)\s+", "", label.lower())


def animations() -> dict[str, dict]:
    """{html file name: {title, summary, wrapper}} from the wrapper pages."""
    out: dict[str, dict] = {}
    for md in sorted((DOCS / "animations").glob("*.md")):
        if md.name == "index.md":
            continue
        meta, body = front_matter(md.read_text(encoding="utf-8"))
        m = re.search(r'<iframe src="\.\./files/([\w\-]+\.html)"', body)
        if not m:
            continue
        para = re.search(r"^#\s+.+?\n\n(.+?)\n\n", body, re.S | re.M)
        out[m.group(1)] = {
            "title": title_of(meta, body),
            "summary": para.group(1).strip() if para else "",
            "wrapper": f"animations/{md.name}",
            "slug": md.stem,
        }
    return out


def scan(page: str, anims: dict[str, dict]) -> tuple[str, list[dict]]:
    meta, body = front_matter((DOCS / page).read_text(encoding="utf-8"))
    title = title_of(meta, body)
    lines = body.splitlines()
    used: dict[str, int] = {}
    heading = None        # (label, anchor) of the section a picture sits in
    fence = None
    items: list[dict] = []
    by_anim: dict[str, dict] = {}
    for i, line in enumerate(lines):
        f = re.match(r"^\s*(```|~~~)", line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
            continue
        if fence:
            continue
        h = HEADING_RE.match(line)
        if h:
            text = h.group("text")
            explicit = ATTR_ID_RE.search(text)
            slug = explicit.group("id") if explicit else toc_slug(plain(text))
            if not explicit and slug in used:       # toc makes repeats unique
                used[slug] += 1
                slug = f"{slug}_{used[slug]}"
            else:
                used.setdefault(slug, 0)
            heading = (display(text), slug)
            continue
        m = FIG_RE.match(line)
        if m:
            cap: list[str] = []
            if i + 1 < len(lines) and lines[i + 1].strip() == "/// figure-caption":
                for nxt in lines[i + 2:]:
                    if nxt.strip() == "///":
                        break
                    cap.append(nxt.strip())
            caption = " ".join(cap).strip()
            svg = posixpath.normpath(posixpath.join(posixpath.dirname(page), m.group("src")))
            stem = Path(svg).stem
            label = label_of(caption or m.group("alt"))
            body = repoint(caption, page) if caption else m.group("alt")
            if body.startswith(label + ". "):       # the title already says it
                body = body[len(label) + 2:]
            items.append({
                "kind": "figure",
                "id": f"fig-{Path(page).stem.split('-')[0]}-{stem}",
                "label": label,
                "caption": body,
                "sections": [heading],
            })
            continue
        m = ANIM_RE.search(line)
        if m and m.group("name") in anims:
            a = anims[m.group("name")]
            if a["slug"] in by_anim:                 # embedded twice on one page
                if heading not in by_anim[a["slug"]]["sections"]:
                    by_anim[a["slug"]]["sections"].append(heading)
                continue
            item = {
                "kind": "animation",
                "id": f"anim-{Path(page).stem.split('-')[0]}-{a['slug']}",
                "label": a["title"],
                "caption": repoint(a["summary"], a["wrapper"]),
                "sections": [heading],
                "wrapper": a["wrapper"],
            }
            by_anim[a["slug"]] = item
            items.append(item)
    return title, items


def main() -> int:
    anims = animations()
    pages = [(p, *scan(p, anims)) for p in nav_pages()]
    pages = [(p, t, items) for p, t, items in pages if items]
    seen: dict[str, int] = {}                        # a figure used twice keeps unique ids
    for _, _, items in pages:
        for it in items:
            n = seen.get(it["id"], 0)
            seen[it["id"]] = n + 1
            if n:
                it["id"] += f"-{n + 1}"
    figs = sum(1 for _, _, items in pages for it in items if it["kind"] == "figure")
    anim_used = {it["label"] for _, _, items in pages for it in items if it["kind"] == "animation"}

    out = [
        "---",
        'title: "Visual index"',
        "hide:",
        "  - toc",
        "---",
        "",
        "<!-- AUTO-GENERATED by scripts/build_visual_index.py — do not edit by hand. "
        "Re-run the script after adding or re-captioning a figure or an animation embed. -->",
        "",
        "# Visual index",
        "",
        f"Every picture in the textbook, page by page: {figs} original figures and "
        f"{len(anim_used)} interactive animations across {len(pages)} chapters and "
        "supplements. Each entry names the section it illustrates and links to it; the "
        "[concept list](#by-concept) at the end gives the same pictures alphabetically. "
        "The [animation gallery](../animations/index.md) has the animations on their own pages.",
        "",
        "**Jump to:** " + " · ".join(
            f"[{short(t)}](#page-{Path(p).stem})" for p, t, _ in pages)
        + " · [By concept](#by-concept)",
        "",
        "## By page",
        "",
    ]
    for page, title, items in pages:
        rel = posixpath.relpath(page, OUT_DIR)
        out += [f"### [{title}]({rel}) {{ #page-{Path(page).stem} }}", ""]
        for it in items:
            where = " and ".join(
                f"[{s[0]}]({rel}#{s[1]})" if s else f"[{title}]({rel})" for s in it["sections"])
            out += [f"#### {it['label']} {{ #{it['id']} }}", ""]
            if it["kind"] == "figure":
                out += [f"*Figure* · in {where}", "", it["caption"], ""]
            else:
                link = posixpath.relpath(it["wrapper"], OUT_DIR)
                out += [f"*Animation* · in {where} · [open the animation page]({link})",
                        "", it["caption"], ""]

    out += ["## By concept { #by-concept data-search-exclude }", "",
            "| What it shows | Kind | Page |", "|---|---|---|"]
    rows = []
    for page, title, items in pages:
        rel = posixpath.relpath(page, OUT_DIR)
        for it in items:
            rows.append((sort_key(it["label"]), it["label"].replace("|", "\\|"),
                         it["id"], "Figure" if it["kind"] == "figure" else "Animation",
                         title, rel))
    for _, label, iid, kind, title, rel in sorted(rows):
        out.append(f"| [{label}](#{iid}) | {kind} | [{title}]({rel}) |")
    out.append("")

    OUT.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}: {figs} figures, "
          f"{len(anim_used)} animations, {len(pages)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
