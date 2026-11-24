---
title: "Animation Gallery"
tags:
  - animations
---

# Animation gallery

Every 🏆 cluster from the [figure atlas](../atlas/figure-atlas-animation-roadmap.md)
build plan, realized as self-contained interactive visualizations. Each one is
also embedded directly in the chapter section whose figures it animates —
look for the collapsed **"🎬 Animate this"** blocks while reading.

## The atlas clusters

<div class="grid cards" markdown>

-   ### A · The Vt Distribution Playground

    ---

    Program one cell, grow a bell curve from 4,000, then drag wear,
    retention and read count until the bells collide — with Read Retry
    and soft-read LLR shading.

    `flash-physics` · `threshold-voltage` · `reliability`

    [→ Play](vt-playground.md)

-   ### B · The Toy SSD Sandbox

    ---

    The book's 4×6×9 toy SSD as a live simulation: GC, the OP slider vs
    the WA meter, Trim, wear-leveling heatmap, bad blocks, and an
    emergent FOB→steady-state curve.

    `ftl` · `garbage-collection` · `write-amplification`

    [→ Play](toy-ssd-sandbox.md)

-   ### C · The NVMe Ring Machine

    ---

    SQ/CQ rings, doorbells, the 8-step flow, the phase-tag wraparound
    flip, the piggybacked SQ head — plus a wire view that shows every
    arrow as its real TLP.

    `nvme` · `queues`

    [→ Play](nvme-ring-machine.md)

-   ### D · The Packet Dresser & ACK/NAK Lab

    ---

    Three layers dress and undress a TLP; a Jammer gremlin corrupts,
    drops and delays; the Replay Buffer cleans up the mess.

    `pcie` · `tlp` · `link-layer`

    [→ Play](packet-dresser.md)

-   ### E · The Flash Timing & Parallelism Lab

    ---

    One shared bus, four dies, cache-register pipelining, dual-plane —
    and the AIPR figure the first edition never had.

    `flash-physics` · `controllers` · `bics8`

    [→ Play](flash-timing-lab.md)

-   ### F · Mapping Lookup Paths

    ---

    DRAM vs DRAM-less vs HMB vs HPB race one 4 KB read; the two-access
    penalty appears as two long bars.

    `ftl` · `mapping` · `hpb`

    [→ Play](mapping-paths.md)

-   ### G · Power-Loss Rebuild & Snapshots

    ---

    Yank the power, rebuild the map from per-page metadata, watch the
    timestamp duel — then let snapshots collapse the recovery time.

    `ftl` · `power-loss-recovery`

    [→ Play](power-loss-rebuild.md)

-   ### H · Stripe RAID & the Chained Warships

    ---

    A real XOR rebuild from four survivors, and the GC trap that forces
    whole stripes to move together.

    `reliability` · `ecc`

    [→ Play](stripe-raid.md)

-   ### I · The Enumeration & Routing Explorer

    ---

    The BAR all-1s sizing trick, the memory map filling in, and TLPs
    finding (or failing to find) their way through Base/Limit windows.

    `pcie` · `tlp`

    [→ Play](enum-routing.md)

-   ### J · The SSD Calculator Bundle

    ---

    PCIe bandwidth & IOPS ceiling, OP↔WA↔TBW/DWPD with the live Fig 4-25
    curve, JESD218A sample sizing, and a QoS nines explorer.

    `write-amplification` · `endurance` · `jedec`

    [→ Play](ssd-calculators.md)

</div>

## The originals

<div class="grid cards" markdown>

-   ### Why SSDs need an FTL — NAND flash, animated

    ---

    Pages, blocks, the program/erase asymmetry — and how those physical
    rules force out-of-place writes, garbage collection, and write
    amplification.

    `flash-physics` · `ftl`

    [→ Watch](nand-flash-animation.md)

-   ### How ECC finds and fixes a bit — Hamming visualizer

    ---

    Flip any bit of a Hamming(12,8) codeword and watch the parity checks
    pinpoint the flipped position.

    `ecc`

    [→ Watch](ecc-bit-correction.md)

-   ### Stronger ECC in action — BCH & LDPC

    ---

    BCH's algebraic error location, and an LDPC Tanner graph converging
    by message passing.

    `ecc` · `bch` · `ldpc`

    [→ Watch](ecc-bch-ldpc.md)

</div>
