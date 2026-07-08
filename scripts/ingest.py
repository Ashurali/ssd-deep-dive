#!/usr/bin/env python3
"""Ingest raw study material from incoming/ into docs/.

Re-runnable pipeline (SITE_SPECIFICATION.md §6.1, §8):

- Markdown guides: copy to their destination under docs/, prepend YAML front
  matter (title, tags, source_anchor), and apply the *only* permitted
  mechanical fix — demote any H1 after the first to H2 (fence-aware).
  Prose is never rewritten. Re-ingesting overwrites the destination.
- Animations: copy each incoming/animations/*.html verbatim to
  docs/animations/files/ and generate a wrapper page if one doesn't already
  exist. Existing wrappers are left untouched (hand edits survive).

Usage: python scripts/ingest.py
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCOMING = ROOT / "incoming"
DOCS = ROOT / "docs"

# ---------------------------------------------------------------------------
# Document registry: incoming filename -> (destination, title, tags, anchor)
# Tag taxonomy per SITE_SPECIFICATION.md §6.2 (controlled vocabulary).
# ---------------------------------------------------------------------------
DOCUMENTS = {
    "SSD_Book_Ch1_Study_Guide.md": (
        "core/ch1-overview.md",
        "Ch 1 — SSD Overview",
        ["ssd-basics", "endurance", "reliability", "form-factors"],
        "CH1 file, pp. 1–61",
    ),
    "SSD_Book_Ch2_Study_Guide.md": (
        "core/ch2-controllers-afa.md",
        "Ch 2 — Controllers & AFA",
        ["controllers", "all-flash-array", "queues", "ecc"],
        "CH2 file",
    ),
    "SSD_Book_Ch3_Study_Guide.md": (
        "core/ch3-nand-flash.md",
        "Ch 3 — NAND Flash",
        ["flash-physics", "3d-nand", "charge-trap", "threshold-voltage",
         "reliability", "read-disturb", "data-retention", "endurance",
         "ecc", "bics8"],
        "CH3 file",
    ),
    "SSD_Book_Ch4_Study_Guide.md": (
        "core/ch4-ftl.md",
        "Ch 4 — FTL",
        ["ftl", "mapping", "garbage-collection", "write-amplification",
         "over-provisioning", "trim", "wear-leveling", "power-loss-recovery",
         "bad-blocks", "slc-cache", "zns", "fdp"],
        "CH4 file, pp. 1–72",
    ),
    "SSD_Book_Ch5_Study_Guide.md": (
        "core/ch5-pcie.md",
        "Ch 5 — PCIe",
        ["pcie", "tlp", "link-layer"],
        "CH5 file, pp. 1–74",
    ),
    "SSD_Book_Ch6_Study_Guide.md": (
        "core/ch6-nvme.md",
        "Ch 6 — NVMe",
        ["nvme", "queues", "prp-sgl", "namespaces", "nvme-of", "zns"],
        "CH6 file, pp. 1–68",
    ),
    "SSD_Book_Ch7_Study_Guide.md": (
        "core/ch7-testing.md",
        "Ch 7 — SSD Testing",
        ["testing", "fio", "jedec", "snia", "power-loss-recovery"],
        "CH7 file, pp. 1–54",
    ),
    "SSD_Book_Supplement_A_ECC_Coding_Theory.md": (
        "supplements/a-ecc-coding-theory.md",
        "Supp A — ECC Coding Theory",
        ["ecc", "bch", "ldpc", "soft-decision", "patents"],
        "2nd-edition Ch 7 topics, reconstructed",
    ),
    "SSD_Book_Supplement_B_UFS.md": (
        "supplements/b-ufs.md",
        "Supp B — UFS",
        ["ufs", "writebooster", "hpb", "queues", "zns"],
        "supplement (no book chapter)",
    ),
    "SSD_Book_Supplement_C_Flash_File_Systems.md": (
        "supplements/c-flash-file-systems.md",
        "Supp C — Flash File Systems",
        ["filesystems", "f2fs", "ext4", "zns", "garbage-collection"],
        "supplement (no book chapter)",
    ),
    "SSD_Book_Supplement_D_Power_Management.md": (
        "supplements/d-power-management.md",
        "Supp D — Power Management",
        ["power-management", "aspm", "apst", "pcie", "nvme"],
        "supplement (no book chapter)",
    ),
    "SSD_Book_Supplement_E_Aerospace_Storage.md": (
        "supplements/e-aerospace-storage.md",
        "Supp E — Aerospace Storage",
        ["aerospace", "radiation", "reliability", "ecc"],
        "supplement (no book chapter)",
    ),
    "SSD_Book_Figure_Atlas_Animation_Roadmap.md": (
        "atlas/figure-atlas-animation-roadmap.md",
        "Figure Atlas & Animation Roadmap",
        ["animations", "flash-physics", "ftl", "pcie", "nvme", "ecc",
         "testing"],
        "catalog of all 359 book figures",
    ),
}

# ---------------------------------------------------------------------------
# Animation registry: known metadata keyed by incoming filename (stem).
# Unknown animations get a generic stub wrapper to be hand-finished.
# ---------------------------------------------------------------------------
ANIMATIONS = {
    "nand-flash-animation": {
        "wrapper": "nand-flash-animation.md",
        "title": "Why SSDs need an FTL — NAND flash, animated",
        "tags": ["animations", "flash-physics", "ftl", "garbage-collection",
                 "write-amplification"],
        "description": (
            "A guided walk through NAND's physical rules — pages, blocks, "
            "program vs erase asymmetry — and how they give rise to "
            "out-of-place writes, garbage collection, and write "
            "amplification. Step through the stages with the on-screen "
            "controls; each stage animates one consequence of the rule "
            "before it."
        ),
        "anchor": "Realizes the Ch 3 page/block model and Ch 4 §4.3 GC "
                  "walk-through (CH4 pp. 16–26, Figs 4-14 to 4-22).",
    },
    "ecc_bit_correction": {
        "wrapper": "ecc-bit-correction.md",
        "title": "How ECC finds and fixes a bit — Hamming visualizer",
        "tags": ["animations", "ecc"],
        "description": (
            "An interactive Hamming(12,8) visualizer: flip any data bit and "
            "watch the parity checks light up to *announce the flipped "
            "bit's own location*, then correct it. The clearest way to "
            "internalize why a syndrome pinpoints a single-bit error."
        ),
        "anchor": "Companion to Supplement A §7.3 (parity, syndrome, "
                  "Hamming codes).",
    },
    "ecc_bch_ldpc": {
        "wrapper": "ecc-bch-ldpc.md",
        "title": "Stronger ECC in action — BCH & LDPC",
        "tags": ["animations", "ecc", "bch", "ldpc", "soft-decision"],
        "description": (
            "A tabbed visualizer for the two production SSD codes: watch a "
            "BCH(15,7) decoder locate multiple errors algebraically, then "
            "switch tabs to see an LDPC Tanner graph converge by iterative "
            "message passing. Toggle errors on and off to see each "
            "decoder's limits."
        ),
        "anchor": "Companion to Supplement A §7.4–7.5 and Ch 3's ECC "
                  "sections.",
    },
}

WRAPPER_TEMPLATE = """---
title: "{title}"
tags: {tags}
---

