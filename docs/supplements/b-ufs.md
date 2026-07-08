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

# SSD Deep Dive — Supplement B: UFS (Universal Flash Storage)
## English Study Companion (2nd-edition topic, reconstructed from standard references)

**Why this exists:** UFS is the **2nd edition's Chapter 10**, not in your PDFs. It's the high-performance storage standard for phones, tablets, automotive, and edge-AI devices — essentially "the NVMe of the mobile world." I've reconstructed it from the JEDEC UFS standards and current industry sources, in your usual guide format.

**Why it matters for you specifically:** Two reasons. First, **it's directly relevant to embedded/NAND firmware work** — UFS devices are managed-NAND products (controller + flash + firmware in one package), running the *same* FTL, ECC, wear-leveling, and SLC-cache logic you've studied, just wrapped in a mobile protocol. KIOXIA's UFS line runs on **BiCS FLASH** — the same 3D NAND family as the BiCS8 targets you're working with — so this is close to your actual bench work, not abstract. Second, for **patent research**, UFS's newer features (WriteBooster extensions, HPB, Zoned UFS, defrag) are actively filed and standardized.

**The pedagogical shortcut:** You already know ~80% of UFS. It's a *synthesis* of things you've learned — I'll teach it mostly by mapping each piece to a concept you already have:

| UFS piece | You already know it as… | Chapter |
|---|---|---|
| SCSI-based command set | SAS/SSP command layer | Ch2 |
| Serial full-duplex differential link | PCIe signaling | Ch5 |
| Command queuing / MCQ | NVMe SQ/CQ | Ch6 |
| UPIU (packet format) | NVMe command / SATA FIS | Ch2, Ch6 |
| Logical Units | NVMe Namespaces | Ch6 |
| WriteBooster | SLC Cache | Ch4 §4.8 |
| HPB (Host Performance Booster) | HMB (Host Memory Buffer) | Ch4 §4.2.3 |
| HIBERN8 / low-power states | SSD power states / DevSleep | Ch1 |
| Zoned UFS (ZUFS) | ZNS | Ch4/Ch6 supplements |

So this guide is less "new material" and more "here's the mobile packaging of what you already understand." Glossary and self-quiz at the end.

**The chapter's shape:** 10.1 what UFS is and why it replaced eMMC. 10.2 the layered protocol stack. 10.3 UPIU (the packet). 10.4 Logical Units. 10.5 RPMB (secure storage). 10.6 low power. 10.7 WriteBooster. 10.8 HPB. If your time is limited, **10.1, 10.2, 10.7, and 10.8** are the ones with the most transfer to your work.

---

## 10.1 What UFS is — the eMMC successor ⭐

**UFS (Universal Flash Storage)** is a JEDEC standard for embedded flash storage in mobile and compact devices. It replaced **eMMC (embedded MultiMediaCard)**, and the reason is *exactly* the SATA→PCIe story from Chapters 5–6, transplanted to phones:

- **eMMC is parallel and half-duplex** — a shared parallel bus where, like SATA, only one direction transmits at a time. It topped out around 400 MB/s and couldn't keep up as mobile SoCs and cameras got hungry.
- **UFS is serial and full-duplex** — separate differential send/receive lanes that transmit *simultaneously*, exactly like PCIe's dual-simplex from Chapter 5. Plus it adds **command queuing** (multiple outstanding commands, out-of-order completion) — which eMMC lacked, just as AHCI's single queue throttled early SSDs.

So the mobile world went through the same evolution you already studied: a parallel, half-duplex, single-command interface designed for slower media (eMMC ≈ the "AHCI+SATA" era) gave way to a serial, full-duplex, deeply-queued interface designed for fast flash (UFS ≈ the "NVMe+PCIe" era).

**What's in a UFS device (p. their 10.1).** Like an SSD, a UFS device is **managed NAND**: one BGA package containing a **controller + NAND flash + firmware**. The controller runs a full FTL — mapping, garbage collection, wear leveling, bad-block management, ECC (LDPC) — everything from Chapters 3–4 and the ECC supplement. The host SoC just sends high-level read/write commands; the device handles all the flash complexity. This is why UFS "reduces host workload and simplifies product development" — the same value proposition as an SSD, in a phone-sized package (~9×13mm, as thin as 0.85mm).

**The key architectural fact:** UFS's command layer is built on **SCSI** — it uses a subset of the SCSI command set (READ, WRITE, etc.). This connects straight back to Chapter 2, where you learned SAS carries SCSI commands via SSP. So UFS is, at the application layer, a SCSI device — which is why its logical structure (Logical Units, below) looks like SCSI/SAS rather than like NVMe namespaces, even though its *queuing* is becoming NVMe-like.

