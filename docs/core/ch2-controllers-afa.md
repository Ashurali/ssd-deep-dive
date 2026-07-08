---
title: "Ch 2 — Controllers & AFA"
tags:
  - controllers
  - all-flash-array
  - queues
  - ecc
source_anchor: "CH2 file"
---

# SSD Deep Dive — Chapter 2: SSD Controllers & All-Flash Arrays (主控和全閃存陣列)
## English Study Companion

**Where we are:** Chapter 1 gave you the whole-drive picture; the three cores were controller + flash + firmware. This chapter zooms into the **controller (主控)** — the brain — then widens out at the end to show what happens when you build an array out of many whole SSDs. Chapter 2 runs pages 1–52 of your file (the last few lines of p. 52 are empty website comments — skip them).

**How to use this guide:** Section numbers match the book. Page references like *(p. 6, Fig 2-6)* point into your CH2 file so you can view the original diagram alongside the explanation. Glossary at the end.

**The chapter's shape:** Two halves. First half (2.1–2.5) = **the controller chip** — its internal architecture, the vendors who make it, and three case studies. Second half (2.6–2.7) = **beyond the single drive** — all-flash arrays and computational storage. If your time is limited, 2.1 and 2.6 are the load-bearing sections.

---

## Chapter opening (p. 1)

An SSD is essentially controller + flash (+ optional cache). The controller is the brain, doing three jobs: (1) talk to the host over a standard interface, (2) talk to the flash, (3) run the internal FTL algorithms. A controller's quality directly determines the SSD's performance, lifespan, and reliability.

---

## 2.1 SSD system architecture — pp. 1–11 ⭐ *the core of the chapter*

An SSD controller is a **SoC (System on Chip)** — a complete little computer on one chip *(p. 1–2, Fig 2-1)*: it has a CPU, RAM, hardware accelerators, buses, and data encode/decode units. This particular design uses an **ARM CPU** and splits into a **front end** and a **back end**, linked by buses (a fast **AXI** bus and a slow **APB** bus). The firmware sits on top, orchestrating all the hardware blocks to move data host↔flash.

Think of it as an assembly line: the **front end** is the loading dock (receives orders from the host), the **CPU + FTL** is the manager (decides what to do), and the **back end** is the warehouse crew (actually stores/retrieves goods in the flash).

### 2.1.1 Front end (前端) — pp. 2–7

The front end is the **host interface controller** — where the drive talks to the computer. Three interfaces dominate; their speeds are in *(p. 2, Table 2-1)*:

