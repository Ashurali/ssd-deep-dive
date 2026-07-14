---
title: "Ch 2 — Controllers & AFA"
tags:
  - controllers
  - all-flash-array
  - queues
  - ecc
source_anchor: "CH2 file"
---

# Chapter 2 — SSD Controllers & All-Flash Arrays (主控和全閃存陣列)

[Chapter 1](ch1-overview.md) reduced an SSD to three core technologies: controller + flash + firmware. This chapter zooms into the first of them — the **controller (主控)**, the SoC that talks to the host on one side, drives the flash on the other, and runs the FTL in between. A controller's quality directly determines a drive's performance, lifespan, and reliability.

The chapter has two halves. The first (§2.1–2.5) dissects **the controller chip**: its internal architecture, the vendors who make it, and three case studies of real silicon. The second (§2.6–2.7) widens out **beyond the single drive**: what happens when you build an enterprise array out of dozens of SSDs, and what happens when you put compute *inside* the storage. If your time is limited, §2.1 and §2.6 are the load-bearing sections.

!!! abstract "In this chapter"
    - **SSD system architecture** ⭐ — front end, CPU cluster, back end, and the channel × die parallelism that sets performance (§2.1)
    - **Who makes controllers** — Marvell, Samsung, and the Taiwanese/mainland-Chinese field (§2.2)
    - **Three case studies** — a SATA speedster, the enterprise/consumer unification argument, an enterprise NVMe ASIC (§2.3–2.5)
    - **All-flash arrays** ⭐ — XtremIO's content-addressed architecture, dedup, and zero-IO copies (§2.6)
    - **Computational storage** — when the CPU becomes the bottleneck, move compute to the data (§2.7)

---

## 2.1 SSD system architecture ⭐

An SSD controller is a **SoC (System on Chip)** — a complete little computer on one chip: CPU cores, RAM, hardware accelerators, buses, and data encode/decode units. A typical design uses **ARM** cores and splits into a **front end** and a **back end**, linked by a fast **AXI** bus for data and a slow **APB** bus for peripherals. The firmware sits on top, orchestrating every hardware block to move data host ↔ flash.

Think of it as an assembly line: the **front end** is the loading dock (receives orders from the host), the **CPU + FTL** is the manager (decides what happens), and the **back end** is the warehouse crew (actually stores and retrieves goods in the flash).

### 2.1.1 Front end (前端)

The front end is the **host interface controller** — where the drive talks to the computer. Three interfaces dominate:

| Interface | Speed class | Where you find it |
|---|---|---|
| **SATA** (Serial ATA) | 6 Gbps (~560 MB/s usable) | consumer & low-end enterprise; SATA 1.0 dates to 2001 (Intel/IBM/Dell/Seagate committee) |
| **SAS** (Serial Attached SCSI) | 12 Gbps per lane | enterprise; the serial successor to parallel SCSI |
| **PCIe** (PCI Express) | ~1 GB/s per lane per direction (Gen3), ×1–×32 | the high-speed path; originally Intel's "3GIO" (2001), built to replace PCI/PCI-X/AGP |

Two details worth keeping:

- **SAS is backward-compatible with SATA** — a SATA drive works in a SAS environment, never the reverse. SAS carries three sub-protocols: SSP (SCSI commands), SMP (management), STP (SATA tunneling).
- **PCIe is point-to-point, not a shared bus** — each device gets dedicated lanes and therefore dedicated bandwidth, plus active power management, error reporting, hot-plug, and QoS. [Chapter 5](ch5-pcie.md) is devoted to it.

**What the front-end hardware actually does.** The **PHY (physical layer)** receives the raw serial bit stream and recovers digital signals. Downstream blocks parse NVMe/SATA/SAS commands and move data by **DMA**; commands queue up and data lands in fast **SRAM**. Encryption and compression, when needed, run in dedicated hardware — done in software they would become the bottleneck.

**A concrete walk-through — SATA Write FPDMA.** Worth internalizing, because it shows the front end isn't passively "receiving" — there's a handshake. All SATA transfers travel as **FIS (Frame Information Structure)** packets:

