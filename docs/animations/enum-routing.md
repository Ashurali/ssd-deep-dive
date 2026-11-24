---
title: "The Enumeration & Routing Explorer"
tags: [animations, pcie, tlp]
---

# The Enumeration & Routing Explorer

How software discovers a PCIe tree, and how a packet finds its way through it.

## What you'll learn

- How software sizes a base address register (BAR): write all 1s, read it back, and the bits that stay 0 give the size.
- How the host then gives each device an address range, building the memory map.
- How a switch routes a memory write by checking each port's [Base, Limit] window, and what happens when none matches: an Unsupported Request.

## Try this

1. Press *▶ enumeration: next step* twelve times (four steps for each of the three devices) and read the log at each step.
2. Fire a write at each address in the list, including *nobody's window!*
3. Reload the page and fire a write before enumerating, to see why nothing can be routed yet.

[Open full-screen ↗](files/enum_routing.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/enum_routing.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="The Enumeration & Routing Explorer"></iframe>

## Where it appears

- Chapter 5, [§5.6 Config space and BARs](../core/ch5-pcie.md#56-config-space-and-bars)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It realizes Figs 5-6→5-10 and 5-27→5-48 of 《深入淺出SSD》 (CH5 pp. 7–10, 29–46) as Cluster I of the [figure atlas](../atlas/figure-atlas-animation-roadmap.md).
