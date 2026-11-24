---
title: "Stripe RAID & the Chained Warships"
tags: [animations, reliability, ecc, flash-physics]
---

# Stripe RAID & the Chained Warships

Four data dies and one XOR parity die. Losing a die's block is survivable, but the parity ties a stripe's members together.

## What you'll learn

- How XOR parity across dies rebuilds a block that error correction could not save (an uncorrectable error, UECC).
- Why garbage collection has to move a whole stripe at once.
- Why closing a half-filled stripe costs padding writes: write amplification paid purely for protection.

## Try this

1. Press *☠ UECC — kill one die's block*, then *rebuild from XOR*, and follow the XOR bit by bit in the log.
2. Press *try to GC just ONE block of a stripe*.
3. Press *"sleep now" — close a half-empty stripe* and look for the padding.

[Open full-screen ↗](files/stripe_raid.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/stripe_raid.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="Stripe RAID & the Chained Warships"></iframe>

## Where it appears

- Chapter 3, [§3.4.4 RAID inside the SSD](../core/ch3-nand-flash.md#344-raid-inside-the-ssd)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It realizes Figs 3-58 and 3-59 of 《深入淺出SSD》 (CH3 pp. 65–66) as Cluster H of the [figure atlas](../atlas/figure-atlas-animation-roadmap.md).