1. Host puts a **Write FPDMA command FIS** on the bus.
2. The SSD checks whether its write buffer has room. If yes → it answers with a **DMA Setup FIS**; if no → it stays silent and the host waits. *(This is flow control, 流控.)*
3. Host sends a **Data FIS** of up to 8 KB.
4. Steps 2–3 repeat until all data has crossed.
5. The SSD sends a **Status FIS** — success or error — and the write is complete at the protocol level.

The front end still isn't done: the firmware's **command decoder** parses the FIS into what the FTL understands — read or write? starting LBA and length? special attributes (FUA? sequential relative to the previous command)? Only then does the command join a queue for the FTL, which can now map that logical range to physical flash. (Watch this handshake play out packet-by-packet in the [Packet Dresser animation](../animations/packet-dresser.md).)

### 2.1.2 Controller CPU (主控CPU)

The CPU cluster looks like any embedded SoC: one or more cores plus peripherals — I-RAM for code, D-RAM for data, PLL, IO, UART, timers, DMA, temperature sensors, power regulators, and the debug ports (UART/GPIO/JTAG) every firmware engineer lives in.

**The design decision that matters — SMP vs AMP:**

- **SMP (Symmetric Multi-Processing):** all cores share one OS image and one copy of code, plus shared I-RAM/D-RAM. Simpler — but cores contend for the shared memory, and contention costs speed.
- **AMP (Asymmetric Multi-Processing):** each core runs *its own* code out of *its own* I-RAM/D-RAM. Cores run independently, with no memory contention.

SSD workloads decompose naturally into independent tasks, so when a controller needs more compute, AMP tends to win. Either way, the firmware architect's goal is **balancing load across cores** — no core worked to death while another idles — because that balance is where maximum throughput comes from.

### 2.1.3 Back end (后端)

??? example "🎬 Animate this — The Flash Timing & Parallelism Lab"

    The bus, the registers and the planes on one timeline — toggle pipelining and AIPR and watch the bars move.

    [Animation page](../animations/flash-timing-lab.md) · [open full-screen ↗](../animations/files/flash_timing_lab.html)

    <iframe src="../../animations/files/flash_timing_lab.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Flash Timing & Parallelism Lab"></iframe>


Two big blocks: the **ECC module** and the **flash controller**.

**ECC module (the data codec).** Flash has an inherent bit-error rate, so every write gets ECC parity added (encoding) and every read gets checked and corrected (decoding). If errors exceed the code's correcting power, the data returns to the host flagged *uncorrectable*. The two algorithm families are **BCH** and **LDPC** — and LDPC has become the mainstream, because it corrects more errors per parity bit, which is exactly what denser 3D/TLC/QLC flash demands. ([Supplement A](../supplements/a-ecc-coding-theory.md) builds both from first principles.)

**Flash controller.** Issues ONFI/Toggle-standard commands and manages the traffic between cache and flash ([Chapter 3](ch3-nand-flash.md) §3.3 covers the flash side of this conversation).

