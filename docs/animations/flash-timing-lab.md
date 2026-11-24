---
title: "The Flash Timing & Parallelism Lab"
tags: [animations, flash-physics, controllers, bics8]
---

# The Flash Timing & Parallelism Lab

Timelines of what the flash bus actually does, drawn to scale with the book's own timings: one shared bus, register pipelining, multi-plane programming and independent plane reads.

## What you'll learn

- How the dies on one channel share an 8-bit bus, and why the bus is free while a die is busy inside its array.
- How the cache register lets the next page load from the array while the previous one streams out.
- How multi-plane programming nearly doubles write throughput on one die.
- How independent plane reads (AIPR) cut read latency, and why data placement still decides whether they help.

## Try this

1. In **1 · One bus, four dies**, press *run: read on die 0, then program on die 2*, and use the legend to tell command, address and data bursts apart.
2. In **2 · Register pipelining**, turn *cache-register pipelining* off and compare the total time.
3. In **3 · Multi-plane**, turn *dual-plane* on.
4. In **4 · AIPR**, press *fire 2 random reads at the same die* a few times, then turn on *independent planes (AIPR)* and *stripe hot data across planes*.

[Open full-screen ↗](files/flash_timing_lab.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/flash_timing_lab.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="The Flash Timing & Parallelism Lab"></iframe>

## Where it appears

- Chapter 2, [§2.1.3 Back end](../core/ch2-controllers-afa.md#213-back-end)
- Chapter 3, [§3.2.5 Read / write / erase on the wire](../core/ch3-nand-flash.md#325-read-write-erase-on-the-wire)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It realizes Figs 2-8, 3-8 and 3-31→3-41 of 《深入淺出SSD》 and the second edition's AIPR addendum (CH2 p. 10; CH3 pp. 8, 33–41) as Cluster E of the [figure atlas](../atlas/figure-atlas-animation-roadmap.md).
