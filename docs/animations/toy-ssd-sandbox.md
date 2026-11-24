---
title: "The Toy SSD Sandbox"
tags: [animations, ftl, garbage-collection, write-amplification, over-provisioning, trim, wear-leveling, bad-blocks]
---

# The Toy SSD Sandbox

The book's toy SSD — 4 channels × 6 blocks × 9 pages — run as a live simulation of the whole Chapter 4 cycle: fill, overwrite, collect, wear, trim.

## What you'll learn

- How overwrites leave invalid pages behind, and how garbage collection (GC) picks a victim block and moves its valid pages out.
- Why more over-provisioning (OP) means less write amplification (WA): the simulation measures WA as you move the OP slider.
- What Trim, static wear-leveling and bad-block handling each change.
- Why a fresh drive is fast and a full one settles to a slower steady state.

## Try this

1. Choose *random*, press *▶ auto-run*, and watch blocks fill with invalid pages until GC starts.
2. Move the *OP* slider and compare the WA reading.
3. Toggle *Trim*, then press *delete a "file"*, and see how much less GC has to copy.
4. Turn on the *🔥 heatmap view*, then *static wear-leveling*, and watch the erase counts even out.

[Open full-screen ↗](files/toy_ssd_sandbox.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/toy_ssd_sandbox.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="The Toy SSD Sandbox"></iframe>

## Where it appears

- Chapter 1, [§1.4 How an SSD actually works](../core/ch1-overview.md#14-how-an-ssd-actually-works)
- Chapter 4, [§4.3 Garbage collection](../core/ch4-ftl.md#43-garbage-collection)
- Chapter 7, [§7.10 Performance testing: the SNIA methodology](../core/ch7-testing.md#710-performance-testing-the-snia-methodology)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It realizes Figs 4-14→4-33, 4-35→4-37, 4-39→4-42, 4-49→4-51, 1-14, 1-21 and 7-27/7-28 of 《深入淺出SSD》 (CH4 pp. 17–61) as Cluster B of the [figure atlas](../atlas/figure-atlas-animation-roadmap.md).
