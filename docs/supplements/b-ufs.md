---
title: "Supp B — UFS"
tags:
  - ufs
  - writebooster
  - hpb
  - queues
  - zns
source_anchor: "supplement (no book chapter)"
textbook: v2
---

# Supplement B — UFS (Universal Flash Storage)

**Universal Flash Storage (UFS)** is the high-performance storage standard for phones, tablets, cars and edge-AI devices — in effect *the NVMe (Non-Volatile Memory Express) of the mobile world*. (The book's 2nd edition gives it a chapter; this supplement reconstructs the topic from the JEDEC (memory standards body) standards and current industry sources.) A UFS device is **managed NAND flash** — controller + flash + firmware in one fingernail-sized package — running the *same* flash translation layer (FTL), error correction (ECC), wear-leveling and SLC-cache machinery as a solid-state drive (SSD), wrapped in a mobile protocol stack.

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
    - **UFS 4.x / 5.0** — MCQ, ZUFS, defrag, and the 10.8 GB/s era (§B.9)

    Short on time? §B.1, §B.2, §B.7, §B.8 carry the most transfer.

---

## B.1 What UFS is: the eMMC successor ⭐

UFS is a JEDEC standard that replaced **eMMC (embedded MultiMediaCard)** — and the reason is *exactly* the story of Serial AT Attachment (SATA) giving way to PCIe (Peripheral Component Interconnect Express) and NVMe in [Chapters 5–6](../core/ch5-pcie.md), transplanted to phones:

- **eMMC is parallel and half-duplex** — a shared bus, one direction at a time (SATA's walkie-talkie, in mobile form), topping out around 400 MB/s while mobile processors and cameras got hungry. And it had no real command queuing — the problem of AHCI (Advanced Host Controller Interface) again.
- **UFS is serial and full-duplex** — separate differential lanes transmitting simultaneously (PCIe's dual-simplex), plus **deep command queuing** with out-of-order completion.

The mobile world re-ran the evolution this site already covered: a parallel, half-duplex, one-command-at-a-time interface built for slow media gave way to a serial, full-duplex, deeply queued one built for fast flash.

**Inside a UFS package** (roughly 1 × 1.3 cm and about a millimetre thick): a controller running a full FTL — mapping, garbage collection, wear leveling, bad blocks, LDPC (low-density parity-check) error correction; everything from [Chapters 3](../core/ch3-nand-flash.md)–[4](../core/ch4-ftl.md) and [Supplement A](a-ecc-coding-theory.md) — plus the NAND itself. The host system-on-chip (SoC) sends high-level reads and writes; the device shoulders all flash complexity. Same value proposition as an SSD, phone-sized. (Kioxia's UFS parts, for instance, use the same BiCS FLASH (Bit Cost Scalable) 3D NAND family as its SSDs — the firmware disciplines are siblings.)

**One key architectural fact:** UFS's command layer is built on **SCSI (Small Computer System Interface)** — a subset of the SCSI command set. That connects straight to [Chapter 2](../core/ch2-controllers-afa.md#211-front-end), where SAS (Serial Attached SCSI) carried SCSI commands over its Serial SCSI Protocol. At the application layer, a UFS device *is* a SCSI device — which is why its logical structure (Logical Units) reads as SCSI/SAS heritage even as its queuing turns NVMe-like (§B.9).

---

## B.2 The UFS protocol stack ⭐⭐

Layered, like PCIe — each layer serving the one above:

![Four stacked layers: the application layer (UAP), the transport layer (UTP), and the interconnect layer (UIC) holding MIPI UniPro above MIPI M-PHY; beside each, its PCIe or NVMe counterpart: the NVMe command set, the Transaction Layer, the Data Link Layer and the Physical Layer](../assets/figures/supp-b/ufs-stack.svg){ .sdd-fig }
/// figure-caption
The UFS stack beside its PCIe/NVMe counterparts. Host and device each run the whole stack; only the physical lanes join them.
///

The same three-tier idea as PCIe and NVMe: a command layer, the UFS application layer (UAP), ≈ NVMe; a packetizing transport, the UFS Transport Protocol layer (UTP), which wraps each command in a UPIU (UFS Protocol Information Unit) as the PCIe Transaction Layer wraps each request in a packet; and a link-plus-physical foundation, the UFS InterConnect layer (UIC): MIPI UniPro (Unified Protocol) plus MIPI M-PHY, ≈ the Data Link and Physical layers. The building blocks come from the **MIPI Alliance**, the consortium behind mobile interface standards.

**B.2.1 — Application layer.** The SCSI-subset command set (READ(10)/(16), WRITE, SYNCHRONIZE CACHE, and UNMAP (Trim's SCSI name — the Trim/Deallocate of [Ch 4 §4.4](../core/ch4-ftl.md#44-trim))), plus the **Device Manager** (configuration via **Descriptors, Attributes, Flags** — the Identify/Get-Set-Features analog) and the **Task Manager** (abort/query queue tasks).

**B.2.2 — Transport layer (UTP).** Wraps commands, data, and responses into **UPIUs** (§B.3) — precisely "NVMe hands 64-byte commands to PCIe, which wraps them in transaction-layer packets," one ecosystem over.

**B.2.3 — Interconnect (UniPro + M-PHY).** **MIPI UniPro** is the link layer: reliable delivery, **flow control, retransmission**, error handling — UFS's counterpart of PCIe's acknowledgment/negative-acknowledgment (ACK/NAK) protocol and credits ([Ch 5 §5.8](../core/ch5-pcie.md#58-data-link-layer)). **MIPI M-PHY** is the physical layer (PHY): differential serial lanes in speed grades called **Gears** (HS-G1 … HS-G6) — the counterpart of PCIe generations. Two service access points split the planes cleanly: **UIC_SAP** carries UPIUs (data), **UIO_SAP** carries control (power modes, attributes).

---

## B.3 UPIU: the UFS packet ⭐

**UPIU (UFS Protocol Information Unit)** is UFS's packet — the analog of an NVMe command entry or a SATA Frame Information Structure (FIS). The command flow mirrors [Chapter 6](../core/ch6-nvme.md#62-nvme-overview-the-command-model)'s dance in UPIU vocabulary:

1. Host sends a **Command UPIU** (the SCSI command: opcode, logical block address (LBA), length).
2. Writes: host sends **Data Out UPIUs**; reads: device sends **Data In UPIUs**.
3. For writes, the device paces the host with **Ready-To-Transfer (RTT) UPIUs** — flow control, the DMA-Setup handshake of [Ch 2 §2.1.1](../core/ch2-controllers-afa.md#211-front-end) reborn.
4. Device closes with a **Response UPIU** — the completion entry.

Query Request/Response UPIUs read and write descriptors/attributes; task-management UPIUs handle aborts. If the NVMe submission/completion-queue lifecycle made sense, this is the same choreography with different costumes.

**Format:** a fixed **basic header** (transaction type, flags, logical unit number (LUN), **Task Tag**, lengths) + type-specific fields + optional data segment. The LUN field selects the logical unit (LU, §B.4); the Task Tag identifies the command in the queue, enabling the out-of-order completion eMMC never had. UniPro 2.0, used from UFS 4.0, raised the maximum payload to **1144 bytes**, trimming per-transfer overhead — the MPS-tuning lesson of [Ch 5 §5.11](../core/ch5-pcie.md#511-max-payload-size-max-read-request-size) in miniature.

---

## B.4 Logical Units ⭐

A UFS device divides its storage into **Logical Units (LUs)** — independent spaces, each with its own LBA range. **This is the SCSI rendition of NVMe namespaces** ([Ch 6 §6.7](../core/ch6-nvme.md#67-namespaces)): carve one flash pool into several logical disks; every command's UPIU header names its target LU, as every NVMe command names a namespace identifier (NSID).

Up to **8 general-purpose LUs**, plus **Well-Known LUs** with fixed roles:

- **Boot LU A/B** — boot code the SoC reads at power-on; two copies for safe A/B firmware updates.
- **RPMB LU** — the Replay Protected Memory Block, an authenticated secure region (§B.5).
- **Device LU / Report LUNs** — management and enumeration.

LUs can carry different configurations — provisioning, WriteBooster settings, reliability options — the "one device, several disks with different personalities" flexibility, exploited hard in automotive (boot, operating-system and data partitions with different guarantees).

---

## B.5 RPMB: Replay-Protected Memory Block ⭐

A small **authenticated** storage region (inherited from eMMC) for data an attacker must never tamper with: encryption keys, secure counters, digital-rights state.

**The threat: a replay attack.** An attacker records a legitimate bus write — say, "set failed-PIN-counter = 0" — and *replays* the recording later to reset security state after their failed guesses. RPMB defeats the whole class:

- A **secret key**, programmed once into the device, is shared by host and device.
- Every access is signed with an **HMAC-SHA256** message authentication code over the data — unsigned or wrongly-signed commands are rejected (defeats spoofing).
- A monotonic **write counter** rides in every authenticated write; the host must echo the current value, and stale counters are refused (**defeats replay** — a recorded message carries yesterday's counter).
- Reads return a host-supplied **nonce** in the signed response — proving freshness and authenticity.

Conceptually, RPMB extends [Ch 6 §6.6](../core/ch6-nvme.md#66-end-to-end-data-protection)'s integrity mindset from the *accidental* to the *adversarial*: Protection Information (PI) — a cyclic redundancy check (CRC) plus a Reference Tag — guards against corruption; RPMB's MAC + counter + nonce guard against malice. 🔬 Key-provisioning and attestation schemes here are patent-active as mobile security and automotive safety requirements tighten.

---

## B.6 UFS low power

Battery devices make power management existential — the consumer-drive priority from [Ch 1 §1.5.5](../core/ch1-overview.md#155-power-thermals), intensified. The states live mostly in the M-PHY/UniPro layers:

- **Active** — full high-speed bursts.
- **STALL / SLEEP** — light line-states between bursts; cheap to enter and leave.
- **HIBERN8 (hibernate)** — the deep link state: M-PHY torn down to near-zero power (microwatts in optimized designs), quick to re-establish. UFS's counterpart of SATA's Device Sleep (DevSleep).
- **Deep Sleep** (UFS 3.1+) — deeper still, device-level, for maximum standby savings.

The trade-off is the same one from Ch 1 and the DevSleep tests of [Ch 7 §7.5](../core/ch7-testing.md#75-devsleep-testing): sleep eagerly to save battery, but not so eagerly that wake latency stings. UFS 4.0 sharpened the wake side with **HS-LSS** (high-speed link startup): the link trains at HS-G1 (1,248 Mbps) instead of the old PWM-G1 (3–9 Mbps) crawl, so it comes up much faster, and UniPro 3.0 (UFS 5.0) makes high-speed startup mandatory.

---

## B.7 WriteBooster ⭐⭐

**WriteBooster is UFS's name for the single-level-cell (SLC) cache of [Ch 4 §4.8](../core/ch4-ftl.md#48-slc-cache).** Identical mechanism: run part of the triple-level (TLC) or quad-level (QLC) array in **pseudo-SLC mode** as a fast, rugged burst buffer, migrating to native storage later. The UFS-specific dressing:

- **Host-configurable and host-enabled** — the host sizes the buffer at configuration and can toggle WriteBooster dynamically (on for the big app install or 8K capture, off otherwise).
- **Two provisioning modes** — dedicated space, or borrowed from user area (Ch 4's "dynamic" flavor: a near-empty device gets a huge buffer).
- **Burst then collapse** — a full buffer drops writes to native TLC/QLC speed, exactly the behavior [Ch 7 §7.10](../core/ch7-testing.md#710-performance-testing-the-snia-methodology)'s steady-state discipline exists to expose. Mobile benchmarks must separate burst from sustained, same as SSD benchmarks.
- **Host-directed flush** — the host schedules buffer flushes into idle/hibernate windows, a host-managed version of Ch 4's background migration.

UFS 4.1 extended it 🔬: the host can ask the device to **resize the buffer**, **pin** hot data in the fast SLC region, and **flush more selectively** — move the cold data out, keep the hot data in. This host↔device choreography of the cache is an active patent area.

---

## B.8 HPB: Host Performance Booster ⭐⭐

**HPB (Host Performance Booster) is UFS's answer to the DRAM-less problem of [Ch 4 §4.2.2](../core/ch4-ftl.md#422-how-mapping-works-and-the-dram-question) — a specialized cousin of HMB (Host Memory Buffer).** Recall the wound: with no DRAM (dynamic random-access memory) on the device, the logical-to-physical (L2P) map lives in flash, so a random read that misses the controller's small map cache costs **two flash accesses** (map, then data). Phones are the ultimate DRAM-less environment, so:

- The **host caches slices of the device's L2P table in host memory.**
- On a read, the host looks up the physical address itself and sends it **with the read command** (HPB READ). The device skips its own map lookup and goes straight to the flash — the second access evaporates. (The device still checks that the hint is current, because the host's copy can go stale after the device moves data.)
- Result: dramatically faster random reads — precisely the workload phones live on (app launches).

![Two timelines of one random read. Without HPB: a link transfer, a flash read of the map, a flash read of the data, a link transfer. With HPB: a tiny host map lookup, a link transfer, one flash read of the data, a link transfer, finishing one flash read sooner](../assets/figures/supp-b/hpb.svg){ .sdd-fig }
/// figure-caption
One random read with and without HPB, not to scale. On a map-cache miss the device must read its map from flash before the data; with HPB the host's lookup in its own memory takes a fraction of a microsecond and removes that first flash read.
///

The distinction from HMB worth savoring: **HMB lends the device generic memory** (the device does what it likes with it); **HPB makes the host an active participant in address translation** (it hands the device a physical-address hint). That's a quiet step toward the **host-managed FTL** of [Ch 4 §4.10–4.11](../core/ch4-ftl.md#410-host-based-ftl) — the host absorbing a slice of the mapping work. Two operating modes (Host Control / Device Control) decide who chooses which L2P regions get cached. 🔬 HPB caching and prefetch policies are patent-active; the feature has its own JEDEC extension (JESD220-3).

**Where HPB stands (2026).** HPB never became standard practice. Android vendor kernels carried it for a few years, but mainline Linux removed its HPB support in 2023, noting that interest had faded and that JEDEC was finishing a successor. The idea, the host helping with address translation, lives on in the host-assisted features of §B.9.

---

## B.9 Modern developments: UFS 4.1 and 5.0

**The version ladder:**

| Version | Published | PHY / UniPro | Per-lane | 2-lane effective | Notes |
|---|---|---|---|---|---|
| 3.1 | Jan 2020 | HS-G4 | ~11.6 Gbps | ~2.1 GB/s | WriteBooster, Deep Sleep, HPB |
| 4.0 | Aug 2022 | M-PHY 5.0 / HS-G5, UniPro 2.0 | 23.2 Gbps | ~4.2 GB/s | doubled 3.1; MCQ |
| 4.1 | Jan 2025 (JESD220G) | same PHY as 4.0 | 23.2 Gbps | ~4.2–4.3 GB/s | feature refresh (below) |
| 5.0 | Feb 2026 (JESD220H) | M-PHY 6.0 / HS-G6 (PAM4), UniPro 3.0 | ~46.6 Gbps | up to ~10.8 GB/s | first parts late 2026, phones 2027 |

Per JEDEC and vendor announcements: UFS 4.1 keeps 4.0's hardware compatibility while refreshing features. UFS 5.0 (JESD220H, published February 2026) builds on M-PHY 6.0 and UniPro 3.0, whose new HS-G6 gear switches to 4-level pulse-amplitude modulation (PAM4) for about 46.6 Gbps per lane, and it still works with UFS 4.x hardware. Samsung unveiled a UFS 5.0 part in June 2026 with sequential reads to **10.8 GB/s** and writes to 9.5 GB/s — flagship-phone storage overtaking the PCIe Gen4 SSDs in most laptops — and planned mass production for the end of 2026, with phones expected in 2027.

**UFS 4.0 brought the queue model over: MCQ (Multi-Circular Queue).** Straight out of NVMe, the companion host-controller standard replaced the single command list with multiple submission and completion queues, so each processor core can submit in parallel — [Ch 6 §6.3](../core/ch6-nvme.md#63-the-three-treasures-in-detail)'s model arriving in UFS, and the clearest sign of the two stacks converging.

**UFS 4.1's additions, mapped to what you know:**

- **ZUFS (Zoned UFS)** — the Zoned Namespaces (ZNS) concept of [Ch 4 §4.11](../core/ch4-ftl.md#411-modern-developments-from-sdf-to-zns-and-fdp), brought to mobile: host and device collaborate on zone placement to cut write amplification. The lineage of host-guided placement — software-defined flash, then ZNS, then Flexible Data Placement (FDP) — now includes phones.
- **Host-initiated defragmentation** — the host schedules the defragmentation of scattered data to restore read speed and, per Kioxia, can have the device postpone its garbage collection through critical moments; a host-managed maintenance operation in the spirit of [Ch 4 §4.3.4](../core/ch4-ftl.md#434-when-gc-runs)'s host-managed garbage collection.
- **WriteBooster resizing, pinning and finer flushing** (§B.7) — hot data kept in the fast SLC region.
- **Stronger RPMB authentication** and other security refinements.

**UFS 5.0's additions:** **Inline Hashing** (hardware data-integrity hashing on the fly — a security step beyond RPMB), **link equalization** (signal-integrity machinery to keep HS-G6 stable), and the move to PAM4 itself — the same wall that pushed PCIe 6.0 to PAM4 with forward error correction (FEC) in [Ch 5 §5.14](../core/ch5-pcie.md#514-modern-developments-pcie-40-70) — for about 2.5× the bandwidth of UFS 4.x, aimed at on-device generative AI, 8K video, and console-class mobile gaming.

**The through-line:** UFS is recapitulating the SSD/NVMe story one step behind and mobile-optimized — serial+queued (SATA→NVMe), multi-queue (MCQ ≈ NVMe queues), host-assisted memory (HPB ≈ HMB), host-managed placement (ZUFS ≈ ZNS), and now the PHY signal-integrity wall (HS-G6 adopting PAM4, as PCIe 6.0 did). Understand the SSD stack and UFS is the same knowledge under mobile constraints: power, package, cost.

---

## Key takeaways

1. **UFS = managed NAND speaking SCSI over a MIPI serial link** — an SSD's firmware in a phone package, with the host spared all flash complexity.
2. **eMMC → UFS replayed SATA/AHCI → PCIe/NVMe**: serial + full-duplex + deep queues, because the media stopped being the bottleneck.
3. **The stack maps 1:1 onto what you know**: UAP ≈ NVMe layer, UTP and its UPIUs ≈ the Transaction Layer and its packets, UniPro ≈ Data Link, M-PHY Gears ≈ PCIe generations.
4. **RPMB adds the adversarial dimension**: MAC + monotonic counter + nonce vs spoofing and replay — security's answer to §6.6's integrity bodyguard.
5. **WriteBooster is the SLC cache; HPB is HMB sharpened to the L2P** — and HPB's host-side lookup was a step toward host-managed FTL, even though HPB itself has faded.
6. **UFS 4.x/5.0 close the loop**: MCQ, ZUFS, host defrag, PAM4 and link equalization — the NVMe/ZNS/PCIe ideas, arriving in mobile on schedule.

---

## Key vocabulary

| Term | 中文 | Meaning |
|---|---|---|
| Universal Flash Storage (UFS) | 通用閃存存儲（台：通用快閃儲存） | JEDEC's storage standard for phones and other mobile devices: managed NAND speaking SCSI over a MIPI serial link. → [§B.1](#b1-what-ufs-is-the-emmc-successor) |
| embedded MultiMediaCard (eMMC) | 嵌入式多媒體卡 | UFS's predecessor: a parallel, half-duplex bus with no real command queuing. → [§B.1](#b1-what-ufs-is-the-emmc-successor) |
| managed NAND | 管理型NAND | Controller, flash and firmware in one package, so the host never handles raw flash. → [§B.1](#b1-what-ufs-is-the-emmc-successor) |
| MIPI Alliance | MIPI聯盟 | The consortium that writes mobile interface standards, including UniPro and M-PHY. → [§B.2](#b2-the-ufs-protocol-stack) |
| M-PHY | M-PHY物理層（台：M-PHY實體層） | UFS's physical layer: differential serial lanes whose speed grade is the Gear. → [§B.2](#b2-the-ufs-protocol-stack) |
| UniPro | UniPro統一協議（台：UniPro統一協定） | UFS's link layer: reliable delivery with flow control and retransmission. → [§B.2](#b2-the-ufs-protocol-stack) |
| HS-Gear (G1–G6) | 高速檔位 | M-PHY's speed grades, the counterpart of PCIe generations; HS-G6 moves to PAM4. → [§B.2](#b2-the-ufs-protocol-stack) |
| UFS Transport Protocol (UTP) | UFS傳輸協議層（台：UFS傳輸協定層） | The layer that wraps commands, data and responses into UPIUs. → [§B.2](#b2-the-ufs-protocol-stack) |
| UFS InterConnect layer (UIC) | UFS互連層 | UniPro and M-PHY together, the link-plus-physical foundation of the stack. → [§B.2](#b2-the-ufs-protocol-stack) |
| Descriptor / Attribute / Flag | 描述符 / 屬性 / 標誌（台：描述元 / 屬性 / 旗標） | The three kinds of device configuration data, read and written with Query UPIUs. → [§B.2](#b2-the-ufs-protocol-stack) |
| UFS Protocol Information Unit (UPIU) | UFS協議信息單元（台：UFS協定資訊單元） | The UFS packet: a basic header naming the logical unit and task, then type-specific fields and optional data. → [§B.3](#b3-upiu-the-ufs-packet) |
| logical unit (LU) | 邏輯單元 | An independently addressed storage space with its own LBA range, UFS's counterpart of an NVMe namespace. → [§B.4](#b4-logical-units) |
| Well-Known LU | 知名邏輯單元 | A logical unit with a fixed role: Boot, RPMB, Device or Report LUNs. → [§B.4](#b4-logical-units) |
| Replay Protected Memory Block (RPMB) | 重放保護內存塊（台：重放保護記憶體區塊） | A small authenticated region whose writes need a valid MAC and the current write counter. → [§B.5](#b5-rpmb-replay-protected-memory-block) |
| message authentication code (MAC / HMAC) | 消息認證碼（台：訊息鑑別碼） | A keyed checksum proving that a message came from a key holder and was not altered; RPMB uses HMAC-SHA256. → [§B.5](#b5-rpmb-replay-protected-memory-block) |
| replay attack | 重放攻擊（台：重送攻擊） | Re-sending a recorded legitimate message later to undo a security state. → [§B.5](#b5-rpmb-replay-protected-memory-block) |
| HIBERN8 | 休眠狀態 | M-PHY's deep low-power link state, UFS's counterpart of DevSleep. → [§B.6](#b6-ufs-low-power) |
| WriteBooster | 寫入加速（WriteBooster） | UFS's host-configurable SLC cache: part of the TLC or QLC array run as a fast write buffer. → [§B.7](#b7-writebooster) |
| Host Performance Booster (HPB) | 主機性能加速（台：主機效能加速） | The host caches slices of the device's L2P map and sends the physical address with each read. → [§B.8](#b8-hpb-host-performance-booster) |
| logical-to-physical map (L2P) | 邏輯到物理映射表（台：邏輯至實體映射表） | The FTL's table from each logical address to the flash location that holds it. → [§B.8](#b8-hpb-host-performance-booster) |
| Multi-Circular Queue (MCQ) | 多循環隊列（台：多重環狀佇列） | UFS 4.0's multiple submission and completion queues, so each CPU core can submit in parallel. → [§B.9](#b9-modern-developments-ufs-41-and-50) |
| Zoned UFS (ZUFS) | 分區UFS | UFS 4.1's zoned storage, ZNS for mobile: host and device cooperate on data placement. → [§B.9](#b9-modern-developments-ufs-41-and-50) |
| host-initiated defragmentation | 主機發起的碎片整理（台：主機啟動的磁碟重組） | UFS 4.1's host-scheduled clean-up of scattered data to restore read speed. → [§B.9](#b9-modern-developments-ufs-41-and-50) |
| Inline Hashing | 內聯哈希（台：內嵌雜湊） | UFS 5.0's on-the-fly hardware hashing of data for integrity checking. → [§B.9](#b9-modern-developments-ufs-41-and-50) |

---

## Check yourself

1. UFS replaced eMMC for the same fundamental reason PCIe+NVMe replaced SATA+AHCI. State the two-part reason (signaling and queuing).

    ??? success "Answer"
        Signaling: eMMC is a parallel, half-duplex shared bus that moves data one direction at a time and tops out around 400 MB/s, while UFS uses serial, full-duplex differential lanes, as PCIe did. Queuing: eMMC handled essentially one command at a time, as AHCI's shallow model did, while UFS has deep command queues with out-of-order completion, as NVMe does. Once flash became fast, the interface rather than the media was the bottleneck. See [§B.1](#b1-what-ufs-is-the-emmc-successor).

2. What does "managed NAND" mean, and why does it mean a UFS device runs essentially all the firmware from Chapters 3–4?

    ??? success "Answer"
        The package holds a controller and firmware alongside the flash, and the host sends only logical reads and writes. Because the host never sees raw flash, the device must itself do everything raw flash needs: address mapping, garbage collection, wear leveling, bad-block management, error correction and the SLC cache. That is the firmware of Chapters 3–4 in a phone-sized package. See [§B.1](#b1-what-ufs-is-the-emmc-successor).

3. Name the four layers of the UFS stack top to bottom, and give the PCIe/NVMe analog of each.

    ??? success "Answer"
        The application layer (UAP) ≈ the NVMe command set; the transport layer (UTP), which builds UPIUs ≈ the PCIe Transaction Layer and its packets; UniPro, the link layer ≈ the PCIe Data Link Layer; and M-PHY, the physical layer ≈ the PCIe Physical Layer, with Gears in place of generations. UniPro and M-PHY together form the interconnect layer (UIC). See [§B.2](#b2-the-ufs-protocol-stack).

4. UFS's command layer is based on which older standard, and where in this book did you first meet it?

    ??? success "Answer"
        SCSI: UFS uses a subset of the SCSI command set (READ, WRITE, UNMAP and so on). It first appeared in Chapter 2's front-end discussion, where SAS carries SCSI commands. See [§B.1](#b1-what-ufs-is-the-emmc-successor).

5. What is a UPIU, and what earlier constructs (name two) is it directly analogous to?

    ??? success "Answer"
        The UFS packet: a basic header with the transaction type, flags, LUN, task tag and lengths, then type-specific fields and an optional data segment. It is the analog of an NVMe command entry and of a SATA FIS, and in its transport role it mirrors a PCIe transaction-layer packet. See [§B.3](#b3-upiu-the-ufs-packet).

6. A UFS Logical Unit is the SCSI equivalent of which NVMe concept? What do both let you do?

    ??? success "Answer"
        An NVMe namespace. Both carve one physical device into several independent logical disks, each with its own LBA range and named in every command (the LUN in the UPIU header, the NSID in an NVMe command), so partitions with different roles or settings can share one device. See [§B.4](#b4-logical-units).

7. Explain a replay attack and the two RPMB mechanisms that defeat spoofing and replay respectively.

    ??? success "Answer"
        A replay attack records a legitimate message, such as "reset the failed-PIN counter," and re-sends it later to undo a security state. The MAC defeats spoofing: every access is signed with HMAC-SHA256 under a key only host and device share, so forged or altered commands are rejected. The monotonic write counter defeats replay: every authenticated write must carry the current counter value, so a recorded message, which carries an old one, is refused. Reads add a host-chosen nonce to prove the response is fresh. See [§B.5](#b5-rpmb-replay-protected-memory-block).

8. WriteBooster is UFS's name for which Chapter 4 feature? Describe the "burst then collapse" behavior and why benchmarks must account for it.

    ??? success "Answer"
        The SLC cache. Writes land at SLC speed in a pseudo-SLC buffer until it fills, then drop to the native TLC or QLC speed until the buffer is flushed. A short benchmark that fits in the buffer measures only the burst, so an honest test runs long enough to fill it and reports sustained speed separately, as the steady-state method of Ch 7 §7.10 does for SSDs. See [§B.7](#b7-writebooster).

9. HPB solves which specific DRAM-less problem from Chapter 4, and how does it differ from HMB? (What does the host hand the device that HMB does not?)

    ??? success "Answer"
        Without device DRAM the L2P map lives in flash, so a random read that misses the controller's small map cache costs two flash reads, one for the map and one for the data. With HPB the host caches slices of the map in its own memory, looks up the physical address itself and sends it with the read, so the device skips the map read. HMB only lends the device host memory to use as it likes; HPB hands the device the physical address, making the host a participant in address translation. See [§B.8](#b8-hpb-host-performance-booster).

10. What is HIBERN8, and which SSD power state is it analogous to?

    ??? success "Answer"
        The deep low-power state of the M-PHY link: the link shuts down to near-zero power and comes back quickly when needed. It is the analog of SATA's DevSleep. See [§B.6](#b6-ufs-low-power).

11. **(Modern)** MCQ, HPB, and ZUFS each mirror a concept from the NVMe/SSD world. Name the analog of each.

    ??? success "Answer"
        MCQ mirrors NVMe's multiple submission and completion queues; HPB mirrors HMB, sharpened to the L2P map; ZUFS mirrors ZNS, Zoned Namespaces. See [§B.9](#b9-modern-developments-ufs-41-and-50).

12. **(Modern)** UFS 5.0 adds Link Equalization at HS-G6. Which PCIe development from Chapter 5 does that echo, and what shared underlying problem drives both?

    ??? success "Answer"
        PCIe 6.0's move to PAM4 signaling with forward error correction (Ch 5 §5.14); UFS 5.0's HS-G6 adopts PAM4 as well. The shared problem is signal integrity: at tens of gigabits per second per lane the channel attenuates and blurs the signal, so links need equalization, multi-level signaling and error correction to stay reliable. See [§B.9](#b9-modern-developments-ufs-41-and-50).

---

??? info "📖 Provenance"

    UFS is a 2nd-edition topic (their Chapter 10), not covered in the 1st
    edition of《深入淺出SSD》. This supplement reconstructs it from the JEDEC
    UFS standards (JESD220 family) and current industry sources, organized
    around the concept mapping to this site's core chapters. Its figures are
    original drawings.

??? info "🔎 Sources for the 2026 update"

    Sections B.6, B.8 and B.9 were brought up to date in November 2026 against these sources:

    - UFS 4.1 (JESD220G, January 2025): host-initiated defragmentation and WriteBooster resizing, pinning and flushing — [JEDEC via Business Wire](https://www.businesswire.com/news/home/20250108099318/en/JEDEC-Announces-Updates-to-Universal-Flash-Storage-UFS-and-Memory-Interface-Standards); postponed garbage collection — [Kioxia](https://www.kioxia.com/en-jp/business/news/2025/20250709-1.html)
    - UFS 5.0 (JESD220H, February 2026), with M-PHY 6.0's PAM4 HS-G6 gear and UniPro 3.0 — [JEDEC via Business Wire](https://www.businesswire.com/news/home/20260226710161/en/JEDEC-Announces-Updates-to-Universal-Flash-Storage-UFS-and-Memory-Interface-Standards), [MIPI Alliance](https://www.mipi.org/blog/laying-the-foundation-for-the-next-leap-in-flash-storage-new-versions-of-mipi-m-phy-and-unipro-offer-significant-performance-and-efficiency-gains)
    - Samsung's UFS 5.0 part (June 2026): 10.8 GB/s reads, 9.5 GB/s writes, production planned for late 2026 — [Samsung Newsroom](https://news.samsung.com/global/samsung-unveils-industrys-fastest-ufs-5-0-solution)
    - MCQ arrived with the UFS 4.0 host-controller standard — [Linaro](https://linaro.org/blog/multi-circular-queue-mcq-support-gets-added-to-the-ufs-subsystem)
    - Mainline Linux removes HPB support (2023) — [the kernel patch](https://lore.kernel.org/r/20230719165758.2787573-1-bvanassche@acm.org)

*Next: [Supplement C — Flash File Systems](c-flash-file-systems.md): the layer above the drive, where EXT4 (the fourth extended filesystem) and the log-structured Flash-Friendly File System (F2FS) meet everything Chapter 4 taught — from the host side.*
