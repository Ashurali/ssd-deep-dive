"""Link every acronym on every page to its glossary entry.

The `abbr` extension turns each acronym into <abbr title="expansion">, using
the definitions in includes/abbreviations.md. This hook adds a Markdown tree
step that wraps each <abbr> in a link to that acronym's entry in
reference/glossary.md.

- The acronym → entry map comes from scripts/build_glossary.py, the same
  code that writes the glossary, so the two cannot drift.
- The links are emitted as relative `.md#anchor` links, before MkDocs' own
  link processing. That means `mkdocs build --strict` validates every target,
  so a glossary that was not regenerated fails the build.

Acronyms are not linked when they sit inside a link already, inside a
heading (headings stay plain), or inside a <summary> (a link there would
steal the tap that opens the block).

assets/javascripts/acronyms.js adds two behaviours on top of these links:
on touch, the first tap shows the expansion and a second tap opens the
glossary; and on the glossary, a "Back" button returns to where the reader
was.
"""
from __future__ import annotations

import importlib.util
import posixpath
import xml.etree.ElementTree as etree
from pathlib import Path

from markdown import Extension, Markdown
from markdown.treeprocessors import Treeprocessor

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY = "reference/glossary.md"
NO_LINK_INSIDE = {"a", "h1", "h2", "h3", "h4", "h5", "h6", "summary"}

_state: dict = {"page": None, "targets": {}}


def _load_targets() -> dict[str, str]:
    """{acronym: glossary anchor id}, computed by scripts/build_glossary.py."""
    spec = importlib.util.spec_from_file_location(
        "build_glossary", ROOT / "scripts" / "build_glossary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.acronym_targets()


class _AcronymLinker(Treeprocessor):
    def run(self, root: etree.Element) -> None:
        page = _state["page"]
        if page is None or not _state["targets"]:
            return
        self.href = posixpath.relpath(GLOSSARY, posixpath.dirname(page) or ".")
        self._walk(root)

    def _walk(self, parent: etree.Element) -> None:
        for i, child in enumerate(list(parent)):
            tag = child.tag if isinstance(child.tag, str) else ""
            if tag == "abbr":
                target = _state["targets"].get(child.text or "")
                if target:
                    link = etree.Element(
                        "a", {"href": f"{self.href}#{target}", "class": "sdd-acr"})
                    link.tail, child.tail = child.tail, None
                    parent[i] = link
                    link.append(child)
            elif tag not in NO_LINK_INSIDE:
                self._walk(child)


class _AcronymLinkExtension(Extension):
    def extendMarkdown(self, md: Markdown) -> None:
        # After `abbr` (priority 7) has created the <abbr>s; before MkDocs'
        # relpath step (0) resolves the .md links and validates their anchors.
        md.treeprocessors.register(_AcronymLinker(md), "sdd_acronym_links", 6)


def on_config(config, **kwargs):
    _state["targets"] = _load_targets()
    config.markdown_extensions.append(_AcronymLinkExtension())
    return config


def on_page_markdown(markdown, page, **kwargs):
    _state["page"] = page.file.src_uri
    return markdown
