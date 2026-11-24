---
title: "The NVMe Ring Machine"
tags: [animations, nvme, queues, pcie]
---

# The NVMe Ring Machine

The submission and completion queues drawn as real rings, with the doorbells on the drive side and the full eight-step command flow.

## What you'll learn

- How one command travels: the host writes it into the submission queue (SQ) and rings the tail doorbell; the controller fetches and runs it, posts an entry in the completion queue (CQ) and raises an interrupt; the host consumes the entry and rings the CQ head doorbell.
- How the phase tag lets the host spot new completions without reading a counter, and why the phase it expects flips each time the ring wraps.
- Why every completion carries the SQ head back to the host.
- That on the PCIe link, all of this is plain memory reads and writes.

## Try this

1. Press *① submit a command* three times, then press *step* repeatedly and read the note under the drawing at each step.
2. Turn on *auto* and watch the CQ entries change colour after the ring wraps.
3. Set the *queue depth limit* to 1, then to 8, and compare how many commands are in flight.
4. Turn on *wire view (TLPs)* to see each step as the packet that carries it.

[Open full-screen ↗](files/nvme_ring_machine.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/nvme_ring_machine.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="The NVMe Ring Machine"></iframe>

## Where it appears

- Chapter 6, [§6.3 The three treasures in detail](../core/ch6-nvme.md#63-the-three-treasures-in-detail)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It realizes Figs 6-9→6-20 (the ring walk-through), 6-29/6-30 and the 6-31→6-39 PCIe trace (as the wire view) of 《深入淺出SSD》 (CH6 pp. 11–22, 33–40) as Cluster C of the [figure atlas](../atlas/figure-atlas-animation-roadmap.md).
