---
title: "Ch 1 — SSD Overview"
tags:
  - ssd-basics
  - endurance
  - reliability
  - form-factors
source_anchor: "CH1 file, pp. 1–61"
---

# SSD Deep Dive — Chapter 1: SSD Overview (綜述)
## English Study Companion

**The book:** 《深入淺出SSD》 (*SSD Deep Dive: Core Technologies, Principles and Practice of Solid-State Storage*), written by the SSDFans engineering community, published 2018. Chapter 1 spans pages 1–60 of your file (pages 61–66 are just website reader comments — skip them).

**How to use this guide:** Section numbers match the book (1.1, 1.2 …). Page references like *(p. 22, Fig 1-14)* point to pages inside your CH1 file so you can look at the original figures and tables while reading the explanation here. A Chinese-to-English glossary at the end helps you decode labels inside the figures themselves.

---

## The big picture (chapter opening, p. 1)

An **SSD (Solid State Drive / 固態硬盤)** stores data on semiconductor chips — NAND flash memory (閃存) — using pure electronics with **no moving parts**. A traditional **HDD (hard disk drive / 機械硬盤)** stores data magnetically on spinning platters read by a mechanical head. That single difference — electrons vs. mechanics — explains almost everything about why SSDs beat HDDs in speed, power, and durability.

The authors note that in 2008 only a handful of companies made SSDs; by 2018, hundreds did, and SSDs were displacing the two HDD giants (Western Digital and Seagate) as the mainstream storage device. The chapter opens with a joke referencing a wuxia novel: anyone in storage who doesn't know SSDs is like a hero who's never met the legendary Chen Jinnan — not really a hero at all.

---

## 1.1 Introduction (引子) — pp. 1–4

The hook is boot time: PCs used to take 30–60+ seconds to boot; with an SSD, about 8 seconds. Speed is the most visceral thing users notice.

**What's physically inside an SSD** *(p. 3, Fig 1-3)* — it's just a circuit board (PCB) carrying:

1. **Controller (主控)** — the brain; a specialized chip (ASIC) that manages everything
2. **NAND flash chips (閃存)** — where your data actually lives
3. **DRAM cache (緩存)** — optional; some SSDs use only small on-chip SRAM instead
4. **Support components** — power regulation chips, resistors, capacitors
5. **Interface connector (接口)** — SATA, SAS, or PCIe

On the software side, the SSD runs **firmware (固件, FW)** internally — code that schedules data between the host interface and the flash, and runs the algorithms that manage flash lifespan and reliability. The book's framing to remember: **controller + flash + firmware are the three core technologies of an SSD**, and each gets its own chapter later.

**Storage media taxonomy** *(p. 4, Fig 1-4)*: media divide into optical (CD/DVD), magnetic (HDD, tape), and semiconductor. Semiconductor is where all the innovation is: flash today, with 3D XPoint, MRAM, RRAM as emerging candidates. As of the book's writing, the flash market was dominated by five suppliers: Micron, Samsung, SK Hynix, Toshiba, and WD/SanDisk.

---

## 1.2 SSD vs HDD — pp. 4–8

HDD = "motor + magnetic head + platters" (mechanical). SSD = "flash media + controller" (semiconductor). See the comparison table *(p. 5, Table 1-1)* and structure diagram *(p. 5, Fig 1-5)*.

**Five advantages of SSDs:**

**1. Performance** *(p. 5, Table 1-2; p. 6, Fig 1-6)* — Sequential read/write is several times faster; **random read/write is where the gap explodes** — up to hundreds of times faster, in both speed and latency. Benchmarks like IOMeter and FIO measure raw throughput/IOPS; PCMark Vantage measures user experience (boot time, file loading), where HDDs get crushed.

**2. Lower power** *(p. 7, Table 1-3)* — Active power: HDD 6–8 W vs SATA SSD ~5 W; but standby drops to *milliwatts* for SSDs. Power categories you'll see repeatedly: peak, active (read/write), idle, standby/sleep, and **DevSleep** (a special ultra-low state below 10 mW, critical for laptops). Where does the power go? Mostly into the flash chips during reads/writes; the controller accounts for roughly 20%. The scientifically fair comparison is **power per IOPS** — and since an SSD delivers ~100× the performance per watt, it's the natural fit for data centers.

