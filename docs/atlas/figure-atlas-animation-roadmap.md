---
title: "Figure Atlas & Animation Roadmap"
tags:
  - animations
  - flash-physics
  - ftl
  - pcie
  - nvme
  - ecc
  - testing
source_anchor: "catalog of all 359 book figures"
---

# SSD Deep Dive — Figure Atlas & Animation Roadmap
## All 359 figures, audited, tiered, and turned into a build plan

*Written mentor-to-junior: I've been through every figure in this book with you in mind. Here's what each one is, which ones hide the mental models that matter, and exactly what I'd build to make them move. Audit method: caption extraction from all 459 OCR'd pages (359 figures found: Ch1=43, Ch2=34, Ch3=62, Ch4=57, Ch5=68, Ch6=67, Ch7=28), cross-referenced against the full text we've already studied, plus visual spot-checks of the anchor figures (scan quality confirmed — clean line diagrams, fully workable as build references). To look at any figure, open the chapter file to the page number given.*

---

## Part 0 — How a senior engineer reads a figure (and decides what to animate)

First lesson, and it shapes everything below: **you don't animate figures — you animate systems.** A book draws nine separate snapshots of garbage collection because paper can't move; you build *one* interactive sandbox and those nine figures become nine moments of it. So this atlas doesn't map figure→animation 1:1; it maps **figure clusters → ten buildable systems.**

Second lesson: every figure in this book is one of five species, and the species tells you what it wants to be:

| Species | Examples | What it wants |
|---|---|---|
| **Process over time** | GC steps, command flows, handshakes | 🎬 **True animation** — these are the gold |
| **Distribution / curve** | Vt distributions, RBER curves, perf phases | 🎚 **Sliders** — let the reader *drag* the physics |
| **Structure / block diagram** | controller SoC, topology, layouts | 🖱 **Hover-explore** — annotate, highlight datapaths |
| **Format / register layout** | TLP headers, DLLP fields, BAR bits | 📄 **Annotated static** — hover tooltips at most |
| **Photo / chart / logo** | product shots, market pies, screenshots | 🚫 **Skip** — zero teaching value in motion |

Third lesson: the figures worth the most effort are the ones **juniors reliably misunderstand until they see them move.** In this book, those are: threshold-voltage distributions drifting (Ch3), the GC/OP/WA dance (Ch4), the SQ/CQ/doorbell ring (Ch6), packet dressing + ACK/NAK (Ch5), and flash timing overlap (Ch3/Ch2). Those five ideas are 80% of what separates someone who's *read* about SSDs from someone who *thinks* in them.

**Tier legend used throughout:**
- 🏆 **T1** — build it; belongs to one of the ten clusters below
- 🔧 **T2** — worth building as a mode/extension of a T1 cluster, or a small standalone
- 📊 **T3** — wants an interactive *calculator/plot*, not an animation
- 📄 — annotated static reference; understand it, don't animate it
- 🚫 — photo/chart/logo; skip
- ✅ — already covered by an animation you've built

---

## Part 1 — The ten animation clusters (the build plan)

### 🏆 Cluster A — The Vt Distribution Playground *(the crown jewel of Ch3, and your patent-presentation asset)*

**Figures absorbed (≈17):** 3-1, 3-2, 3-52 (cell + tunneling), 3-3/3-4/3-5 (SLC/MLC/TLC distributions), 3-9/3-10/3-11 (op voltages), 1-27 (lower/upper RBER), 3-44/3-45 (read/program disturb), 3-46/3-47/3-48 (endurance drift), 3-50/3-53/3-54/3-55/3-56 (retention & disturb shifts, neighbor effects), 3-57 (read retry), 3-60 (randomization effect), plus side-plots 1-24/1-25/1-26 (UBER/RBER/PE curves).

**Why this one first:** Fig 3-3's threshold-voltage distribution is *the* diagram of the entire flash half of the book. Every failure mode in Chapter 3 is "the bells move"; every fix is "cope with the bells moving." Read retry, soft reads, LLRs, LDPC — all of it lives on this one x-axis. I spot-checked the scans (Ch3 p3–4): clean Gaussian humps with read-reference lines, exactly the geometry to recreate.

**The build (scenes):**
1. **Scene 0 — the cell.** One floating-gate transistor (Fig 3-1 geometry). Program button → electrons tunnel *in*, a marker slides right on the Vt axis. Erase → electrons out, marker slides left. This links your existing erase-physics animation down to single-cell level.
2. **Scene 1 — from cell to bell.** Spawn 10,000 cells; their Vt markers pile into a histogram → the bell curve *emerges*. This is the "aha" no static figure delivers: the distribution isn't drawn, it's *population statistics*.
3. **Scene 2 — SLC/MLC/TLC selector.** 2, 4, or 8 bells crammed into the same voltage window. Watch the margins collapse as bits/cell rises — the entire SLC>MLC>TLC story in one toggle.
4. **Scene 3 — the physics sliders.** Three sliders, three failure modes: **P/E cycles** (bells widen + shift — Figs 3-46/48/53), **retention time** (bells drift *left* — Fig 3-54), **read count** (bells drift *right* — Fig 3-55). Overlap regions glow red; a live RBER counter ticks up. Optional: randomization toggle (Fig 3-60 — off = some bells fatten).
5. **Scene 4 — read references & retry.** Draggable read-voltage lines. As bells drift, the fixed lines misread cells (errors flash). "Read Retry" button auto-walks the reference to the new valley (Fig 3-57) — errors vanish *as long as the bells haven't merged.* That last clause is the entire limit of hard-decision reading, made visible.
6. **Scene 5 — soft reads & LLR bridge.** Multiple read strobes subdivide the overlap region; each cell gets an LLR color (confident blue → uncertain gray). One button hands the LLR vector to your existing LDPC visualizer. **This scene is your patent-presentation centerpiece** — it *shows* the exact mechanism the LDPC/soft-read patents optimize.

