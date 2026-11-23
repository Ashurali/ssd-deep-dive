---
title: "Specifications & Standards"
---

# Specifications & standards

The authoritative public specifications behind the protocol and testing
chapters. These are **pointers only** — download each document from the
standards body that publishes it. Nothing is rehosted here, and the exact
revision the corpus was written against is noted so you can match section
numbers.

## NVM Express (NVMe)

Download from the official specification library:
[nvmexpress.org/specifications](https://nvmexpress.org/specifications/).
Since NVMe 2.0 the specification is split into a base spec plus per-command-set
and interface specs, so all three below travel together.

**NVM Express Base Specification — Revision 2.3** (2025-08-01, ratified)
: The core protocol: queues, doorbells, the controller/namespace model, the
  command lifecycle. This is the spine of [Ch 6 — NVMe](../core/ch6-nvme.md)
  and the *NVMe Ring Machine* animation.

**NVM Express NVM Command Set Specification — Revision 1.2** (2025-08-01, ratified)
: The block-storage command set (Read/Write/Compare/Dataset Management, etc.)
  that was factored out of the base spec in NVMe 2.0. Read alongside
  [Ch 6 — NVMe](../core/ch6-nvme.md).

**NVM Express Management Interface (NVMe-MI) — Revision 1.1d** (2021-04-19, ratified)
: Out-of-band management of the drive over SMBus/I²C and MCTP — inventory,
  health, and configuration independent of the host driver. Relevant to
  [Ch 6 — NVMe](../core/ch6-nvme.md) and the management/telemetry themes in
  [Supp D — Power Management](../supplements/d-power-management.md).

## Other standards referenced by the corpus

These are membership- or registration-gated, so only pointers are given:

**PCI Express Base Specification** — PCI-SIG ([pcisig.com](https://pcisig.com/specifications))
: The transport layer underneath NVMe — TLPs, the link/transaction layers,
  enumeration and routing. Backs [Ch 5 — PCIe](../core/ch5-pcie.md), the
  *Packet Dresser* and *Enumeration & Routing* animations.

**JEDEC JESD218 / JESD219** — JEDEC ([jedec.org](https://www.jedec.org/))
: SSD endurance requirements and the enterprise/client workloads used to
  qualify them — the basis of the sample-size math in
  [Ch 7 — SSD Testing](../core/ch7-testing.md).

**SNIA Solid State Storage Performance Test Specification (SSS PTS)** — SNIA ([snia.org](https://www.snia.org/))
: The preconditioning-and-steady-state methodology behind the performance
  measurements discussed in [Ch 7 — SSD Testing](../core/ch7-testing.md).
