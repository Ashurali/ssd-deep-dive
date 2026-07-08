---
title: "Ch 3 — NAND Flash"
tags:
  - flash-physics
  - 3d-nand
  - charge-trap
  - threshold-voltage
  - reliability
  - read-disturb
  - data-retention
  - endurance
  - ecc
  - bics8
source_anchor: "CH3 file"
---

# SSD Deep Dive — Chapter 3: The Storage Medium — Flash (閃存)
## English Study Companion

**Where we are:** Chapter 1 gave the whole-drive picture; Chapter 2 dissected the controller. This chapter goes all the way down to the **physics of a single flash cell** — how one bit is actually held as trapped electrons — then builds back up through chip architecture, the electrical protocols, and finally the many ways flash *fails* and how firmware fights back. Chapter 3 runs pages 1–69 of your file (p. 70 is empty website comments).

**How to use this guide:** Section numbers match the book. Page references like *(p. 3, Fig 3-3)* point into your CH3 file so you can view the original diagram beside the explanation. Glossary at the end. This chapter has more physics than the others, so I've leaned on the book's own analogies (they're genuinely good) and added a few of my own.

**The chapter's shape — four movements:**
- **3.1** = the physics (how a cell stores a bit; the cell→block→die hierarchy; 3D flash; alternatives)
- **3.2** = the electrical reality (how the controller actually talks to a chip — timing, commands, addresses)
- **3.3** = why flash is hard (all the ways it degrades and fails)
- **3.4** = fighting back (ECC, RAID, retry, scrubbing, randomization)

If your time is limited, **3.1.1–3.1.4** and **3.3** are the heart of it. 3.2 is reference-grade detail you can skim.

---

## 3.1 Flash physical structure — pp. 1–32

### 3.1.1 How a flash cell works (p. 1–3) ⭐ *the foundational idea*

Nearly all SSDs use **NAND flash**, a **non-volatile** memory (keeps data with power off). The reason SSDs behave the way they do traces entirely to two physical facts about flash, both stated on p. 1:
1. **You must erase before writing — you cannot overwrite in place.** → this forces garbage collection.
2. **Each block survives only a limited number of erase cycles**, after which it becomes a bad block or holds unreliable data. → this forces wear leveling.

The basic storage unit is a **cell (Cell)** — an NMOS-like transistor with a **floating gate (浮柵)** *(p. 1–2, Figs 3-1/3-2)*. Between the source and drain sits a gate that can trap electrons, wrapped above and below by insulating layers. Electrons trapped inside **don't leak away when power is lost** — that's why flash is non-volatile.

- **Write (program):** apply positive voltage to the control gate → electrons tunnel *through* the insulator *into* the floating gate.
- **Erase:** apply positive voltage to the substrate → electrons are pulled *out* of the floating gate.

*(A charming aside, p. 2–3: the floating-gate transistor was invented in 1967 by Simon Sze (施敏) and Dawon Kahng at Bell Labs — reportedly inspired over lunch by a cheesecake, imagining "what if we put something in the middle of a MOSFET?" Sze received a lifetime achievement award at the 2014 Flash Memory Summit; the author argues he deserves a Nobel, since the discoverer of GMR — the effect behind HDDs — already won one.)*

### 3.1.2 SLC / MLC / TLC — the voltage picture (p. 3–5) ⭐

??? example "🎬 Animate this — The Vt Distribution Playground"

    SLC/MLC/TLC bells in one window — drag wear, retention and read count and watch every Ch 3 failure mode happen.

    [Animation page](../animations/vt-playground.md) · [open full-screen ↗](../animations/files/vt_playground.html)

    <iframe src="../../animations/files/vt_playground.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Vt Distribution Playground"></iframe>


The names describe **how many bits one cell stores**, which physically means **how finely you subdivide the electron count** in the floating gate:

The key diagram to understand is the **threshold-voltage distribution** *(p. 3–5, Figs 3-3/3-4/3-5)*: the x-axis is threshold voltage, the y-axis is the number of cells. Cells storing the same value don't all sit at exactly one voltage — they form a *bell curve* centered on a target. Reading means checking which range the cell's voltage falls into.

- **SLC (1 bit)** — two states, so one clean divide. After erase the cell reads **1**; after programming it reads **0**. (So writing a 1 means "do nothing"; writing a 0 means "inject charge.")
- **MLC (2 bits)** — four states, so you must distinguish four electron-count bands (e.g., <10 electrons = state 0, 11–20 = 1, 21–30 = 2, >30 = 3).
- **TLC (3 bits)** — eight states, finer still.

**The fundamental trade-off (p. 5, Table 3-2):** on the same silicon area, SLC→MLC→TLC store 1→2→3 bits, so capacity rises. But more bands means (a) writing must control electron count more precisely → **slower writes**, (b) reading must try more reference voltages → **slower reads**, and (c) the bands sit closer together → **less margin for error → shorter endurance**. So performance and lifespan go **SLC > MLC > TLC**, while capacity-per-area and cheapness go the other way. 3D TLC is now mainstream; QLC (4 bits) was arriving — slower and less reliable still.

### 3.1.3 Flash chip architecture — the hierarchy (p. 5–9) ⭐ *memorize this*

??? example "🎬 Animate this — Why SSDs need an FTL — NAND flash, animated"

    Pages, blocks and the no-overwrite rule — the hierarchy this section describes, animated stage by stage.

    [Animation page](../animations/nand-flash-animation.md) · [open full-screen ↗](../animations/files/nand-flash-animation.html)

    <iframe src="../../animations/files/nand-flash-animation.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="Why SSDs need an FTL — NAND flash, animated"></iframe>


A flash chip is millions of cells organized in a strict nesting *(p. 6–7, Figs 3-6/3-7)*. From smallest to largest:

**cell → (page) → wordline → block → plane → die/LUN → chip**

- A **wordline** corresponds to one or more **pages**: SLC = 1 page/wordline; MLC = 2 (a pair: **Lower Page** + **Upper Page**); TLC = 3 (Lower, Upper, Extra).
- A **block (Block)** is the group of wordlines that **share one substrate** — this is why erase happens at block granularity (more below).
- A **die/LUN** is **the basic unit that receives and executes a flash command.** Two LUNs can execute *different* commands simultaneously — this is a key source of parallelism — but within one LUN, only one operation runs at a time (you can't read one page while writing another on the same LUN).
- A **plane** (commonly 1, 2, or now 4 per die) each has its own **Cache Register** and **Page Register**, each the size of one page.

**The two registers and why they exist (p. 7–9, Fig 3-8).** To write, the controller sends data into the target plane's **Cache Register**, then it's written to the flash array; to read, data goes flash → register → controller. Crucially, **transfers between flash media and register always happen a whole page at a time.** Two registers exist to **overlap bus transfer with media access**: while page N is being handed to the controller (Cache Register → controller), page N+1 can already be loading from the media (media → Page Register). This hides the slower operation behind the faster one (**Cache Read / Cache Program**).

**Important definitional subtlety (p. 9):** the quoted "flash write time" and "read time" refer *only* to moving a page between the flash media and the Page Register — **not** the register↔controller transfer. This matters when you reason about timing.

**Multi-Plane (Dual-Plane) operation — a big performance lever (p. 8–9).** Instead of writing planes one at a time, the controller loads several planes' Cache Registers, then commits them together. The book's worked numbers: if writing a page = 1.5 ms and transferring = 50 μs, then two pages single-plane = (1.5 ms + 50 μs) × 2, but dual-plane = 1.5 ms + 50 μs × 2 — **nearly half the time, ~2× write speed.** Reads similarly speed up (two planes' pages load in one read time).

**Why erase is per-block (p. 9):** all cells in a block share one substrate, so applying the strong erase voltage to that substrate pulls electrons out of *every* floating gate at once. Max erase cycles fall SLC (up to 100K) → MLC (a few K to tens of K) → TLC (hundreds to a few K). As process shrinks (into the 1Xnm era), capacity rises but performance and reliability worsen — pushing more work onto firmware.

### 3.1.4 Read / write / erase — the actual voltages (p. 9–12, Figs 3-9/3-10/3-11)

- **Erase:** apply ~20 V to the Pwell; quantum tunneling pulls electrons from the floating gates into the channel; the whole block's threshold voltage becomes −VT = state "1". (Blocks not being erased have their gates left floating, so no tunneling.)
- **Write:** the target cell's wordline gets high voltage with bitline = 0 V → electrons tunnel into the floating gate → "0". Cells *not* being written get bitline = 2 V, which suppresses tunneling.
- **Read:** unread wordlines get 5 V (keeping those transistors conducting); the target wordline gets 0 V. An erased (−VT) cell conducts → the bitline sensor reads "1"; a programmed (+VT) cell doesn't conduct → "0".

*(You don't need to memorize the exact voltages — they vary by chip — but internalize the pattern: **erase = all 1s via substrate**, **write = inject charge to make 0s**, **read = sense conduction at 0 V**.)*

### 3.1.5 3D flash (p. 13–21)

**The problem 3D solves (p. 13–14, Fig 3-12).** For a decade, 2D (planar) flash shrank cells to cut cost — but as cells got smaller, **cell-to-cell interference got worse**, until shrinking further no longer reduced cost-per-bit. A wall.

**The 3D idea (p. 14–16, Figs 3-13/3-14).** Instead of shrinking cells in a plane, **stack layers vertically** — the channel stands upright and wordlines are stacked "floor by floor" like a building. Each generation adds ~40% more stacked gate layers, effectively shrinking cost ~40% per generation *without* shrinking the individual cell — so **interference actually drops** (the cells got *bigger* again). This is why 3D flash rapidly pushed 2D out and SSDs displaced HDDs (SSD share of the flash market rose 23%→43%, 2013–2017).

**Two milestone technologies (p. 16, Fig 3-15):** **BiCS** (Bit Cost Scalable, 2007) and **TCAT** (Terabit Cell Array Transistor, 2009). They differ in cell-string structure, stacking, program/erase window, and erase method — BiCS uses polysilicon gates and GIDL erase with a narrow P/E window; TCAT uses metal gates and bulk erase with a wide window. Versus 2D, TCAT *(p. 16, Fig 3-16)*: **−84% interference, >10× endurance, half the program time, −67% threshold-voltage shift.** Layer counts marched 24 → 32 → 48 → 64, roughly doubling density each generation *(p. 16, Fig 3-17)*.

**3D's own challenges (p. 17–21, Figs 3-18/3-19):**
1. **More layers** → smaller string current, and **growing differences between top and bottom cells**. More pages per block also means more accumulated reads per block → worse read disturb → need lower Vread → weaker signal.
2. **Layer-to-layer variation:** the channel-hole size and gate thickness differ top vs bottom, causing differences in program/erase speed, interference, and retention. (Bottom cells: smaller channel hole → higher coupling → faster erase, but thinner gate → shorter retention.)

### 3.1.6 Charge Trap flash (p. 21–24) — the other way to store a bit

**Charge Trap (CT, 電阱)** replaces the floating gate's *conductor* with an **insulator** (usually silicon nitride, Si₃N₄) full of "traps" that catch electrons *(p. 22, Fig 3-20)*. The book's analogy *(p. 22, Fig 3-21)*: a floating gate is like **water** — electrons move freely inside; CT is like **cheese** — electrons get stuck and move only with great difficulty.

**Why "stuck" is an advantage (p. 23–24, Figs 3-22/3-23):**
- **Insensitive to tunnel-oxide wear.** In a floating gate, once the oxide thins (smaller process) or ages (many erases), the free-moving electrons leak out easily. In CT, the electrons are already trapped, so even a degraded oxide doesn't let them escape easily.
- **Less cell-to-cell coupling.** A floating gate is a conductor, so any two nearby floating gates form a capacitor (C = εS/4πkd) — one cell's charge disturbs its neighbors, and this worsens as cells shrink. CT's insulator storage largely avoids this.
- **Lower program/erase voltage.** A CT cell is physically shorter (control gate to substrate), so the same tunneling field needs less voltage (E = U/d) → less oxide stress, slower wear, lower power.

**CT's weaknesses:** worse at **Read Disturb** and **Data Retention** than floating gate. CT is now the dominant 3D technology — **every major vendor except Micron uses CT for 3D flash** (Micron sticks with floating gate).

### 3.1.7 3D XPoint and other emerging memories (p. 24–32)

**The gap 3D XPoint targets (p. 24–25).** There's a speed chasm: DDR4 DRAM does ~61/46 GB/s but loses data on power-off; a 4-channel PCIe 3.0 SSD tops out ~4 GB/s and SATA ~600 MB/s. The dream is **DRAM-like speed that survives power loss.** Candidates listed: ReRAM (memristor), FeRAM, MRAM, PRAM/PCM (phase-change), cbRAM/PMC, SONOS, CMOx.

**Phase-Change Memory (PCM/PRAM)** is the most mature *(p. 26–31)*. The physics: a material (Intel used chalcogenides; the common one is **GST**, Ge₂Sb₂Te₅) switches between an **amorphous (glass-like, high-resistance)** state and a **crystalline (ordered, low-resistance)** state — like water freezing into ordered snow crystals *(p. 27–28, Figs 3-25/3-26)*. These two states are **bistable and non-reversible along the same path** — exactly what you need to represent 0 and 1.
- **Read:** measure the voltage/resistance at the GST node — low resistance (crystalline) = "0", high resistance (amorphous) = "1" *(p. 29, Fig 3-27)*.
- **Write:** a tiny heater passes current to melt/reshape the GST; different temperature+time pulses yield different phases (a short, very-hot pulse → amorphous; a longer, hot pulse → crystalline) *(p. 29–30, Figs 3-28/3-29)*.

PCM's attractions vs flash *(p. 28, Table 3-3)*: non-volatile, **byte-addressable**, simple software, **no erase-before-write**, low power, fast, and **far longer endurance** than flash. It's organized in a bitline/wordline matrix like flash *(p. 31–32, Fig 3-30)*.

---

## 3.2 Flash practical guide (the electrical protocols) — pp. 32–44

*This section is reference-grade detail on how the controller physically talks to a flash chip. Skim it unless you're doing hardware work; the one genuinely important idea for everyone is the ONFI-vs-Toggle story in 3.2.6.*

### 3.2.1 Asynchronous timing (p. 32–35, Figs 3-31/3-32/3-33)

Flash interfaces are **async** (slow, no clock) or **sync** (fast, clocked). In async, each data read is triggered by an **RE_n** pulse and each write by a **WE_n** pulse. Key signals: **CLE** (Command Latch Enable — bytes on the IO bus are a command), **ALE** (Address Latch Enable — bytes are an address), **CE_n** (Chip Enable — selects which logical chip/"Target"; the industry calls a Target a "CE"), **WE_n** (Write Enable), **RE_n** (Read Enable), **R/B_n** (Ready/Busy — the chip is busy during internal reads). Timing parameters (tWP, tWH, tWC, tDS, tDH) describe pulse widths and data setup/hold windows.

### 3.2.2 Synchronous timing (p. 35–37, Figs 3-34/3-35)

Sync uses a clock (**CLK**) and a data strobe (**DQS**). Modern flash uses **DDR** — data on both clock edges — so 100 MHz → 200 MT/s. **DQS** marks each transfer window (generated by the flash on reads, by the controller on writes) so the receiver samples correctly. **W/R_n** picks direction.

### 3.2.3 Flash command set (p. 37–38, Table 3-5)

The controller drives flash via a command set (ONFI 2.3 example). Commands you'll see repeatedly: **Read (00h–30h)**, **Read Multi-plane (00h–32h)**, **Change Read Column (05h–E0h** — read only part of a page from an offset), **Block Erase (60h–D0h)**, **Read Status (70h)**, **Read Status Enhanced (78h** — for multi-LUN), **Page Program (80h–10h)**, **Page Program Multi-plane (80h–11h** — multiplies write performance), **Read ID (90h)**, **Read Parameter Page (ECh** — reports the chip's capabilities), **Get/Set Features (EEh/EFh)**.

### 3.2.4 Flash addressing (p. 38–40, Figs 3-36/3-37/3-38)

Flash uses a **Row Address** and a **Column Address**. The **column address is the offset within a page.** The **row address**, high bits to low, is **LUN → Block → Page**. Where's the plane? It sits in the **lowest bit(s) of the block address** — so multi-plane operations tend to split into odd/even planes. A vendor quirk: for multi-plane, all planes must share the same *page* address; Intel/Micron and Toshiba allow different *blocks*, but Samsung requires the same block address.

### 3.2.5 Read / write / erase timing (p. 40–41, Figs 3-39/3-40/3-41)

??? example "🎬 Animate this — The Flash Timing & Parallelism Lab"

    The bus, the registers and the planes on one timeline — toggle pipelining and AIPR and watch the bars move.

    [Animation page](../animations/flash-timing-lab.md) · [open full-screen ↗](../animations/files/flash_timing_lab.html)

    <iframe src="../../animations/files/flash_timing_lab.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Flash Timing & Parallelism Lab"></iframe>


- **Read:** send 00h, then 2 column + 3 row address bytes, then 30h; the status bit SR[6] goes Busy, then Ready, then data can be read.
- **Write:** send 80h, then the address (**column is usually 0 — you must fill a whole page from the start, or you risk data errors**), then data into the register, then 10h to commit; SR[6] Busy→Ready.
- **Erase:** just LUN + block row address between 60h and D0h (block granularity).

### 3.2.6 ONFI vs Toggle — the protocol war (p. 41–44) ⭐ *the one story to read here*

There are **two** flash interface standards, and the book tells their rivalry as a playful allegory borrowed from China's Warring States period (the "vertical alliance vs. horizontal alliance" strategies) — but the real facts:

Flash tech was long dominated by **Samsung and Toshiba** (~70% share). In 2006, **Intel and Micron led the formation of the ONFI (Open NAND Flash Interface) alliance** to standardize the flash interface — joined by flash makers (Intel, Micron, Hynix, SanDisk), controller vendors (LSI, Marvell, SMI, JMicron, Phison), product makers (Kingston, Seagate, WD, etc.), and IP firms (Synopsys). Samsung and Toshiba responded by allying with each other (cross-licensing their OneNAND/LBA-NAND technologies) and co-developing **Toggle NAND**.

Where they landed *(p. 42–43, Table 3-6, Fig 3-42)*: ONFI 4.0 (2014) and the latest Toggle both hit **800 MT/s**; market share is roughly **50/50** (Samsung/Toshiba slightly ahead). The pin definitions aren't that different. The technical distinction: **Toggle** (sync) uses no clock — writes triggered by the **DQS** differential-signal edges, reads by the controller's **REN** differential signal; **ONFI** (sync) uses a clock with everything synchronized to it, but its DQS/Clock aren't differential (so edges are more noise-prone). Notably, **ONFI 3.0's NV-DDR2 mode dropped the clock and adopted DQS+REN differential signals — converging toward Toggle.** (The open question the book poses: will JEDEC eventually unify them?)

---

## 3.3 Flash characteristics — why flash is hard — pp. 44–58 ⭐ *the core failure modes*

### 3.3.1 The problems flash faces (p. 44–48) — *a catalog worth knowing cold*

Five ways flash misbehaves. Note which are **permanent** vs **non-permanent (fixable by erasing)**:

1. **Bad blocks (p. 44–45, Fig 3-43)** — blocks have finite life; nearing/exceeding max erase count can **permanently** damage cells. Flash also ships with **factory bad blocks**, and accumulates new ones in use — hence mandatory **bad-block management**. All written data needs **ECC** protection so occasional bit-flips are correctable; when flips exceed ECC's power, the block should be retired.
2. **Read Disturb (讀干擾) (p. 45–46, Fig 3-44)** — reading a page requires putting positive voltage on the *other* wordlines in the block (to keep them conducting). Doing this repeatedly slightly injects electrons into those cells — a "light write" that eventually flips bits. **Non-permanent** (erase fixes it). Crucially, it affects the *other* pages in the block, not the page being read.
3. **Program Disturb (寫干擾) (p. 46–47, Fig 3-45)** — writing also causes light-writes on neighbors. When writing a page, cells being written to 0 ("Programmed Cells") sit on grounded strings, while cells staying 1 ("Stressed Cells") sit on strings at positive voltage — the stressed cells get lightly written. **Non-permanent.** Unlike read disturb, program disturb affects **both** other pages *and* the page itself.
4. **Cell-to-cell coupling (p. 47–48)** — floating gates are conductors, so neighboring cells form capacitors; one cell's charge can unexpectedly shift a neighbor's, causing read errors.
5. **Charge leakage (p. 48)** — charge stored a long time slowly leaks. **Non-permanent.**

These afflict all flash (SLC/MLC/TLC); different vendors/processes/2D-vs-3D add their own. Firmware's job is to overcome or mitigate them (methods in Chapter 4).

### 3.3.2 Endurance — the physics of wearing out (p. 48–51, Figs 3-46/3-47/3-48)

Recall the read mechanism: an erased cell (−Vt) conducts at 0 V gate → "1"; a programmed cell (+Vt) doesn't → "0". For correct reads, the 0 and 1 distributions must stay **well separated**. As erase cycles accumulate, **three failure modes** appear:
1. Erased cells' threshold voltage drifts up (−Vt → 0 V) → weaker channel current → sensor misses it → error.
2. Programmed cells' threshold drifts down (+Vt → 0 V) → misread as erased.
3. Programmed cells' threshold drifts *too high* (>5 V) → the transistor stays off even at 5 V, which can shut off the entire bitline during other cells' reads.

**Why it happens:** the tunnel oxide is sensitive to thinning (smaller process) and aging (many erases). With use, the oxide develops **charge traps** that "eat" electrons, so fewer electrons reach the floating gate on writes — pushing the 0 and 1 distributions toward each other. After many erases the *erased-state* threshold rises noticeably, so drives verify after erase (set all wordlines to 0 V, check each bitline's current; a zero-current bitline means a cell's erase threshold is near 0 V → mark the block bad).

**How SSDs extend life in practice (p. 50):** **wear leveling** (spread erases evenly so no block dies early), **lower write amplification** (less wear per unit of user data), and **better ECC** (tolerate a higher raw error rate).

### 3.3.3 Flash testing (p. 51–52, Fig 3-49)

*Why do SSD makers test flash — isn't that the flash vendor's job?* "Very naive." Because: (a) shipped flash isn't guaranteed defect-free; (b) SSD manufacturing has yield issues (imperfect soldering — Fig 3-49 shows a void in a BGA solder ball); (c) makers buy cheap flash from various channels needing screening. So every chip is tested pre-ship: check each CE (Reset, Read ID), then read/write-test each LUN/plane with different data patterns (all-0s, all-1s) accounting for bit-flip rates. Bad chips get replaced; the removed ones might be repurposed into USB drives. **A useful hierarchy to remember:** flash quality demands rise USB drive → consumer SSD → enterprise SSD (as write intensity rises). Enterprise SSDs use the most expensive original flash; USB drives use the worst.

### 3.3.4 MLC usage characteristics (p. 52–54) ⭐ *the Lower-Page-corruption problem*

For MLC/TLC, pages within a block **must be written in strict sequential order** (Page 0, 1, 2, 3… — no random order). Two reasons: (a) one cell holds two pages, and you must write **Lower Page before Upper Page**; (b) cell coupling requires that earlier pages already be written before later ones. (Reads have no such restriction; SLC has no restriction.)

MLC's specific problems:
- Smaller max erase count → more need for wear leveling.
- **The Lower Page corruption problem** — this is the big one. Writing the Upper Page changes the whole cell's state *based on* the existing Lower Page. If **power is lost mid-Upper-Page-write, the already-safely-written Lower Page data can be destroyed too.** In other words, failing to write one page can corrupt a *different, already-committed* page.
- Can't write out of order (Upper before Lower) → constrains flexibility.
- Lower Page writes are fast, Upper Page writes are slow → uneven per-page write speed.

**Why Lower Page corruption is a serious design problem (p. 53–54).** It breaks two sacred storage rules: (1) once a write returns "success," the data is supposed to be safe; (2) if power is lost *during* a write, losing *that* write is acceptable. Lower Page corruption violates rule 1 — data you were told was safely written can later be destroyed by an unrelated power loss during a subsequent Upper Page write.

**Mitigations (p. 54):**
- *Consumer drives:* write Lower Page only (costly); pack Lower+Upper together (needs One-Pass Programming); **periodically flush pending Upper Pages before entering sleep**; **back up Lower Page data to another block until its Upper Page is written**; or **use MLC blocks as SLC** then migrate via garbage collection.
- *Enterprise drives:* they can't nap constantly, so they use a **large capacitor** — on power loss it supplies tens of milliseconds, enough to finish the in-flight flash writes, flush the cache, and write critical management data (like the mapping table).

### 3.3.5 Read Disturb, revisited (p. 54–56, Fig 3-50)

A real war story: a customer's read performance kept dropping over time; the culprit was read disturb. **Why it hurts performance:** read disturb injects electrons → threshold voltage drifts **right** (Data Retention drifts it *left*). If the chip keeps using the old reference voltage, it misjudges the data. The drift rate depends on **read count** (more reads → more drift) and **erase count** (more wear → easier electron entry). The fix: **track each block's read count**, and before it hits the vendor's threshold, **refresh the block** (read out, erase, rewrite) or move the data elsewhere. That refreshing consumes back-end bandwidth — which is exactly why heavy read disturb *drops performance*. (One research mitigation — lowering Vpass — helps but vendors don't expose that control, and too-low Vpass causes read failures.)

### 3.3.6 Data Retention — how long data survives (p. 56–58, Figs 3-51/3-52)

*(The book opens philosophically: even the world's oldest paper map, ~2000 years old, has decayed; even giant text carved in rock vanishes over millions of years. No storage lasts forever.)* In flash, the retention limit is reached when read data can no longer be ECC-corrected. Flash errors fall into three kinds: electrical (bad solder/chip — caught at factory test), read/write/erase command failures (rare, reported via status bits), and **ECC-uncorrectable errors** (error rate exceeds ECC power — **Data Retention is a prime cause**).

**The physics (p. 57–58):** electrons tunnel into the floating gate on write and stay — but over time they have some probability of leaking back to the channel. Enough leakage makes a written cell read like an erased one. Retention depends on tunnel-oxide thickness (thicker → slower leak; ~4.5 nm theoretically gives ~10-year retention). **Why does worn flash retain data for less time?** An effect called **Trap-Assisted Tunneling (TAT)**: with many erase cycles, the aging oxide traps charges and gains slight conductivity, so electrons escape the floating gate faster. Hence more erase cycles → shorter retention; near end-of-life (~3000 cycles) even freshly-written data errors easily. (SLC retention is years; TLC can be under a year, sometimes months.)

**The fix — Read Scrub (p. 58).** Named after the scrub feature in Sun's ZFS filesystem (which scans data and pre-corrects bit-rot before it's needed). SSD Read Scrub scans the whole drive when idle; if a page's flip count exceeds a threshold, it rewrites the data elsewhere — heading off retention-induced errors before they exceed ECC's power.

---

## 3.4 Flash data integrity — fighting back — pp. 58–69 ⭐

Because flash bit-flips grow with use, retention time, and shrinking process, SSDs deploy a stack of integrity techniques: **ECC, RAID, Read Retry, Read Scrub, and data randomization.**

### 3.4.1 Sources of read error (p. 59–63) — a consolidated summary

Five causes, each shown as a threshold-voltage distribution shift *(Figs 3-53 to 3-56)*:
1. **Erase-cycle wear** — aging oxide → charge anomalies → errors.
2. **Data Retention** — leaking electrons → whole distribution shifts **left**.
3. **Read Disturb** — accumulated light-writes → distribution shifts **right**.
4. **Cell-to-cell interference** — a neighbor's state shifts the center cell's threshold.
5. **Write errors (p. 63)** — mainly in MLC/TLC 2-pass writes: if the Lower Page is already wrong when the Upper Page is written (and note: **the Lower Page is *not* ECC-checked during the internal Upper-Page write**), the cell lands in the wrong state. (TLC 1-pass programming avoids this, since Lower and Upper are written together.)

### 3.4.2 Read Retry (p. 63–64, Fig 3-57)

??? example "🎬 Animate this — The Vt Distribution Playground"

    SLC/MLC/TLC bells in one window — drag wear, retention and read count and watch every Ch 3 failure mode happen.

    [Animation page](../animations/vt-playground.md) · [open full-screen ↗](../animations/files/vt_playground.html)

    <iframe src="../../animations/files/vt_playground.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Vt Distribution Playground"></iframe>


For the *distribution-shift* problems (retention, read disturb), data is still cleanly separated — just misread with the old reference voltage. **Read Retry keeps changing the reference voltage** until it finds a point that reads the data correctly. As long as the states haven't *overlapped*, retry can recover the data. A fancier variant, **Advanced Read Retry**, first reads nearby cells to determine their states, then reads the target twice with different references, choosing based on the neighbors.

### 3.4.3 ECC — error-correcting codes (p. 64–65) ⭐

??? example "🎬 Animate this — Stronger ECC in action — BCH & LDPC"

    BCH's algebraic error hunt and an LDPC Tanner graph converging by message passing, side by side.

    [Animation page](../animations/ecc-bch-ldpc.md) · [open full-screen ↗](../animations/files/ecc_bch_ldpc.html)

    <iframe src="../../animations/files/ecc_bch_ldpc.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="Stronger ECC in action — BCH & LDPC"></iframe>


Every SSD controller (and some flash chips) has an **ECC** module. The common algorithms are **BCH** (named for Bose, Ray-Chaudhuri, Hocquenghem) and **LDPC** (Low-Density Parity Check) — **LDPC is the growing trend** (BCH still common today). ECC parity is stored in each page's **spare/reserved area**; stronger correction needs more parity, so **correction strength is limited by that spare space** — more spare = stronger ECC.

**Static vs dynamic ECC.** Most drives use **static** ECC — fixed user-data-size and parity-size for the whole drive life, so correction strength never changes. But since young flash flips few bits and old flash flips many, some drives use **dynamic ECC**: start with *less* parity (fitting more user data per page), then strengthen correction as the drive ages. Benefits: early on, more user data per page = effectively more **OP** (lower write amplification) and better channel-bandwidth utilization. Dynamic ECC can also **vary by location** — good dies/Lower Pages get weaker ECC, weak dies/Upper Pages get stronger ECC.

### 3.4.4 RAID inside the SSD (p. 65–67) ⭐ *harder than it looks*

??? example "🎬 Animate this — Stripe RAID & the Chained Warships"

    A real XOR rebuild, then the GC trap: one block can't move alone when a parity equation chains the stripe.

    [Animation page](../animations/stripe-raid.md) · [open full-screen ↗](../animations/files/stripe_raid.html)

    <iframe src="../../animations/files/stripe_raid.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="Stripe RAID & the Chained Warships"></iframe>


When bit-flips exceed ECC's power, ECC fails — so many drives add **RAID** (typically **RAID 5**) *across dies*, treating the internal flash array like a disk array *(p. 65, Fig 3-58)*. Example: 5 dies, Die 0–3 hold user data, Die P holds their **XOR** parity; if Die 1 becomes ECC-uncorrectable, XOR the others to rebuild it. (RAID 5 recovers only a *single* uncorrectable failure; costs user space for parity — "no free lunch.")

**Why SSD RAID is genuinely hard (p. 66–67, Fig 3-59).** Traditional disk RAID writes data in stripes and updates parity in place. But **SSDs can't overwrite** — every new write goes to a new location. That's tolerable *as long as the old data isn't erased* (the stripe stays valid). The real danger: **what if one die's block in a stripe gets garbage-collected?** The stripe breaks — catastrophic. So the central problem of SSD RAID is **garbage collection: the entire RAID stripe must be garbage-collected together.** The book's vivid image: internal RAID blocks are "chained together like Cao Cao's warships at the Battle of Red Cliffs" — written together, garbage-collected together, erased together. Chaining is *stable* but *inflexible*: the big RAID blocks waste space (e.g., before sleep you must pad unfinished stripes with random data → higher write amplification), and sometimes a stripe must be garbage-collected wholesale even though one block still holds lots of valid data. (And, as at Red Cliffs, chained ships share fate — one fire burns them all.)

### 3.4.5 Data randomization (p. 67–69, Figs 3-60/3-61/3-62)

If you write raw data + ECC straight to flash, you hit many errors — because **flash is sensitive to data patterns.** Long runs of all-0s or all-1s cause **charge imbalance** inside the flash, degrading noise immunity and reliability. Two physical reasons randomization helps:
1. **Better 0/1 separation** *(Fig 3-60)* — randomized data keeps each state's distribution tight and well-isolated; un-randomized data widens some distributions, which drift into their neighbors over time and cause errors.
2. **Lower coupling impact** *(Fig 3-61)* — the four directly-adjacent cells most affect a cell's threshold; randomizing evens this out.

So controllers (or the flash) include a **randomizer** that scrambles user data so the bits written are roughly balanced 0/1 — vendors often recommend **AES** for this. Placement in the data flow *(Fig 3-62)*: randomization happens **just before the data is written to flash, after ECC parity is added** (though the ECC and randomization order can be swapped).

---

## Key vocabulary — for decoding the original figures

| 中文 | English |
|---|---|
| 閃存 | flash memory (NAND) |
| 存儲單元 | (storage) cell |
| 浮柵 (浮柵極) | floating gate |
| 電阱 / 電荷捕捉 | charge trap (CT) |
| 控制極 / 襯底 | control gate / substrate |
| 溝道 | channel |
| 隧道氧化層 | tunnel oxide |
| 量子隧道效應 | quantum tunneling |
| 閾值電壓 | threshold voltage |
| 非易失性 | non-volatile |
| 塊 (Block) / 頁 (Page) | block / page |
| 字線 / 位線 | wordline / bitline |
| 平面 (Plane) | plane |
| 緩存/頁寄存器 | cache register / page register |
| 讀干擾 | read disturb |
| 寫干擾 / 編程干擾 | program disturb |
| 耦合電容 | coupling capacitance |
| 電荷泄漏 | charge leakage |
| 數據保存期 | data retention |
| 磨損平衡 | wear leveling |
| 寫放大 | write amplification |
| 壞塊 | bad block |
| 三維閃存 | 3D flash |
| 堆疊柵極層 | stacked gate layers |
| 相變存儲器 | phase-change memory (PCM/PRAM) |
| 無定形態 / 晶體態 | amorphous / crystalline state |
| 同步 / 異步 | synchronous / asynchronous |
| 尋址 | addressing |
| 行地址 / 列地址 | row address / column address |
| 糾錯碼 | error-correcting code (ECC) |
| 重讀 | read retry |
| 掃描重寫 / 數據巡檢 | read scrub |
| 數據隨機化 / 擾碼 | data randomization / scrambling |
| 異或 | XOR |

---

## Check yourself

1. Flash's two core physical constraints each force one SSD algorithm. Name both constraints and the algorithm each one forces.
2. Going SLC → MLC → TLC, capacity per area rises but three things get worse. What are they, and what's the single underlying reason?
3. Erase happens at *block* granularity but read/write at *page* granularity. What physical fact makes erase a block-level operation?
4. Explain the Lower-Page-corruption problem and why it violates the usual "write returned success = data is safe" rule.
5. Data Retention shifts the threshold-voltage distribution one direction; Read Disturb shifts it the other. Which way does each go, and which technique exploits the fact that the states are still *separated*?
6. Why is building RAID *inside* an SSD harder than building it across ordinary disks? What single operation is the central problem, and what must be done about it?
7. Why must user data be randomized before writing to flash — give one of the two physical reasons.
8. A floating gate stores charge in a conductor; Charge Trap stores it in an insulator. Give two advantages CT gains from that, and one thing it does *worse*.

---

---

## 📘 2nd-Edition Addendum (their §5.4.3 and §5.5.4)

*Two topics the 2nd edition adds to the flash chapter that the 1st edition (your PDF) doesn't have. Both are directly relevant to your BiCS8 work.*

## A1. Asynchronous / Independent Plane Operations (their §5.4.3) ⭐

**Recall the classic constraint.** In §3.1.3 and §3.2.4 you learned that multi-plane operations run in *lockstep*: all planes get the same command at the same time, with the same page address (only the block may differ, vendor-depending). And in Chapter 2, the **die/LUN was "the basic unit that executes a flash command"** — one operation per die at a time.

**Modern NAND relaxes this — for reads.** Recent generations (roughly BiCS5 / 6th-gen V-NAND era onward, standard by BiCS8) support **Independent Plane Read (IPR)**, often in its **asynchronous** form (**AIPR**): each plane can execute its *own* read, at a *different* page address, *started at a different time* — fully independently. A 4-plane die effectively behaves like four smaller dies **for reads**.

**Why reads only (mostly)?** Reads are short and dominate QoS; programs are long, power-hungry, and share the die's charge-pump budget — so writes generally stay lockstep multi-plane while reads go independent.

**Why it matters:**
- **Random-read IOPS and tail latency.** The classic collision — a read stuck waiting because *another* read is busy on the same die — now only happens if both target the same *plane*. The effective unit of read parallelism drops from the die to the **plane**, extending the Chapter-2 parallelism ladder: channels × dies × (now) planes-for-reads.
- **Firmware implications (your world):** the flash scheduler must track *per-plane* busy state instead of per-die, interleave independent reads, and — more subtly — **data placement across planes now matters for read QoS** (striping hot data across planes avoids plane-level collisions). Cache-read pipelining (§3.1.3's two registers) also operates per plane.

## A2. 3D peripheral-circuit architectures (their §5.5.4) ⭐ *BiCS8's headline feature*

A NAND die isn't just the memory array — it needs **peripheral CMOS**: charge pumps (the ~20 V for erase, §3.1.4), sense amps, page buffers/registers, IO circuits, and the command state machine. *Where you put that periphery* has become a defining architectural choice:

**Generation 1 — periphery beside the array** (2D and early 3D): the CMOS sits next to the array on the same silicon, wasting die area — array efficiency only ~70%.

**Generation 2 — CuA (CMOS under Array; Micron from 64L, Samsung's "COP"):** build the CMOS first, then stack the 3D array *on top of it*. Array efficiency jumps (the periphery hides under the array). **The catch:** the array's high-temperature processing steps come *after* the CMOS is built, degrading those transistors — and it worsens as layer counts (and thermal budget) grow. The periphery's performance is hostage to the array's process.

**Generation 3 — wafer bonding: CBA (CMOS directly Bonded to Array).** Build the **CMOS wafer and the array wafer separately**, each on its own *optimal* process, then bond them face-to-face with millions of tiny copper contacts. YMTC pioneered the approach as "Xtacking"; **KIOXIA/WD's version, CBA, debuts with BiCS8 (218 layers)** — i.e., *your target flash is the industry's first KIOXIA/WD wafer-bonded NAND.* The wins:
- **Each wafer gets its best process** — the CMOS is no longer cooked by array thermal steps, so IO circuits can be much faster (BiCS8's headline ~3600 MT/s interface speed comes directly from this).
- **Higher array efficiency and density** (periphery consumes ~no array-side area) — BiCS8 achieves leading bit density *without* the tallest layer count.
- **Independent scaling** — the CMOS and the array can evolve on separate roadmaps.

**The takeaway:** as stacking matures, the competitive lever is shifting from raw layer count to *architecture* — periphery placement, bonding, and IO speed. When you see BiCS8's specs (moderate 218 layers, top-tier density and interface speed), CBA is the reason.

---

*Next up: Chapter 4 — SSD Core Technology: the FTL (Flash Translation Layer) — how firmware turns this fragile, can't-overwrite, wears-out medium into a reliable disk.*