# {title}

{description}

**Book anchor:** {anchor}

[Open full-screen ↗](files/{html_name}){{ .md-button }}

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/{html_name}" width="100%" height="720"
        style="border:1px solid #26304d;border-radius:12px;background:#0b1020"
        loading="lazy" title="{title}"></iframe>
"""


def demote_extra_h1s(lines: list[str]) -> list[str]:
    """Demote every H1 after the first to H2. Skips fenced code blocks."""
    out = []
    in_fence = False
    fence_re = re.compile(r"^(```|~~~)")
    seen_h1 = False
    for line in lines:
        if fence_re.match(line.lstrip()):
            in_fence = not in_fence
        elif not in_fence and line.startswith("# "):
            if seen_h1:
                line = "#" + line  # '# ' -> '## '
            seen_h1 = True
        out.append(line)
    return out


def front_matter(title: str, tags: list[str], anchor: str) -> str:
    tag_lines = "\n".join(f"  - {t}" for t in tags)
    return (
        "---\n"
        f'title: "{title}"\n'
        f"tags:\n{tag_lines}\n"
        f'source_anchor: "{anchor}"\n'
        "---\n\n"
    )


def strip_existing_front_matter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:].lstrip("\n")
    return text


def ingest_documents() -> int:
    count = 0
    for name, (dest_rel, title, tags, anchor) in DOCUMENTS.items():
        src = INCOMING / name
        if not src.exists():
            continue
        dest = DOCS / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = strip_existing_front_matter(src.read_text(encoding="utf-8"))
        lines = demote_extra_h1s(text.splitlines())
        body = "\n".join(lines).rstrip() + "\n"
        dest.write_text(front_matter(title, tags, anchor) + body,
                        encoding="utf-8")
        print(f"  doc  {name} -> docs/{dest_rel}")
        count += 1
    return count


def ingest_animations() -> int:
    src_dir = INCOMING / "animations"
    if not src_dir.is_dir():
        return 0
    files_dir = DOCS / "animations" / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for html in sorted(src_dir.glob("*.html")):
        shutil.copyfile(html, files_dir / html.name)  # verbatim, untouched
        print(f"  anim {html.name} -> docs/animations/files/")
        count += 1

        meta = ANIMATIONS.get(html.stem)
        if meta is None:
            wrapper = DOCS / "animations" / f"{html.stem}.md"
            meta = {
                "title": html.stem.replace("-", " ").replace("_", " ").title(),
                "tags": ["animations"],
                "description": "_TODO: describe what this animation teaches "
                               "and how to interact with it._",
                "anchor": "_TODO_",
            }
        else:
            wrapper = DOCS / "animations" / meta["wrapper"]

        if wrapper.exists():
            continue  # never clobber a (possibly hand-edited) wrapper
        wrapper.write_text(
            WRAPPER_TEMPLATE.format(
                title=meta["title"],
                tags="[" + ", ".join(meta["tags"]) + "]",
                description=meta["description"],
                anchor=meta["anchor"],
                html_name=html.name,
            ),
            encoding="utf-8",
        )
        print(f"       wrapper created: docs/animations/{wrapper.name}")
        print("       -> remember to add it to mkdocs.yml nav and the "
              "gallery (docs/animations/index.md)")
    return count


def main() -> int:
    print("Ingesting from incoming/ ...")
    docs = ingest_documents()
    anims = ingest_animations()
    print(f"Done: {docs} document(s), {anims} animation(s).")
    if docs == 0 and anims == 0:
        print("Nothing found in incoming/. Drop files there and re-run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