- **SATA** (Serial ATA) — the mature, ubiquitous consumer/low-end-enterprise interface. Established by an Intel/IBM/Dell/Seagate/etc. committee (SATA 1.0 in 2001). *(p. 3, Fig 2-2)*
- **SAS** (Serial Attached SCSI) — the enterprise interface; the serial successor to parallel SCSI. **Key compatibility rule:** SAS is backward-compatible with SATA (a SATA drive works in a SAS environment, but not vice versa — a SATA controller can't drive a SAS disk). SAS uses three sub-protocols: SSP (carries SCSI commands), SMP (management), STP (SATA tunneling). *(p. 3–4, Fig 2-3)*
- **PCIe** (PCI Express) — the high-speed interface, originally Intel's "3GIO" (2001), meant to replace PCI/PCI-X/AGP. Unlike a shared bus, PCIe is **point-to-point with dedicated per-device lanes** — each device gets its own bandwidth, not a shared slice. Comes in widths ×1 to ×32. Supports active power management, error reporting, hot-plug, and QoS. *(p. 4–5, Figs 2-4 AIC card, 2-5 U.2)*

**What the front-end hardware does (p. 5–6):** The **PHY (physical layer)** receives the raw serial bit stream and converts it to digital signals. Downstream blocks parse NVMe/SATA/SAS commands, using **DMA** to move data. Commands queue up; data lands in fast **SRAM**. If encryption or compression is needed, dedicated hardware handles it — and if software had to do it instead, it would become a performance bottleneck.

**A concrete command walk-through — SATA Write FPDMA (p. 6–7, Fig 2-6).** This is worth understanding because it shows the front end isn't just "receiving" — there's a handshake. All SATA transfers use **FIS (Frame Information Structure)** packets:

1. Host sends a **Write FPDMA command FIS** onto the bus.
2. SSD checks whether its write buffer has room. If yes → sends **DMA Setup FIS**; if no → sends nothing, host waits. *(This is flow control — 流控.)*
3. Host sends a **Data FIS** of ≤8 KB.
4. Repeat 2–3 until all data is sent.
5. SSD sends a **Status FIS** (good, or bad/error) — from the protocol's view the write is now complete.

But the front end's job isn't done. The firmware's **command decoder** parses the FIS into things the FTL understands: is it read or write? what's the starting LBA and length? any special attributes (FUA? sequential or random vs. the previous command)? Once decoded, the command joins a queue for the FTL. Now that the FTL knows the starting LBA and length, it can map that logical range to physical flash.

### 2.1.2 Controller CPU (主控CPU) — pp. 7–8

The controller SoC is like any embedded SoC: one or more CPU cores plus peripherals (I-RAM for code, D-RAM for data, PLL, IO, UART, buses). The firmware runs on these cores.

**A design decision that matters — SMP vs AMP:**
- **SMP (Symmetric Multi-Processing):** all cores share one OS and one copy of code; they share I-RAM/D-RAM. Simpler, but cores can contend for shared memory, slowing execution.
- **AMP (Asymmetric Multi-Processing):** each core runs its *own* code with its *own* I-RAM/D-RAM; cores run independently with no memory contention.

When a controller needs more compute, AMP suits the "independent tasks" model better because it eliminates the resource-contention slowdown. A key firmware-architecture goal is **balancing load across cores** so no core is "worked to death while another sits idle" — that's how you extract maximum read/write performance.

Peripheral blocks include UART/GPIO/JTAG (essential debug ports), timers, DMA, temperature sensors, and power regulators.

### 2.1.3 Back end (后端) — pp. 8–11

??? example "🎬 Animate this — The Flash Timing & Parallelism Lab"

    The bus, the registers and the planes on one timeline — toggle pipelining and AIPR and watch the bars move.

    [Animation page](../animations/flash-timing-lab.md) · [open full-screen ↗](../animations/files/flash_timing_lab.html)

    <iframe src="../../animations/files/flash_timing_lab.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Flash Timing & Parallelism Lab"></iframe>


Two big blocks: the **ECC module** and the **flash controller** *(p. 8–9, Fig 2-7)*.

**ECC module (data codec).** Because flash has an inherent bit-error rate, every write gets ECC parity added (encoding); every read gets checked and corrected (decoding). If errors exceed the ECC's correcting power, the data is returned to the host flagged "uncorrectable." The main algorithms are **BCH** and **LDPC** — and **LDPC is becoming mainstream** (it corrects more errors for the same data, which matters as flash moves to denser 3D/TLC/QLC).

**Flash controller.** Issues ONFI/Toggle-standard flash commands, managing reads/writes between cache and flash.

**How the controller physically wires to flash (p. 9–11, Fig 2-8).** The basic unit that executes a flash command is a **Die/LUN**. The pin interface per die: 8 I/O pins (command, address, *and* data all share these 8 pins), 5 enable signals (ALE, CLE, WE#, RE#, CE#), 1 status pin (R/B#), 1 write-protect pin (WP#). CLE vs ALE tell the chip whether the bytes on the I/O pins are a command or an address.

**Channels and parallelism — the key performance idea.** For speed, the flash controller runs **multiple channels** in parallel, and each channel hosts multiple dies. More dies = more parallelism = more performance. Since all dies on a channel share the same bus, how does the controller pick which die to talk to? The **CE# (chip-enable) select signal** — it asserts the target die's CE# before sending commands/data. A channel typically has 4–8 CEs, giving flexibility in total capacity. *(This channel × die parallelism is the single biggest lever on SSD throughput — remember it.)*

---

## 2.2 Controller vendors — pp. 11–22

The controller is a chip product with both deep technical barriers and broad market reach. Early on, few players (chip design/fab barriers are high); as SSDs boomed, controller startups sprang up "like bamboo shoots after rain."

### 2.2.1 Marvell (p. 11–14, Figs 2-9 to 2-11)

The **world's #1 HDD and SSD controller vendor.** Entered SSD controllers in 2007, shipped its first SATA controller (Davinci) in 2008. Full product line across low/mid/high end. Key differentiators:
- **NANDEdge** — its proprietary LDPC error-correction tech (now 3rd generation), used across all its latest SATA/SAS/NVMe controllers; works with 2D/3D and TLC/QLC.
- **Artemis series (88NV1120/1160)** — the world's first PCIe NVMe controller needing **no DRAM cache**, supporting **HMB (Host Memory Buffer)**.
- A rich **SDK** that lets partners focus their own software teams on differentiation.
- Aggressive process migration: first to 28nm, moving the whole line to 16nm (others still on 40/55nm). The 88SS1074 SATA controller shipped 50M+ units in 18 months.

### 2.2.2 Samsung (p. 14–15, Fig 2-12)

Samsung's controllers are basically **only used in Samsung's own SSDs**. A lineage worth recognizing: MCX (830 series) → MDX (840/840 Pro) → MEX (850 Pro/840 EVO, added TurboWrite) → MGX/MFX (lower-capacity EVO drives). Rising core counts, clock speeds, and cache sizes across generations.

### 2.2.3 Domestic (Chinese/Taiwanese) controllers (p. 15–22)

The common **Taiwanese** controllers are from **JMicron, Silicon Motion (SMI, 慧榮), and Phison (群聯)** — cheap, popular with small/mid SSD makers. JMicron has faded; the book focuses on SMI and Phison.

**Silicon Motion / SMI (p. 15–17).** A global leader in flash controllers since 2000 (CF/SD/USB → eMMC/UFS → SSD); shipped 5B+ flash controllers and 100M+ SSD controllers. Works with every major flash fab, which lets it see NAND roadmaps early and design matching controllers. Even Intel's consumer SSDs and Crucial's MX500 (SM2258H + Micron 64-layer TLC) use SMI. Advantages: full **turnkey** solutions (controller → firmware → board → flash pairing), **NANDExtend** ECC (LDPC + patents, extends life up to 3×, now 4th-gen), and **self-developed PHY** (moving to 28nm for PCIe Gen3, and the first vendor targeting **12nm** for PCIe Gen4).

**Phison (p. 17–19, Table 2-2).** Founded Nov 2000; started with the world's first single-chip USB-drive controller, now a leader across USB/SD/eMMC/UFS/SATA. A **co-founder of ONFI** and an SD Association board member. Like SMI, popular with smaller makers and as big brands' entry-level choice.

**Other Chinese players (p. 19–22)** — a survey worth skimming, not memorizing. Highlights: **HiSilicon** (very strong, but Huawei-internal only); **Unigroup/Ramaxel, Guoke Micro (GK2101, 40nm, SATA/NVMe/LDPC), Hualan Micro** (uses a bridge-chip approach — SATA-to-eMMC — so its controller needs no FTL, lowering dev difficulty at some cost to performance/life); **DERA (得瑞领新)** — TAI controller, NVMe 1.2/PCIe 3.0, 500K random-write / 1250K random-read IOPS (see 2.5); **Starblaze (憶芯)** — spun out of Memblaze (see STAR1000 in 2.4); plus Shandong Huaxin, Greenliant (from SST founder Bing Yeh), SiliconGo (硅格, see 2.3), and GigaDevice (兆易创新), which bought a Wuhan SSD fab and hired ex-SandForce staff. The theme: a crowded field where survival requires patience and good products.

---

## 2.3 Case study: SiliconGo SG9081 (a SATA controller) — pp. 22–23, Fig 2-14

How a real controller achieves high performance — three techniques:

1. **HAM + GoCache accelerate random IOPS.** HAM (Hardware Acceleration Module) moves parts of algorithms into hardware, freeing the MCU and speeding small-data handling. GoCache (SiliconGo-proprietary) efficiently manages the mapping table, boosting small-data transfer. Together they raise random performance.
2. **DMAC accelerates sequential throughput.** The DMA Controller lets large sequential transfers proceed *without* tying up the MCU: when a DMA request fires, the bus arbiter hands control to the DMAC, high-speed transfer runs, the MCU does other work, then the DMAC returns the bus. Result: excellent sequential read/write.
3. **LDPC + RAID for reliability.** As flash goes 2D→3D, BCH can't keep up; LDPC corrects more errors and extends flash life. RAID adds a second layer — parity that can rebuild original data when needed.

*(Notice the recurring pattern: hardware-accelerate the small random stuff, DMA the big sequential stuff, and layer LDPC + RAID for reliability. Nearly every controller in this chapter follows this template.)*

---

## 2.4 Case study: unifying enterprise & consumer controller design — pp. 23–26

**The two markets differ (p. 23, Table 2-3):** enterprise SSDs prioritize random performance, latency, IO QoS, and stability; consumer SSDs prioritize sequential performance, power, and price. Designing separate controllers for each raises R&D cost and downstream complexity.

**Can one unified controller serve both?** The book argues yes, going through six dimensions and finding they're converging:

1. **Cost** — enterprise is cost-insensitive, so target the consumer budget with a common hardware architecture; differentiate via firmware.
2. **Performance** — NVMe U.2 and M.2 have become mainstream with converging needs; 1U servers carry 8+ U.2 drives at 300–400K random IOPS each (enough for most uses), while high-end consumer M.2 already hits 3.5 GB/s (near enterprise sequential). Data centers often pre-optimize data into *sequential* writes, lowering the need for enterprise random performance.
3. **Endurance** — differs by market, but the real driver is *flash* endurance; the controller just maximizes error correction. So the *controller* design goal is the same.
4. **Capacity** — differs, so the controller must support large flash cheaply enough to cover both.
5. **Reliability** — enterprise wants ECC + Die-RAID; as 3D flash spreads, fabs now recommend Die-RAID for consumer too → goals converge.
6. **Power** — consumer (battery devices) is most sensitive, needing many power states and fast wake; enterprise is less sensitive, *but* power is ~20% of data-center operating cost, so low power is becoming an enterprise goal too.

**The conclusion:** hardware unification is feasible; product differentiation lives in **firmware**. The book cites Starblaze's **STAR1000** *(p. 25, Fig 2-15)* as a successful attempt — SMP architecture for flexibility, error-checking on SRAM/DRAM/datapaths (enterprise-grade), cheap RAID5/6 with clever SRAM sharing (give the RAM back to firmware when RAID isn't needed), and an NVMe subsystem using two 32-bit CPUs + an NVMe hardware accelerator that hits consumer power targets while supporting enterprise features (queue scheduling, high-performance SGL, atomic ops, HMB/CMB, SR-IOV multi-VF).

---

## 2.5 Case study: DERA TAI NVMe controller — pp. 26–28

NVMe is designed for modern multi-core systems, exploiting flash's high concurrency and low latency. A NVMe SSD internally juggles huge numbers of concurrent IO transactions, each needing hardware operations — some compute-heavy (ECC codec, encryption) — all under tight power budgets. Hence NVMe controllers are **highly customized ASICs** tightly co-designed with the NAND-management software.

**DERA TAI (p. 26–27, Fig 2-16):** front end supports PCIe Gen3 ×8 or ×4, with multiple NAND channels and strong ECC; all data paths get ECC + CRC protection. Positioned for **enterprise**, so its core design points are **performance stability** and **data reliability** — enterprise apps need consistent high performance and low latency, which requires careful engineering to avoid performance jitter and latency spikes (achieved by finely scheduling front-end IO against background activity).

**Reliability mechanisms (p. 27–28):**
- **Per-channel ECC** at 100 bits/1KB — balancing complexity, area, power, and decode-latency determinism.
- **Active fault management** — flash degrades *gradually* (rising bit-error rate before hard failure); DERA tracks per-page raw error rate in real time to proactively retire failing units, and dynamically adjusts **wear leveling** based on real cell tracking.
- **Chip-to-chip redundancy** (RAID across dies) — if one chip's data block errors out, the algorithm rebuilds it from other chips.
- **Power-loss protection** — hardware continuously monitors supply; on anomaly, switches to backup capacitors to preserve data integrity.
- **Thermal/power self-monitoring** — dynamically throttles to avoid heat-induced failure in poorly-ventilated installs.

*(Performance figures: p. 28, Table 2-4.)*

---

## 2.6 All-Flash Arrays (AFA) — pp. 28–50 ⭐ *the chapter's second pillar*

**What is an all-flash array?** It's a big enterprise storage box built from many SSDs. The book teaches it through one example: **EMC XtremIO (XIO)**. (Sourced from Vijay Swami's XtremIO architecture write-up.)

