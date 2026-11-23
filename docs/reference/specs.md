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
  [Supp D — Power Management](../supplements/d-power-management.md), and the fleet
  management of [Supp I — Data-Center SSDs](../supplements/i-data-center.md#i6-managing-fleets-nvme-mi-and-the-bmc).

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

## Security, data-center and mobile standards

Pointers for the newer supplements; each was checked against the revision
named here in November 2026.

**TCG Storage Security Subsystem Class: Opal — Version 2.02** (2022-01-24), with Pyrite and Ruby — Trusted Computing Group ([trustedcomputinggroup.org](https://trustedcomputinggroup.org/))
: Self-encrypting drive management: locking ranges, shadow MBR, PSID revert.
  Backs [Supp F §F.3](../supplements/f-security.md#f3-the-tcg-storage-specifications-opal-pyrite-and-ruby).

**IEEE 1619 (XTS-AES) and IEEE 2883-2022 (Sanitizing Storage)** — IEEE ([standards.ieee.org](https://standards.ieee.org/))
: The disk-encryption mode, and the per-interface clear / purge / destruct
  techniques. Backs [Supp F §F.2 and §F.4](../supplements/f-security.md).

**NIST SP 800-88 Revision 2** (2025-09) and **FIPS 140-3** — NIST ([csrc.nist.gov](https://csrc.nist.gov/))
: Media-sanitization program guidance, and cryptographic-module validation
  (FIPS 140-2 certificates moved to the historical list on 2026-09-21).
  Backs [Supp F §F.4.3 and §F.7](../supplements/f-security.md).

**DMTF Security Protocol and Data Model (SPDM), DSP0274** — DMTF ([dmtf.org](https://www.dmtf.org/))
: Device identity, signed measurements and attestation. Backs
  [Supp F §F.6](../supplements/f-security.md#f6-attestation-spdm-and-caliptra).

**OCP Datacenter NVMe SSD Specification — Version 2.7** (2026) — Open Compute Project ([opencompute.org](https://www.opencompute.org/))
: The large buyers' requirements for latency, logs, telemetry, firmware,
  security and power. Backs [Supp I §I.3](../supplements/i-data-center.md#i3-the-ocp-datacenter-nvme-ssd-specification).

**SNIA SFF-TA-1006 / 1007 / 1008 (EDSFF E1.S, E1.L, E3)** — SNIA SFF ([snia.org](https://www.snia.org/technology-communities/sff/specifications))
: Data-center form factors. Backs [Ch 1 §1.6.6](../core/ch1-overview.md) and
  [Supp I §I.2](../supplements/i-data-center.md#i2-form-factors-u2-u3-and-edsff).

**Compute Express Link (CXL) — Revision 4.0** (2025-11) — CXL Consortium ([computeexpresslink.org](https://computeexpresslink.org/))
: Coherent memory over the PCIe physical layer. Backs
  [Supp I §I.8](../supplements/i-data-center.md#i8-cxl-memory-over-the-pcie-wires).

**JEDEC JESD220H (UFS 5.0)** (2026-02), with MIPI M-PHY 6.0 and UniPro 3.0 — JEDEC ([jedec.org](https://www.jedec.org/)), MIPI Alliance ([mipi.org](https://www.mipi.org/))
: Mobile storage. Backs [Supp B §B.9](../supplements/b-ufs.md#b9-modern-developments-ufs-41-and-50).