**3. Shock resistance** — No mechanics means nothing to physically crash. An HDD head touching a platter during a drop causes permanent damage; an SSD is just chips on a board.

**4. Silence** — No spinning motor.

**5. Tiny, flexible form factors** — HDDs only come in 3.5″ and 2.5″. SSDs go down to M.2 sticks and even single chips (BGA SSDs as small as 11.5 mm × 13 mm).

**The one HDD advantage: price.** *(p. 8, Table 1-4)* And the authors predict even that will erode as flash density grows. (Spoiler from 2026: they were right for most uses.)

---

## 1.3 History of solid-state storage — pp. 9–19

A condensed timeline (much of it sourced from StorageSearch.com). Worth skimming; the details matter less than the arc: *expensive curiosity → niche → tipping point → explosion → consolidation*.

- **1976** — Dataram sells "Bulk Core," a 2 MB RAM-based SSD on eight large boards *(p. 10, Fig 1-7)*. RAM SSDs were blazing fast and byte-addressable but lost data on power-off and cost a fortune. For ~20 years these remained toys for the rich (main player: Texas Memory Systems).
- **1967** — The foundational invention: at Bell Labs, **Dawon Kahng and Simon Sze (施敏) invent the floating-gate transistor** *(p. 11–12, Fig 1-9)* — a MOSFET with an extra electrically-isolated gate that traps charge, which is exactly how flash stores bits. Sze was born in Nanjing, educated at National Taiwan University and Stanford.
- **1988** — Giant magnetoresistance (GMR) discovered — this made *HDDs* huge in capacity and cheap, winning its discoverers the 2007 Nobel Prize and making HDD king for two decades.
- **1991** — SanDisk ships a 20 MB flash SSD.
- **1997–1999** — First commercial flash SSDs (Altec, BiTMICRO). Flash keeps data without power — now it truly behaves like a "disk."
- **2005–2006** — Samsung becomes the first tech giant to enter; laptops start shipping with SSDs; Windows Vista is the first OS with SSD-specific support.
- **2007 — "the year of revolution"** — Flash SSDs (Mtron, Memoright) finally match the fastest enterprise HDDs; the disk war begins. TMS's RamSan-500: 2 TB, 2 GB/s sequential.
- **2008** — Vendor count hits ~100. Intel ships the X-25E (SLC, 250/170 MB/s). EMC puts SSDs in enterprise arrays.
- **2009** — PureSilicon fits **1 TB in a 2.5″ SSD** using MLC — SSDs match HDD capacity in the same volume while destroying them on speed. SandForce launches its first controller. Steve Wozniak joins Fusion-IO.
- **2010** — Market hits $1B. Enterprise still uses SLC; consumer moves to MLC.
- **2011–2012** — IPOs and a buying spree: OCZ buys Indilinx ($32M); LSI buys SandForce ($370M); Hynix buys LAMD. SandForce pioneers **real-time in-controller compression** (fiendishly hard: compressed pages vary in size, so the mapping tables get very clever) — the book calls SandForce the most successful controller company ever.
- **2013** — PCIe SSDs reach consumers: SATA's 6 Gbps (~560 MB/s real-world) and shallow command queues had become the bottleneck. Violin Memory's IPO flops.
- **2014** — Software ecosystems (VMware VSAN, etc.) rebuild around fast storage. SanDisk buys Fusion-IO ($1.1B); Seagate buys LSI's flash divisions.
- **2015** — **Intel + Micron announce 3D XPoint**, a new memory class. WD acquires SanDisk for $19B. Toshiba samples 48-layer 3D NAND.
- **2016** — PCIe 4.0 demos; 60 TB SAS SSD shown; all-flash-array vendor Pure Storage out-earns the top HDD-array vendor; Violin files for bankruptcy protection.

---