**How the controller physically wires to flash.** The unit that executes a flash command is a **die (LUN)**. Its pin interface is startlingly narrow: **8 I/O pins** carry command, address, *and* data — all multiplexed — plus 5 enable signals (ALE, CLE, WE#, RE#, CE#), a ready/busy status pin (R/B#), and write-protect (WP#). CLE vs ALE tell the chip whether the bytes currently on the I/O pins are a command or an address.

**Channels and parallelism — the key performance idea.** The flash controller runs **multiple channels** in parallel, and each channel hosts multiple dies sharing one bus. Which die is being addressed? Whichever one has its **CE# (chip enable)** asserted — a channel typically offers 4–8 CE lines. More channels × more dies per channel = more operations in flight = more throughput. **This channel × die parallelism is the single biggest lever on SSD performance** — it's why the timing-lab animation above is worth ten minutes of play, and why thermal throttling (Ch 1 §1.5.5) works by *reducing* that parallelism.

---

## 2.2 Controller vendors

The controller is a chip business with high technical barriers (chip design and fabrication) and broad market reach. Early on there were few players; as SSDs boomed, controller startups sprang up like bamboo shoots after rain. A field guide:

### 2.2.1 Marvell

The **world's #1 HDD and SSD controller vendor**. Entered SSD controllers in 2007; first SATA controller (Davinci) shipped 2008; full product line across low/mid/high end. Its differentiators:

- **NANDEdge** — proprietary LDPC error correction (3rd generation), used across its SATA/SAS/NVMe lines, supporting 2D/3D and TLC/QLC flash.
- **Artemis series (88NV1120/1160)** — the world's first PCIe NVMe controllers needing **no DRAM cache**, via **HMB (Host Memory Buffer)** ([Chapter 4](ch4-ftl.md) §4.2 explains the trade-off).
- A rich **SDK**, letting partners spend their software teams on differentiation instead of plumbing.
- Aggressive process migration: first to 28 nm, moving the line to 16 nm while competitors sat on 40/55 nm. Its 88SS1074 SATA controller shipped 50M+ units in 18 months.

### 2.2.2 Samsung

Samsung's controllers go **only into Samsung's own SSDs** — vertical integration in silicon form. The lineage is worth recognizing on datasheets: MCX (830 series) → MDX (840/840 Pro) → MEX (850 Pro/840 EVO, which added TurboWrite) → MGX/MFX (lower-capacity EVOs). Each generation raised core counts, clocks, and cache sizes.

### 2.2.3 Taiwanese & mainland-Chinese controllers

The common **Taiwanese** controllers come from **JMicron, Silicon Motion (SMI, 慧榮), and Phison (群聯)** — inexpensive and beloved by small and mid-size SSD makers. JMicron has faded; SMI and Phison matter:

**Silicon Motion (SMI).** A flash-controller leader since 2000 (CF/SD/USB → eMMC/UFS → SSD): 5B+ flash controllers and 100M+ SSD controllers shipped. SMI works with every major flash fab, which gives it early sight of NAND roadmaps — and design wins even inside Intel consumer SSDs and Crucial's MX500 (SM2258H + Micron 64-layer TLC). Strengths: full **turnkey** solutions (controller → firmware → reference board → flash pairing), **NANDExtend** LDPC-based ECC (claimed up to 3× flash-life extension, 4th generation), and a **self-developed PHY** — moving to 28 nm for PCIe Gen3 and first to target 12 nm for Gen4.

**Phison.** Founded November 2000 on the world's first single-chip USB-drive controller; now a leader across USB/SD/eMMC/UFS/SATA, a **co-founder of ONFI**, and an SD Association board member. Like SMI, it powers smaller makers and serves as the big brands' entry-level choice.

**Mainland players**, in one breath each: **HiSilicon** (very strong, Huawei-internal only); **Unigroup/Ramaxel**; **Guoke Micro** (GK2101: 40 nm, SATA/NVMe, LDPC); **Hualan Micro** (a bridge-chip approach — SATA-to-eMMC — whose controller needs no FTL at all, trading performance and lifespan for much lower development difficulty); **DERA** (TAI controller — §2.5); **Starblaze** (spun out of Memblaze — its STAR1000 stars in §2.4); plus Shandong Huaxin, Greenliant (founded by SST's Bing Yeh), SiliconGo (硅格 — §2.3), and GigaDevice, which bought a Wuhan SSD fab and hired ex-SandForce engineers. The theme: a crowded field where survival takes patience and genuinely good products.

---

## 2.3 Case study: SiliconGo SG9081 — anatomy of a fast SATA controller

Three techniques carry this design, and the pattern generalizes:

1. **HAM + GoCache accelerate random IOPS.** HAM (Hardware Acceleration Module) moves hot algorithm paths into hardware, freeing the MCU; GoCache manages the mapping table efficiently in hardware. Together they lift small-block random performance.
2. **DMAC accelerates sequential throughput.** Large sequential transfers run through the DMA controller *without* occupying the MCU: the bus arbiter hands the bus to the DMAC, the transfer streams at full speed while the MCU does other work, then the bus comes back.
3. **LDPC + internal RAID for reliability.** As flash went 2D → 3D, BCH stopped keeping up; LDPC corrects more errors per parity bit, and a RAID layer across flash provides parity to rebuild data when a whole region fails.

!!! tip "The template hiding in this case study"
    Hardware-accelerate the small random stuff, DMA the big sequential stuff, and layer LDPC + RAID underneath. Nearly every controller in this chapter — and most on the market — follows exactly this template.

---

## 2.4 Case study: one controller for enterprise *and* consumer?

The two markets pull in different directions: enterprise SSDs prioritize random performance, latency, QoS, and stability; consumer SSDs prioritize sequential performance, power, and price. Separate controller designs for each double the R&D bill. Can one chip serve both? Walking the six dimensions, the differences turn out to be shrinking:

1. **Cost** — enterprise tolerates higher cost, so target the consumer budget with shared hardware and differentiate in firmware.
2. **Performance** — NVMe U.2/M.2 became mainstream in both markets; a 1U server carries 8+ U.2 drives at 300–400K random IOPS each (plenty for most workloads), while high-end consumer M.2 already streams ~3.5 GB/s, near enterprise sequential numbers. Data centers also increasingly reorganize writes into *sequential* patterns before they hit the drive, softening the enterprise random-write requirement.
3. **Endurance** — differs by market, but endurance is mostly a *flash* property; the controller's job — maximize error correction — is identical in both.
4. **Capacity** — differs, so the controller must simply support large flash configurations cheaply enough for both.
5. **Reliability** — enterprise demands ECC + die-level RAID; with 3D flash, fabs now recommend die-RAID even for consumer drives. Converged.
6. **Power** — consumer is most sensitive (batteries), needing many power states and fast wake. But power is ~20% of a data center's operating cost, so enterprise is converging here too.

**Conclusion: hardware unification is feasible; differentiation lives in firmware.** Starblaze's **STAR1000** is the proof-of-concept: SMP architecture for flexibility; error-checking on SRAM, DRAM, and every datapath (an enterprise-grade requirement); RAID5/6 made cheap by clever SRAM sharing (the RAM returns to firmware when RAID isn't in use); and an NVMe subsystem built from two 32-bit CPUs plus an NVMe hardware accelerator — hitting consumer power targets while still offering queue scheduling, high-performance SGL, atomic operations, HMB/CMB, and SR-IOV with multiple virtual functions ([Chapter 6](ch6-nvme.md) explains those NVMe features).

---

## 2.5 Case study: DERA TAI — an enterprise NVMe ASIC

NVMe was designed for modern multi-core hosts and for flash's native concurrency ([Chapter 6](ch6-nvme.md)). Inside an NVMe SSD, enormous numbers of IO transactions are in flight at once, each demanding hardware work — some of it compute-heavy (ECC codecs, encryption) — under a tight power budget. That's why serious NVMe controllers are **highly customized ASICs co-designed with their NAND-management firmware**, not general-purpose chips.

**DERA TAI:** PCIe Gen3 ×8 (or ×4) front end, many NAND channels, strong ECC, and **ECC + CRC protection on every internal datapath**. It targets the enterprise, so the two design pillars are **performance stability** and **data reliability** — enterprise applications want consistently low latency, which means engineering away jitter by finely scheduling front-end IO against background work. (Rated at 500K random-write / 1,250K random-read IOPS.)

Its reliability toolbox is a checklist of enterprise-grade mechanisms:

- **Per-channel ECC at 100 bits / 1 KB** — balancing decoder complexity, silicon area, power, and *deterministic* decode latency.
- **Active fault management** — flash degrades gradually (error rates climb before hard failure), so TAI tracks per-page raw error rates in real time, proactively retires failing regions, and feeds real wear data into **wear leveling** decisions.
- **Chip-to-chip redundancy** — RAID across dies: if one chip's block goes bad, rebuild it from the others ([Chapter 3](ch3-nand-flash.md#344-raid-inside-the-ssd) §3.4.4 shows the mechanism).
- **Power-loss protection** — hardware monitors the supply and fails over to backup capacitors to preserve in-flight data ([Supplement D](../supplements/d-power-management.md) covers the circuit design).
- **Thermal/power self-monitoring** — dynamic throttling to survive poorly ventilated installations.

---

## 2.6 All-Flash Arrays (AFA) ⭐

An all-flash array is a big enterprise storage box built from many SSDs. The instructive example — and this section's case study throughout — is **EMC XtremIO (XIO)**.

*The mental model to carry through: an AFA is "an array of SSDs" the way an SSD is "an array of flash dies" — but each level up is a qualitative leap that demands a re-designed architecture, not just more of the same.*

### 2.6.1 The anatomy

A standard XtremIO array is two or more **X-Bricks** linked by **InfiniBand**. One X-Brick contains:

- 1 high-end UPS
- **2 storage controllers**
- a **DAE** (Disk Array Enclosure) full of SSDs, each SAS-connected to both controllers
- (in multi-brick arrays) 2 InfiniBand switches for the controller interconnect

**A storage controller is just an Intel server**: NUMA, two Xeon E5 CPUs, 256 GB RAM per CPU, two InfiniBand controllers, two SAS HBAs — with every cable duplicated for redundancy.

**Capacity math:** one X-Brick = 10 TB raw, 7.5 TB usable — but with the typical ~5:1 dedup + compression ratio, ~37.5 TB *effective*. **Real deployment numbers:** a 2-X-Brick array ran 550 VMs serving 7,000 users, averaging 350–400 MB/s at 20K IOPS with peaks of 20 GB/s and 200K IOPS. The management console shows the live data-reduction ratio (e.g. 2.5:1 = dedup 1.5:1 × compression 1.7:1) alongside per-SSD and aggregate bandwidth/IOPS/latency.

### 2.6.2 Hardware architecture

XtremIO was EMC's assault on the AFA market, designed **from the ground up around flash characteristics** rather than adapted from a disk array. Each X-Brick's DAE holds **25 × 400 GB eMLC SSDs** — enterprise MLC with roughly 10× the endurance of ordinary MLC — plus two **BBUs** (battery backup units; the second is for redundancy).

**Scale-out:** X-Bricks cascade to 4 (later 8), interconnected by **40 Gbps InfiniBand** on the back end; hosts connect over **8 Gbps FC or 10 Gbps iSCSI**; SSDs attach via **6 Gbps SAS**. Each controller also carries two local SSDs — for dumping in-memory metadata on power loss (dedup is memory-hungry: every stored block needs a hash entry) — and two SAS disks for the OS. The separation is deliberate: controllers own their system disks, the DAE holds only user data, so **controllers can be upgraded without touching stored data**.

**The "real performance" lesson.** Many vendors quote peak numbers from an empty array — or worse, from DRAM cache hits. What matters is **steady state**: XtremIO's per-brick ratings — **100K IOPS** at 100% 4KB write, **150K** at 50/50, **250K** at 100% read — are measured **with the array over 80% full**, because only then is garbage collection running inside the SSDs and the numbers honest. This is the array-scale version of the FOB-vs-steady-state lesson from [Chapter 1](ch1-overview.md#152-performance), and adding bricks scales these numbers linearly.

### 2.6.3 Software architecture — the real value

Storage hardware is commoditized; **software is the product**. (If an iPhone ran Android, would anyone queue overnight for it?) XIO's software weapons:

- **Dedup** — saves capacity, and *because it eliminates duplicate writes*, it also reduces write amplification, extending flash life.
- **Thin provisioning** — volumes take capacity only as data actually lands.
- **Mirroring** without capacity/performance penalty.
- **XDP** — RAID6-class data protection.
- **VAAI integration** — the VMware offload interface (§2.6.4).

**Six design principles**, each a direct answer to a flash property:

1. **Everything for random performance** — any block on any node costs the same to access, so performance scales linearly with nodes.
2. **Minimize write amplification** — fewer background writes, longer flash life.
3. **No global garbage collection** — the SSDs' own controllers already collect garbage well; duplicating it at array level would only add write amplification. Let each layer do its job.
4. **Content-based placement** — a block's location derives from a *hash of its content*, not its logical address. Data spreads evenly and randomly by construction.
5. **True Active/Active** — LUNs have no owning controller; any node serves any volume, so a node failure degrades capacity, not architecture.
6. **Linear scalability** — capacity and performance grow together as bricks are added.

**Why does XIO run in Linux *user space*?** Three reasons, one of them legal: (1) **speed** — no kernel-mode context switches on the IO path; (2) **simpler development** — no kernel interfaces, kernel memory management, or kernel crash semantics; (3) **the GPL** — kernel code must be open-sourced, and XIO's algorithms are the crown jewels. (Open-sourced, the array couldn't command premium prices — high tech sold at cabbage prices.) One process, **X-ENV**, runs per CPU and deliberately grabs *all* CPU and memory — to use 100% of the hardware, to prevent any other process from disturbing latency, and to stay portable. That portability was proven when EMC moved XIO onto its standard white-box servers after the acquisition: no FPGAs, no custom silicon anywhere, so the software rides each new Intel generation for free.

