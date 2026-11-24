---
title: "The Vt Distribution Playground"
tags: [animations, flash-physics, threshold-voltage, reliability, read-disturb, data-retention, endurance]
---

# The Vt Distribution Playground

The threshold-voltage (V<sub>t</sub>) picture behind every Chapter 3 failure mode, made draggable: one cell, then a population of cells, then the bells that wear, retention and reads push into each other.

## What you'll learn

- Why programming a cell raises its threshold voltage and erasing lowers it, and why every cycle wears the oxide a little.
- Why thousands of cells form a bell curve, and why packing 2, 4 or 8 bells into one voltage window (SLC, MLC, TLC) leaves each bell less margin.
- How program/erase cycles, retention and read disturb move and widen the bells, and how the raw bit error rate (RBER) climbs once they overlap.
- What Read Retry fixes (bells that shifted) and what it cannot (bells that merged), and what soft reads add for LDPC.

## Try this

1. In **1 · The cell**, press *Program* and then *Erase*, and watch the marker move along the V<sub>t</sub> axis.
2. In **2 · Cells → bells**, press *Program 4,000 cells* and watch the bell build up.
3. In **3 · Bells, stress & read retry**, choose *TLC*, drag *P/E cycles* to about 3,000 and *retention* to 24 months, and watch the RBER. Then press *Read Retry*.
4. Tick *soft reads* to see the band around each reference where a cell's value is uncertain.

[Open full-screen ↗](files/vt_playground.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/vt_playground.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="The Vt Distribution Playground"></iframe>

## Where it appears

- Chapter 3, [§3.1.2 SLC / MLC / TLC: the threshold-voltage picture](../core/ch3-nand-flash.md#312-slc-mlc-tlc-the-threshold-voltage-picture)
- Chapter 3, [§3.4.2 Read Retry](../core/ch3-nand-flash.md#342-read-retry)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It realizes Figs 3-1→3-5, 3-9→3-11, 3-44→3-48, 3-50→3-57, 3-60 and 1-24→1-27 of 《深入淺出SSD》 (CH3 pp. 1–13, 44–63; CH1 pp. 38–40) as Cluster A of the [figure atlas](../atlas/figure-atlas-animation-roadmap.md).