*(Mental model to carry through this whole section: an AFA is "an array of SSDs" the way an SSD is "an array of USB drives" — but each level up is a qualitative leap, needing a re-designed architecture. The book makes this analogy explicitly on p. 50.)*

### 2.6.1 The anatomy (p. 28–34)

**Structure (p. 29, Fig 2-17):** A standard XtremIO array = two or more **X-Bricks** linked by **InfiniBand**. The X-Brick is the core building block. One X-Brick contains:
- 1 high-end UPS
- **2 storage controllers**
- a **DAE** (Disk Array Enclosure) holding many SSDs, each SAS-connected to the controllers
- (if multiple X-Bricks) 2 InfiniBand switches for high-speed controller interconnect

**Storage controller (p. 30–31, Figs 2-18/2-19):** it's just an Intel server — NUMA architecture, 2 CPUs (Intel E5), 256 GB RAM per CPU, 2 InfiniBand controllers, 2 SAS HBAs. Lots of cabling is redundant for clustering.

**Configuration (p. 32, Table 2-5):** one X-Brick = 10 TB raw, 7.5 TB usable — but with ~5:1 dedup+compression, ~37.5 TB effective.

**Performance (p. 32–33):** a 2-X-Brick array ran 550 VMs serving 7000 users; daily average 350–400 MB/s at 20K IOPS, peaking at 20 GB/s and 200K IOPS.