## 1.4 How an SSD actually works — pp. 19–22 ⭐ *the most important section*

From the host's perspective an SSD looks exactly like an HDD: the OS/file system sends standardized read/write **commands**; the drive returns **data and status**. Internally *(p. 20, Fig 1-13)*, an SSD has three functional blocks:

1. **Front end (前端)** — speaks the host protocol. Interface ↔ protocol pairs *(p. 20, Table 1-5)*: **SATA → ATA/AHCI**, **SAS → SCSI**, **PCIe → NVMe**.
2. **FTL — Flash Translation Layer** — the middle layer, the soul of the SSD (all of Chapter 4).
3. **Back end (後端)** — talks to the flash chips using standard flash interfaces (ONFI or Toggle protocol).

**The write path:** Host sends a write → data lands in the SSD's RAM buffer → the FTL assigns each logical block an address in flash → once enough data accumulates, the back end flushes it to those flash locations.

**Why the FTL must exist:** flash **cannot be overwritten in place** (不能覆蓋寫). A flash block must be *erased* before it can be written again. So incoming logical block X doesn't live at any fixed physical spot — the SSD writes it wherever convenient and records the location in a **mapping table (映射表)**: logical address → physical flash address.

*Worked example from the book (p. 21):* a 128 GB SSD with 4 KB logical blocks has 128 GB ÷ 4 KB = 32M logical blocks. At 4 bytes per map entry, the mapping table is 32M × 4 B = **128 MB** — which is why SSDs carry DRAM roughly proportional to capacity (1 : 1000 ratio).

Reads are the reverse: look up the logical address in the map → fetch from that flash location → return to host.

**The key competitive insight:** front-end protocols are standardized; the flash interface is standardized. So once interface and flash are chosen, **an SSD's performance, reliability, and power are decided by its FTL algorithms** — that's where vendors differentiate.

**What else the FTL must do:**

- **Garbage collection (垃圾回收, GC)** *(p. 22, Fig 1-14)*: since you can't overwrite, updated data gets written elsewhere and the old copy becomes garbage (invalid). GC copies the still-valid data out of mostly-garbage blocks into a fresh block, then erases the old blocks to free them. Fig 1-14 shows valid data A/B/C from Block X and D/E/F/G from Block Y being consolidated into empty Block Z.
- **Wear leveling (磨損平衡)**: every flash block has a limited number of erase cycles, so the FTL spreads writes evenly across all blocks instead of wearing out a few.
- Plus: bad block management, read-disturb handling, data retention handling, error handling.

The book's claim: *understand the FTL and you understand SSDs.*

---

## 1.5 Core product parameters — pp. 22–47

This long section teaches you to read an SSD datasheet, using Intel's enterprise DC S3710 as the running example *(p. 23, Fig 1-15)*. A spec sheet covers: basic info (capacity, media, form factor, temperature, certifications), performance (bandwidth, IOPS, latency, QoS), reliability & endurance, and power. Things a datasheet *can't* show: real-world return rate (RMA) and system compatibility — those you learn from testing and reputation.

### 1.5.1 Basic information — pp. 24–29

**Capacity — decimal vs binary (p. 24–25).** Marketed capacity is decimal (128 GB = 128×10⁹ bytes); the flash chips inside are binary (128 GiB = 137.4×10⁹ bytes). The **~7% difference** isn't wasted — the SSD uses it internally for the FTL mapping table, spare blocks for garbage collection, and bad-block replacements. This surplus is called **OP (Over-Provisioning, 預留空間)**:

> OP = (raw capacity − user capacity) ÷ user capacity

Enterprise SSDs often add even more OP to boost sustained performance and endurance.

**Media info — SLC / MLC / TLC (p. 25–26, Table 1-6).** These names tell you *bits stored per flash cell*:

| Type | Bits/cell | Erase-cycle life (P/E) | Speed | Price |
|---|---|---|---|---|
| SLC (Single-Level Cell) | 1 | 50,000–100,000 | fastest | ~3×+ MLC |
| MLC (Multi-Level Cell) | 2 | 3,000–10,000 | medium | medium |
| TLC (Triple-Level Cell) | 3 | 500–1,500 | slowest | cheapest |

