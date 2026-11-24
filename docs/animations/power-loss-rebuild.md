---
title: "Power-Loss Rebuild & Snapshots"
tags: [animations, ftl, power-loss-recovery]
---

# Power-Loss Rebuild & Snapshots

The map table lives in RAM, and RAM forgets at power-off. This animation shows how the drive rebuilds the map from what every flash page carries with it.

## What you'll learn

- Why the logical-to-physical map is lost at power-off, and how the logical address and timestamp stored with each page let the controller rebuild it.
- How the rebuild settles two copies of the same logical address: the newer timestamp wins.
- How periodic snapshots shorten recovery to a scan of the pages written since the last snapshot.

## Try this

1. Press *write 5 pages* a few times (or turn on *auto-write*), then *⚡ YANK POWER* and *power on → rebuild*.
2. Watch for the timestamp duel when a logical address turns up twice.
3. Turn on *snapshots every 12 writes*, write some more, and compare how much of the flash the next rebuild has to scan.

[Open full-screen ↗](files/power_loss_rebuild.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/power_loss_rebuild.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="Power-Loss Rebuild & Snapshots"></iframe>

## Where it appears

- Chapter 4, [§4.6 Power-loss recovery](../core/ch4-ftl.md#46-power-loss-recovery)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It realizes Figs 4-33 and 4-43→4-46 of 《深入淺出SSD》 (CH4 pp. 41, 53–56) as Cluster G of the [figure atlas](../atlas/figure-atlas-animation-roadmap.md).
