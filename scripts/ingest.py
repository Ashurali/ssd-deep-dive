#!/usr/bin/env python3
"""Ingest raw study material from incoming/ into docs/.

Re-runnable pipeline (SITE_SPECIFICATION.md §6.1, §8):

- Markdown guides: copy to their destination under docs/, prepend YAML front
  matter (title, tags, source_anchor), demote any H1 after the first to H2
  (fence-aware), and inject collapsed animation-embed blocks after the
  sections whose figures each animation realizes (EMBEDS registry below).
  Prose itself is never rewritten. Re-ingesting overwrites the destination.
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
# Animation registry, keyed by incoming filename stem.
#   wrapper: docs/animations/<wrapper>  title/tags/description: wrapper page
#   anchor:  book-anchor line           blurb: one-liner for chapter embeds
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
        "blurb": "Pages, blocks and the no-overwrite rule — the hierarchy "
                 "this section describes, animated stage by stage.",
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
        "blurb": "Flip a bit and watch the parity checks announce its "
                 "location — the syndrome idea made tangible.",
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
        "blurb": "BCH's algebraic error hunt and an LDPC Tanner graph "
                 "converging by message passing, side by side.",
    },
    "vt_playground": {
        "wrapper": "vt-playground.md",
        "title": "The Vt Distribution Playground",
        "tags": ["animations", "flash-physics", "threshold-voltage",
                 "reliability", "read-disturb", "data-retention",
                 "endurance"],
        "description": (
            "The diagram of the entire flash half of the book, made "
            "draggable: program a single cell, watch 4,000 cells pile into "
            "a bell curve, cram 2/4/8 bells into the same window "
            "(SLC/MLC/TLC), then drag P/E cycles, retention and read count "
            "to drift the bells into each other while a live RBER counter "
            "ticks. Read Retry re-centers the references — until the bells "
            "merge, which is the whole limit of hard-decision reading."
        ),
        "anchor": "Realizes Figs 3-1→3-5, 3-44→3-48, 3-50→3-57, 3-60 and "
                  "1-24→1-27 (CH3 pp. 1–13, 44–63) — atlas Cluster A.",
        "blurb": "SLC/MLC/TLC bells in one window — drag wear, retention "
                 "and read count and watch every Ch 3 failure mode happen.",
    },
    "toy_ssd_sandbox": {
        "wrapper": "toy-ssd-sandbox.md",
        "title": "The Toy SSD Sandbox",
        "tags": ["animations", "ftl", "garbage-collection",
                 "write-amplification", "over-provisioning", "trim",
                 "wear-leveling", "bad-blocks"],
        "description": (
            "The book's exact toy — 4 channels × 6 blocks × 9 pages — as a "
            "living simulation: sequential vs random fill, garbage "
            "collection with victim selection, an OP slider that re-derives "
            "the WA curve from the simulation itself, Trim on/off, a "
            "wear-leveling heatmap, bad-block injection, and a throughput "
            "sparkline where the FOB → steady-state curve *emerges* "
            "instead of being drawn."
        ),
        "anchor": "Realizes Figs 4-14→4-33, 4-35→4-37, 4-39→4-42, "
                  "4-49→4-51, 1-14, 1-21, 7-27/7-28 (CH4 pp. 17–61) — "
                  "atlas Cluster B.",
        "blurb": "This section's walkthrough as a live simulation — write, "
                 "overwrite, collect, and watch WA respond to the OP "
                 "slider.",
    },
    "nvme_ring_machine": {
        "wrapper": "nvme-ring-machine.md",
        "title": "The NVMe Ring Machine",
        "tags": ["animations", "nvme", "queues", "pcie"],
        "description": (
            "SQ and CQ drawn as actual rings with head/tail pointers, "
            "doorbell registers on the SSD side, and the whole 8-step "
            "command flow — including the two details everyone gets wrong: "
            "the phase-tag color flip on ring wraparound and the "
            "piggybacked SQ head riding home on every completion. A wire "
            "view re-labels every arrow as its real PCIe TLP."
        ),
        "anchor": "Realizes Figs 6-9→6-20 and the 6-31→6-39 trace "
                  "(CH6 pp. 11–22, 35–40) — atlas Cluster C.",
        "blurb": "The SQ/CQ/doorbell dance as a working machine — submit "
                 "commands, watch the phase tag flip on wraparound.",
    },
    "packet_dresser": {
        "wrapper": "packet-dresser.md",
        "title": "The Packet Dresser & ACK/NAK Lab",
        "tags": ["animations", "pcie", "tlp", "link-layer", "testing"],
        "description": (
            "A TLP gets dressed by three layers and undressed by three "
            "layers — then a Jammer gremlin sits on the wire. Corrupt an "
            "LCRC, drop a TLP, or delay an ACK, and watch the Replay "
            "Buffer, NAKs and timeouts play out the entire §5.8 state "
            "machine. Includes the through-a-switch scene and flow-control "
            "credits."
        ),
        "anchor": "Realizes Figs 5-11→5-20, 5-49→5-55 and Ch7's Jammer "
                  "(Figs 7-15/7-16) — atlas Cluster D.",
        "blurb": "Dress a TLP layer by layer, then let the Jammer corrupt "
                 "the wire and watch ACK/NAK recover.",
    },
    "flash_timing_lab": {
        "wrapper": "flash-timing-lab.md",
        "title": "The Flash Timing & Parallelism Lab",
        "tags": ["animations", "flash-physics", "controllers", "bics8"],
        "description": (
            "Gantt-chart timelines of what the flash bus actually does: "
            "one shared 8-bit bus and CE# picking a die, cache-register "
            "pipelining hiding transfers under media loads (the book's own "
            "1.5 ms / 50 µs numbers, to scale), dual-plane programming, "
            "and the AIPR scene — the 2nd edition's independent-plane-read "
            "figure the first edition never had."
        ),
        "anchor": "Realizes Figs 2-8, 3-8, 3-31→3-41 and the 2nd-edition "
                  "AIPR addendum — atlas Cluster E.",
        "blurb": "The bus, the registers and the planes on one timeline — "
                 "toggle pipelining and AIPR and watch the bars move.",
    },
    "mapping_paths": {
        "wrapper": "mapping-paths.md",
        "title": "Mapping Lookup Paths",
        "tags": ["animations", "ftl", "mapping", "ufs", "hpb"],
        "description": (
            "Four architectures race the same 4 KB random read: DRAM drive "
            "(map in DRAM), DRAM-less (two flash accesses on a miss — the "
            "Fig 4-13 penalty as two long bars), HMB (a PCIe hop into "
            "borrowed host RAM), and HPB (the host supplies the physical "
            "address). Switch to sequential and watch DRAM-less catch up. "
            "Warm-up scene: block mapping's read-modify-write pain."
        ),
        "anchor": "Realizes Figs 4-3→4-13 (CH4 pp. 5–14) plus Supplement "
                  "B's HPB — atlas Cluster F.",
        "blurb": "DRAM vs DRAM-less vs HMB vs HPB racing the same read — "
                 "the two-flash-access penalty as two long bars.",
    },
    "power_loss_rebuild": {
        "wrapper": "power-loss-rebuild.md",
        "title": "Power-Loss Rebuild & Snapshots",
        "tags": ["animations", "ftl", "power-loss-recovery"],
        "description": (
            "Every written page carries its passport (LBA + timestamp). "
            "Yank the power mid-run, then watch the reboot scan crawl the "
            "flash re-deriving the map — including the timestamp duel when "
            "the same LBA turns up twice. Turn snapshots on and the next "
            "rebuild loads the last snapshot and scans only the tail."
        ),
        "anchor": "Realizes Figs 4-33, 4-43→4-46 (CH4 pp. 41, 53–56) — "
                  "atlas Cluster G.",
        "blurb": "Yank the power, then watch the map rebuild from "
                 "metadata tags — and the timestamp duel resolve stale "
                 "copies.",
    },
    "stripe_raid": {
        "wrapper": "stripe-raid.md",
        "title": "Stripe RAID & the Chained Warships",
        "tags": ["animations", "reliability", "ecc", "flash-physics"],
        "description": (
            "Four data dies plus an XOR parity die. Kill a die's block and "
            "rebuild it bit by bit from the survivors — the XOR runs for "
            "real. Then try to garbage-collect just one member of a stripe "
            "and watch the chain yank: the parity equation forces the "
            "whole stripe to move together, warships chained at Red "
            "Cliffs."
        ),
        "anchor": "Realizes Figs 3-58/3-59 (CH3 pp. 65–66) — atlas "
                  "Cluster H.",
        "blurb": "A real XOR rebuild, then the GC trap: one block can't "
                 "move alone when a parity equation chains the stripe.",
    },
    "enum_routing": {
        "wrapper": "enum-routing.md",
        "title": "The Enumeration & Routing Explorer",
        "tags": ["animations", "pcie", "tlp"],
        "description": (
            "A live PCIe tree: replay enumeration step by step — read "
            "BAR0, write all-1s, read back the stuck bits, decode the "
            "size, allocate a base — and watch the host memory map fill "
            "in. Then fire TLPs at chosen addresses and watch each switch "
            "port check its [Base, Limit] window; aim outside every window "
            "and the packet dies as an Unsupported Request."
        ),
        "anchor": "Realizes Figs 5-6→5-10, 5-27→5-48 (CH5 pp. 7–10, "
                  "29–46) — atlas Cluster I.",
        "blurb": "The BAR all-1s sizing trick and Base/Limit routing, "
                 "played out on a live tree.",
    },
    "ssd_calculators": {
        "wrapper": "ssd-calculators.md",
        "title": "The SSD Calculator Bundle",
        "tags": ["animations", "pcie", "write-amplification",
                 "over-provisioning", "endurance", "testing", "jedec"],
        "description": (
            "The book's formula figures as live number-crunchers: PCIe "
            "generation/lanes/MPS → effective bandwidth and the 4 KB IOPS "
            "ceiling; the OP ↔ WA ↔ TBW/DWPD chain with the Fig 4-25 curve "
            "recomputed live (S3710 preset included); the JESD218A "
            "sample-size inequalities with temperature acceleration "
            "(reproduces Ch 7 §7.8's 31-drives answer); and a QoS "
            "percentile explorer where you drag the nines into the tail."
        ),
        "anchor": "Realizes §5.13's overhead model (Fig 5-66), Fig 4-25 + "
                  "§1.5.3's formulas, Ch7 §7.8 Tables 7-6→7-9, and "
                  "Fig 1-20 — atlas Cluster J.",
        "blurb": "This section's formulas as live sliders — move an input "
                 "and watch the answer (and the curve) recompute.",
    },
}

# ---------------------------------------------------------------------------
# Chapter-embed registry: which animation belongs after which section.
#   incoming filename -> [(heading-line prefix, animation stem), ...]
# The trailing space in prefixes matters ("## 5.1 " must not match "## 5.13").
# ---------------------------------------------------------------------------
EMBEDS = {
    "SSD_Book_Ch1_Study_Guide.md": [
        ("## 1.4 ", "toy_ssd_sandbox"),
        ("### 1.5.3 ", "ssd_calculators"),
    ],
    "SSD_Book_Ch2_Study_Guide.md": [
        ("### 2.1.3 ", "flash_timing_lab"),
    ],
    "SSD_Book_Ch3_Study_Guide.md": [
        ("### 3.1.2 ", "vt_playground"),
        ("### 3.1.3 ", "nand-flash-animation"),
        ("### 3.2.5 ", "flash_timing_lab"),
        ("### 3.4.2 ", "vt_playground"),
        ("### 3.4.3 ", "ecc_bch_ldpc"),
        ("### 3.4.4 ", "stripe_raid"),
    ],
    "SSD_Book_Ch4_Study_Guide.md": [
        ("## 4.2 ", "mapping_paths"),
        ("## 4.3 ", "toy_ssd_sandbox"),
        ("### 4.3.2 ", "ssd_calculators"),
        ("## 4.6 ", "power_loss_rebuild"),
    ],
    "SSD_Book_Ch5_Study_Guide.md": [
        ("## 5.1 ", "ssd_calculators"),
        ("## 5.3 ", "packet_dresser"),
        ("## 5.6 ", "enum_routing"),
        ("## 5.8 ", "packet_dresser"),
        ("## 5.13 ", "ssd_calculators"),
    ],
    "SSD_Book_Ch6_Study_Guide.md": [
        ("## 6.3 ", "nvme_ring_machine"),
    ],
    "SSD_Book_Ch7_Study_Guide.md": [
        ("### 7.3.3 ", "packet_dresser"),
        ("## 7.8 ", "ssd_calculators"),
        ("## 7.10 ", "toy_ssd_sandbox"),
    ],
    "SSD_Book_Supplement_A_ECC_Coding_Theory.md": [
        ("### 7.3.2 ", "ecc_bit_correction"),
        ("## 7.5 ", "ecc_bch_ldpc"),
    ],
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

# Collapsed by default; the lazy iframe only loads when the reader opens it.
EMBED_TEMPLATE = """
??? example "🎬 Animate this — {title}"

    {blurb}

    [Animation page](../{updir}animations/{wrapper}) · [open full-screen ↗](../{updir}animations/files/{html_name})

    <iframe src="../../animations/files/{html_name}" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="{title}"></iframe>
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