---

## 10.2 The UFS protocol stack ⭐⭐ *the core structure*

UFS is layered, and — like PCIe (Ch5) — each layer serves the one above. The stack, top to bottom *(p. their 10.2)*:

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
│   │  MIPI UniPro  (link + transport)    │   │  ← routing, flow control,
│   │  MIPI M-PHY   (physical layer)      │   │     retransmission, PHY
│   └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
        host  ⇄  UFS device (over M-PHY lanes)
```

Notice this is the *same three-tier idea* as PCIe+NVMe: a **command/application layer** (like NVMe), a **transport layer** that packetizes (UTP making UPIUs, like the Transaction Layer making TLPs), and a **physical/link layer** (UniPro+M-PHY, like PCIe's Data Link + Physical layers). The industry even borrowed the same building blocks from the **MIPI Alliance** (the consortium behind mobile interface standards).

### 10.2.1 Application layer (p. their 10.2.1)

Holds the **UFS command set** (a SCSI subset — READ(10)/(16), WRITE, SYNCHRONIZE CACHE, UNMAP [= Trim/Deallocate from Ch4/6], etc.), plus two managers:
- **Device Manager** — configures the device via **Descriptors, Attributes, and Flags** (structured metadata describing capabilities and settings — analogous to NVMe's Identify/Get-Set-Features from Ch6).
- **Task Manager** — handles command-queue management tasks (abort, clear, query task status).

### 10.2.2 Transport layer — UTP (p. their 10.2.2)

The **UFS Transport Protocol** turns commands, data, and responses into **UPIU** packets (§10.3) and hands them to the interconnect layer. This is the direct analog of "the NVMe layer hands 64-byte commands to PCIe, which wraps them in TLPs" from Chapter 6 — here, UTP wraps everything in UPIUs.

### 10.2.3 Interconnect layer — UniPro + M-PHY (p. their 10.2.3)

The physical transport, from two MIPI specs:
- **MIPI UniPro** (Unified Protocol) — the link/network layer: reliable delivery, **flow control**, **retransmission**, error handling, and routing. This is UFS's equivalent of PCIe's **Data Link Layer** (ACK/NAK, credit-based flow control from Ch5).
- **MIPI M-PHY** — the physical layer: differential serial signaling over lanes, organized in speed **"Gears."** This is UFS's equivalent of PCIe's **Physical Layer**. Speed grades are HS-Gear 1 through HS-Gear 5 (current mainstream), each roughly doubling the previous — directly parallel to PCIe generations.

Two "service access points" connect the layers: **UIC_SAP** carries UPIUs (the data path), and **UIO_SAP** issues control commands to UniPro/M-PHY (power-mode changes, attribute config) — a clean data-plane/control-plane split.

---

## 10.3 UPIU — the UFS packet ⭐

### 10.3.1 UPIU transactions (p. their 10.3.1)

**UPIU (UFS Protocol Information Unit)** is UFS's packet — the unit that carries a command, data, or response between host and device. It's the exact analog of an NVMe command entry (Ch6) or a SATA FIS (Ch2): a structured container that the transport layer builds and parses.

The command flow mirrors the NVMe 8-step dance from Chapter 6, in UPIU terms:
1. Host sends a **Command UPIU** (contains the SCSI command — e.g., READ with LBA and length).
2. For a write, host may send **Data Out UPIU(s)**; for a read, the device sends **Data In UPIU(s)**.
3. The device may send **Ready-To-Transfer (RTT) UPIU** for flow control (telling the host it's ready to receive write data — like the DMA-Setup handshake in the SATA FIS example from Ch2).
4. Device sends a **Response UPIU** with completion status (success/error) — the analog of the NVMe completion entry.

Other UPIU types handle queries (**Query Request/Response UPIU** — read/write descriptors and attributes), task management, and rejections. If you understood the NVMe SQ/CQ command lifecycle, UPIU transactions are the same choreography with different packet names.

### 10.3.2 UPIU format (p. their 10.3.2)

A UPIU has a **basic header** (fixed fields: transaction type, flags, LUN, Task Tag, command set type, data segment length) plus type-specific fields and an optional **data segment** (the payload). The header's **LUN** field selects which Logical Unit (§10.4); the **Task Tag** identifies the command in the queue (enabling out-of-order completion — the queuing that eMMC lacked). In UFS 4.0, **UniPro 2.0 raised the max payload to 1144 bytes**, lowering protocol overhead per transfer — a throughput optimization analogous to PCIe's Max Payload Size tuning from Chapter 5.

---

## 10.4 Logical Units (p. their 10.4) ⭐

A UFS device's storage is divided into **Logical Units (LUs)** — independent addressable spaces, each with its own LBA range 0…N−1. **This is the SCSI equivalent of NVMe Namespaces from Chapter 6 §6.7** — same concept (carve one physical flash space into multiple logical disks), different heritage (SCSI LUNs vs NVMe NSIDs). Every command's UPIU header specifies which LU it targets, exactly as NVMe commands specify an NSID.

UFS defines up to **8 general-purpose LUs** plus several **Well-Known LUs** with special roles:
- **Boot LU** (A/B) — holds boot code the SoC reads at power-on (two for A/B redundancy — safe firmware updates).
- **RPMB LU** — the secure Replay-Protected region (§10.5).
- **Device LU** — device-level management.
- **UFS Descriptor / Report LUNs** — configuration and enumeration.

LUs can have different configurations — different **write-booster** settings, different provisioning, and (in modern UFS) different characteristics — the same "one device, several disks with different features" flexibility the book highlighted for NVMe namespaces. Enterprise/automotive use cases exploit this to separate, say, boot/OS/data partitions with different reliability settings.

---

## 10.5 RPMB — Replay Protected Memory Block (p. their 10.5) ⭐ *the security feature*

**RPMB** is a small, special **authenticated** storage area (also present in eMMC) designed to store sensitive data — encryption keys, secure counters, DRM state, authentication tokens — such that it **cannot be tampered with or replayed** by an attacker who can eavesdrop on or spoof the bus.

**The threat it defends against — a "replay attack":** imagine an attacker records a legitimate write to secure storage (say, "set failed-PIN-count = 0"), then later *replays* that recorded message to undo a security state (resetting the counter after failed attempts). RPMB prevents this. **How it works:**
- The host and RPMB share a **secret authentication key**, programmed once (fused in) at manufacture.
- Every RPMB access is signed with a **MAC (Message Authentication Code, HMAC-SHA256)** computed over the data using that key — so the device rejects any command not signed with the correct key (defeats spoofing).
- RPMB maintains a monotonically-increasing **Write Counter** included in every authenticated write. The host must read the current counter and include it in the next write; the device rejects any write with a stale counter — **defeating replay** (a recorded old message carries an old counter and is refused).
- Reads return a host-supplied **nonce** (random number) in the signed response, so the host can verify the response is fresh and from the genuine device.

Conceptually, RPMB extends the *data-integrity* mindset from Chapter 6 §6.6 (end-to-end protection) into the *security* domain: §6.6's PI protected against *accidental* corruption (CRC + Reference Tag); RPMB protects against *malicious* tampering (MAC + monotonic counter + nonce). 🔬 RPMB and its key-provisioning/attestation schemes are patent-active, especially as mobile security and automotive functional-safety requirements tighten.

---

## 10.6 UFS low power (p. their 10.6) ⭐ *connects to power management*

Because UFS targets battery devices, aggressive power management is central — the same priority you saw for consumer SSDs in Chapter 1, and the subject of your topic #4. UFS power states live mostly in the M-PHY/UniPro layers:

- **Active** — full HS burst transfers.
- **STALL / SLEEP** — light idle states (M-PHY line states) that cut power between bursts while keeping the link quickly recoverable.
- **HIBERN8** — the deep low-power link state: the M-PHY link is torn down to near-zero power (~30 µW in optimized designs) but can be re-established quickly. This is UFS's analog of **DevSleep** from Chapter 1 — ultra-low power with fast wake.
- **Deep Sleep** (UFS 3.1+) — an even deeper device-level state for maximum standby savings.

The firmware tradeoff is identical to the one from Chapter 1 and the DevSleep testing in Chapter 7: enter low-power states eagerly to save battery, but not so eagerly that wake-up latency hurts responsiveness. The host drives the transitions based on activity, and (as in SSDs) the timers must be tuned. **UFS 4.0 also added HS-LSS (High-Speed Link Startup Sequence)** — bringing the link up at HS-G1 (1248 Mbps) instead of the old slow PWM-G1 (3–9 Mbps), cutting link-startup time ~70% — which matters for fast wake from deep states.

---

## 10.7 WriteBooster (p. their 10.7) ⭐⭐ *you already know this — it's SLC Cache*

**WriteBooster is UFS's name for the SLC Cache from Chapter 4 §4.8.** The mechanism is identical: temporarily configure part of the TLC (or QLC) NAND to run in **pseudo-SLC mode** (1 bit/cell), giving a fast, durable write buffer that accelerates bursts — then migrate the data to normal TLC/QLC storage later.

The UFS-specific details:
- **Host-configurable buffer.** The host sets the max SLC buffer size at device configuration and **dynamically enables** WriteBooster based on performance needs (e.g., turn it on for a big app install or 8K video capture).
- **Two provisioning modes** — the SLC buffer can be carved from dedicated space, or borrowed from the shared user-data area (the "dynamic" approach from Ch4, which gives a bigger buffer when the drive is emptier).
- **The buffer fills → performance drops.** Exactly the "burst then collapse" behavior the book warned about in Ch4: once the finite SLC buffer is full, writes fall through to native TLC/QLC speed. This is why UFS benchmarks, like SSD benchmarks (Ch7), must distinguish burst from sustained performance.
- **Host-directed flush.** The host can tell the device to **flush** the SLC buffer to normal storage during idle/hibernate, freeing it for the next burst — a host-managed version of the background migration from Ch4.

**Modern extension (UFS 4.1):** WriteBooster gained **buffer resizing** and **partial/pinned flush** — the host can flush *some* data while retaining frequently-used data in the fast SLC region (a "pinned WriteBooster" that keeps hot data fast). 🔬 This host↔device coordination of the SLC cache is an active patent area.

---

## 10.8 HPB — Host Performance Booster (p. their 10.8) ⭐⭐ *you already know this too — it's HMB, specialized*

**HPB is UFS's answer to the DRAM-less problem from Chapter 4 §4.2 — and it works like HMB.** Recall the issue: a device without its own DRAM can't hold the full L2P mapping table on-chip, so on a cache miss it must **read the mapping from flash first, then read the data — two flash accesses**, which crushes random-read performance (Ch4 §4.2.2). HMB (Ch4 §4.2.3) solved this for NVMe by lending the device a slice of *host* DRAM. **HPB does the same for UFS, but specialized specifically to the L2P table:**

- UFS devices are cost/space-constrained and typically **DRAM-less** (no room for a big DRAM in a phone package).
- With HPB, the **host caches parts of the device's L2P mapping table in host system memory.**
- On a read, the **host looks up the physical address in its cached L2P and sends it *along with* the read command** (in the HPB READ command). The device then goes straight to the flash location — **skipping the internal mapping-table lookup entirely**, avoiding that costly second flash access.
- Result: **dramatically faster random reads** (the workload most hurt by DRAM-less designs), especially app launches and random access patterns typical of phones.

The distinction from HMB worth noting: **HMB** lends *generic* device memory (the device uses it however it likes — mapping table, data cache); **HPB** is *purpose-built* for the L2P table and involves the host *actively participating* in address translation (the host hands the device a physical-address hint). In that sense HPB is a small step toward the **host-managed FTL** ideas from Chapter 4 §4.10 and the ZNS/FDP supplements — the host taking on a piece of the mapping work. HPB has **two operating modes** (Host Control Mode and Device Control Mode) governing who decides which L2P regions to cache. 🔬 HPB caching policies and prefetch strategies are patent-active, and HPB is defined in its own JEDEC extension (JESD220-3).

---

## 📌 Modern developments (UFS 4.1 and 5.0)

*The 2nd edition covers UFS through roughly 4.0. Here's the current state — relevant both to your embedded work and your patent scans. Grounded in current JEDEC and industry sources.*

**The version ladder as of 2026:**

| Version | Published | M-PHY / UniPro | Per-lane | 2-lane effective | Notes |
|---|---|---|---|---|---|
| 3.1 | 2020 | M-PHY 4.x / HS-G4 | ~11.6 Gbps | ~2.1 GB/s | prev. mainstream |
| 4.0 | Aug 2022 | M-PHY 5.0 / HS-G5, UniPro 2.0 | 23.2 Gbps | ~4.2 GB/s | doubled 3.1; WriteBooster, Deep Sleep |
| 4.1 | Dec 2024 (JESD220G) | same PHY as 4.0 | 23.2 Gbps | ~4.2–4.3 GB/s | feature refresh (below) |
| 5.0 | Feb 2026 (JESD220H) | M-PHY 6.0 / HS-G6, UniPro 3.0 | ~46.6 Gbps | up to **10.8 GB/s** read | mass prod. late 2026 |

Per JEDEC, <cite index="27-1">UFS 4.1 (JESD220G) was published in January 2025 as an update to UFS 4.0, maintaining hardware compatibility with 4.0 while leveraging M-PHY 5.0 and UniPro 2.0 to enable up to ~4.2 GB/s</cite>, and <cite index="28-1">UFS 5.0 (JESD220H) was published in February 2026, referencing MIPI M-PHY v6.0 and UniPro v3.0</cite>. Notably, <cite index="21-1">Samsung's UFS 5.0 announcement cited sequential reads up to 10.8 GB/s and writes up to 9.5 GB/s — which would make flagship-phone storage faster than the PCIe Gen4 NVMe SSDs common in laptops</cite>, with <cite index="21-1">mass production beginning Q4 2026 and first phones expected around 2027</cite>.

**What UFS 4.1 added (the parts relevant to firmware and patents):**
- **Zoned Storage (ZUFS)** — the **ZNS concept from your Chapter 4/6 supplements, brought to UFS.** The host and device collaborate on data placement using zones, cutting write amplification — the same host-managed-flash idea, now in the mobile stack. This is a significant convergence: the write-amplification-reduction thread you traced (SDF → ZNS → FDP) now includes mobile.
- **Host-Initiated / Intelligent Defragmentation** — the host tells the device when to defragment (rather than the device deciding), improving read speed on cluttered devices (reportedly up to ~60%). A host-managed maintenance operation — conceptually like the host-managed GC preview from Ch4 §4.3.4.
- **Pinned WriteBooster** — keep frequently-used data pinned in the SLC turbo region for faster random reads (~30% on hot apps).
- **MCQ (Multi-Circular Queue)** — **this one is straight out of NVMe.** UFS 4.x adds *multiple* command queues (rather than one), letting the host parallelize command submission across queues — exactly the NVMe SQ/CQ multi-queue model from Chapter 6, now in UFS. It's the clearest sign of NVMe and UFS converging architecturally.
- **QLC support and boot security** enhancements — QLC (Ch3) is now explicitly supported in mobile, and secure boot is strengthened.

**What UFS 5.0 adds:**
- **Inline Hashing** — hardware-level data-integrity hashing on the fly, strengthening tamper-resistance (a security escalation beyond RPMB).
- **Link Equalization** — signal-integrity technology to keep the much-faster HS-G6 link stable and error-free (as with PCIe Gen6's move to PAM4 in Ch5, higher speeds force new signal-integrity techniques).
- **~2.5× the bandwidth** of UFS 4.x, targeted squarely at **on-device generative AI** (loading large models fast), 8K video, and console-class mobile gaming.

**The through-line for your studies.** UFS's evolution is recapitulating the SSD/NVMe story you've already learned, one step behind and mobile-optimized: it went serial+full-duplex+queued (like SATA→NVMe), it adopted **multi-queue** (MCQ ≈ NVMe queues), it borrowed **host-assisted memory** (HPB ≈ HMB), it added **host-managed zoned placement** (ZUFS ≈ ZNS), and it's now hitting signal-integrity walls that force new PHY techniques (HS-G6 equalization ≈ PCIe PAM4). If you understand the SSD stack, UFS is that same knowledge re-applied under mobile constraints (power, package size, cost) — which is exactly why it's a natural extension of your work at a NAND company.

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
4. UFS's command layer is based on which older standard, and which earlier chapter did you first meet that standard in?
5. What is a UPIU, and what earlier constructs (name two) is it directly analogous to?
6. A UFS Logical Unit is the SCSI equivalent of which NVMe concept? What do both let you do?
7. Explain a replay attack and the two RPMB mechanisms that defeat spoofing and replay respectively.
8. WriteBooster is UFS's name for which Chapter 4 feature? Describe the "burst then collapse" behavior and why benchmarks must account for it.
9. HPB solves which specific DRAM-less problem from Chapter 4, and how does it differ from HMB? (What does the host hand the device that HMB does not?)
10. What is HIBERN8, and which SSD power state is it analogous to?
11. **(Modern)** MCQ, HPB, and ZUFS each mirror a concept from the NVMe/SSD world. Name the analog of each.
12. **(Modern/relevant)** Given that KIOXIA's UFS runs on BiCS flash, explain in one or two sentences why UFS firmware is close to the BiCS8 SSD-controller work — what's shared and what differs.

---

*Next up (your list of 5): **flash file systems** — EXT4 and especially F2FS (the Flash-Friendly File System). This is the layer *above* the SSD, where the OS filesystem cooperates with flash; F2FS is log-structured specifically to cut write amplification, connecting straight back to Chapter 4 from the host side. Then power management (ASPM/DevSleep) and aerospace storage to finish the set.*
