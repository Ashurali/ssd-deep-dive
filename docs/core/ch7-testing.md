---
title: "Ch 7 — SSD Testing"
tags:
  - testing
  - fio
  - jedec
  - snia
  - power-loss-recovery
source_anchor: "CH7 file, pp. 1–54"
---

# SSD Deep Dive — Chapter 7: SSD Testing
## English Study Companion

**Where we are:** Chapters 1–6 built the SSD from the inside out — media, controller, flash physics, FTL, PCIe, NVMe. This final chapter turns to **practice**: how SSDs are actually validated and tested before shipping. It's the least theoretical and, for your internship, probably the **most immediately useful** chapter — the tools (FIO, IOMeter), the equipment (analyzers, jammers, emulators), and the standardized test methods (JEDEC endurance, SNIA performance) are things you may touch directly. Chapter 7 runs pages 1–54 of your file (p. 55 is empty website comments).

**How to use this guide:** Section numbers match the book. Page references like *(p. 39, Fig 7-6)* point into your CH7 file so you can view the original table/figure beside the explanation. Because this chapter is practical, I've kept the concrete numbers (FIO command flags, the endurance sample-size formulas, the SNIA test matrix) that you'd actually use, and worked through the calculations. A **"Modern developments"** section at the end updates the tool landscape (the async-I/O story in particular has moved on in a way that beautifully echoes Chapter 6), and there's a short **closing note on the whole book**. Glossary and self-quiz at the very end.

**The chapter's shape:** 7.1 the software tools. 7.2 the vocabulary of "testing" (verification vs validation). 7.3 the lab equipment (emulator, analyzer, jammer). 7.4 regression testing. 7.5 DevSleep testing. 7.6 PCIe interop/compliance. 7.7 measuring write amplification. 7.8 endurance testing (the most formula-heavy section). 7.9 certification bodies. 7.10 performance testing (the SNIA methodology). If your time is limited, **7.1 (FIO), 7.8 (endurance), and 7.10 (performance)** are the ones that map to real bench work.

---

## 7.1 SSD testing software — pp. 1–15

### 7.1.1 FIO — the king of performance testing ⭐⭐ *the one tool to actually learn*

**FIO (Flexible I/O tester)** is the book's "number one tool" for SSD performance. It's open-source, written by **Jens Axboe** — a Linux kernel heavyweight who maintains the **block device layer** (the layer between the filesystem and the device driver, i.e., the one closest to SSDs) and wrote the Deadline and CFQ I/O schedulers. *(p. 1–2)*

**Concepts you need first (p. 2–3) — these are storage-testing fundamentals, not just FIO trivia:**
- **Threads** — how many read/write tasks run in parallel. One CPU core runs one thread at a time; more parallelism needs more threads (or time-slicing).
- **Sync vs async mode** — this is *the* key idea. A host sends a command in a few microseconds, but the SSD takes hundreds of μs to ms to finish it. In **sync mode**, the thread issues one command then *sleeps* until the result returns — which wastes the SSD, because an enterprise SSD has 8–16 channels × 4–16 parallel units = **32–256 commands executable at once**, and sync mode keeps only *one* busy. So real testing uses **async mode**: fire a command, don't wait, keep firing; completions come back via interrupt/polling. Now all the parallel units get work → huge efficiency gain.
- **Queue depth** — in async mode you can't fire *infinitely* (a stalled SSD would let commands pile up, exhausting memory). Queue depth caps outstanding commands: depth 64 means the queue holds 64; when full, no new commands until some complete. *(This is the same SQ depth concept from Chapter 6, seen from the test side.)*
- **Offset** — start testing from a byte offset into the device/file (e.g., offset=4G).
- **DirectIO** — Linux normally buffers reads/writes in a kernel cache (fast, but lost on power-off, and *hides true device speed*). **DirectIO bypasses the cache** to read/write the SSD directly — essential for honest benchmarks.
- **BIO (Block-IO)** — Linux's block-request structure (carries LBA, size, memory address).

**A real FIO command, flag by flag (p. 4) — worth memorizing the important ones:**
```
fio -rw=randwrite -ioengine=libaio -direct=1 -thread -numjobs=1 \
    -iodepth=64 -filename=/dev/sdb4 -size=10G -name=job1 -bs=4k \
    --output TestResult.log
```
- `-rw=randwrite` — access mode: `randwrite`/`randread` (random), `write`/`read` (sequential), or mixed.
- `-ioengine=libaio` — `libaio` = async; `sync` = synchronous.
- `-direct=1` — use DirectIO (bypass cache). **Almost always 1 for real tests.**
- `-thread` — use threads (lighter than processes).
- `-numjobs=1` — threads per named job. **Total threads = jobs × numjobs.**
- `-iodepth=64` — queue depth.
- `-filename=/dev/sdb4` — target (a device, partition, or file).
- `-size=10G` — data per thread.
- `-bs=4k` — block size per I/O. **This is where you set 4 KB for the classic 4K IOPS test.**