**Node pre-verify:** the histogram statistics and RBER computation (sample Gaussians, count misreads vs reference positions) — trivial to verify numerically before HTML.

---

### 🏆 Cluster B — The Toy SSD Sandbox *(19 figures become one interactive; extends your existing WA animation)*

**Figures absorbed (≈27):** 4-14→4-22 (the fictional-SSD GC walkthrough), 4-23/4-24/4-25 (WA & OP math), 4-26→4-32 (GC implementation, valid counts, bitmaps), 1-14 (GC concept), 4-35/4-36/4-37 (Trim & the three tables), 4-39→4-42 (wear-leveling cold/hot mixing), 4-49/4-50/4-51 (bad-block skip vs replace), plus live meters realizing 1-21 and 7-27/7-28 (FOB→transition→steady-state performance).

**Why:** the book spends nineteen figures walking one toy SSD through its life because this *is* Chapter 4. You've already built the page/block/WA animation — this is its natural adult form, and it absorbs your planned wear-leveling animation as a scene.

**The build:** a persistent 4-channel × 6-block × 9-page grid (the book's exact toy, Fig 4-14), with:
- **Write modes:** sequential (watch striping across channels — Fig 4-15) vs random. Fill user space, then overwrite — garbage squares darken (Figs 4-17/4-18).
- **GC:** manual "collect" or automatic threshold. Victim selection animates: each block shows its **VPC** (valid-page count, Table 4-3's mechanism); greedy picks the minimum; valid pages fly to a fresh block; erase flashes. Toggle the *find-valid-data* method: **bitmap** (instant lookup, RAM cost shown) vs **read-all + metadata check** (slow crawl) — Figs 4-29→4-33 as a switch.
- **The OP slider** ⭐ — this is the money interaction. Drag OP from 7%→28%→50%; the live **WA meter** re-derives the Fig 4-25 curve *from the simulation itself*, not from a formula. Junior drags, watches WA fall, finally *feels* why enterprises burn capacity on OP.
- **Trim scene:** delete a "file"; without Trim, GC dutifully relocates dead data (WA climbs); press Trim and watch the three tables (map/VPBM/VPC — Fig 4-36) update and GC skip it.
- **Wear-leveling scene:** per-block erase-count heatmap; hot data (red) hammers a few blocks; enable dynamic WL (hot→young blocks), then static WL (cold→old blocks) and watch the heatmap flatten. Include the Fig 4-39→4-42 trap: mix cold data into GC streams and watch it get re-relocated forever (WA creep) vs dedicated cold blocks.
- **Bad-block event:** kill a block mid-run; **skip** strategy (parallelism wobbles 4→3 dies — perf meter stutters) vs **replace** strategy (remap table pops up, parallelism stays 4). Figs 4-49/4-51 as a fault injection.
- **Live meters throughout:** WA, free blocks, and a scrolling performance curve that *naturally reproduces* the FOB→transition→steady-state shape of Figs 1-21/7-27 — because that shape isn't drawn, it *emerges* from GC kicking in. When the junior sees the curve appear on its own, Chapter 7's SNIA methodology stops being ritual and becomes obvious.

**Node pre-verify:** the whole simulation core (block states, VPC bookkeeping, WA accounting) as a headless model with unit tests — then the HTML is just a renderer over it. This is the one where pre-verification pays off most.

---

### 🏆 Cluster C — The NVMe Ring Machine *(SQ/CQ/DB with a wire view)*

**Figures absorbed (≈21):** 6-9 (where SQ/CQ/DB live), 6-10 (the 8-step flow — spot-checked, clean), 6-11→6-20 (ring walkthrough: init, 3 commands in, fetch, 2 completions, head/tail updates, phase tag, piggybacked SQ head), 6-29/6-30 (stack), 6-31→6-39 (the PCIe trace of one read).

**The build:** two panes — **Host memory** (SQ ring + CQ ring drawn as actual circles with head/tail pointers) and **SSD** (doorbell registers + execution units).
- Click "submit" up to N times → commands drop into SQ slots, tail advances, **tail-DB write flies to the SSD** (step 2). SSD fetches (arrows pull commands across), executes (progress bars — out-of-order completion allowed!), completions land in CQ (tail advances), MSI-X bolt fires, host consumes, **head-DB write flies back** (step 8). All eight steps, numbered, pausable, step-through.
- **The two subtle mechanisms that juniors never get from the text, made visible:** (a) the **phase-tag bit** — color each CQ entry by P; watch the host scan for the color boundary to find new completions, and watch the color convention *flip* on ring wraparound (Fig 6-20 — this wraparound flip is the detail everyone gets wrong); (b) the **piggybacked SQ head** — each completion carries the SQ head value home (Fig 6-19), shown as a little tag on the completion.
- **Queue-depth slider** — drag QD from 1 to 64 and watch throughput scale; this quietly teaches the IOPS = QD/latency intuition from Ch6 §6.1 and sets up FIO's iodepth flag from Ch7.
- **Wire-view toggle** ⭐ — flip it and every arrow re-renders as its actual PCIe TLP: doorbell writes = MemWr, command fetch = MemRd + Completion, data return = MemWr ×4, MSI-X = MemWr. This is Figs 6-31→6-39 (the trace section) fused onto the flow — the single best Ch5↔Ch6 integration you can build, and the punchline ("the whole protocol is just MemRd and MemWr") lands visually.
- **Bonus scene — PRP/SGL pointer chase** (Figs 6-21→6-28): attach a data buffer to a command and watch the SSD *walk* PRP1→PRP2→PRP list entries (pointer-to-pointer peeling, like watching C pointers dereference), then switch to SGL and do the 13KB-read-keep-11KB scatter with a Bit Bucket swallowing the unwanted 2KB (Fig 6-27). PRP = rigid pages, SGL = arbitrary ranges — one toggle makes the difference tactile.

**Node pre-verify:** ring-pointer arithmetic including wraparound + phase-flip — 50 lines, worth every one, because an off-by-one here would teach the junior something *wrong*.

---

### 🏆 Cluster D — The Packet Dresser + ACK/NAK Lab *(with a Jammer mode)*

**Figures absorbed (≈15):** 5-11→5-16 (three layers, dress/undress, through-a-switch), 5-17/5-18 (MRd/MWr flows), 5-19/5-20 (TLP anatomy), 5-49→5-55 (DLLP, ACK/NAK internals, credit flow control), 5-3 & 5-5 (duplex + skew intros), and — from Ch7 — the *concept* of Figs 7-15/7-16 (the Jammer) as a mode.

**The build:**
1. **Dressing room.** A payload gets dressed layer by layer exactly as §5.3 taught: Transaction adds Header+ECRC, Data Link adds Seq#+LCRC, Physical adds Start/End — each garment a colored wrapper with hover-labels (Fig 5-19/5-20 anatomy). Send it across a lane; the receiver undresses in reverse, each layer *checking* before stripping.
2. **Through a switch.** Route the TLP RC→Switch→EP and watch the switch undress *to the Transaction layer* (it must read the address to route!), re-dress, and forward — the Fig 5-15/5-16 point that answers "why does a mere forwarder implement all three layers."
3. **ACK/NAK scene** ⭐. Show the sender's **Replay Buffer** filling with in-flight TLPs, batched ACKs draining it. Then the fun part — **Jammer mode**: a little gremlin sits on the wire (this *is* Ch7's Jammer, §7.3.3, folded in). Buttons: *corrupt LCRC* (receiver NAKs → watch replay from the buffer), *drop a TLP* (receiver sees seq jump 11→13 → NAK → replay), *delay an ACK* (sender times out → re-sends → receiver spots the *lower-than-expected* seq → silently discards the duplicate → ACKs). Those three faults are the entire §5.8 state machine, and injecting them yourself is worth ten readings. It also plants the Ch7 lesson early: robustness means handling a hostile wire gracefully.
4. **Credit flow-control scene** (Figs 5-54/5-55): receiver advertises buffer credits; sender's transmit gate opens/closes as credits drain/refill. Small, but it kills the "why doesn't the sender just blast?" confusion.

---

### 🏆 Cluster E — The Flash Timing & Parallelism Lab *(BiCS8-relevant scheduling intuition)*

**Figures absorbed (≈10):** 3-8 (cache/page register pipelining), 2-8 (channel/CE/die wiring), 3-36/3-37/3-38 (addressing & plane bits), 3-39/3-40/3-41 (read/write/erase timing), 3-31→3-35 (async/sync waveforms, as a reference pane), plus the **AIPR addendum** (no 1st-ed figure — you'll be drawing the figure the book doesn't have).

**Why:** this is the cluster closest to your day job. Firmware performance work *is* reasoning about these timelines.

**The build:** a **Gantt-chart timeline** of operations across channels → dies → planes:
- **CE-select scene** (Fig 2-8): one channel's shared 8-bit bus, four dies; watch CE# assert to pick a die, command/address/data time-share the same pins (CLE/ALE flags lighting to show *what* the bytes mean). The "8 pins carry everything" fact becomes visible.
- **Register pipelining scene** (Fig 3-8): run Cache Read — while page N transfers register→controller (50 µs bar), page N+1 loads media→register (long bar) *underneath it*. Toggle pipelining off and watch total time stretch. Use the book's own numbers (1.5 ms program, 50 µs transfer) so the dual-plane arithmetic from §3.1.3 falls out on screen: two pages ≈ 1.5 ms + 2×50 µs instead of 2×(1.5 ms+50 µs).
- **Multi-plane scene:** single vs dual-plane program — throughput meter nearly doubles.
- **AIPR scene** ⭐ (the addendum): classic lockstep mode — two random reads to the same die *queue up* (collision, latency spike on a QoS meter); flip to independent-plane mode — they run concurrently if they hit different planes; still collide same-plane. Add a "placement matters" toggle (stripe hot data across planes) and watch tail latency drop. **This is the figure the 2nd edition describes but you get to invent — and it's directly about BiCS8's read-QoS behavior.**

---

### 🏆 Cluster F — Mapping Lookup Paths *(DRAM / DRAM-less / HMB / HPB)*

**Figures absorbed (≈11):** 4-3/4-4/4-5 (block/page/hybrid mapping), 4-6→4-13 (map mechanics, DRAM vs DRAM-less vs HMB, latency comparison).

**The build:** issue a random 4K read and **race three drives side by side**: (1) DRAM drive — map lookup in DRAM (fast tick) → one flash read; (2) DRAM-less — L1 in SRAM, L2 miss → *flash read for the mapping* → flash read for the data (the two-access penalty of Fig 4-13, visible as two long bars); (3) HMB — map fetched over a PCIe hop (medium bar) → one flash read. Then switch workload to *sequential* and watch the DRAM-less drive catch up (one map chunk serves many pages) — the exact §4.2.2 asymmetry. **Intro scene:** block-mapping's read-modify-write pain (update 1 page → rewrite the whole block, Fig 4-3) vs page mapping — the ten-second demo of why USB sticks have tragic random writes. **Epilogue toggle:** HPB mode (from the UFS supplement) — the *host* hands the physical address with the command; the device skips its lookup entirely. Four architectures, one latency bar chart, complete story.

---

### 🏆 Cluster G — Power-Loss Rebuild & Snapshots

**Figures absorbed (≈5):** 4-33, 4-43/4-44 (metadata packing), 4-45/4-46 (snapshots, crash-after-C).

**The build:** a write stream where each flash page visibly carries its **metadata tag** (LBA + timestamp). A big red **"yank power"** button (let the junior choose the moment — mid-GC is the spicy one). On reboot: **full-scan rebuild** — a scan cursor crawls the whole flash, re-deriving map entries from tags; when it meets the same LBA twice, the **timestamp duel** plays out visibly (older mapping overwritten by newer — Fig 4-44's exact scenario). Progress bar ∝ capacity: agonizing. Then enable **snapshots** (Fig 4-45): periodic camera-click persists state; next crash → load snapshot C, scan only the C→crash tail (Fig 4-46) — recovery time collapses. Optional cruelty: a "Lower-Page corruption" event (Ch3 §3.3.4) where the crash destroys an *already-acknowledged* page, and an enterprise-capacitor toggle that saves it. This cluster is the visual twin of the new Ch7 power-loss-testing addendum — build it and the test methodology explains itself.

---

### 🏆 Cluster H — Stripe RAID & the Chained-Warships Problem

**Figures absorbed (2, but heavyweight):** 3-58 (die-level RAID 5), 3-59 (why SSD RAID ≠ disk RAID).

**The build:** five dies, data striped with an XOR parity die. (1) **Rebuild scene:** poison one die's block (UECC flash) → XOR the survivors → the lost data reassembles bit by bit. Pre-verify the XOR in Node; render honestly. (2) **The GC trap** ⭐: attempt to garbage-collect *one* block belonging to a stripe → the stripe visibly *breaks* (parity no longer covers) → the animation forces the whole stripe to move together, chained like the warships at Red Cliffs. (3) The cost: a "sleep now" event forces padding half-empty stripes with junk (WA meter blips). Two figures, but this is the deepest reliability-vs-flexibility tradeoff in Chapter 3, and it only makes sense in motion.

---

### 🏆 Cluster I — Enumeration & Routing Explorer *(bring-up engineer's playground)*

**Figures absorbed (≈19):** 5-6→5-10 (PCI vs PCIe topology), 5-27→5-29 (config space), 5-30→5-37 (CPU-can't-touch-devices, memory mapping, the BAR all-1s trick, BDF), 5-38→5-48 (address routing with Base/Limit, ID routing with Primary/Secondary/Subordinate, implicit routing).

**The build:** a small live tree — RC, one switch, three EPs.
1. **Enumeration replay:** boot the system and watch software walk the tree: read BAR0 → **write all-1s** → read back → the *stuck* low bits decode into a size (bit math shown live — the Fig 5-32→5-35 trick that every bring-up engineer eventually does with real registers) → allocate a region → write the base back. Repeat per BAR, per device; the host memory map fills in on a side pane.
2. **Routing range:** fire TLPs at chosen targets and watch each hop *decide*: address routing checks the TLP address against each downstream port's [Base, Limit] window (windows drawn as shaded ranges); ID routing checks bus numbers against the Secondary/Subordinate triple. Deliberately mis-aim one (address in nobody's window) and watch it rejected. Fig 5-38's question — "how does a TLP find its way?" — answered by letting the junior *be* the switch.

---

### 📊 Cluster J — The Calculator Bundle *(quick wins; an afternoon each)*

Not animations — interactive number-crunchers realizing the book's formula figures:
1. **PCIe bandwidth & IOPS ceiling** (Ch5 §5.1 + §5.13): gen/lanes/encoding → GB/s; then the full §5.13 overhead model with **MPS and Max-Read-Request sliders** — reproduce the book's 1689→1912 MB/s result live (Fig 5-66's registers as the controls). Extend to Gen4–7 from the modern supplement.
2. **OP ↔ WA ↔ TBW/DWPD** (Fig 4-25 + Ch1 §1.5.3 formulas): capacity, P/E, OP, workload → WA estimate, TBW, DWPD. The S3710 worked example as a preset.
3. **Endurance sample-size + temperature acceleration** (Ch7 §7.8, Fig 7-24, Tables 7-6→7-9): FFR/UBER/TBW → drives needed & allowed errors; hours ↔ temperature lookup. Your Ch7 guide's worked examples as presets.
4. **QoS percentile explorer** (Fig 1-20): a latency histogram where you drag the "nines" cursor — ties directly to reading FIO's clat percentiles (§7.1.1).

---

## Part 2 — The complete figure catalog (all 359, tiered)

*Grouped rows = a sequence forming one unit. Pages refer to the chapter's own file.*

### Chapter 1 — Overview (43 figures)

| Fig(s) | p. | What it shows | Tier |
|---|---|---|---|
| 1-1 | 2 | Boot-time statistics bar chart | 🚫 |
| 1-2 | 2 | SSD product photos (2.5″, M.2) | 🚫 |
| 1-3 | 3 | SSD internals: PCB, controller, flash, cache, connector | 📄 (hover-map candidate; see Ch2's 2-1) |
| 1-4 | 4 | Storage-media taxonomy tree | 📄 |
| 1-5 | 5 | SSD vs HDD structural comparison | 📄 |
| 1-6 | 6 | Benchmark score comparison | 🚫 |
| 1-7, 1-8 | 10–11 | 1976 Bulk Core photo; HDD sales chart | 🚫 |
| 1-9 | 12 | Floating-gate transistor structure | 🏆 → **A** (duplicate of 3-1) |
| 1-10→1-12 | 13–16 | Big-SSD photo, SandForce poster, Skyera logo | 🚫 |
| 1-13 | 20 | SSD's three internal blocks (front end/FTL/back end) | 📄 (Cluster B's intro frame) |
| 1-14 | 22 | Garbage-collection concept (valid data A–G consolidated) | 🏆 → **B** |
| 1-15 | 23 | Intel S3700 datasheet screenshot | 🚫 |
| 1-16, 1-17 | 26–27 | 2D vs 3D flash sketch; fab roadmap | 📄 / 🚫 |
| 1-18, 1-19 | 28–29 | Form-factor overview; compatibility example | 📄 |
| 1-20 | 31 | Latency distribution & QoS "nines" | 📊 → **J4** |
| 1-21 | 32 | Empty-vs-full performance (SSD/HDD/SSHD) | 🏆 → **B** (emerges as the live perf meter) |
| 1-22, 1-23 | 35–36 | Data-tiering pyramid; real-world DWPD needs | 📄 / 📊 → **J2** |
| 1-24→1-27 | 38–40 | UBER↔ECC strength; UBER↔RBER; RBER↔P/E; lower/upper-page RBER | 📊 → **A** side-plots |
| 1-28, 1-29 | 43–44 | AnandTech power comparison charts | 🚫 |
| 1-30 | 45 | Thermal-throttling sawtooth (temp vs perf feedback loop) | 🔧 T2 — small standalone: heat rises → throttle → cool → repeat; pairs with Supplement D |
| 1-31→1-40 | 48–57 | Form-factor gallery, M.2 keying/naming, BGA vs M.2, P900, SDP photos | 📄 (1-33 M.2 naming worth an annotated static) / 🚫 photos |
| 1-41→1-43 | 58–61 | Attach rate, price trend, market share | 🚫 |

### Chapter 2 — Controllers & AFA (34 figures)

| Fig(s) | p. | What it shows | Tier |
|---|---|---|---|
| 2-1 | 2 | **Controller SoC block diagram** (CPU, front end, back end, buses) | 🏆 hover-explore "home map" — see note below |
| 2-2→2-5 | 3–5 | SATA/SAS/PCIe-AIC/U.2 connector photos | 🚫 |
| 2-6 | 6 | SATA Write FPDMA FIS handshake (with flow control) | 🔧 T2 — sequence animation; the "buffer full → silence" beat is the teachable moment |
| 2-7 | 9 | ECC module + flash controller placement | 📄 |
| 2-8 | 10 | Flash chip interface: channel bus, CE per die | 🏆 → **E** |
| 2-9→2-13 | 12–16 | Marvell/Samsung/SMI product-line charts | 🚫 |
| 2-14→2-16 | 22–27 | SG9081 / STAR1000 / DERA TAI block diagrams | 📄 |
| 2-17→2-26 | 29–37 | XtremIO hardware: X-Brick anatomy, cabling, console screenshots, scale-out, perf | 📄 (2-24 interconnect) / 🚫 photos |
| 2-27 | 38 | "iPhone running Android" joke image | 🚫 |
| 2-28 | 40 | XIO software architecture (R/C/D + P/M/L modules) | 📄 (stage set for the T2 below) |
| 2-29→2-32 | 43–47 | Write flow, dedup write flow, copy-before state, copy flow | 🔧 T2 — **XIO dedup theater**: hash a block → C-module lookup → duplicate? bump refcount, write nothing; then the zero-IO VM copy (metadata range copy + refcounts). Systems-taste builder, lower priority than firmware clusters |
| 2-33, 2-34 | 48–51 | X-Brick internal interconnect; IT-infrastructure sketch | 📄 / 🚫 |

*Mentor note on 2-1:* consider making this diagram your **navigation hub** — a clickable controller map where each block links to the relevant animation (front end → Cluster C/D, back end → E, FTL/CPU → B/F/G, ECC → your LDPC visualizer). One page that *is* the book's architecture.

### Chapter 3 — Flash (62 figures)

| Fig(s) | p. | What it shows | Tier |
|---|---|---|---|
| 3-1, 3-2 | 2 | Floating-gate cell; program/erase tunneling | 🏆 → **A** scene 0 |
| 3-3→3-5 | 3–4 | **SLC/MLC/TLC threshold-voltage distributions** | 🏆 → **A** core (spot-checked: clean) |
| 3-6, 3-7 | 5–7 | Block organization; full cell→page→block→plane→die hierarchy | ✅ your existing hierarchy animation |
| 3-8 | 8 | Cache/Page register pipelining | 🏆 → **E** |
| 3-9→3-11 | 11–13 | Erase/program/read voltage diagrams | 🔧 T2 — voltage-overlay mode inside A scene 0 |
| 3-12→3-19 | 14–21 | Scaling-vs-interference trend; market share; 3D structure; BiCS/TCAT compare; density growth; layer-count effects; top-vs-bottom cell differences | 📄 (3-13 🚫) |
| 3-20→3-23 | 22–25 | Charge-trap vs floating gate ("water vs cheese"), coupling capacitance | 📄 — or a cute T2 toggle in A scene 0: FG mode (electrons slosh out through worn oxide) vs CT mode (electrons stuck in cheese) |
| 3-24→3-30 | 26–31 | Emerging memories; PCM crystal/amorphous, temp-pulse programming, bitline/wordline array | 🔧 T2 low — small temp-pulse phase toggle; otherwise 📄 |
| 3-31→3-35 | 33–37 | Pinout; async & sync read/write waveforms | 🔧 T2 — waveform explorer (step a WE#/RE# pulse train, watch bytes latch under CLE/ALE); genuine bring-up value, reference-grade otherwise |
| 3-36→3-38 | 39–40 | Internal architecture; row/column address split; plane bits | 📄 → labels inside **E** |
| 3-39→3-41 | 40–41 | Read/write/erase command timing | 🏆 → **E** |
| 3-42, 3-43 | 43–45 | ONFI vs Toggle pin comparison; flash damage states | 📄 |
| 3-44, 3-45 | 46–47 | Read-disturb & program-disturb mechanisms | 🏆 → **A** scene 3 |
| 3-46→3-48 | 48–51 | SLC distribution; read voltages; threshold drift with wear | 🏆 → **A** |
| 3-49 | 51 | X-ray of a solder-ball void | 🚫 (great war story, no motion) |
| 3-50→3-56 | 55–63 | Threshold shifts: retention (left), read-disturb (right), per-wear RBER, neighbor-state effects | 🏆 → **A** scenes 3–4 |
| 3-57 | 63 | Read Retry — moving the reference voltage | 🏆 → **A** scene 4 |
| 3-58, 3-59 | 65–66 | Die-level RAID 5; traditional-RAID contrast (the chained-stripes problem) | 🏆 → **H** |
| 3-60→3-62 | 68–69 | Randomized vs raw distributions; neighbor influence; randomizer dataflow | 🔧 T2 → toggle in **A** scene 3 |

### Chapter 4 — FTL (57 figures)

| Fig(s) | p. | What it shows | Tier |
|---|---|---|---|
| 4-1, 4-2 | 4 | Host-based vs device-based FTL | 📄 |
| 4-3→4-5 | 5–7 | Block / page / hybrid mapping | 🔧 T2 → **F** intro (block-mapping RMW pain demo) |
| 4-6→4-13 | 9–14 | Map mechanics; DRAM architecture; two-level L2P; DRAM-less; HMB; latency comparison | 🏆 → **F** |
| 4-14→4-22 | 17–26 | **The toy-SSD GC walkthrough** (build-up, fill, overwrite, collect, erase, random-fill variant) | 🏆 → **B** (spot-familiar from our Ch4 read) |
| 4-23→4-25 | 27–29 | WA arithmetic blocks; OP-vs-WA-vs-endurance curve | 🏆 → **B** (the OP slider) + 📊 **J2** |
| 4-26→4-33 | 32–41 | GC implementation: valid-count tables, first-fill states, bitmap examples, metadata layout | 🏆 → **B** (method toggle) / 4-33 also → **G** |
| 4-34 | 43 | Host-managed-GC steady performance | 📄 |
| 4-35→4-37 | 44–46 | File delete; the three FTL tables; Trim flow | 🏆 → **B** Trim scene |
| 4-38 | 47 | P/E cycles by process node/type | 📄 |
| 4-39→4-42 | 49–50 | Static-WL mixing traps; cold/hot separation | 🏆 → **B** WL scene |
| 4-43→4-46 | 53–56 | Metadata+data storage; snapshot "photos"; crash-after-snapshot-C | 🏆 → **G** |
| 4-47, 4-48 | 57–58 | Factory bad-block marking; table-build flow | 📄 |
| 4-49→4-51 | 59–61 | Skip strategy; user/OP split; replace strategy | 🔧 T2 → **B** fault-injection event |
| 4-52→4-57 | 66–72 | Host-based architecture; SDF board/architecture/IO-stack comparison | 📄 (4-57's 12µs→2–4µs stack collapse = one good annotated static) |

### Chapter 5 — PCIe (68 figures)

| Fig(s) | p. | What it shows | Tier |
|---|---|---|---|
| 5-1, 5-2 | 2 | Lanes as highway; Link concept | 📄 intro art |
| 5-3 | 3 | SATA half-duplex ("walkie-talkie") | 🔧 T2 → **D** intro toggle |
| 5-4 | 5 | Intel 750 datasheet | 🚫 |
| 5-5 | 6 | Parallel-bus skew timing | 🔧 T2 → **D** intro (bits arriving ragged vs serial embedded-clock) |
| 5-6→5-10 | 7–10 | PCI shared bus vs PCIe tree; RC internals; switch internals | 🏆 → **I** topology |
| 5-11→5-16 | 11–16 | **Layered stack; TLP dress/undress; all nodes implement 3 layers; RC↔EP path** | 🏆 → **D** |
| 5-17, 5-18 | 20–21 | MemRd flow (1 request, 4 CplD); MemWr flow (posted, no reply) | 🏆 → **D** scene |
| 5-19, 5-20 | 21–22 | TLP anatomy; header fields | 📄 hover-anatomy inside **D** |
| 5-21→5-26 | 24–27 | Header variants (Memory/Config/Message/Completion) + status codes | 📄 |
| 5-27→5-29 | 29–30 | PCI 256B vs PCIe 4KB config space; header layout | 📄 → **I** reference pane |
| 5-30→5-37 | 31–36 | CPU-can't-reach-devices; memory mapping; **BAR all-1s sizing trick**; BDF | 🏆 → **I** enumeration |
| 5-38→5-48 | 37–46 | "How does a TLP travel?"; address routing (Base/Limit); ID routing (Pri/Sec/Sub); implicit routing | 🏆 → **I** routing |
| 5-49→5-53 | 48–52 | Data-link layer role; DLLP formats; **ACK/NAK internals** | 🏆 → **D** |
| 5-54, 5-55 | 53–54 | Flow-control DLLP; credit advertisement | 🏆 → **D** credit scene |
| 5-56 | 54 | Power-management DLLP | 📄 (Supp D context) |
| 5-57, 5-58 | 56–58 | PHY tx/rx logic pipeline (stripe→scramble→encode) | 🔧 T2 — optional pipeline animation |
| 5-59→5-65 | 61–66 | PERST# power-up; TS1 bits; link-control/capability/status registers | 📄 |
| 5-66 | 67 | Device Control Register (MPS/MRRS) | 📊 → **J1** controls |
| 5-67, 5-68 | 69–71 | Hot-plug diagram; PCIe 2.0 TLP format | 📄 |

### Chapter 6 — NVMe (67 figures)

| Fig(s) | p. | What it shows | Tier |
|---|---|---|---|
| 6-1→6-5 | 3–6 | Latency & perf comparisons; stack position; interface speeds; founding companies | 📄 / 🚫 |
| 6-6→6-8 | 7–9 | Command-set taxonomy; Admin & NVM command tables | 📄 |
| 6-9→6-20 | 11–22 | **SQ/CQ/DB placement; the 8-step flow; full ring walkthrough; piggybacked SQ head; phase tag** | 🏆 → **C** (6-10 spot-checked: clean) |
| 6-21→6-28 | 24–32 | Data flow; PRP entry/list layouts & examples; SGL example; SGL read (bit bucket); PRP-vs-SGL | 🏆 → **C** pointer-chase scene |
| 6-29, 6-30 | 33–34 | PCIe+NVMe stack; two-device communication | 📄 |
| 6-31→6-39 | 35–40 | **The PCIe trace of one NVMe read** (per-step TLPs, MSI-X) | 🏆 → **C** wire-view |
| 6-40→6-49 | 41–46 | E2E protection: metadata inline/separate; PI format (Guard/AppTag/RefTag); write & read check flows; SSD-internal PI | 🔧 T2 strong — **PI bodyguard demo**: flip a data bit → Guard CRC catches; swap two blocks' LBAs → RefTag catches. Small, elegant, pre-verify CRC16 in Node; pairs with your ECC theme |
| 6-50→6-58 | 48–55 | Namespaces; SR-IOV; multi-controller; dual-port topologies; Z-Drive 6000 | 📄 |
| 6-59→6-67 | 57–67 | NVMe-oF: traditional connection; latency evolution; stack compare; interconnect taxonomy; RDMA transfer; capsule formats; IO flow; target-pulls-data | 📄 (6-66 capsule flow = optional T2) |

*Plus (no 1st-ed figures): the **ZNS zone state machine + Zone Append** from the addendum — a T2 build I'd genuinely encourage: zones as progress bars with write pointers, the QD>1 ordering problem, and Append fixing it.*

### Chapter 7 — Testing (28 figures)

| Fig(s) | p. | What it shows | Tier |
|---|---|---|---|
| 7-1 | 1 | Jens Axboe photo | 🚫 |
| 7-2→7-7 | 9–14 | AS SSD / ATTO / CrystalDiskMark / IOMeter screenshots | 🚫 |
| 7-8→7-14 | 17–24 | Emulator, SATA & PCIe analyzers, interposers, NVMe-decode screenshots | 🚫 (concepts already live in **D**'s framing) |
| 7-15, 7-16 | 25–26 | The Jammer; injecting a CRC error into a Data FIS | 🏆 *concept* → **D** Jammer mode |
| 7-17 | 28 | Test-coverage-vs-time balance | 🚫 |
| 7-18→7-22 | 30–35 | DevSlp cable/results; PCIe link capability/status registers | 📄 |
| 7-23 | 45 | Endurance Direct-Method/Ramped flow chart | 📄 annotated |
| 7-24 | 46 | Temperature-acceleration table/curve | 📊 → **J3** |
| 7-25, 7-26 | 47–49 | Event schedule; UNH-IOL scope | 🚫 |
| 7-27, 7-28 | 51–52 | **FOB→transition→steady-state curve; valid measurement window** | 🏆 → **B** perf meter + 📊 |

---

## Part 3 — Build order (my recommendation, tied to your calendar)

| # | Build | Effort | Why now |
|---|---|---|---|
| 1 | **A — Vt Distribution Playground** | L | Feeds the patent presentation directly (soft reads/LLR = the patent-hot mechanism); extends your ECC visualizers into one continuous story: physics → LLR → LDPC |
| 2 | **B — Toy SSD Sandbox** | L | Your existing WA animation grows up; absorbs the planned wear-leveling piece; also the best single visual for the week-2 five-minute SSD intro |
| 3 | **C — NVMe Ring Machine** | M | The protocol core; the wire-view is the best Ch5↔Ch6 unifier |
| 4 | **D — Packet Dresser + Jammer** | M | Makes Ch5 tactile; Jammer mode plants the Ch7 robustness mindset |
| 5 | **E — Timing & Parallelism Lab** | M | Closest to BiCS8 scheduling reality; the AIPR scene is a figure the book doesn't even have |
| 6 | **J — Calculators (any order, fill gaps)** | S each | Afternoon builds; J2 (OP↔WA↔TBW) and J1 (bandwidth) first |
| 7 | **F — Mapping Paths** | S | Small, complete story; HPB epilogue ties in the UFS supplement |
| 8 | **G — Power-Loss Rebuild** | S | Twins the new Ch7 PLR-testing addendum |
| 9 | **H — Stripe RAID** | S | Two figures, one deep tradeoff |
| 10 | **I — Enumeration & Routing** | M | Bring-up gold, but the least urgent for your current work |

Tier-2 pool for spare evenings, in the order I'd pick them: **PI bodyguard demo** (6-40→6-49), **ZNS zones + Append** (addendum), **thermal-throttle sawtooth** (1-30), **FPDMA handshake** (2-6), **XIO dedup theater** (2-29→2-32), **waveform explorer** (3-31→3-35), **PCM phase toggle** (3-25→3-29).

## Part 4 — Engineering discipline (the part I'd insist on if you worked for me)

1. **Simulation core first, pixels second.** For B, C, G, H especially: write the state model as plain headless JS, unit-test it in Node (ring wraparound + phase flip; VPC/WA bookkeeping; XOR rebuild; timestamp-duel rebuild), *then* wrap the renderer. You already work this way with your ECC visualizers — keep it. An animation that's subtly wrong is worse than no animation.
2. **Reuse your design system** (bg `#0b1020`, data cyan `#4dd0c4`, parity amber `#f2b13c`, violet `#a78bfa`, IBM Plex/Space Grotesk, `prefers-reduced-motion`, single-file HTML, no localStorage). Twelve consistent-looking artifacts read as *one body of work* in a final presentation; twelve styles read as homework.
3. **Every animation gets a "book anchor" footer** — the figure numbers and chapter pages it realizes (e.g., "realizes Figs 4-14→4-25, CH4 pp. 17–29") — so anyone (including presentation reviewers) can trace it back to the source.
4. **Playwright-screenshot each finished scene** as you already do, and keep the screenshots — they become presentation slides for free.
5. **Scope ruthlessly.** Each cluster above lists more scenes than its minimum viable version needs. A shipped three-scene sandbox beats a planned seven-scene one. Ship, then accrete.

*That's the whole territory. My honest bottom line as your mentor: clusters A and B alone, done well, would carry both your five-minute intro and half your patent presentation — everything else is compounding interest.*
