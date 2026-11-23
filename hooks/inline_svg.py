"""Inline the site's SVG figures so they follow the light/dark theme.

Authoring (README → "Figures"):

    ![Short alt text](../assets/figures/ch3/vt-bells.svg){ .sdd-fig }
    /// figure-caption
    What the figure shows, in a sentence or two.
    ///

Markdown renders the image as an <img>, and an <img> can't see the page's
CSS. This hook replaces every <img class="sdd-fig"> that points at a local
.svg with the SVG's own markup. The drawing then takes its colours from the
theme tokens in assets/extra.css (classes such as .f-ink and .f-cyan) and
switches with the light/dark toggle.

On the way in:
  - width/height are dropped (CSS sizes the figure) and a viewBox is required;
  - role="img" and aria-labelledby point at the SVG's <title> and <desc>;
  - every id inside the SVG gets a per-figure prefix, so two figures on one
    page can't collide;
  - the SVG is marked data-search-exclude, so diagram labels stay out of
    search results (the caption stays searchable);
  - .sdd-fig--wide figures get a frame that scrolls sideways on phones.

A missing file, or an SVG without a viewBox, fails the build.
"""
from __future__ import annotations

import posixpath
import re
from pathlib import Path

from mkdocs.exceptions import PluginError

IMG_RE = re.compile(r'<img\b[^>]*\bclass="(?:[^"]*\s)?sdd-fig(?:\s[^"]*)?"[^>]*>')
ATTR_RE = re.compile(r'([\w:-]+)="([^"]*)"')
ROOT_RE = re.compile(r"<svg\b[^>]*>", re.S)
DROP_ROOT_ATTRS = {"width", "height", "class", "role", "aria-labelledby",
                   "aria-hidden", "aria-label"}


def _inline(svg: str, rel: str, prefix: str, classes: str, alt: str) -> str:
    svg = re.sub(r"<\?xml.*?\?>|<!DOCTYPE[^>]*>|<!--.*?-->", "", svg,
                 flags=re.S).strip()

    for old in dict.fromkeys(re.findall(r'\bid="([^"]+)"', svg)):
        new = f"{prefix}-{old}"
        svg = re.sub(rf'\bid="{re.escape(old)}"', f'id="{new}"', svg)
        svg = svg.replace(f"url(#{old})", f"url(#{new})")
        svg = svg.replace(f'href="#{old}"', f'href="#{new}"')

    labelled_by = []
    for tag in ("title", "desc"):
        svg, n = re.subn(rf"<{tag}\b[^>]*>", f'<{tag} id="{prefix}-{tag}">',
                         svg, count=1)
        if n:
            labelled_by.append(f"{prefix}-{tag}")

    root = ROOT_RE.search(svg)
    if not root:
        raise PluginError(f"{rel}: no <svg> element")
    attrs = dict(ATTR_RE.findall(root.group(0)))
    if "viewBox" not in attrs:
        raise PluginError(f"{rel}: the <svg> needs a viewBox")
    kept = " ".join(f'{k}="{v}"' for k, v in attrs.items()
                    if k not in DROP_ROOT_ATTRS)
    label = (f'aria-labelledby="{" ".join(labelled_by)}"' if labelled_by
             else f'aria-label="{alt}"')
    new_root = (f'<svg {kept} class="{classes}" role="img" {label} '
                'data-search-exclude>')
    svg = svg[:root.start()] + new_root + svg[root.end():]

    if "sdd-fig--wide" in classes.split():
        svg = f'<span class="sdd-fig-scroll">{svg}</span>'
    return svg


def on_page_content(html, page, config, **kwargs):
    if "sdd-fig" not in html:
        return html
    docs = Path(config.docs_dir)
    url = page.url
    base = url if url.endswith("/") or not url else posixpath.dirname(url) + "/"
    count = 0

    def replace(m: re.Match) -> str:
        nonlocal count
        attrs = dict(ATTR_RE.findall(m.group(0)))
        src = attrs.get("src", "")
        if not src.endswith(".svg") or "//" in src:
            return m.group(0)
        rel = posixpath.normpath(posixpath.join(base, src))
        path = docs / rel
        if not path.is_file():
            raise PluginError(f"{page.file.src_uri}: figure not found: {rel}")
        count += 1
        return _inline(path.read_text(encoding="utf-8"), rel,
                       f"fig{count}-{path.stem}", attrs.get("class", "sdd-fig"),
                       attrs.get("alt", ""))

    return IMG_RE.sub(replace, html)