**Software console (p. 33–34, Figs 2-21/2-22):** shows live data-reduction ratio (e.g., 2.5:1 = dedup 1.5:1 × compression 1.7:1) plus per-SSD and aggregate bandwidth/IOPS/latency.

### 2.6.2 Hardware architecture (p. 34–38)

XtremIO was EMC's assault on the AFA market, designed **from the ground up around flash characteristics** *(p. 34–35, Fig 2-23)*. Each X-Brick: 2 controllers, a DAE of **25 × 400 GB SSDs** (10 TB raw, using high-end **eMLC** — ~10× the endurance of ordinary MLC), and 2 **BBUs** (Battery Backup Units; the second is for redundancy — extra X-Bricks need only one each).

**Scale-out (p. 35–36, Figs 2-24/2-25):** X-Bricks cascade up to 4 (or 8), interconnected by **40 Gbps InfiniBand** for the back end. Host connectivity is **8 Gbps FC or 10 Gbps iSCSI**; SSDs connect via **6 Gbps SAS**. Each controller also has its own 2 SSDs (to save in-memory metadata on power loss — dedup is memory-hungry because every block needs a hash, sometimes double-hashed) plus 2 SAS disks for the OS. Clean separation: controllers have their own disks; the DAE flash holds only user data — so you can upgrade controllers without touching stored data.