### 2.6.4 Workflow — how IO actually flows

Six software modules. Three move data — **R, C, D** — and three control the system — **P** (Platform: hardware monitoring, one per node), **M** (Management: volumes, LUN masking via the XMS server; one active + one standby), **L** (Cluster: membership, one per node).

The data path trio:

- **R (Routing)** — the gatekeeper: owns the FC/iSCSI ports, translates SCSI into XIO's internal commands, **splits all IO into 4 KB blocks**, and **computes each block's SHA-1 hash**.
- **C (Control)** — owns the **A2H table** (logical Address → Hash); the home of mirroring, dedup accounting, and auto-expansion.
- **D (Data)** — owns the **H2P table** (Hash → Physical SSD address) — *placement depends only on content* — and performs the actual SSD IO plus XDP protection.

**Read:** host → R (split into 4 KB) → C (A2H: address → hash) → D (H2P: hash → physical → read).

**Fresh write:** host → R (split, hash) → C (hash not found — new entry) → D (allocate physical address, write).

**Duplicate write:** host → R (split, hash) → C (hash **found**) → D **writes nothing and increments the block's reference count**. Dedup isn't a background scrubber — it happens *inline, on the write path, for free*.

**The payoff — copying with zero IO.** When an ESXi host clones a VM through **VAAI** (VMware's array-offload API), R routes the request to a C module, which copies a *metadata address range* in the A2H table; D sees every target block is a duplicate and just bumps reference counts. **An entire VM copy causes no SSD data IO at all.** The catch: those metadata updates live in RAM, so power loss is the dread scenario — hence a journaling scheme that RDMAs metadata changes to a remote controller and persists them via XDP.

**Module placement follows the silicon.** Each controller runs one X-ENV per CPU: **R+C on CPU1, D on CPU2** — because the SAS HBA hangs off CPU2's PCIe lanes (Sandy Bridge integrated the PCIe root complex into the CPU), and D is the module that talks to the SSDs. Software arranging itself around the hardware topology, and re-arranging when the topology changes, is XIO's quiet superpower.

**Inter-module communication** all rides InfiniBand — **RDMA** for data, **RPC** for control. Out of a total IO latency of 600–700 µs, InfiniBand contributes only 7–16 µs — which is why adding X-Bricks doesn't add latency: a 4 KB block enters at some R, its hash lands on a statistically random C, and no node is special. That's the mechanism behind "linear scalability."

### 2.6.5 Use cases

Enterprise flash is expensive, so an AFA doesn't replace big-capacity SAN arrays. It wins where the working set is small but hot: **VDI** (virtual desktops), **databases**, **SAP**. Databases benefit twice — raw performance *plus* near-free copies for dev/test replicas. Real deployments ran **2,500–3,500 VDI VMs on a single X-Brick at sub-millisecond latency** — VDI is dedup heaven, since thousands of VMs share nearly identical OS images.

**What makes an AFA architecturally distinctive?** Versus an SSD: it does **no** garbage collection, wear leveling, or read-disturb handling — the member SSDs' controllers own all of that. Versus a traditional disk array: its defining features are **inline dedup** and **RAID6-style protection that always writes to new addresses**.

---

## 2.7 Computational storage — SSDs that compute

**The problem.** Data is exploding (one autonomous car generates ~64 TB/day) while the three legs of infrastructure grew unevenly: networks got fast, storage got fast (PCIe 3.0 ×8 SSDs exceed 4 GB/s) — but CPU scaling stalled as Moore's law slowed. **Compute became the bottleneck**: data now streams off the SSD faster than the CPU can process it, especially for image/video pipelines and deep learning.

**The idea: move compute into the storage.** Fangyi Technology's **CFS (Computing Flash System)** is the pattern: an **FPGA riding a PCIe 3.0 ×8 SSD** (~5 GB/s). Data streams off the flash straight into the FPGA, which filters/transforms/analyzes it and sends only *results* to the host. Every part returns to its natural role: **CPU controls, FPGA computes, SSD stores.**

**Why it matters.** A self-driving car's sensors produce ~1 GB/s. CPU+GPU compute boxes for the job draw ~5,000 W — a thermal and electrical hazard in a vehicle — while FPGAs deliver the needed throughput at a fraction of the power (Audi's autonomous platform chose FPGAs). Only PCIe SSDs can even *record* that sensor stream (>1 GB/s sustained writes), data that today mostly gets discarded; an FPGA-SSD both stores it and analyzes it in place. The same logic drives AI storage: run the hardware algorithm where the data lives, ship back only the answers.