**Reading FIO output (p. 5–7):** the aggregate line matters most. `aggrb=784568KB/s` ÷ 4 KB = **~196K IOPS**. Latency breaks into **slat** (submission latency — time to issue), **clat** (completion latency — time to execute), and **lat** (total). FIO also prints **percentiles**: `90.00th=[684]` means 90% of reads completed within 684 μs — this is how you read tail latency / QoS.

**FIO can also verify data integrity (p. 7):** `-verify=<algo>` (md5, crc32c, sha256…) with `do_verify=1` writes then reads-back-and-checks; `verify=meta` embeds timestamps and logical addresses (so it catches the "wrong-LBA" mix-ups from Chapter 6's data-protection discussion). Note the memory cost: FIO stores every block's checksum in RAM. Config files (`fio test.log`) let you script all this. *(This R/W/C — read/write/compare — integrity testing recurs throughout the chapter.)*

### 7.1.2–7.1.6 The GUI benchmarks (p. 8–15) — *know what each measures and its data-pattern trap*

The book surveys five consumer/Windows tools. The recurring gotcha to understand: **whether a tool uses compressible or incompressible test data drastically changes results on compressing controllers** (like SandForce).

- **AS SSD Benchmark (p. 8–9)** — German tool; tests sequential, 4K, 4K-QD64 (to expose NCQ), and access time; gives a composite score. Uses **random (incompressible) data** — realistic. Also reports whether AHCI is on and whether partitions are 4K-aligned. Needs ≥2 GB free; a full run ~1 hour.
- **ATTO Disk Benchmark (p. 10–11)** — tests across block sizes (512B→8K). Uses **all-0 (highly compressible) data** by default → flattering numbers on compressing drives; represents a best-case ceiling, not typical use.
- **CrystalDiskMark (p. 11–13)** — sequential, random 512K, 4K, 4K-QD32. Defaults to **incompressible data**, but has `0Fill`/`1Fill` options that switch to compressible data (title bar flags it) — same caveat as ATTO. Bigger test files reduce cache interference (truer result) but wear the drive more.
- **PCMark Vantage (p. 13)** — whole-PC benchmark with a storage component modeling real app traces (boot, app launch, media). *(This one is dated — see modern note.)*
- **IOMeter (p. 13–15)** — the most *configurable* tool: set LBA range, queue depth, data pattern, random/sequential mix, R/W ratio, duration. Reports IOPS, MB/s, average response time, CPU utilization. No GUI report viewer — export the CSV to Excel. A typical run is ~10 minutes.

---

## 7.2 Verification vs Validation — pp. 15–16 ⭐ *a vocabulary distinction worth getting right*

Chinese says "测试" for everything; English splits it into Simulation, Emulation, Verification, Validation, Test, QA. The two that matter here hinge on the **chip design flow**: (1) requirements → (2) architecture → (3) ASIC design (assemble IP) → (4) **tape-out** → (5) chip returns.

- **Verification** = testing *during design* (using an **Emulator** or **FPGA**, before the chip exists) — *"helping the ASIC do the thing right."*
- **Validation** = testing *after the chip returns* (using a dev board) — *"confirming the ASIC did the thing right."*

The stakes differ enormously: a bug found in **Verification** is cheap — the ASIC engineer fixes the RTL, reloads the emulator database or FPGA bitfile, re-tests. The *same* bug found in **Validation** is expensive — it may require a **re-tape-out** (with metal fix) or a firmware workaround to "cover" for the hardware. This is why so much effort goes into pre-silicon verification.

---

## 7.3 Test equipment — pp. 16–27

### 7.3.1 Emulator (p. 16–18)

First, **Simulation vs Emulation**: a **Simulator** is *software* that models the chip's function and outputs results; an **Emulator** is *hardware* that reproduces the chip's internal design to run its function. In controller design, besides RTL simulation you do Verification on an **Emulator** (e.g., Cadence Palladium) or an **FPGA**. Emulator vs FPGA trade-offs *(p. 17–18)*:
- **Price:** Emulator ~$1M+; FPGA ~$1K–10K.
- **Capacity:** Emulator ~billions of gates (whole ASIC fits); FPGA ~millions (one FPGA might hold only the front end — PCIe+NVMe — needing a second for the flash controller).
- **Debug:** Emulator easily exports internal signals/waveforms; FPGA connects more easily to protocol/logic analyzers.
- **Speed:** FPGA is *much* faster — the book's line: booting an OS might take hours on FPGA but **days** on an emulator.

Both let the **firmware team start before silicon returns**, skipping the painful bring-up-then-guess-if-it's-hardware-or-code phase.

### 7.3.2 Protocol Analyzer (p. 18–24) ⭐ *you saw its output already*

SSD front ends fall into two protocol families: **SATA/SAS** and **PCIe**. An **Analyzer** is a **wiretap**: it sits on the link between host and SSD and shows you *everything* they say to each other, invisibly. (This is exactly the tool that captured the NVMe/PCIe trace in Chapter 6.)
- **SATA/SAS Analyzers** — vendors: SerialTek, LeCroy *(Figs 7-9 to 7-11)*.
- **PCIe Analyzers** — vendors: LeCroy, SerialTek, Agilent *(Figs 7-12 to 7-14)*; use **interposer** cards, and can *decode NVMe/AHCI* on top of the raw PCIe. Unlike an oscilloscope, an analyzer parses all lanes' transactions per the protocol and provides **triggers**.

**The hard part (p. 24):** capturing correctly across **power-state transitions**. The book's real example — a `CfgWr` writes the wrong value, but *only when ASPM is enabled*. Power transitions stress the link and can corrupt packets; to debug, the analyzer must capture *every* TLP as the link exits L0s back to L0 — and L0s exit is so brief the analyzer must lock on within tens of **FTS** (Fast Training Sequences) of leaving electrical idle. *"Tools are dead, people are alive"* — knowing when to capture, where, and how to set triggers is the engineer's skill.

### 7.3.3 Jammer (p. 24–27) ⭐ *the robustness tool*

??? example "🎬 Animate this — The Packet Dresser & ACK/NAK Lab"

    Dress a TLP layer by layer, then let the Jammer corrupt the wire and watch ACK/NAK recover.

    [Animation page](../animations/packet-dresser.md) · [open full-screen ↗](../animations/files/packet_dresser.html)

    <iframe src="../../animations/files/packet_dresser.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Packet Dresser & ACK/NAK Lab"></iframe>


The motivation (p. 25): an SSD ships to countless customers with unknown hosts, OSes, drivers, and environments. Someday one host will send a malformed FIS/primitive. The book's memorable vignette: the SSD lovingly reads data from flash, ECC-decodes it, checks it, hands the host an `X_RDY`, hopefully awaits an `R_RDY` — and the host coldly replies `R_ERR`, rejecting it. The requirement — *"however many times the host abuses you, treat it like your first love"* — is called **Robustness**, and it demands extensive **error handling** in RTL and firmware. The problem: these error paths might not trigger once in a week of normal lab testing, and no engineer can foresee every error.

**Solution: the Jammer.** If an Analyzer is a *wiretap*, a Jammer is a *mail carrier* — **all traffic passes through it, and it can open, modify, or replace the contents**, then forward *(Figs 7-15/7-16)*. So you can deliberately turn a normal `R_RDY` into `R_ERR`, or inject a **CRC error into a Data FIS**, and check the SSD handles it correctly. It's also a *scenario explorer* — e.g., if the device sets an Error bit in its SDB, or never sends the SDB, does the host resend? How many times? Does the driver start OOB? Does the app error out? *"Better to make trouble for yourself than let others find it."*

---

## 7.4 Regression testing — pp. 27–29

Firmware changes constantly — new features, bug fixes, requirement changes, performance tuning — and every change risks **breaking something that worked** (fixing Bug B reopens last month's Bug A, or creates Bug C). This is nearly unavoidable. **Regression testing** = ensuring new code hasn't broken existing function, by re-running some or all existing test cases.

The catch (p. 28): you *can't* re-run everything on every firmware build — not enough people, drives, or time. So you **select** wisely *(p. 29)*: prioritize frequently-failing tests (e.g., stress tests), user-visible functions (benchmarks), core functions, in-progress/just-completed features, **data-integrity tests (R/W/C)**, and **boundary-value tests**. The book cites that effective regression testing saves ~60% of bug-fix time and ~40% of cost — and invokes the parable of the physician Bian Que: treat illness early.

---

## 7.5 DevSleep testing — pp. 29–32

**DevSleep (DevSlp)** is the ultra-low-power SATA state from Chapter 1 (<10 mW). Testing it needs two abilities: get the device *into* DevSleep, and *detect* the state. Detection uses the **SATA Status Register** — bits [11:8] map to Interface Power Management (IPM), so reading it tells you what state the host is commanding *(p. 29–30, Table 7-1)*. Register reads confirm entry/exit, but the *physical-layer timing parameters* (MDAT, DETO, etc.) need a proper instrument — a LeCroy SATA analyzer with a **special DevSleep-supporting cable** *(p. 30, Fig 7-18)*.

Two test cases *(p. 30–32)*:
- **IPM-12 (entering DevSleep):** put the SSD in DevSleep, then keep sending packets while DevSleep is asserted and confirm the SSD **does not respond**, and that timing params are in range. Key numbers: **MDAT** — the host must assert DevSleep (the "lullaby") for at least **10 ms**; **DXET** — the device must be asleep within **100 ms** (example: it slept at 60 ms). Crucially, while DevSleep is asserted, the host hammers **COMRESET** to try to wake it — if the device *detects* COMRESET and wakes, **the test fails** (it must stay asleep).
- **IPM-13 (exiting DevSleep):** exit doesn't need a full power-up — a **COMWAKE** signal brings the link quickly to PHY Ready. **DETO** — the device must respond to the OOB signal within **20 ms** of DevSleep de-assertion. (Just *responding* passes IPM-13; whether OOB completes is a separate OOB test.)

---

## 7.6 PCIe InterOp — pp. 32–36

**PCI-SIG** (the PCIe standards body) runs **Compliance Workshops** where companies test products. Two parts:

**Compliance testing (p. 33) — "you fight only your future spouse":** your product is tested against the *spec* across five areas — **Electrical** (PHY Tx/Rx), **Configuration** (config space), **Link Protocol**, **Transaction Protocol**, and **Platform BIOS**. Pass all, and PCI-SIG adds your device to the **Integrators List** (the "honor roll").

**Interoperability testing (p. 34–36) — "the sword-fighting summit":** here you test your product *against other companies' products* to check they team up correctly. The book's worked example of interop steps with a hypothetical partner (Synopsys, an IP vendor): (1) read each side's **Link Capability Register** for speed [3:0] and width [9:4]; (2) say your SSD is Gen3×4, partner RC is Gen3×16; (3) plug into the partner's dev board; (4) power on, confirm the OS sees the SSD and the **Link Status Register** shows Gen3×4; (5) if the SSD supports narrower widths (×1), physically reduce lanes (tape/reducer) and re-verify; (6) run a simple data transfer to confirm data flows. Upload results to PCI-SIG. The prep lesson *(p. 36)*: before the workshop, test against many real RCs/motherboards yourself — grab ~10 recent Intel/ASUS/Gigabyte boards, power-cycle each ~200 times (needs **automation**), checking link speed/width.

---

## 7.7 Write Amplification testing — pp. 36–37 ⭐ *simple and practical*

Recall from Chapter 4: **WA = data written to flash ÷ data written by host.** To measure it, you need both numbers, and they come from **SMART** data. *(p. 36–37)*
- **Host-written data** is reported directly (e.g., SandForce SMART attribute *241: Lifetime writes from host*).
- **Flash-written data** often isn't reported directly, so use a second formula: **flash-written = average Wear Leveling count × SSD capacity.** The Wear Leveling count is the average P/E cycles across blocks (e.g., Micron's SMART *173: Wear Leveling Count*).

The practical tip: in internal testing this is trivial — just ask the firmware team to **expose both attributes** in SMART, and the test engineer can compute the drive's WA directly. *(This is exactly the kind of firmware↔test collaboration your internship involves.)*

---

## 7.8 Endurance testing — pp. 37–46 ⭐⭐ *the formula-heavy core*

??? example "🎬 Animate this — The SSD Calculator Bundle"

    This section's formulas as live sliders — move an input and watch the answer (and the curve) recompute.

    [Animation page](../animations/ssd-calculators.md) · [open full-screen ↗](../animations/files/ssd_calculators.html)

    <iframe src="../../animations/files/ssd_calculators.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The SSD Calculator Bundle"></iframe>


Every SSD must pass strict **endurance** testing before shipping. **JEDEC** provides two specs: **JESD218A** (the *method*) and **JESD219** (the *workload*). *(p. 37–38)*

**Key concepts:**
- **TBW** — total bytes written (the endurance rating).
- **FFR (Functional Failure Requirement)** — allowed cumulative functional failures during the whole write process.
- **Data Retention** — ability to hold data while powered off.
- **UBER** — Uncorrectable Bit Error Rate = data errors ÷ bits read.

Enterprise vs consumer requirements differ across **operating time, operating temperature, UBER, and retention temperature/time** *(p. 38, Table 7-5)*. Importantly, **JESD218A tests both endurance AND data retention.** Two methods: **Direct** ("straight-ahead") and **Extrapolation** ("roundabout"); the book focuses on Direct.

**Direct method essentials (p. 38–39):** write hard, read hard — *"push the SSD to the limit"* — with (a) required high/low temperatures, (b) the specified workload, and (c) a **retention test immediately after** endurance.

**How many drives to test? — the sample-size calculation (p. 39–41). This is the part to actually understand:**
- **Requirement 1:** if it's the series' *first* test, pull samples from **≥3 non-consecutive production lots**; otherwise one lot is fine.
- **Requirement 2:** two formulas govern sample size **SS**:
  - `UCL(functional_failures) ≤ FFR × SS`
  - `UCL(data_errors) ≤ min(TBW, TBR) × 8×10¹² × UBER × SS`
  - **UCL** = Upper Confidence Limit — don't derive it, just look it up in a table *(Table 7-6)*. With **AL=0** (zero accepted functional failures), UCL = **0.92**.

**Worked example (p. 40):** FFR=3%, UBER=10⁻¹⁶, TBW=100:
- SS ≥ 0.92 ÷ 0.03 = **30.1** (functional-failure requirement)
- SS ≥ 0.92 ÷ (100 × 1 × 8×10¹² × 10⁻¹⁶) = **11.5** (data-failure requirement)
- Take the **larger** → 30.1 → round up → **31 drives.**
- Plug SS=31 back: UCL(data_errors) ≤ 100 × 1 × 8×10¹² × 10⁻¹⁶ × 31 = **2.48** → reverse-look-up *(Table 7-7)* → **max allowed data errors = 1.**
- **Conclusion:** test 31 drives; to pass, allow **zero functional failures and at most 1 data error.**

The **JESD219 workload** for consumer SSDs is ~**400 million** write/trim/flush commands, with read-back verification after each write.

**Temperature acceleration (p. 41–43) — the clever part.** Endurance/retention testing uses controlled high/low temperatures (enterprise requirements much stricter than consumer). Two strategies: **Ramped-Temperature** (all drives together, cycling hot/cold) vs **Split-Flow** (half hot, half cold). Low temp ≤ 25°C; high temp is a range (e.g., client SSD: 40°C ≤ T ≤ Tmax). **Higher temperature accelerates aging**, so you can simulate a year of use in less time *(Table 7-9)*: e.g., at **86°C**, **50 hours** of the official workload = **1 year** at room temp; but at only **48°C**, you'd need **3000 hours** for the same effect.

**Determining Tmax (p. 43) — a worked chain worth following:**
- 160 GB TLC SSD at 500 P/E cycles → TBW = **80 TB**.
- One workload pass = 1 TBW → need **80 passes**.
- One pass takes ~5 hours → total = **400 hours**.
- Look up 400 hours in Table 7-9 → **66°C** (client, ramped) → that's **Tmax**.

The full **Direct Method / Ramped flow (p. 43–45, Fig 7-23):** (1) sample selection → (2) endurance test → (3) optional component-level room-temp retention → (4) write data for retention test → (5) optional product-level room-temp retention → (6) high-temp retention → (7) data comparison → (8) pass/fail (check FFR and data-errors against the two formulas). Steps 3–7 are the retention test, run *immediately* after endurance: **write → power off → high temp → power on → compare.**

**Extrapolation method (p. 45–46):** shortcuts to finish faster — modify the workload to inflate P/E cycles quickly, or **shrink the drive** via firmware (limit a 160 GB SSD to 40 GB → endurance time drops from 400h to 100h, with high-temp adjusted 66°C → 79°C). **Critical caveat:** when firmware shrinks the drive, it must shrink the internal **OP proportionally** too — otherwise the reduced drive has artificially generous over-provisioning and the WA (and thus wear) won't match the real product.

---

## 7.9 Certification — pp. 46–50 ⭐ *the external bodies*

Beyond internal testing, SSDs go out for third-party certification:

- **SATA-IO (p. 46–48)** runs two event types. **Plugfest** — *development-stage* products, informal vendor-to-vendor testing, results not submitted. **IW (Interoperability Workshop)** — *production* products, SATA-IO-led with fixed procedures; results submitted, and passing devices join the **Integrators List**.
- **PCI-SIG Compliance Program (p. 48)** — the five test areas from §7.6 (Electrical, Configuration [tool: PCIE CV], Link Protocol, Transaction Protocol, Platform BIOS); passing joins the Integrators List.
- **UNH-IOL NVMe (p. 48–50)** — the University of New Hampshire InterOperability Laboratory, a famous public test lab. Defines **NVMe Conformance** and **NVMe Interoperability** test suites (updated alongside the NVMe spec) and provides tools: **IOL INTERACT PC Edition** (open-source, GUI, easy) and **IOL INTERACT Teledyne-LeCroy Edition** (advanced; drives a LeCroy PCIe Exerciser+Analyzer to auto-run conformance tests and auto-capture traces). Completing conformance (both tools) plus interoperability (VDbench) gets you onto the **NVMe Integrators List**.

---

## 7.10 SSD Performance testing — pp. 50–54 ⭐⭐ *the SNIA methodology*

??? example "🎬 Animate this — The Toy SSD Sandbox"

    This section's walkthrough as a live simulation — write, overwrite, collect, and watch WA respond to the OP slider.

    [Animation page](../animations/toy-ssd-sandbox.md) · [open full-screen ↗](../animations/files/toy_ssd_sandbox.html)

    <iframe src="../../animations/files/toy_ssd_sandbox.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Toy SSD Sandbox"></iframe>


**SNIA** publishes performance-test specs for both client and enterprise SSDs. The whole methodology rests on one truth from Chapter 1: **SSD performance changes as the drive is used**, so you must measure in a controlled, repeatable state.

**The three performance phases (p. 50–51, Fig 7-27) — the core concept:**
- **FOB (Fresh Out of Box)** — a brand-new drive; performance is inflated ("power level over 9000 but not sustainable") — *not* representative of real long-term use.
- **Transition** — after some read/write, performance declines toward stability.
- **Steady State** — performance stabilizes in a band; **all reported metrics (throughput, IOPS, latency) MUST be measured here.** The rule: steady state = performance varies **≤ ±10%** over the measurement window.

**Four setup concepts (p. 51–52):**
- **Purge** — before *every* performance test, erase the drive to a known state (removes the influence of prior operations — e.g., small-block random writes distorting a following large-block sequential test). Think of Purge as **"return the drive to FOB."** Methods: ATA **Security Erase / Sanitize (Block Erase)**, SCSI **Format Unit**, or a vendor tool.
- **Precondition** — drive the drive into steady state in two steps: **WIPC (Workload-Independent Preconditioning)** first (write *without* the test workload), then **WDPC (Workload-Dependent Preconditioning)** (write *with* the test workload).
- **Active Range** — the LBA range you send I/O to during the test.
- **Data pattern** — performance tests **must use random (incompressible) data** written to flash.

**The IOPS test procedure (p. 52–54) — the canonical example:**
1. **Purge** the SSD.
2. **WIPC:** write the whole drive twice with 128 KB sequential.
3. **WDPC + Test:** run **Random I/O** across a matrix of **7 R/W mixes** (100/0, 95/5, 65/35, 50/50, 35/65, 5/95, 0/100) × **8 block sizes** (1024K, 128K, 64K, 32K, 16K, 8K, 4K, 512B) = **56 combinations per round**, each run 1 minute. Use the **0/100 (100% write), 4 KB** result to judge steady state. Record data in the **measurement window** (the round where steady state is reached, call it x; Round 1→x is the convergence interval, Round (x−4)→x is the 4-round measure window). If steady state isn't reached in 25 rounds, either continue or just take x=25. **Steps 2→3 must not be interrupted.**

**Throughput and Latency tests (p. 54):** same skeleton, different matrices.
- **Throughput:** only two combos — 1024K sequential write and 1024K sequential read; judge steady state on sequential write.
- **Latency:** only 3 R/W mixes (100/0, 65/35, 0/100) × 3 block sizes (8K, 4K, 512B), with **queue depth and thread count both set to 1** (to measure true per-command latency, not throughput).

**Write Saturation Test (WST, optional):** long-duration random 4K writes to see behavior after sustained writing. The book cites TechReport's famous 18-month endurance experiment — 6 drives written **over 2 PB** each. The full config matrix is in *(Table 7-10)*.

---

## 📌 Modern developments (post-2018 supplement)

*Testing methodology is more stable than the hardware — the JEDEC endurance specs, the SNIA performance methodology, and the certification bodies are all still current and still used essentially as described. But the tooling has moved on, and one change echoes Chapter 6 so neatly it's worth calling out. This section is drawn from current knowledge of the storage-testing landscape.*

**The async-I/O story got a sequel — io_uring, and it mirrors NVMe.** The book's FIO discussion centers on **libaio** as *the* Linux async engine. Since then, **Jens Axboe (FIO's author, still the Linux block-layer maintainer, now at Meta) created `io_uring`** — a new async-I/O interface that merged into the Linux kernel in 2019 and has become the high-performance path that supersedes libaio for demanding storage work. Here's the elegant part: **io_uring is built on two ring buffers shared between application and kernel — a submission queue and a completion queue** — which is *exactly the SQ/CQ producer-consumer design you learned for NVMe in Chapter 6.* The same architectural idea (rings + doorbells, batch submissions, minimize expensive syscalls/context-switches) that made NVMe fast at the device interface was applied to the *software* I/O path. Practically, **FIO now ships an `io_uring` ioengine** (`-ioengine=io_uring`), and for maximum-IOPS testing of a fast NVMe drive it typically beats `libaio` by cutting per-I/O overhead. If you benchmark a modern drive, io_uring is the current best-practice engine.