**The "real performance" lecture (p. 36–38, Fig 2-26).** The book editorializes: many vendors brag about peak numbers from a fresh/empty drive (or even DRAM-cache reads) — "treating users like 3-year-olds." What matters, especially to enterprises, is **stable steady-state performance**. XtremIO's per-X-Brick IOPS (**100K** at 100% 4KB write, **150K** at 50/50, **250K** at 100% read) are measured **after the array is ≥80% full** — because only then does garbage collection kick in and reveal true performance. Scaling X-Bricks multiplies these linearly.

### 2.6.3 Software architecture (p. 38–41) — *the real value*

Storage hardware is now commoditized, so **software** is where you differentiate (and software is non-standard, creating lock-in). The book's punchy line: *if an iPhone ran Android, would you queue up to pay $800 for it?* The AFA's soul is its software.

**XIO's software weapons (p. 39):**
- **Dedup** — boosts performance *and*, by reducing write amplification, extends flash life and reliability.
- **Thin Provisioning** — volumes grow capacity on demand.
- **Mirroring** — advanced, without capacity/performance penalty.
- **XDP** — data protection via RAID6.
- **VAAI integration** — (explained in 2.6.4).

**XIO's core design principles (p. 39):**
1. **Everything for random performance** — accessing any block on any node costs the same (fair access to all resources), so performance scales linearly as nodes are added.
2. **Minimize write amplification** — less background writing = longer life, better reliability.
3. **No global garbage collection** — the SSDs' own strong controllers already do GC well, so XIO doesn't duplicate it (saving write amplification and freeing resources for data services).
4. **Content-based data placement** — a block's address is derived from its *content* (hash), not its logical address, so data can live anywhere → great random performance and even distribution.
5. **True Active/Active** — LUNs have no owner; any node serves any volume, so one node's failure doesn't cripple performance.
6. **Linear scalability** — performance and capacity both scale linearly.