More bits per cell = more capacity per silicon area = cheaper per GB, but slower and shorter-lived. (QLC, 4 bits, was just emerging.)

**2D → 3D flash (p. 26–27, Fig 1-16, Table 1-7).** Instead of shrinking cells in a flat plane, 3D NAND stacks layers vertically. Samsung's 48-layer 3D V-NAND achieved 2,600 Mb/mm² — about **3× the density of 2D**, meaning roughly ⅓ the cost per GB. The industry race *(p. 27, Fig 1-17 roadmap)* is simply: denser, faster, cheaper.

**Form factor (p. 27–28, Fig 1-18)** — covered in depth in section 1.6.

**Temperature (p. 28).** Operating: 0 °C to 70 °C. Non-operating (storage/transport): −50 °C to 90 °C. Outside these ranges, anomalies or damage aren't covered by warranty.

**Certifications & compatibility (p. 28–29, Fig 1-19).** Third-party standard-body test suites; passing them spares customers some of their own testing.

### 1.5.2 Performance — pp. 29–33

**Three core metrics (p. 29):**

- **IOPS** — I/O operations per second; measures **random** small-block performance (typically 4 KB). Higher is better.
- **Throughput / Bandwidth (吞吐量/帶寬, MB/s)** — measures **sequential** large-block performance (typically 512 KB+). Higher is better.
- **Latency (時延/響應時間)** — time from command sent to status returned; reported as **average** and **maximum**. Lower is better. Once latency reaches the *seconds* range, humans perceive stutter.

**Access patterns (p. 29–30).** Every benchmark workload is a combination of three knobs:
1. **Random vs Sequential** — are consecutive commands' LBAs (logical block addresses) contiguous?
2. **Block size** — 4 KB for random tests, 512 KB–1 MB for sequential
3. **Read/write ratio** — e.g., 100% write, 100% read, or mixed like 65:35

**QoS — Quality of Service (p. 30–31, Fig 1-20).** Max latency expressed at confidence levels: the worst command among 99% ("two nines") up to 99.999% ("five nines") of commands in a test window. Enterprise/data-center customers (the book cites Baidu/Alibaba/Tencent) care intensely about tail latency because one slow I/O stalls a user-facing request; they often care about QoS more than raw IOPS.

**Empty drive vs full drive — the marketing tell (p. 31–33, Fig 1-21).** Performance is measured **FOB (Fresh Out of Box, 空盤)** and **steady-state/full (滿盤)**:

- HDDs perform the same empty or full (no garbage collection).
- SSDs slow down dramatically when full, because writes now trigger garbage collection (and consumer drives may exhaust their SLC cache).
- **Consumer SSD specs quote empty-drive numbers** — look for the phrase "up to" (最高可達).
- **Enterprise SSD specs quote steady-state (full) numbers** — no "up to."

The book's trick: you can identify whether a drive is consumer or enterprise-grade just by whether the spec sheet says "up to."

One more subtlety (p. 33): quoted latencies are measured **cache-on** — the command completes when data reaches the SSD's RAM buffer, not flash. Writing through to flash (FUA) would take hundreds of microseconds even on SLC.

### 1.5.3 Endurance (壽命) — pp. 34–37

Two interchangeable lifespan metrics:

- **DWPD (Drive Writes Per Day)** — how many times per day you can fill the entire drive, sustained over the warranty period (usually 5 years).
- **TBW (Terabytes Written)** — total bytes writable over the drive's life.

*Worked example (p. 34):* the 200 GB S3710 is rated 3,600 TB TBW over 5 years → 3,600 TB ÷ (5 × 365) ≈ 1,972 GB/day ≈ 10 full drive writes → **10 DWPD**.

**The formulas (p. 36–37):**

> TBW ≈ (Capacity × NAND P/E cycles) ÷ WA
>
> DWPD = TBW ÷ (365 × years × Capacity)

