---
title: "The SSD Calculator Bundle"
tags: [animations, pcie, write-amplification, over-provisioning, endurance, testing, jedec]
---

# The SSD Calculator Bundle

The book's formulas as live calculators. The presets reproduce the chapters' worked examples.

## What you'll learn

- How PCIe generation, lane count and maximum payload size (MPS) turn into effective bandwidth and a 4 KB IOPS ceiling.
- How over-provisioning sets worst-case write amplification, and how that sets terabytes written (TBW) and drive writes per day (DWPD).
- How JESD218A picks the sample size for an endurance test, and how many errors it allows.
- Why quality of service (QoS) is quoted as percentiles: each extra nine reaches deeper into the latency tail.

## Try this

1. In **J1**, keep Gen 3 ×4 and change *MPS* from 128 to 512 bytes.
2. In **J2**, press *S3710 preset*, then drag *OP* and watch TBW.
3. In **J3**, leave the defaults: they reproduce Chapter 7 §7.8's worked example of 31 drives.
4. In **J4**, drag *confidence* from 99% to 99.9999% and watch the mean stay where it is.

[Open full-screen ↗](files/ssd_calculators.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/ssd_calculators.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="The SSD Calculator Bundle"></iframe>

## Where it appears

- Chapter 1, [§1.5.3 Endurance](../core/ch1-overview.md#153-endurance)
- Chapter 4, [§4.3.2 Write amplification](../core/ch4-ftl.md#432-write-amplification)
- Chapter 5, [§5.1 Starting with speed](../core/ch5-pcie.md#51-starting-with-speed)
- Chapter 5, [§5.13 PCIe link performance-loss analysis](../core/ch5-pcie.md#513-pcie-link-performance-loss-analysis)
- Chapter 7, [§7.8 Endurance testing](../core/ch7-testing.md#78-endurance-testing)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It realizes §5.13's overhead model (Fig 5-66), Fig 4-25 with §1.5.3's formulas, §7.8 with Tables 7-6→7-9, and Fig 1-20 of 《深入淺出SSD》 as Cluster J of the [figure atlas](../atlas/figure-atlas-animation-roadmap.md).