**Why does XIO run in Linux user space? (p. 40–41, Fig 2-28)** Three reasons: (1) **speed** — avoids kernel-mode context switches; (2) **simpler development** — no kernel interfaces or complex kernel memory/exception handling; (3) **avoids the GPL** — code running in the kernel would have to be open-sourced under GPL, but their crown-jewel algorithms stay closed in user space. (The book underscores the business logic: open-sourced, the array couldn't command premium prices — "high-tech sold like cabbage.") A single program, **X-ENV**, runs per CPU and grabs *all* CPU/memory resources — to (a) let XIO use 100% of the hardware, (b) prevent other processes from disrupting performance stability, and (c) stay portable (user-space code moves easily to UNIX/Windows or ARM/PowerPC). Indeed, after EMC's acquisition XIO quickly moved to EMC's standard white-box hardware — proof the software is hardware-independent (no FPGAs, no custom chips/firmware — all standard parts, so it can always adopt the newest X86 and interconnects).

### 2.6.4 Workflow (p. 41–49) — *how a read/write/copy actually flows*

**Six modules (p. 41–42):** three data modules **R, C, D** and three control modules **P, M, L**.
- **P** (Platform) — monitors hardware; one per node.
- **M** (Management) — system config via the XMS server (create volumes, LUN masking); one active + one standby.
- **L** (Cluster) — manages cluster membership; one per node.
- **R** (Routing) — the node's "gatekeeper": translates SCSI commands to XIO's internal commands, handles the FC/iSCSI ports, **splits all IO into 4KB blocks**, and **computes each block's hash (SHA-1)**; one per node.
- **C** (Control) — holds the **A2H table** (block logical Address → Hash); provides mirroring, dedup, auto-expansion.
- **D** (Data) — holds the **H2P table** (Hash → SSD Physical address — so placement depends only on content, not logical address); does the SSD reads/writes and the **XDP** RAID protection.

**Read flow (p. 42):** host → R (splits to 4KB) → C (A2H lookup → hash) → D (H2P lookup → physical address → read).

**Non-duplicate write (p. 42–43, Fig 2-29):** host → R (split, hash) → C (hash not found, insert) → D (allocate physical address, write).

**Dedup write (p. 43–44, Fig 2-30):** host → R (split, hash) → C (hash *found* — duplicate!) → D (**don't write; just increment the block's reference count**). Auto-expansion and dedup happen naturally in the background without hurting normal IO.

**ESXi & VAAI (p. 45):** **ESXi** is VMware's bare-metal hypervisor (a VM platform running many VMs). **VAAI** (vStorage APIs for Array Integration) is the protocol ESXi uses to send commands to the array.

**Copy flow (p. 45–47, Figs 2-31/2-32) — the payoff of content-addressing:** an ESXi host issues a VM-copy via VAAI → R receives it, picks a C → C copies the *metadata* address range (e.g., 0–6 → 7–D) → D finds the data is duplicate, so **writes nothing, just increments reference counts.** Copy done, with **zero actual SSD IO.** (Because of A2H + H2P, copying a file becomes "registering a couple of counters" — no data movement.) The catch: these metadata ops happen in memory, so power loss is dangerous — XIO uses a complex journaling scheme (RDMA the metadata changes to a remote controller, write metadata updates to SSD via XDP).

**Module placement & interconnect (p. 47–49, Fig 2-33):** With 2 CPUs per controller (one X-ENV each), **R+C run on one CPU, D on the other.** Why? Intel Sandy Bridge integrates the PCIe controller, so connecting devices directly to a CPU's PCIe lanes is fastest — the SAS HBA sits on CPU2's PCIe slot, so D runs on CPU2. This shows XIO's architectural strength: **software lays itself out to match standard hardware** for optimal performance, and re-adjusts if the hardware layout changes.

**Inter-module communication & scalability (p. 49):** Modules needn't share a CPU; **all inter-module comms go over InfiniBand** — data path via **RDMA**, control path via **RPC**. The cost breakdown: total IO latency is **600–700 μs, of which InfiniBand is only 7–16 μs.** The scalability payoff: adding X-Bricks doesn't raise latency (the communication path is unchanged) — a 4KB block hits some R, its hash lands randomly on *any* C (none special), so everything stays linear. Add/remove X-Bricks → performance changes linearly.

### 2.6.5 Use cases (p. 49–50)

Flash (especially enterprise eMLC/SLC) is still expensive, so an AFA like XtremIO **doesn't replace big-capacity SAN arrays.** It fits apps that need **low capacity but low latency + high IOPS**: **VDI** (virtual desktops), **databases**, **SAP**. Databases benefit doubly — high performance *plus* near-free copies (easy, fast data replicas). Real deployments ran **2500–3500 VDI VMs on one X-Brick at <1ms latency** (VMs share lots of duplicate OS files, so dedup shines).

**What makes an AFA distinctive (p. 50)?**
- *Vs. an SSD:* it has **no** garbage collection / wear leveling / read-disturb handling — the SSDs' own controllers handle all that.
- *Vs. a traditional array:* its specialties are **dedup** and **RAID6-with-always-write-to-new-address.**

---

## 2.7 Computational storage — SSDs with compute — pp. 50–52

**The problem:** we're in a data explosion (phones, sensors, cameras, self-driving cars — one autonomous car generates ~64 TB/day). IT infrastructure = network + compute + storage. Networks are now fast; **storage got fast too** (PCIe 3.0 ×8 SSDs exceed 4 GB/s) — but **CPUs stalled** (Moore's law slowing), so **compute became the bottleneck**, especially for image/video processing and deep learning. Data streams off the SSD faster than the CPU can process it.

