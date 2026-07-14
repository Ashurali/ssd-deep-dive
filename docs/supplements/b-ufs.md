---
title: "Supp B — UFS"
tags:
  - ufs
  - writebooster
  - hpb
  - queues
  - zns
source_anchor: "supplement (no book chapter)"
---

# Supplement B — UFS (Universal Flash Storage)

**UFS** is the high-performance storage standard for phones, tablets, automotive, and edge-AI devices — essentially *the NVMe of the mobile world* (the book's 2nd edition gives it a chapter; this supplement reconstructs the topic from the JEDEC standards and current industry sources). A UFS device is **managed NAND** — controller + flash + firmware in one fingernail-sized package — running the *same* FTL, ECC, wear-leveling, and SLC-cache machinery as an SSD, wrapped in a mobile protocol stack.

Here's the pedagogical shortcut: **if you've read the core chapters, you already know ~80% of UFS.** It's a synthesis of things this site has already taught, so this supplement teaches mostly by mapping:

| UFS piece | You already know it as… | Where |
|---|---|---|
| SCSI-based command set | SAS/SSP command layer | [Ch 2](../core/ch2-controllers-afa.md#211-front-end) |
| Serial full-duplex differential link | PCIe signaling | [Ch 5](../core/ch5-pcie.md#51-starting-with-speed) |
| Command queuing / MCQ | NVMe SQ/CQ | [Ch 6](../core/ch6-nvme.md#63-the-three-treasures-in-detail) |
| UPIU (packet format) | NVMe command / SATA FIS | Ch 2, Ch 6 |
| Logical Units | NVMe Namespaces | [Ch 6 §6.7](../core/ch6-nvme.md#67-namespaces) |
| WriteBooster | SLC Cache | [Ch 4 §4.8](../core/ch4-ftl.md#48-slc-cache) |
| HPB (Host Performance Booster) | HMB | [Ch 4 §4.2.3](../core/ch4-ftl.md#423-hmb-host-memory-buffer) |
| HIBERN8 / low-power states | DevSleep & friends | [Ch 1 §1.5.5](../core/ch1-overview.md#155-power-thermals) |
| Zoned UFS (ZUFS) | ZNS | [Ch 4 §4.11](../core/ch4-ftl.md#411-modern-developments-from-sdf-to-zns-and-fdp) |

!!! abstract "In this supplement"
    - **What UFS is** ⭐ — the eMMC → UFS transition as a replay of SATA → NVMe (§B.1)
    - **The protocol stack** ⭐⭐ — UAP / UTP / UniPro / M-PHY, layer by layer (§B.2) · **UPIU packets** (§B.3)
    - **Logical Units** (§B.4) · **RPMB secure storage** ⭐ (§B.5) · **Low power: HIBERN8 & Deep Sleep** (§B.6)
    - **WriteBooster** ⭐⭐ — SLC cache in mobile clothes (§B.7) · **HPB** ⭐⭐ — host-assisted L2P (§B.8)
    - **UFS 4.1 / 5.0** — ZUFS, MCQ, defrag, and the 10.8 GB/s era (§B.9)

    Short on time? §B.1, §B.2, §B.7, §B.8 carry the most transfer.

---

## B.1 What UFS is: the eMMC successor ⭐

UFS is a JEDEC standard that replaced **eMMC (embedded MultiMediaCard)** — and the reason is *exactly* the SATA → PCIe/NVMe story of [Chapters 5–6](../core/ch5-pcie.md), transplanted to phones:

- **eMMC is parallel and half-duplex** — a shared bus, one direction at a time (SATA's walkie-talkie, in mobile form), topping out ~400 MB/s while mobile SoCs and cameras got hungry. And it had no real command queuing — the AHCI problem again.
- **UFS is serial and full-duplex** — separate differential lanes transmitting simultaneously (PCIe's dual-simplex), plus **deep command queuing** with out-of-order completion.

The mobile world re-ran the evolution this site already covered: a parallel, half-duplex, one-command-at-a-time interface built for slow media gave way to a serial, full-duplex, deeply queued one built for fast flash.

**Inside a UFS package** (~9 × 13 mm, down to 0.85 mm thick): a controller running a full FTL — mapping, GC, wear leveling, bad blocks, LDPC ECC; everything from [Chapters 3](../core/ch3-nand-flash.md)–[4](../core/ch4-ftl.md) and [Supplement A](a-ecc-coding-theory.md) — plus the NAND itself. The host SoC sends high-level reads and writes; the device shoulders all flash complexity. Same value proposition as an SSD, phone-sized. (KIOXIA's UFS parts, for instance, run on the same BiCS 3D NAND family as its SSDs — the firmware disciplines are siblings.)

**One key architectural fact:** UFS's command layer is built on **SCSI** — a subset of the SCSI command set. That connects straight to [Chapter 2](../core/ch2-controllers-afa.md#211-front-end), where SAS carried SCSI over SSP. At the application layer, a UFS device *is* a SCSI device — which is why its logical structure (Logical Units) reads as SCSI/SAS heritage even as its queuing turns NVMe-like (§B.9).

---

## B.2 The UFS protocol stack ⭐⭐

Layered, like PCIe — each layer serving the one above:

```
┌─────────────────────────────────────────────┐
│  Application Layer (UAP)                     │  ← SCSI command set
│   - UFS command set (SCSI-based)             │     + device management
│   - Device Manager, Task Manager             │
├─────────────────────────────────────────────┤
│  UFS Transport Protocol layer (UTP)          │  ← packages commands
│   - creates/parses UPIUs                     │     into UPIU packets
├─────────────────────────────────────────────┤
│  UFS Interconnect Layer (UIC)                │
│   ┌─────────────────────────────────────┐   │
│   │  MIPI UniPro  (link + transport)    │   │  ← flow control,
│   │  MIPI M-PHY   (physical layer)      │   │     retransmission, PHY
│   └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
        host  ⇄  UFS device (over M-PHY lanes)
```

The same three-tier idea as PCIe+NVMe: a command layer (≈ NVMe), a packetizing transport (UTP making UPIUs ≈ the Transaction Layer making TLPs), and a link+physical foundation (UniPro + M-PHY ≈ Data Link + Physical). The building blocks come from the **MIPI Alliance**, the consortium behind mobile interface standards.

**B.2.1 — Application layer.** The SCSI-subset command set (READ(10)/(16), WRITE, SYNCHRONIZE CACHE, UNMAP — the Trim/Deallocate of [Ch 4 §4.4](../core/ch4-ftl.md#44-trim) under its SCSI name), plus the **Device Manager** (configuration via **Descriptors, Attributes, Flags** — the Identify/Get-Set-Features analog) and the **Task Manager** (abort/query queue tasks).

**B.2.2 — Transport layer (UTP).** Wraps commands, data, and responses into **UPIUs** (§B.3) — precisely "NVMe hands 64-byte commands to PCIe, which wraps them in TLPs," one ecosystem over.

**B.2.3 — Interconnect (UniPro + M-PHY).** **MIPI UniPro** is the link layer: reliable delivery, **flow control, retransmission**, error handling — UFS's counterpart of PCIe's ACK/NAK + credits ([Ch 5 §5.8](../core/ch5-pcie.md#58-data-link-layer)). **MIPI M-PHY** is the physical layer: differential serial lanes in speed grades called **Gears** (HS-G1 … HS-G6) — the counterpart of PCIe generations. Two service access points split the planes cleanly: **UIC_SAP** carries UPIUs (data), **UIO_SAP** carries control (power modes, attributes).

---

## B.3 UPIU: the UFS packet ⭐

**UPIU (UFS Protocol Information Unit)** is UFS's packet — the analog of an NVMe command entry or a SATA FIS. The command flow mirrors [Chapter 6](../core/ch6-nvme.md#62-nvme-overview-the-command-model)'s dance in UPIU vocabulary:

1. Host sends a **Command UPIU** (the SCSI command: opcode, LBA, length).
2. Writes: host sends **Data Out UPIUs**; reads: device sends **Data In UPIUs**.
3. For writes, the device paces the host with **Ready-To-Transfer (RTT) UPIUs** — flow control, the DMA-Setup handshake of [Ch 2 §2.1.1](../core/ch2-controllers-afa.md#211-front-end) reborn.
4. Device closes with a **Response UPIU** — the completion entry.

Query Request/Response UPIUs read and write descriptors/attributes; task-management UPIUs handle aborts. If the NVMe SQ/CQ lifecycle made sense, this is the same choreography with different costumes.

**Format:** a fixed **basic header** (transaction type, flags, **LUN**, **Task Tag**, lengths) + type-specific fields + optional data segment. The LUN field selects the Logical Unit (§B.4); the Task Tag identifies the command in the queue, enabling the out-of-order completion eMMC never had. UFS 4.0's UniPro 2.0 raised the max payload to **1144 bytes**, trimming per-transfer overhead — the MPS-tuning lesson of [Ch 5 §5.11](../core/ch5-pcie.md#511-max-payload-size-max-read-request-size) in miniature.

---

## B.4 Logical Units ⭐

A UFS device divides its storage into **Logical Units (LUs)** — independent spaces, each with its own LBA range. **This is the SCSI rendition of NVMe namespaces** ([Ch 6 §6.7](../core/ch6-nvme.md#67-namespaces)): carve one flash pool into several logical disks; every command's UPIU header names its target LU, as every NVMe command names an NSID.

Up to **8 general-purpose LUs**, plus **Well-Known LUs** with fixed roles:

- **Boot LU A/B** — boot code the SoC reads at power-on; two copies for safe A/B firmware updates.
- **RPMB LU** — the authenticated secure region (§B.5).
- **Device LU / Report LUNs** — management and enumeration.

LUs can carry different configurations — provisioning, WriteBooster settings, reliability options — the "one device, several disks with different personalities" flexibility, exploited hard in automotive (boot / OS / data partitions with different guarantees).

---

## B.5 RPMB: Replay-Protected Memory Block ⭐

A small **authenticated** storage region (inherited from eMMC) for data an attacker must never tamper with: encryption keys, secure counters, DRM state.

**The threat: a replay attack.** An attacker records a legitimate bus write — say, "set failed-PIN-counter = 0" — and *replays* the recording later to reset security state after their failed guesses. RPMB defeats the whole class:

- A **secret key**, fused in at manufacture, is shared by host and device.
- Every access is signed with an **HMAC-SHA256 MAC** over the data — unsigned or wrongly-signed commands are rejected (defeats spoofing).
- A monotonic **write counter** rides in every authenticated write; the host must echo the current value, and stale counters are refused (**defeats replay** — a recorded message carries yesterday's counter).
- Reads return a host-supplied **nonce** in the signed response — proving freshness and authenticity.

Conceptually, RPMB extends [Ch 6 §6.6](../core/ch6-nvme.md#66-end-to-end-data-protection)'s integrity mindset from the *accidental* to the *adversarial*: PI's CRC + Reference Tag guard against corruption; RPMB's MAC + counter + nonce guard against malice. 🔬 Key-provisioning and attestation schemes here are patent-active as mobile security and automotive safety requirements tighten.

---

## B.6 UFS low power

Battery devices make power management existential — the consumer-drive priority from [Ch 1 §1.5.5](../core/ch1-overview.md#155-power-thermals), intensified. The states live mostly in the M-PHY/UniPro layers:

- **Active** — full high-speed bursts.
- **STALL / SLEEP** — light line-states between bursts; cheap to enter and leave.
- **HIBERN8** — the deep link state: M-PHY torn down to near-zero power (~30 µW in optimized designs), quick to re-establish. UFS's **DevSleep**.
- **Deep Sleep** (UFS 3.1+) — deeper still, device-level, for maximum standby savings.

The trade-off is the same one from Ch 1 and the DevSleep tests of [Ch 7 §7.5](../core/ch7-testing.md#75-devsleep-testing): sleep eagerly to save battery, but not so eagerly that wake latency stings. UFS 4.0 sharpened the wake side with **HS-LSS** (high-speed link startup): the link now trains up at HS-G1 (1,248 Mbps) instead of the old PWM-G1 (3–9 Mbps) crawl — ~70% faster link startup.

---

## B.7 WriteBooster ⭐⭐

**WriteBooster is UFS's name for the SLC cache of [Ch 4 §4.8](../core/ch4-ftl.md#48-slc-cache).** Identical mechanism: run part of the TLC/QLC array in **pseudo-SLC mode** as a fast, rugged burst buffer, migrating to native storage later. The UFS-specific dressing:

- **Host-configurable and host-enabled** — the host sizes the buffer at configuration and can toggle WriteBooster dynamically (on for the big app install or 8K capture, off otherwise).
- **Two provisioning modes** — dedicated space, or borrowed from user area (Ch 4's "dynamic" flavor: a near-empty device gets a huge buffer).
- **Burst then collapse** — a full buffer drops writes to native TLC/QLC speed, exactly the behavior [Ch 7 §7.10](../core/ch7-testing.md#710-performance-testing-the-snia-methodology)'s steady-state discipline exists to expose. Mobile benchmarks must separate burst from sustained, same as SSD benchmarks.
- **Host-directed flush** — the host schedules buffer flushes into idle/hibernate windows, a host-managed version of Ch 4's background migration.

UFS 4.1 extended it 🔬: **buffer resizing** and **partial/pinned flush** — flush the cold data, *pin* the hot data in the fast SLC region. This host↔device choreography of the cache is an active patent area.

---

## B.8 HPB: Host Performance Booster ⭐⭐

**HPB is UFS's answer to the DRAM-less problem of [Ch 4 §4.2.2](../core/ch4-ftl.md#422-how-mapping-works-and-the-dram-question) — a specialized cousin of HMB.** Recall the wound: no DRAM → the L2P map lives in flash → a random read on a cache miss costs **two flash accesses** (map, then data). Phones are the ultimate DRAM-less environment, so:

- The **host caches slices of the device's L2P table in host memory.**
- On a read, the host looks up the physical address itself and sends it **with the read command** (HPB READ). The device skips its own map lookup and goes straight to the flash — the second access evaporates.
- Result: dramatically faster random reads — precisely the workload phones live on (app launches).

The distinction from HMB worth savoring: **HMB lends the device generic memory** (the device does what it likes with it); **HPB makes the host an active participant in address translation** (it hands the device a physical-address hint). That's a quiet step toward the **host-managed FTL** of [Ch 4 §4.10–4.11](../core/ch4-ftl.md#410-host-based-ftl) — the host absorbing a slice of the mapping work. Two operating modes (Host Control / Device Control) decide who chooses which L2P regions get cached. 🔬 HPB caching and prefetch policies are patent-active; the feature has its own JEDEC extension (JESD220-3).

---

## B.9 Modern developments: UFS 4.1 and 5.0

**The version ladder:**

| Version | Published | PHY / UniPro | Per-lane | 2-lane effective | Notes |
|---|---|---|---|---|---|
| 3.1 | 2020 | HS-G4 | ~11.6 Gbps | ~2.1 GB/s | previous mainstream |
| 4.0 | Aug 2022 | M-PHY 5.0 / HS-G5, UniPro 2.0 | 23.2 Gbps | ~4.2 GB/s | doubled 3.1 |
| 4.1 | JESD220G, published Jan 2025 | same PHY as 4.0 | 23.2 Gbps | ~4.2–4.3 GB/s | feature refresh (below) |
| 5.0 | JESD220H, Feb 2026 | M-PHY 6.0 / HS-G6, UniPro 3.0 | ~46.6 Gbps | up to ~10.8 GB/s read | mass production late 2026 |

Per JEDEC and vendor announcements: UFS 4.1 keeps 4.0's hardware compatibility while refreshing features; UFS 5.0 references M-PHY 6.0/UniPro 3.0, with Samsung citing sequential reads to **10.8 GB/s** and writes to 9.5 GB/s — flagship-phone storage overtaking the PCIe Gen4 SSDs in most laptops — with first phones expected around 2027.

**UFS 4.1's additions, mapped to what you know:**

- **ZUFS (Zoned UFS)** — the ZNS concept of [Ch 4 §4.11](../core/ch4-ftl.md#411-modern-developments-from-sdf-to-zns-and-fdp), brought to mobile: host/device collaborate on zone placement to cut write amplification. The WA-reduction lineage (SDF → ZNS → FDP) now includes phones.
- **Host-initiated defragmentation** — the host schedules defrag (reportedly up to ~60% read-speed recovery on cluttered devices); a host-managed maintenance op in the spirit of [Ch 4 §4.3.4](../core/ch4-ftl.md#434-when-gc-runs)'s host-managed GC.
- **Pinned WriteBooster** (§B.7) — ~30% faster random reads on pinned hot data.
- **MCQ (Multi-Circular Queue)** — *straight out of NVMe*: multiple command queues instead of one, parallel submission across cores — [Ch 6 §6.3](../core/ch6-nvme.md#63-the-three-treasures-in-detail)'s model arriving in UFS. The clearest sign of the two stacks converging.
- **QLC support** and boot-security enhancements.

**UFS 5.0's additions:** **Inline Hashing** (hardware data-integrity hashing on the fly — a security escalation beyond RPMB), **Link Equalization** (signal-integrity machinery to hold HS-G6 stable — the same wall that pushed PCIe Gen6 to PAM4+FEC in [Ch 5 §5.14](../core/ch5-pcie.md#514-modern-developments-pcie-40-70)), and ~2.5× UFS 4.x bandwidth aimed at on-device generative AI, 8K video, and console-class mobile gaming.

**The through-line:** UFS is recapitulating the SSD/NVMe story one step behind and mobile-optimized — serial+queued (SATA→NVMe), multi-queue (MCQ ≈ NVMe queues), host-assisted memory (HPB ≈ HMB), host-managed placement (ZUFS ≈ ZNS), and now PHY signal-integrity walls (HS-G6 ≈ PAM4). Understand the SSD stack and UFS is the same knowledge under mobile constraints: power, package, cost.

---

## Key takeaways

1. **UFS = managed NAND speaking SCSI over a MIPI serial link** — an SSD's firmware in a phone package, with the host spared all flash complexity.
2. **eMMC → UFS replayed SATA/AHCI → PCIe/NVMe**: serial + full-duplex + deep queues, because the media stopped being the bottleneck.
3. **The stack maps 1:1 onto what you know**: UAP ≈ NVMe layer, UTP/UPIU ≈ Transaction Layer/TLP, UniPro ≈ Data Link, M-PHY Gears ≈ PCIe generations.
4. **RPMB adds the adversarial dimension**: MAC + monotonic counter + nonce vs spoofing and replay — security's answer to §6.6's integrity bodyguard.
5. **WriteBooster is the SLC cache; HPB is HMB sharpened to the L2P** — and HPB's host-side lookup is a quiet step toward host-managed FTL.
6. **UFS 4.1/5.0 close the loop**: MCQ, ZUFS, host defrag, link equalization — the NVMe/ZNS/PAM4 ideas, arriving in mobile on schedule.

---

## Key vocabulary

| Term | Meaning |
|---|---|
| UFS | Universal Flash Storage (JEDEC mobile storage standard) |
| eMMC | predecessor; parallel, half-duplex, no queuing |
| managed NAND | controller + flash + firmware in one package |
| MIPI | consortium behind mobile interface specs |
| M-PHY | UFS physical layer (differential serial, "Gears") |
| UniPro | UFS link/transport layer (flow control, retransmit) |
| HS-Gear (G1–G6) | M-PHY speed grades (≈ PCIe generations) |
| UTP | UFS Transport Protocol (makes UPIUs) |
| UPIU | UFS Protocol Information Unit (the packet) |
| UIC | UFS Interconnect (UniPro + M-PHY) |
| Descriptor / Attribute / Flag | device config metadata |
| Logical Unit (LU) | addressable storage space (≈ NVMe Namespace / SCSI LUN) |
| Well-Known LU | special LUs: Boot, RPMB, Device, Report |
| RPMB | Replay-Protected Memory Block (authenticated secure region) |
| MAC / HMAC | message authentication code (signs RPMB access) |
| replay attack | re-sending a recorded message to undo a security state |
| WriteBooster | UFS pseudo-SLC turbo write buffer (≈ SLC Cache, Ch4) |
| HPB | Host Performance Booster (host caches L2P; ≈ HMB, Ch4) |
| L2P | logical-to-physical mapping table (Ch4) |
| HIBERN8 | deep low-power M-PHY link state (≈ DevSleep) |
| MCQ | Multi-Circular Queue (≈ NVMe multi-queue) |
| ZUFS | Zoned UFS (≈ ZNS for mobile) |
| Inline Hashing | UFS 5.0 hardware integrity hashing |

---

## Check yourself

1. UFS replaced eMMC for the same fundamental reason PCIe+NVMe replaced SATA+AHCI. State the two-part reason (signaling and queuing).
2. What does "managed NAND" mean, and why does it mean a UFS device runs essentially all the firmware from Chapters 3–4?
3. Name the four layers of the UFS stack top to bottom, and give the PCIe/NVMe analog of each.
4. UFS's command layer is based on which older standard, and where in this book did you first meet it?
5. What is a UPIU, and what earlier constructs (name two) is it directly analogous to?
6. A UFS Logical Unit is the SCSI equivalent of which NVMe concept? What do both let you do?
7. Explain a replay attack and the two RPMB mechanisms that defeat spoofing and replay respectively.
8. WriteBooster is UFS's name for which Chapter 4 feature? Describe the "burst then collapse" behavior and why benchmarks must account for it.
9. HPB solves which specific DRAM-less problem from Chapter 4, and how does it differ from HMB? (What does the host hand the device that HMB does not?)
10. What is HIBERN8, and which SSD power state is it analogous to?
11. **(Modern)** MCQ, HPB, and ZUFS each mirror a concept from the NVMe/SSD world. Name the analog of each.
12. **(Modern)** UFS 5.0 adds Link Equalization at HS-G6. Which PCIe development from Chapter 5 does that echo, and what shared underlying problem drives both?

---

??? info "📖 Provenance"

    UFS is a 2nd-edition topic (their Chapter 10), not covered in the 1st
    edition of《深入淺出SSD》. This supplement reconstructs it from the JEDEC
    UFS standards (JESD220 family) and current industry sources, organized
    around the concept mapping to this site's core chapters.

*Next: [Supplement C — Flash File Systems](c-flash-file-systems.md): the layer above the drive, where EXT4 and the log-structured F2FS meet everything Chapter 4 taught — from the host side.*