**Tool landscape updates.** FIO and IOMeter remain the workhorses (FIO is *the* standard for serious/Linux testing; IOMeter's original project is old but forks/derivatives persist). Among the GUI consumer tools, **CrystalDiskMark** is actively maintained and now defaults to modern NVMe-oriented test patterns (its current versions use a random-4K test at high queue depth, `RND4K Q…T…`, reflecting how NVMe parallelism is exercised). **PCMark Vantage is obsolete** — the current whole-PC storage benchmark is **PCMark 10** with a dedicated storage test using real application traces, and **3DMark Storage** exists for gaming-focused drive testing. ATTO and AS SSD are still around and still carry the compressible-vs-incompressible-data caveat the book emphasizes.

**Standards are current, with newer additions.** **JESD218/219** are still the endurance/retention references; **SNIA's** performance test spec is still the methodology for FOB→transition→steady-state measurement. **UNH-IOL** still runs the NVMe Integrators List and has extended its suites to cover **NVMe 2.x**, **NVMe/TCP**, and **NVMe-oF** (the transports from Chapter 6's supplement) — so the same conformance/interoperability model now spans the modular NVMe family. **PCI-SIG** compliance now covers the newer PCIe generations (the Gen4/5/6 drives from Chapter 5's supplement need compliance at those speeds, which is a much harder electrical test — PAM4 signaling at Gen6 raises the bar significantly).

**One practical note for your internship.** The two things this chapter describes that you're most likely to *do* are (1) run **FIO/IOMeter** performance and R/W/C integrity tests following the **SNIA** purge→precondition→steady-state discipline, and (2) participate in **JEDEC endurance** runs with the temperature-acceleration and sample-size logic above. The firmware↔test collaboration in §7.7 (asking firmware to expose SMART attributes so you can compute WA) is exactly the kind of cross-team interaction the chapter is preparing you for.

---

## 📖 Closing note — the whole book

That completes all seven chapters. Here's the arc you've worked through, and how the pieces lock together:

1. **Overview** — what an SSD is, and the one fact that drives everything: *flash can't be overwritten in place.*
2. **Controller & Arrays** — the brain (channels × dies = parallelism) and what happens when you build arrays of SSDs.
3. **Flash physics** — how a cell traps electrons to store a bit, and every way that goes wrong (the failure catalog).
4. **FTL** — the software that tames the fragile medium: mapping, garbage collection, write amplification, wear leveling, power-loss recovery. *The heart of the book.*
5. **PCIe** — the road: tree topology, layered packets, how bits travel.
6. **NVMe** — the traffic protocol on that road: queues, doorbells, the 8-step command flow.
7. **Testing** — how it's all validated before it ships.

The single thread connecting Chapters 3→4→7: flash is unreliable and wears out (Ch3), so firmware compensates with clever algorithms (Ch4), and testing proves those algorithms actually work under stress (Ch7). And the thread connecting Chapters 5→6→7: PCIe carries the bits (Ch5), NVMe gives them meaning (Ch6), and analyzers/jammers let you watch and stress that conversation (Ch7). The modern supplements traced how the book's 2018 snapshot evolved — host-managed flash became **ZNS/FDP**, PCIe reached **Gen7**, NVMe **restructured and added TCP**, and even the async-I/O path (**io_uring**) borrowed NVMe's ring design.

You now have a complete, self-consistent mental model of how a modern SSD works, from trapped electrons to test bench.

---

## Key vocabulary — for decoding the original figures

| 中文 | English |
|---|---|
| 性能測試 | performance testing |
| 線程 | thread |
| 隊列深度 | queue depth |
| 同步 / 異步 | synchronous / asynchronous |
| 順序 / 隨機讀寫 | sequential / random read-write |
| 數據校驗 | data verification |
| 驗證 / 確認 | verification / validation |
| 仿真 / 模擬 | simulation / emulation |
| 協議分析儀 | protocol analyzer |
| 邏輯分析儀 | logic analyzer |
| 觸發 | trigger |
| 健壯性 | robustness |
| 錯誤處理 | error handling |
| 回歸測試 | regression test |
| 邊界值測試 | boundary-value test |
| 耐久度測試 | endurance test |
| 數據保持 | data retention |
| 總寫入量 | TBW (Total Bytes Written) |
| 樣本大小 | sample size |
| 溫度加速 | temperature acceleration |
| 認證 | certification |
| 一致性測試 | conformance/compliance test |
| 交互性測試 | interoperability test |
| 全新盤 | FOB (Fresh Out of Box) |
| 穩定態 | steady state |
| 擦除 (預處理) | purge |
| 預處理 | preconditioning |
| 飽和寫測試 | write saturation test |

---

## Check yourself

1. In FIO, what's the difference between sync and async mode, and why does sync mode waste an enterprise SSD's performance? (Reference the drive's internal parallelism.)
2. Why must a real FIO benchmark use `-direct=1`? What does the kernel do otherwise that corrupts the measurement?
3. A benchmark reports great numbers using all-0 test data on a SandForce drive. Why is that misleading, and which two tools default to compressible vs incompressible data?
4. Distinguish Verification from Validation. Why is a bug found in Validation so much more expensive than one found in Verification?
5. An Analyzer is a "wiretap"; a Jammer is a "mail carrier." Explain what each does and give one thing a Jammer lets you test that an Analyzer cannot.
6. You need to measure a drive's write amplification. What two numbers do you need, where do they come from, and what's the formula for flash-written data if SMART doesn't report it directly?
7. Endurance test, worked: FFR=2%, UBER=10⁻¹⁶, TBW=50. Roughly how many drives (use UCL=0.92), and which of the two formulas dominates?
8. Explain temperature acceleration in endurance testing. If 400 hours of workload maps to 66°C, what happens to the required time if you test cooler?
9. When Extrapolation testing shrinks a drive via firmware to save time, what must *also* be shrunk proportionally, and why?
10. Why must all SNIA performance metrics be measured in steady state, not FOB? What's the numerical definition of steady state?
11. In the SNIA IOPS test, what's the purpose of Purge and the two-step Precondition (WIPC then WDPC)?
12. Why does the SNIA *latency* test set queue depth and thread count to 1, unlike the IOPS test?
13. **(Modern)** io_uring's design mirrors something you learned in Chapter 6. What is it, and why did applying that idea to the software I/O path improve performance?

---

---

## 📘 2nd-Edition Addendum (their §11.3–11.4)

*The 2nd edition adds two test categories the 1st edition lacked — both squarely in firmware-validation territory.*

## A1. FTL function-module testing (their §11.3)

Beyond the WA test (§7.7), the 2nd edition tests the FTL's other modules directly:

**Garbage-collection test.** Verify the Chapter-4 GC machinery behaves: fill the drive past FOB into steady state and confirm **foreground GC** triggers at the free-block threshold (watch performance step down as it kicks in — the Ch7 §7.10 steady-state transition *is* GC becoming visible); confirm **background GC** runs during idle — a neat trick: you often can't see background GC in I/O, but you *can* see it in the **power trace** (the drive draws active power while "idle"); and measure WA under sequential vs random patterns to validate victim selection is working (random WA should still stay within design targets).

**Wear-leveling test.** Run a deliberately *skewed* workload — hammer a small hot LBA range while a large cold region sits static (the exact scenario from Ch4 §4.5) — then dump **per-block erase counts** via vendor command or SMART. Pass criteria: the max−min erase-count spread (or max/mean ratio) stays within spec, proving static WL is actually relocating cold data onto worn blocks rather than letting the hot region burn out.

## A2. Power-loss recovery testing (their §11.4) ⭐⭐ *the big addition — pure Chapter 4 §4.6 validation*

**Device-level test (their 11.4.1).** The method: a **programmable power module** (the Quarch PPM class of equipment from §7.5's power testing) cuts the drive's power at *random instants* during active writes — repeated for **thousands of cycles**, automated. Each cycle:
1. Write tracked, verifiable data (FIO with `verify=meta` — the Ch7 §7.1.1 mode that embeds LBAs and sequence stamps — or a dedicated journaling tool that records exactly which writes were *acknowledged*).
2. Cut power without warning (this is the "abnormal power loss" of Ch4 §4.6).
3. Restore power. The drive must **enumerate** (no bricking — ever), **rebuild its mapping table** (the Ch4 metadata-scan + snapshot mechanism), and come ready within a bounded recovery time.
4. Verify: **every acknowledged write is intact** — especially anything completed under Flush/FUA semantics; unacknowledged in-flight data may be lost (that's allowed); and critically, **no previously-committed data was destroyed** — i.e., no Lower-Page corruption (Ch3 §3.3.4), the classic failure this test exists to catch.

Target the *nasty windows* deliberately: cut power **during GC**, **during a map-table flush**, **during SLC-cache migration**, and **during a firmware update** — the moments when the most internal state is in flight. For enterprise drives, also validate the **capacitor (power-loss protection)**: measure the hold-up time on a scope/power module and confirm it covers the worst-case cache-flush (Ch4 §4.6's "capacitor supplies tens of milliseconds").

**Whole-system test (their 11.4.2).** Cut **AC power to the entire host** mid-workload instead of just the drive. This exercises the full stack — OS page cache, filesystem journal (Supplement C!), driver, *then* the drive — and matches the real user event (blackout, yanked cord). Its diagnostic value: it separates **device-level data loss** (the SSD's fault) from **OS-level loss** (data that never left the page cache — not the drive's fault), which is exactly the distinction you need when a customer reports "the power went out and I lost my file."

**Why this matters for you:** power-loss recovery is the single most firmware-intensive reliability feature (Ch4 §4.6), and this is its validation. If your internship touches PLR/journaling/mount-time code paths in the BiCS8 firmware, this is the test suite that judges that code.

---

*That's the whole book. If you'd like, I can now build cross-chapter study aids — a master glossary, a one-page "exam cram" sheet, flashcards, or an interactive diagram of how the pieces fit — or go deeper on any single topic for your patent-research project.*