where **WA = Write Amplification (寫放大)** — the ratio of data actually written to flash vs data the host sent (garbage collection forces extra internal writes; WA depends heavily on firmware quality and whether your workload is sequential or random). Full treatment in Chapter 4.

**Matching DWPD to workload (p. 34–36, Table 1-8, Figs 1-22/1-23).** Applications split into **write-intensive (WI)** and **read-intensive (RI)**. Real-world data: **83% of applications need less than 1 DWPD**; mainstream consumer SSDs are ~**0.3 DWPD** (you'll almost never fill your laptop drive daily). High-DWPD drives cost more, so architects tier data: hot OLTP data on expensive write-intensive SSDs, warm read-mostly data on read-intensive SSDs, cold data on cheap HDDs.

### 1.5.4 Data reliability — pp. 37–41

Three metrics:

- **RBER (Raw Bit Error Rate)** — how often the raw flash flips bits *before* any correction. This reflects flash quality.
- **UBER (Uncorrectable Bit Error Rate)** — probability of a bit error that survives *even after* error correction. This is the number users care about.
- **MTBF (Mean Time Between Failures)** — whole-product reliability in hours.

**Why flash flips bits at all (p. 38):** ① program/erase wear (P/E cycling), ② **read disturb** (讀取乾擾 — reading a page slightly disturbs neighbors), ③ **program disturb** (編程干擾 — writing disturbs neighbors), ④ **data retention** loss (數據保持 — trapped charge leaks over time). The controller fights back with **ECC (error-correcting codes**, e.g., BCH) and sometimes internal RAID — but correction has limits, hence UBER.

Relationships shown in the figures: stronger ECC → exponentially lower UBER *(p. 38, Fig 1-24)*; lower RBER → exponentially lower UBER *(p. 39, Fig 1-25)*; RBER rises as the flash wears *(p. 40, Fig 1-26)* — at end of life you may face ~1 bad bit per 100; and RBER varies *within* a block: upper pages can be ~100× worse than lower pages *(p. 40, Fig 1-27)*. Typical requirements *(p. 40, Table 1-9)*: enterprise SSDs demand lower UBER (commonly 10⁻¹⁶) than consumer (10⁻¹⁵).

**MTBF (p. 41).** Computed per standards (MIL-HDBK-217, Bellcore/Telcordia, China's GJB/Z299B) from component failure rates, and for SSDs tested per **JESD218A** — crucially, MTBF depends on workload: the same drive rated 1.2M hours at 20 GB/day of writes becomes 2.5M hours at 10 GB/day and 4M hours at 5 GB/day.

### 1.5.5 Power & thermals — pp. 41–45

**SSD power states (p. 41–42):** Idle → Standby/Sleep (consumer: 100–500 mW) → **DevSleep** (<10 mW; a newer SATA/PCIe state for system hibernation where the SSD shuts nearly everything off). Max active power occurs under sustained sequential writes (all flash channels busy + controller at full tilt).

**Host power states S0–S5 (p. 42):** the host drives power transitions; the SSD follows. S0 = working; S1/S2 = light sleep variants; S3 = sleep (RAM stays alive, SSD off); S4 = hibernate (RAM contents written *to the SSD*, then everything off); S5 = soft-off.

**The latency trade-off (p. 42–43, Table 1-10).** Entering/leaving low-power states takes time (exit is slower). Firmware must pick a timer: switch to low power too eagerly and you hurt performance on wake; too lazily and you waste energy. Low power matters enormously for laptops, much less for enterprise (which prioritizes consistent performance). Figs 1-28/1-29 *(pp. 43–44)* show AnandTech comparisons of slumber power and max write power across drives — max write power tracks write performance, since flash writes dominate consumption.

**Thermal throttling (p. 44–45, Fig 1-30).** The controller and flash are the heat sources. When a temperature sensor hits a threshold (e.g., 70 °C), firmware reduces the number of parallel flash writes → temperature falls → performance falls too; when it cools below threshold, parallelism (and heat) return. The result is the sawtooth performance-vs-temperature oscillation in Fig 1-30. This matters most in hot ambient environments (50–60 °C).

### 1.5.6 System compatibility — pp. 45–47

The least quantifiable spec and the most painful in practice: a drive with beautiful benchmark numbers that isn't recognized by some motherboard is "a pretty vase — nice to look at, useless." Three categories:

1. **BIOS/OS compatibility (p. 46).** The boot chain: link negotiation at the electrical level → BIOS issues Identify to read drive info (part number, firmware version) → reads SMART → finds and loads the MBR → MBR reads the partition table → hands control to the partition boot record → OS loads via normal reads. A failure at *any* step = boot failure or blue screen. Because there are thousands of motherboard × BIOS × OS combinations, compatibility certification must cover OS types/versions, chipsets (Intel/AMD), BIOS versions, and key applications.
2. **Electrical/hardware compatibility (p. 46–47).** The drive must tolerate imperfect-but-in-spec signals (jitter, marginal signal integrity), temperature extremes, and EMI — robustness comes from good power-regulator and signal-integrity design.
3. **Error tolerance (p. 47).** When the *host* misbehaves (CRC errors, dropped packets, malformed commands), the SSD must at minimum not brick itself (變磚 = "turn into a brick"), and ideally return proper error status plus logs for debugging.

The authors' verdict: compatibility is earned through long, painful accumulated experience — "the mines must be stepped on" — and it's a core competitive advantage.

---

## 1.6 Form factors (接口形態) — pp. 47–57

Because SSDs are standardized commodities, standards bodies define **Form Factors** — physical dimensions + connector + electrical specs *(p. 47–48, Fig 1-31, Table 1-11)*. The interface landscape at the time:

- **SATA SSDs** — the volume leader; consumer (mostly M.2 and 2.5″) and low-end enterprise.
- **PCIe SSDs** — rising fast since 2016 thanks to NVMe; consumer = M.2, enterprise = 2.5″/U.2/AIC (add-in card).
- **SAS SSDs** — enterprise arrays only, riding the mature SAS ecosystem; 2.5″.

**1.6.1 — 2.5-inch (p. 49).** The enterprise mainstay: a 1U server front panel fits 20–30 of them. As flash density grows, one 2.5″ shell can hold 16–32 TB.

**1.6.2 — M.2 (p. 50–51, Figs 1-32/1-33).** Originally "NGFF," designed for ultrabooks. The naming code is **width × length in mm**: Type 2280 = 22 mm wide, 80 mm long (also 2242, 2260, 22110, etc.). Thickness and single/double-sided mounting are specified separately. The critical detail is the **key notch**:

- **B key (Socket 2):** supports SATA or PCIe ×2 → up to ~2 GB/s
- **M key (Socket 3):** adds PCIe ×4 → up to ~4 GB/s; the mainstream going forward
- B+M keyed cards fit both sockets.

M.2 defines only the physical/electrical connector — whether a given card speaks SATA or NVMe/PCIe depends on the product.

**1.6.3 — BGA SSD (p. 51–55).** The whole SSD (controller + flash) in one soldered-down chip package. Benefits vs an M.2 stick *(p. 52)*: ~15% board-space saving, ~10% battery-life gain, 0.5–1.5 mm height saving, better heat conduction through the solder balls. Samsung's PM971 (2016) opened the consumer era. The book profiles Longsys's **P900** *(pp. 53–55)*: at 11.5 × 13 mm the world's smallest NVMe SSD at the time — PCIe Gen3 ×2, NVMe 1.3, 64-layer 3D TLC, and notably **HMB (Host Memory Buffer)**: the SSD borrows a slice of the host's RAM instead of carrying its own DRAM, cutting cost and power. It also supports Boot Partition (host can boot without a separate SPI flash chip).

**1.6.4 — SDP (p. 55–57).** "SATA Disk in Package" (a Longsys product concept): controller + flash sealed into one tested module (33.4 × 17.2 × 1.23 mm, 1.9 g) — a semi-finished SSD needing only a case. Point: modular manufacturing cut production from 15 days to 1 day and scaled capacity from 15K to 100K units/day.

**1.6.5 — U.2 (p. 57).** Also known as SFF-8639: a 2.5″-drive connector that **unifies SATA, SAS, and PCIe on one socket**, simplifying deployment. Expected to become the main enterprise form factor as PCIe displaces SATA/SAS.

---

## 1.7 The solid-state storage market — pp. 57–61

**1.7.1 — SSD is replacing HDD (p. 58–59).** Consumer SSD attach rate hit 30–40% in 2017, predicted >50% in 2018 *(Fig 1-41)*. The pace of replacement is governed by one variable: **price per GB of flash**. At writing, a 128 GB SSD cost about the same as a 1 TB HDD — an ~8× per-GB gap — but flash density growth (Moore's law) was steadily closing it *(p. 59, Fig 1-42)*.

**1.7.2 — Where each belongs (p. 59): data tiering by temperature.**

- Acceleration tier → PCIe SSDs
- Hot data (frequent access) → SATA/SAS SSDs
- Warm data → fast HDDs
- Cold data → HDDs
- Archive → cheap high-capacity HDDs or tape

SSD = performance-first, smaller capacity; HDD = capacity/price-first. (熱/溫/冷數據 = hot/warm/cold data.)

**1.7.3 — Market structure (p. 60–61, Fig 1-43).** Per 2016 TrendFocus data, **Samsung held roughly half the SSD market**, powered by owning both controller and (industry-leading) flash media. Since **flash is 90%+ of an SSD's cost**, flash fabs (原廠) dominate — especially in cut-throat consumer SSDs. Non-fab players like Kingston and Lite-ON still carved out 5–10% via brand and channel strength, buying flash and third-party turnkey controllers. The market is a three-way dance: **flash fabs + controller vendors + channel/brand SSD makers**.

---

## Key vocabulary — for decoding the original figures

| 中文 | English |
|---|---|
| 固態硬盤 | solid-state drive (SSD) |
| 機械硬盤 | mechanical hard drive (HDD) |
| 閃存 | flash memory (NAND) |
| 主控 | (main) controller |
| 固件 | firmware |
| 緩存 | cache / buffer |
| 介質 | storage medium |
| 接口 | interface / connector |
| 映射表 | mapping table |
| 垃圾回收 | garbage collection |
| 磨損平衡 | wear leveling |
| 壞塊管理 | bad block management |
| 擦除 / 寫入(編程) / 讀取 | erase / write (program) / read |
| 覆蓋寫 | overwrite-in-place |
| 壽命 | endurance / lifespan |
| 寫放大 | write amplification (WA) |
| 功耗 | power consumption |
| 時延 / 響應時間 | latency / response time |
| 吞吐量 / 帶寬 | throughput / bandwidth |
| 隨機 / 順序(連續) | random / sequential |
| 容量 | capacity |
| 裸容量 / 用戶容量 | raw capacity / user capacity |
| 空盤 / 滿盤 | empty (fresh) drive / full drive |
| 消費級 / 企業級 | consumer-grade / enterprise-grade |
| 可靠性 | reliability |
| 兼容性 | compatibility |
| 掉電 / 上電 | power loss / power on |
| 原廠 | original flash manufacturer (fab) |
| 顆粒 | flash chips (colloquial: "grains") |
| 熱/溫/冷數據 | hot / warm / cold data |

---

## Check yourself

1. Why does an SSD need a mapping table when an HDD doesn't? *(Hint: what operation can't flash do in place?)*
2. A datasheet says "up to 550 MB/s." Consumer or enterprise drive — and why?
3. A 480 GB SSD uses flash rated 3,000 P/E cycles and its firmware achieves WA = 2. Roughly what TBW should you expect? *(≈ 480 GB × 3000 ÷ 2 = 720 TB)*
4. Your laptop hibernates (S4). What happens to the RAM contents, and which SSD power state exists specifically for this scenario?
5. Why can an M.2 drive with a B key never reach 4 GB/s?

---

*Next up: Chapter 2 — SSD Controllers and All-Flash Arrays.*
