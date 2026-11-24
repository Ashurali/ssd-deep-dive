---
title: "Why SSDs need an FTL — NAND flash, animated"
tags: [animations, flash-physics, ftl, garbage-collection, write-amplification]
---

# Why SSDs need an FTL — NAND flash, animated

A guided walk through NAND's physical rules, and the consequences they force: out-of-place writes, garbage collection and write amplification.

## What you'll learn

- Why a page is the smallest unit NAND writes and a block the smallest it erases.
- Why erase is block-wide: all of a block's cells share one substrate.
- Why programming only turns 1s into 0s, so a page cannot be overwritten in place.
- How that leads to garbage collection, and to write amplification.

## Try this

1. Press play and let the four chapters run, or step with the arrow buttons (← and → on a keyboard).
2. In **03 The no-overwrite rule**, watch the attempt to turn a 0 back into a 1 get blocked.
3. In **04 Garbage collection & wear**, compare the 3 pages the host wrote with the 6 the flash wrote.

[Open full-screen ↗](files/nand-flash-animation.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/nand-flash-animation.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="Why SSDs need an FTL — NAND flash, animated"></iframe>

## Where it appears

- Chapter 3, [§3.1.3 The hierarchy: cell → page → block → plane → die](../core/ch3-nand-flash.md#313-the-hierarchy-cell-page-block-plane-die)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It predates the [figure atlas](../atlas/figure-atlas-animation-roadmap.md) and animates Chapter 3's page and block model and Chapter 4's garbage-collection walk-through (Figs 4-14→4-22 of 《深入淺出SSD》, CH4 pp. 16–26).