**The idea:** combine storage and compute. Shanghai's **Fangyi Technology** built **CFS (Computing Flash System)** — an **FPGA-equipped SSD** on PCIe 3.0 ×8 (~5 GB/s). The SSD stores data at high speed; the **FPGA computes on the data as it comes off the SSD**, offloading the CPU. Roles return to their natural places: **CPU controls, FPGA computes, SSD stores.**

**Why it matters (p. 51–52):** ideal for massive-data storage + AI. Example — self-driving cars generate ~1 GB/s from radar/lidar/cameras. Today many use CPU+GPU boxes drawing **5000 W** — a thermal and power hazard in a car. An **FPGA** approach cuts power dramatically while meeting compute needs (Audi's self-driving platform uses FPGAs). And only PCIe SSDs can hit the >1 GB/s writes needed to *save* this valuable driving data (currently discarded) for later analysis/backup. So an FPGA-SSD both stores driving data fast *and* analyzes it — a perfect fit. Likewise for AI: run FPGA hardware algorithms directly on the SSD's data, then send just the results to the host. (The book notes both FPGAs and flash increasingly have Chinese domestic suppliers — YMTC flash expected to mass-produce in 2018.)

---

## Key vocabulary — for decoding the original figures

| 中文 | English |
|---|---|
| 主控 | (main) controller |
| 前端 / 后端 | front end / back end |
| 主機接口 | host interface |
| 物理層 | PHY / physical layer |
| 命令解析 | command decode/parsing |
| 流控 | flow control |
| 幀信息結構 | FIS (Frame Information Structure) |
| 寫緩存 / 緩沖 | write buffer / buffer |
| 對稱/非對稱多處理 | SMP / AMP |
| 閃存控制器 | flash controller |
| 通道 | channel |
| 使能信號 / 選通信號 | enable signal / select signal |
| 編碼 / 解碼 | encode / decode |
| 糾錯 | error correction (ECC) |
| 硬件加速模塊 | hardware acceleration module |
| 歸一化 | unified / normalized (design) |
| 掉電保護 | power-loss protection |
| 冗余校驗 | redundancy / parity check |
| 全閃存陣列 | all-flash array (AFA) |
| 存儲控制器 | storage controller |
| 磁盤陣列存儲柜 | DAE (disk array enclosure) |
| 級聯 | cascade / scale-out |
| 去重 | deduplication |
| 壓縮 | compression |
| 引用數 | reference count |
| 鏡像 | mirroring |
| 用戶態 / 內核態 | user space / kernel space |
| 元數據 | metadata |
| 路由模塊 | routing module |
| 帶計算功能 | with computation capability |

---

## Check yourself

1. A single flash channel hosts 8 dies. What signal does the controller use to pick which die to talk to, and why do more dies mean more performance?
2. In the SATA Write FPDMA handshake, what does the SSD do if its write buffer is full — and what is that mechanism called?
3. XtremIO derives a data block's storage location from its *content*, not its logical address. Name two capabilities this design directly enables.
4. Copying a VM on XtremIO involves almost no SSD reads or writes. Explain what actually happens instead.
5. Why does XtremIO deliberately *not* perform its own garbage collection, even though it's a flash-based system?
6. Give one performance reason and one legal/business reason XIO runs in Linux user space rather than kernel space.
7. A computational-storage SSD puts an FPGA next to the flash. What bottleneck is this solving, and why not just use a faster CPU?

---

*Next up: Chapter 3 — SSD Storage Media: Flash (閃存) — the physics of how a flash cell actually holds a bit.*
