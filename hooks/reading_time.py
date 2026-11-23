"""Put "≈ N min read" under the title of every chapter and supplement.

Counts the words a reader actually reads: prose, lists, admonitions and
captions. It skips code blocks, tables (the vocabulary tables are scanned,
not read), raw HTML such as animation embeds, and link targets. It assumes
200 words a minute, a typical pace for technical text. The line is excluded
from search.
"""
from __future__ import annotations

import re

PAGES = ("core/", "supplements/")
WPM = 200
FENCE_RE = re.compile(r"^(\s*)(```|~~~).*?^\1\2", re.S | re.M)
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’.-][A-Za-z0-9]+)*|[一-鿿]")


def _minutes(markdown: str) -> int:
    text = FENCE_RE.sub("", markdown)
    lines = [ln for ln in text.splitlines()
             if not ln.lstrip().startswith(("|", "<"))]
    text = "\n".join(lines)
    text = re.sub(r"\]\([^)]*\)", "]", text)      # link targets
    text = re.sub(r"<[^>]+>", " ", text)          # inline HTML
    words = len(WORD_RE.findall(text))
    return max(1, round(words / WPM))


def on_page_markdown(markdown, page, **kwargs):
    if not page.file.src_uri.startswith(PAGES):
        return markdown
    line = (f'<p class="sdd-readtime" data-search-exclude>'
            f'≈ {_minutes(markdown)} min read</p>')
    # under the first H1 (outside code fences: no page starts with one)
    return re.sub(r"^(# .+)$", lambda m: f"{m.group(1)}\n\n{line}\n",
                  markdown, count=1, flags=re.M)