---

## Key takeaways

1. **A controller is a small computer**: front end (host protocol + flow control), CPU cluster (SMP/AMP running the FTL), back end (ECC codec + flash controller).
2. **Channel × die parallelism is the throughput lever.** Everything from datasheet IOPS to thermal throttling traces back to how many flash operations are in flight.
3. **The controller-design template**: hardware-accelerate random IO, DMA the sequential IO, and lay LDPC + die-RAID underneath.
4. **Hardware converges, firmware differentiates** — one silicon design can serve consumer and enterprise; the firmware decides which drive it becomes.
5. **XtremIO's lesson in layering**: address data by content hash, dedup inline, copy by reference count, and *don't* redo the garbage collection your SSDs already do.
6. **Computational storage inverts the data flow**: when the CPU is the bottleneck, ship compute to the data, not data to the compute.

---

## Key vocabulary

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

??? info "📖 Book page map — for readers of 《深入淺出SSD》"

    This chapter follows the section numbering of Chapter 2 of《深入淺出SSD》
    (SSDFans, 2018); the XtremIO material draws on Vijay Swami's XtremIO
    architecture write-up. Original figures by section:

    | Section | Book pages | Key figures/tables |
    |---|---|---|
    | 2.1 Architecture | pp. 1–11 | Fig 2-1 (SoC), Table 2-1 (speeds), Fig 2-6 (FPDMA), Fig 2-7 (back end), Fig 2-8 (die wiring) |
    | 2.2 Vendors | pp. 11–22 | Figs 2-9…2-12, Table 2-2 |
    | 2.3 SiliconGo | pp. 22–23 | Fig 2-14 |
    | 2.4 Unified design | pp. 23–26 | Table 2-3, Fig 2-15 (STAR1000) |
    | 2.5 DERA TAI | pp. 26–28 | Fig 2-16, Table 2-4 (performance) |
    | 2.6 AFA / XtremIO | pp. 28–50 | Figs 2-17…2-33, Table 2-5 |
    | 2.7 Computational storage | pp. 50–52 | — |

*Next: [Chapter 3 — NAND Flash](ch3-nand-flash.md) — the unruly physics of how a cell actually holds a bit.*