def inject_embeds(lines: list[str], name: str, dest_rel: str) -> list[str]:
    """Insert an embed block after each section heading listed in EMBEDS."""
    rules = list(EMBEDS.get(name, []))
    if not rules:
        return lines
    out = []
    for line in lines:
        out.append(line)
        for rule in rules:
            prefix, stem = rule
            if line.startswith(prefix):
                meta = ANIMATIONS.get(stem)
                if meta is None:
                    continue
                html_name = _html_name_for(stem)
                if html_name is None:
                    continue  # animation not ingested (yet) — skip quietly
                out.append(EMBED_TEMPLATE.format(
                    title=meta["title"],
                    blurb=meta["blurb"],
                    wrapper=meta["wrapper"],
                    html_name=html_name,
                    updir="",
                ))
                rules.remove(rule)
                break
    for prefix, stem in rules:
        print(f"  WARN: embed anchor '{prefix}' not found in {name}",
              file=sys.stderr)
    return out


def _html_name_for(stem: str) -> str | None:
    """Find the animation's html filename (checks incoming/ then docs/)."""
    for d in (INCOMING / "animations", DOCS / "animations" / "files"):
        p = d / f"{stem}.html"
        if p.exists():
            return p.name
    return None


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
        lines = inject_embeds(lines, name, dest_rel)
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
    anims = ingest_animations()      # animations first: embeds reference them
    docs = ingest_documents()
    print(f"Done: {docs} document(s), {anims} animation(s).")
    if docs == 0 and anims == 0:
        print("Nothing found in incoming/. Drop files there and re-run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
