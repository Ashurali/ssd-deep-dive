---
title: "The Packet Dresser & ACK/NAK Lab"
tags: [animations, pcie, tlp, link-layer, testing]
---

# The Packet Dresser & ACK/NAK Lab

A transaction layer packet (TLP) dressed by three PCIe layers on the way out and undressed by three on the way in, with a Jammer on the wire between them.

## What you'll learn

- What each PCIe layer adds to a packet on the way down, and checks on the way up.
- Why a switch has to unwrap a packet to the Transaction layer to route it.
- How ACK/NAK, the replay buffer and the replay timer recover from a corrupted, a dropped or a delayed packet.
- How flow-control credits keep a sender from overrunning the receiver's buffers.

## Try this

1. In **1 · Dressing room**, press *dress next layer* three times, then *send across the link*.
2. In **3 · ACK/NAK + Jammer**, press *corrupt LCRC*, then *send next TLP*, and follow the log. With *drop a TLP*, send two packets so the receiver sees the gap; then try *delay the ACK*.
3. In **4 · Flow-control credits**, send until the gate closes, then let the receiver return a credit.

[Open full-screen ↗](files/packet_dresser.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/packet_dresser.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="The Packet Dresser & ACK/NAK Lab"></iframe>

## Where it appears

- Chapter 5, [§5.3 The three-layer stack](../core/ch5-pcie.md#53-the-three-layer-stack)
- Chapter 5, [§5.8 Data Link Layer](../core/ch5-pcie.md#58-data-link-layer)
- Chapter 7, [§7.3.3 Jammer](../core/ch7-testing.md#733-jammer)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It realizes Figs 5-3/5-5, 5-11→5-20 and 5-49→5-55, and the Jammer of Figs 7-15/7-16, of 《深入淺出SSD》 (CH5 pp. 11–27, 47–54; CH7 pp. 25–26) as Cluster D of the [figure atlas](../atlas/figure-atlas-animation-roadmap.md).
