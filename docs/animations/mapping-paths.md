---
title: "Mapping Lookup Paths"
tags: [animations, ftl, mapping, ufs, hpb]
---

# Mapping Lookup Paths

Where the map table lives decides what every read costs. Four architectures race the same 4 KB random read.

## What you'll learn

- Why block mapping turns a one-page update into a whole-block read-modify-write, and why SSDs pay for page mapping.
- What a random read costs with the map in onboard DRAM, in flash (a DRAM-less drive), in borrowed host memory (HMB) and on the host side (HPB).
- Why sequential reads hide most of the DRAM-less penalty.

## Try this

1. Press *update ONE page on a block-mapped drive* and count the pages it touches.
2. Run *random 4K read*, then *sequential read (map already cached)*, and compare the DRAM-less lane.
3. Add the *+ HPB lane (UFS)* and watch the lookup disappear.

[Open full-screen ↗](files/mapping_paths.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/mapping_paths.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="Mapping Lookup Paths"></iframe>

## Where it appears

- Chapter 4, [§4.2 Mapping management](../core/ch4-ftl.md#42-mapping-management)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It realizes Figs 4-3→4-13 of 《深入淺出SSD》 (CH4 pp. 5–14), plus the HPB material from Supplement B, as Cluster F of the [figure atlas](../atlas/figure-atlas-animation-roadmap.md).
