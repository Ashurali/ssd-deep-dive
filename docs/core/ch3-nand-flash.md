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

# Chapter 3 — The Storage Medium: NAND Flash (閃存)

[Chapter 1](ch1-overview.md) saw the whole drive; [Chapter 2](ch2-controllers-afa.md) dissected the controller. This chapter goes all the way down — to the **physics of a single flash cell**, where one bit of your data is a few dozen electrons trapped behind an insulator — then builds back up through chip architecture, the electrical protocols, and the many ways flash *fails*.

Two physical facts about flash generate almost everything else in this book:

1. **You must erase before you can write — nothing is overwritten in place.** This single constraint forces garbage collection and the whole FTL of [Chapter 4](ch4-ftl.md).
2. **Each block survives only a limited number of erase cycles.** This forces wear leveling and the entire reliability apparatus.

Everything from write amplification to enterprise endurance ratings is downstream of those two sentences.

!!! abstract "In this chapter — four movements plus a modern coda"
    - **The physics** — how a cell stores a bit; SLC/MLC/TLC; the cell → block → die hierarchy; 3D stacking; charge trap; PCM (§3.1)
    - **The electrical reality** — timing modes, the command set, addressing, ONFI vs Toggle (§3.2, reference-grade; skim freely)
    - **Why flash is hard** — bad blocks, read/program disturb, wear, retention, the Lower-Page trap (§3.3) ⭐
    - **Fighting back** — Read Retry, ECC, in-drive RAID, randomization (§3.4) ⭐
    - **Modern NAND** — independent plane reads and wafer-bonded dies, the BiCS8-era additions (§3.5)

    Short on time? §3.1.1–3.1.4 and §3.3 are the heart.

---

## 3.1 Flash physical structure

### 3.1.1 How a flash cell works ⭐

Nearly all SSDs use **NAND flash**, a **non-volatile** memory — it keeps data with the power off. The basic unit is a **cell**: an NMOS-like transistor with an extra **floating gate (浮柵)** sandwiched between insulating layers, sitting between the control gate above and the channel below. Electrons trapped in the floating gate stay put when power disappears — that isolation *is* the non-volatility.

- **Write (program):** apply a positive voltage to the control gate → electrons tunnel *through* the insulator *into* the floating gate.
- **Erase:** apply a positive voltage to the substrate → electrons are pulled back *out* of the floating gate.

The floating-gate transistor was invented at Bell Labs in 1967 by **Dawon Kahng and Simon Sze (施敏)** — by the story, inspired over lunch by a layered cheesecake: *what if we put something extra in the middle of a MOSFET?* Sze received a lifetime achievement award at the 2014 Flash Memory Summit, and there's a fair case he deserved more — the discoverers of GMR, the effect that kept the *hard disk* dominant, won a Nobel Prize for it.

### 3.1.2 SLC / MLC / TLC: the threshold-voltage picture ⭐

??? example "🎬 Animate this — The Vt Distribution Playground"

    SLC/MLC/TLC bells in one window — drag wear, retention and read count and watch every Ch 3 failure mode happen.

    [Animation page](../animations/vt-playground.md) · [open full-screen ↗](../animations/files/vt_playground.html)

    <iframe src="../../animations/files/vt_playground.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Vt Distribution Playground"></iframe>


SLC/MLC/TLC describe **how many bits one cell stores** — which physically means **how finely you subdivide the electron count** in the floating gate.

The one diagram to internalize in this whole chapter is the **threshold-voltage (Vt) distribution**: x-axis = threshold voltage, y-axis = number of cells. Cells programmed to the same value don't sit at exactly one voltage — they form a *bell curve* around a target. Reading a cell means testing which voltage band it falls into.

- **SLC (1 bit)** — two states, one clean divide. Erased reads **1**, programmed reads **0**. (Writing a 1 means "do nothing"; writing a 0 means "inject charge.")
- **MLC (2 bits)** — four states: four electron-count bands to tell apart (think: <10 electrons = state A, 11–20 = B, 21–30 = C, more = D).
- **TLC (3 bits)** — eight states, finer still.

**The fundamental trade-off:** on the same silicon, SLC → MLC → TLC stores 1 → 2 → 3 bits, so cost per GB falls. But more bands means (a) programming must place the electron count more precisely → **slower writes**, (b) reading must test more reference voltages → **slower reads**, and (c) the bells sit closer together → **less margin → shorter endurance**. Performance and lifespan rank **SLC > MLC > TLC**; capacity-per-dollar ranks the other way. 3D TLC is today's mainstream; QLC (4 bits, sixteen bands) continues the same trade.

### 3.1.3 The hierarchy: cell → page → block → plane → die ⭐

??? example "🎬 Animate this — Why SSDs need an FTL — NAND flash, animated"

    Pages, blocks and the no-overwrite rule — the hierarchy this section describes, animated stage by stage.

    [Animation page](../animations/nand-flash-animation.md) · [open full-screen ↗](../animations/files/nand-flash-animation.html)

    <iframe src="../../animations/files/nand-flash-animation.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="Why SSDs need an FTL — NAND flash, animated"></iframe>


A flash chip is millions of cells in a strict nesting — memorize this ladder:

**cell → (page) → wordline → block → plane → die/LUN → chip**

- A **wordline** carries one or more **pages**: SLC = 1 page per wordline; MLC = 2 (**Lower Page** + **Upper Page**); TLC = 3 (Lower, Upper, Extra).
- A **block** is the set of wordlines **sharing one substrate** — which is exactly why erase happens at block granularity (§3.1.4).
- A **die (LUN)** is **the basic unit that receives and executes a flash command.** Two dies can run *different* commands simultaneously — a key source of parallelism — but within one die, classically only one operation runs at a time. (§3.5.1 shows how modern flash relaxes this for reads.)
- A **plane** (1, 2, now commonly 4 per die) has its own **Cache Register** and **Page Register**, each one page in size.

**Why two registers?** All media transfers happen **a whole page at a time**: writes go controller → Cache Register → flash array; reads go array → register → controller. Two registers let the chip **overlap bus transfer with media access**: while page N streams out of the Cache Register to the controller, page N+1 is already loading from the media into the Page Register (**Cache Read / Cache Program**). The slower operation hides behind the faster one.

!!! note "A definitional subtlety that bites timing calculations"
    Quoted flash "read time" and "program time" cover only the media ↔ Page Register hop — **not** the register ↔ controller bus transfer. Keep the two separate when you reason about throughput (the timing-lab animation in §3.2.5 draws them as separate bars).

**Multi-plane operation — a big cheap win.** Load several planes' Cache Registers, then commit them together. With a 1.5 ms program and 50 µs transfer: two pages single-plane = (1.5 ms + 50 µs) × 2; dual-plane = 1.5 ms + 2 × 50 µs — **nearly 2× the write speed**. Reads gain the same way.

**Endurance by cell type:** maximum erase cycles fall from SLC (up to ~100K) → MLC (thousands to tens of thousands) → TLC (hundreds to a few thousand). And as process nodes shrank into the 1X nm era, capacity rose while raw performance and reliability *worsened* — pushing ever more of the burden onto firmware. That's the recurring theme of this book: **the medium gets worse; the algorithms get better.**

### 3.1.4 Read, write, erase: the actual voltages

- **Erase:** ~20 V on the P-well; quantum tunneling pulls electrons out of every floating gate in the block; the whole block reads "1" (−Vt). Blocks not being erased float their gates — no field, no tunneling.
- **Write:** the target wordline gets a high voltage with its bitline at 0 V → electrons tunnel into the floating gate → "0". Cells to be left alone get their bitline at ~2 V, suppressing tunneling.
- **Read:** all *other* wordlines get ~5 V (forcing those transistors to conduct regardless of state); the target wordline gets 0 V. An erased cell (−Vt) conducts → the bitline sense amp reads "1"; a programmed cell (+Vt) stays off → "0".

Don't memorize the numbers — they vary by chip. Internalize the pattern: **erase = whole block to all-1s via the substrate; write = inject charge to make 0s; read = sense conduction at 0 V.**

### 3.1.5 3D flash

**The wall 2D hit.** For a decade, planar flash shrank cells to cut cost — but smaller cells sit closer together, and **cell-to-cell interference grows** as spacing shrinks, until shrinking further stopped reducing cost-per-good-bit.

**The 3D answer: stop shrinking, start stacking.** Stand the channel upright and stack wordlines "floor by floor" like a building. Each generation adds roughly 40% more gate layers — cutting cost ~40% per generation *without* shrinking the cell. The cells actually got *bigger* again, so **interference dropped** even as density soared. This is the technology that let SSDs chase HDDs out of the mainstream (flash-market share of SSDs rose from 23% to 43% between 2013 and 2017).

**Two milestone architectures:** **BiCS** (Bit Cost Scalable, Toshiba 2007) and **TCAT** (Terabit Cell Array Transistor, Samsung 2009). They differ in cell-string structure and erase method — BiCS: polysilicon gates, GIDL erase, narrower program/erase window; TCAT: metal gates, bulk erase, wider window. Against 2D, TCAT delivered **−84% interference, >10× endurance, half the program time, −67% threshold-voltage shift**. Layer counts marched 24 → 32 → 48 → 64, roughly doubling density each step — and kept going (§3.5.2 picks the story up at 218 layers).

**3D's own headaches:**

1. **More layers → smaller string current** and **growing top-vs-bottom differences**. More pages per block also concentrates more reads per block → worse read disturb → lower read-pass voltages → weaker signal margins.
2. **Layer-to-layer variation:** the etched channel hole tapers — bottom cells have smaller holes (higher coupling → faster erase) and thinner gate films (shorter retention). The firmware increasingly has to treat *layers* differently, not just blocks.

### 3.1.6 Charge-trap flash: the other way to hold an electron

**Charge Trap (CT, 電荷捕捉)** replaces the floating gate's *conductor* with an **insulator** — usually silicon nitride, Si₃N₄ — riddled with "traps" that catch electrons. The classic analogy: a floating gate stores electrons like **water** (they slosh freely inside the container); charge trap stores them like **cheese** (each electron is stuck where it landed).

**Why "stuck" wins:**

- **Insensitive to tunnel-oxide wear.** In a floating gate, once the oxide thins or ages, the free-sloshing electrons leak out through any weak point. Trapped electrons can't reach the weak point.
- **Far less cell-to-cell coupling.** Two nearby *conductors* form a capacitor (C = εS/4πkd) — so floating-gate neighbors disturb each other, worse as distance d shrinks. An insulator mostly opts out of this.
- **Lower program/erase voltage.** The CT stack is physically shorter, and the same tunneling field needs less voltage across less distance (E = U/d) → less oxide stress, slower wear, lower power.

**The cost:** CT is *worse* at read disturb and data retention than floating gate. The market's verdict anyway: **every major vendor except Micron builds 3D flash on charge trap** (Micron held to floating gate).

### 3.1.7 3D XPoint and the emerging-memory zoo

**The gap being targeted:** DDR4 DRAM moves ~46–61 GB/s but forgets everything at power-off; a 4-lane PCIe 3.0 SSD tops out ~4 GB/s and SATA at ~600 MB/s. The dream: **DRAM-class speed that survives power loss.** The candidate list: ReRAM/memristor, FeRAM, MRAM, PRAM/PCM, cbRAM/PMC, SONOS, CMOx.

**Phase-Change Memory (PCM)** is the most mature. The physics: a chalcogenide (typically **GST**, Ge₂Sb₂Te₅) switches between an **amorphous** state (disordered like glass — high resistance) and a **crystalline** state (ordered like snowflakes — low resistance). Two stable, distinguishable states = one bit.

- **Read:** measure resistance — low (crystalline) = "0", high (amorphous) = "1".
- **Write:** a microscopic heater melts and re-forms the material — a short, very hot pulse freezes it amorphous; a longer, gentler pulse lets it crystallize.

PCM's attractions over flash: byte-addressable, **no erase-before-write**, fast, low power, and orders-of-magnitude longer endurance — organized in a familiar bitline/wordline matrix. Intel/Micron's 3D XPoint (Ch 1 §1.3, 2015) was the first mass-market attempt to fill the DRAM-flash gap with this class of memory.

---

## 3.2 Talking to a flash chip: the electrical protocols

*Reference-grade detail on how the controller physically drives a chip. Skim unless you do hardware or firmware work — but read §3.2.6, which everyone should know.*

### 3.2.1 Asynchronous timing

Flash interfaces come **async** (slow, no clock) and **sync** (fast, clocked). Async: each data-out is triggered by an **RE_n** pulse, each data-in by **WE_n**. The signal cast, which you met from the controller side in [Chapter 2](ch2-controllers-afa.md#213-back-end): **CLE** (bytes on the bus are a command), **ALE** (bytes are an address), **CE_n** (chip select — the industry calls one selectable target "a CE"), **WE_n**, **RE_n**, **R/B_n** (ready/busy). Datasheet timing parameters (tWP, tWH, tWC, tDS, tDH) specify pulse widths and setup/hold windows.

### 3.2.2 Synchronous timing

Sync adds a clock (**CLK**) and a **data strobe (DQS)**, and modern flash runs **DDR** — data on both clock edges, so 100 MHz → 200 MT/s. DQS frames every transfer window (driven by the flash on reads, by the controller on writes) so the receiver samples at the right instant; **W/R_n** sets direction.

### 3.2.3 The command set

The controller drives flash with two-phase command sequences (ONFI 2.3 shown): **Read (00h–30h)**, **Multi-plane Read (00h–32h)**, **Change Read Column (05h–E0h** — fetch from an offset within the loaded page), **Block Erase (60h–D0h)**, **Read Status (70h)** and **Read Status Enhanced (78h**, multi-LUN), **Page Program (80h–10h)**, **Multi-plane Program (80h–11h)**, **Read ID (90h)**, **Read Parameter Page (ECh** — the chip describes its own geometry and capabilities), **Get/Set Features (EEh/EFh)**.

### 3.2.4 Addressing

Two coordinates: the **column address** is the byte offset *within* a page; the **row address**, high bits to low, is **LUN → block → page**. The plane number hides in the **lowest bit(s) of the block address** — which is why multi-plane operations pair odd/even blocks. Vendor quirk: all planes in a multi-plane op must share the same *page* address; Intel/Micron and Toshiba allow different *block* addresses, Samsung requires the same.

### 3.2.5 Read / write / erase on the wire

??? example "🎬 Animate this — The Flash Timing & Parallelism Lab"

    The bus, the registers and the planes on one timeline — toggle pipelining and AIPR and watch the bars move.

    [Animation page](../animations/flash-timing-lab.md) · [open full-screen ↗](../animations/files/flash_timing_lab.html)

    <iframe src="../../animations/files/flash_timing_lab.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Flash Timing & Parallelism Lab"></iframe>


- **Read:** 00h → 2 column bytes + 3 row bytes → 30h; status bit SR[6] goes Busy while the array loads the register, then data streams out.
- **Program:** 80h → address (**column normally 0 — pages must be filled from the start, or you risk data errors**) → data into the register → 10h to commit; SR[6] Busy → Ready.
- **Erase:** 60h → LUN + block row address → D0h. Block granularity only.

### 3.2.6 ONFI vs Toggle: the protocol war ⭐

There are **two** flash interface standards, and the split is pure industry politics. Flash was long dominated by **Samsung and Toshiba** (~70% share together). In 2006, **Intel and Micron formed the ONFI alliance** (Open NAND Flash Interface) to standardize the interface — pulling in flash makers (Hynix, SanDisk), controller vendors (LSI, Marvell, SMI, JMicron, Phison), system makers (Kingston, Seagate, WD…), and IP firms (Synopsys). Samsung and Toshiba answered by allying with *each other* — cross-licensing and co-developing **Toggle NAND**.

Where it landed: ONFI 4.0 (2014) and contemporary Toggle both reached **800 MT/s**; market share split roughly **50/50** (Samsung/Toshiba slightly ahead); the pinouts aren't even very different. The real technical distinction: **Toggle** has no free-running clock — writes are strobed by **DQS** differential edges, reads by the controller's **REN** differential signal; **ONFI** synchronizes everything to a clock, but its strobe/clock weren't differential, making edges more noise-prone. Tellingly, **ONFI 3.0's NV-DDR2 mode dropped the clock and adopted differential DQS + REN — converging on Toggle's approach.** The two standards have been drifting together ever since; whether JEDEC one day unifies them formally remains open.

---

## 3.3 Why flash is hard: the failure modes ⭐

### 3.3.1 The five problems — a catalog to know cold

Note which are **permanent** and which are **non-permanent** (cured by erasing the block):

1. **Bad blocks** — blocks have finite life; wear can damage cells **permanently**. Chips also ship with **factory bad blocks** and grow new ones in service — hence mandatory bad-block management ([Chapter 4](ch4-ftl.md) §4.5), ECC on everything, and retirement of blocks whose error counts exceed correction capacity.
2. **Read disturb (讀干擾)** — reading a page puts pass voltage on all *other* wordlines in the block (to force them conducting, §3.1.4). Each read is a faint program pulse on those neighbors; enough reads flip bits. **Non-permanent.** Affects the block's *other* pages, not the one being read.
3. **Program disturb (寫干擾)** — programming also lightly writes neighbors: cells meant to stay "1" ("stressed cells") sit on strings at positive voltage while their wordline fires. **Non-permanent.** Unlike read disturb, it can hit **both** other pages *and* the page being written.
4. **Cell-to-cell coupling** — floating gates are conductors; neighbors form capacitors; one cell's charge shifts another's apparent threshold (§3.1.6 explained why charge trap suffers less).
5. **Charge leakage** — stored charge slowly escapes over time. **Non-permanent.** (This is data retention, expanded in §3.3.6.)

All flash suffers all five; process node, 2D vs 3D, and vendor recipes shift the mix. Firmware's whole job ([Chapter 4](ch4-ftl.md)) is living with them.

### 3.3.2 Endurance: the physics of wearing out

For a correct read, the erased (−Vt) and programmed (+Vt) distributions must stay **separated** (§3.1.2). Accumulating erase cycles blurs that separation in three ways:

1. Erased cells' threshold drifts *up* toward 0 V → weaker channel current at read → sensed as programmed.
2. Programmed cells' threshold drifts *down* toward 0 V → sensed as erased.
3. Programmed cells' threshold drifts *too high* (> read-pass voltage) → the cell won't conduct even as a "pass" transistor — which corrupts reads of *every other page* on its bitline.

**The mechanism:** the tunnel oxide degrades with every erase. The aging oxide accumulates **charge traps** that swallow electrons in transit, so programs place less charge than intended and the distributions creep toward each other. Because the *erased* threshold rises with wear, drives verify erases (all wordlines at 0 V; any bitline with no current ⇒ some cell failed to erase ⇒ retire the block as bad).

**The three levers that extend life in practice:** **wear leveling** (no block dies early), **lower write amplification** (less wear per byte of user data), and **stronger ECC** (tolerate a higher raw error rate). All three are Chapter 4's business.

### 3.3.3 Flash testing

Why do SSD makers test flash — isn't that the fab's job? Three reasons: shipped flash isn't guaranteed defect-free; SSD assembly has its own yield problems (BGA solder voids are a classic); and cheaper flash from secondary channels needs screening. So every chip is exercised before a drive ships: per-CE Reset + Read ID, then read/write tests per LUN and plane with multiple data patterns (all-0s, all-1s), tracking flip rates. Failing chips are replaced — and often live a second life in USB drives.

!!! tip "The flash quality ladder"
    Required flash quality rises **USB drive → consumer SSD → enterprise SSD**, in step with write intensity. Enterprise drives get the best original flash; USB sticks get what's left. Worth remembering when a bargain drive seems too cheap.

### 3.3.4 MLC's rules — and the Lower-Page corruption trap ⭐

MLC/TLC blocks must be written **in strict page order** (0, 1, 2, 3…). Two reasons: one physical cell carries two (or three) pages, and the **Lower Page must be programmed before the Upper Page**; and coupling compensation assumes earlier pages are already in place. (Reads have no ordering rule; SLC has no rule at all.)

The consequences stack up:

- Lower max erase counts → wear leveling matters more.
- Lower Pages program fast, Upper Pages slow → per-page write latency is uneven.
- No out-of-order writes → less scheduling freedom.
- And the big one:

!!! warning "Lower-Page corruption"
    Programming the Upper Page re-shapes the *whole cell's* charge based on the Lower Page already in it. **Lose power mid-Upper-Page-program, and the previously committed Lower Page data is destroyed too.** This violates storage's most sacred rule — *data acknowledged as written stays written* — because a page that succeeded long ago dies in someone else's power failure. (Losing the write that was actually in flight is considered acceptable; losing a *different, older* write is not.)

**Mitigations.** Consumer drives: write Lower Pages only (expensive); pair Lower+Upper in one pass (needs One-Pass Programming support); flush pending Upper Pages before entering sleep; keep a backup copy of Lower-Page data in another block until its Upper Page lands; or run MLC blocks in SLC mode as a staging cache and migrate later via GC. Enterprise drives can't nap, so they carry **capacitors**: tens of milliseconds of reserve power — enough to finish in-flight programs, flush caches, and save the mapping table ([Supplement D](../supplements/d-power-management.md) designs that circuit; [Chapter 4](ch4-ftl.md) §4.9 covers the recovery logic).

### 3.3.5 Read disturb in the field

A war story that generalizes: a customer's read performance sagged steadily over weeks; the culprit was read disturb. The mechanism connects §3.3.1 to performance: read disturb injects electrons → the Vt distribution drifts **right** (retention drifts it **left**); with the old reference voltage, reads start failing and the drive burns time on error recovery. Drift rate scales with **read count** and with **wear** (aged oxide admits electrons more easily).

The management strategy: **count reads per block**, and before the count reaches the vendor's threshold, **refresh** — read the data out, erase the block, rewrite (or move the data elsewhere). Refreshing consumes back-end bandwidth, which is precisely *why* heavy read disturb shows up as a performance drop. (Research suggests lowering the pass voltage helps; vendors don't expose that knob, and too low causes read failures.)

### 3.3.6 Data retention: how long does data survive?

No storage lasts forever — the oldest surviving paper maps are ~2,000 years old and fading; even words carved in rock erode. Flash's version: **retention ends when accumulated bit-flips exceed what ECC can correct.**

**The physics.** Programmed electrons sit behind the tunnel oxide, but each has some probability of leaking back to the channel. Enough leakage and a programmed cell reads erased. Retention depends on oxide thickness (~4.5 nm theoretically yields ~10-year retention) — and on wear, through **Trap-Assisted Tunneling (TAT)**: an aged, trap-riddled oxide becomes slightly conductive, so electrons escape *faster* from worn cells. Hence the double squeeze: more erase cycles → shorter retention. Near end of life (~3,000 cycles for the MLC of this era), even freshly written data errors easily. Rules of thumb: SLC retains for years; TLC can be months.

**The countermeasure — Read Scrub.** Named for ZFS's scrub feature: patrol the data *before* it's needed. The SSD scans itself during idle time; any page whose correctable-flip count crosses a threshold gets rewritten to a fresh location. Retention errors are headed off while they're still correctable.

---

## 3.4 Fighting back: the data-integrity stack ⭐

Flash error rates grow with wear, retention time, and process shrink — so SSDs stack defenses: **Read Retry, ECC, internal RAID, Read Scrub, and randomization.**

### 3.4.1 Sources of read error, consolidated

Five causes, all visible as Vt-distribution movements (and all reproducible in the playground animation below):

1. **Erase-cycle wear** — trap buildup distorts programming (§3.3.2).
2. **Data retention** — leakage shifts distributions **left**.
3. **Read disturb** — accumulated soft-programming shifts them **right**.
4. **Cell-to-cell interference** — a neighbor's state nudges the victim's apparent Vt.
5. **Write errors** — mainly the MLC two-pass sequence: if a Lower Page is already corrupt when its Upper Page programs, the cell lands in the wrong final state — and **the internal Upper-Page program does not ECC-check the Lower Page it builds on**. (TLC one-pass programming sidesteps this by writing all pages of a wordline together.)

### 3.4.2 Read Retry

??? example "🎬 Animate this — The Vt Distribution Playground"

    SLC/MLC/TLC bells in one window — drag wear, retention and read count and watch every Ch 3 failure mode happen.

    [Animation page](../animations/vt-playground.md) · [open full-screen ↗](../animations/files/vt_playground.html)

    <iframe src="../../animations/files/vt_playground.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Vt Distribution Playground"></iframe>


The drift failures (retention, read disturb) share a saving grace: the distributions moved, but they're usually still *separated* — the data is intact, just misread against a stale reference voltage. **Read Retry re-reads with shifted reference voltages** until one lands between the bells. As long as adjacent states haven't overlapped, retry recovers everything. The refinement, **Advanced Read Retry**, first reads the *neighboring* cells, then reads the target twice with different references and picks the result the neighbors vote for.

### 3.4.3 ECC: error-correcting codes ⭐

??? example "🎬 Animate this — Stronger ECC in action — BCH & LDPC"

    BCH's algebraic error hunt and an LDPC Tanner graph converging by message passing, side by side.

    [Animation page](../animations/ecc-bch-ldpc.md) · [open full-screen ↗](../animations/files/ecc_bch_ldpc.html)

    <iframe src="../../animations/files/ecc_bch_ldpc.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="Stronger ECC in action — BCH & LDPC"></iframe>


Every controller carries an ECC engine ([Chapter 2](ch2-controllers-afa.md#213-back-end) placed it in the back end). The algorithms: **BCH** (Bose–Ray-Chaudhuri–Hocquenghem) and **LDPC** (Low-Density Parity-Check), with LDPC taking over as flash got denser. Parity lives in each page's **spare area**, so **correction strength is capped by spare-area size** — more spare bytes, stronger code. [Supplement A](../supplements/a-ecc-coding-theory.md) derives both algorithms from first principles.

**Static vs dynamic ECC.** Most drives fix the user-data/parity split for life (**static**). But young flash barely errs while old flash errs constantly — so some drives run **dynamic ECC**: start with less parity (more user data per page → effectively more OP → lower write amplification, better bus utilization), then strengthen the code as wear accumulates. Dynamic schemes can also vary **by location**: strong dies and Lower Pages get light parity; weak dies and Upper Pages get heavy parity.

### 3.4.4 RAID inside the SSD ⭐

??? example "🎬 Animate this — Stripe RAID & the Chained Warships"

    A real XOR rebuild, then the GC trap: one block can't move alone when a parity equation chains the stripe.

    [Animation page](../animations/stripe-raid.md) · [open full-screen ↗](../animations/files/stripe_raid.html)

    <iframe src="../../animations/files/stripe_raid.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="Stripe RAID & the Chained Warships"></iframe>


When flips exceed ECC's power, the last line of defense is **RAID across dies** (typically RAID 5): dies 0–3 hold data, die P holds their **XOR**; when one die's page turns uncorrectable, XOR the survivors to rebuild it. Limits apply — RAID 5 absorbs exactly *one* uncorrectable member per stripe, and parity costs user capacity. No free lunch.

**Why in-SSD RAID is genuinely hard.** Disk RAID updates parity *in place* — and flash can't overwrite (§3.1.1). New writes land at new locations, which is survivable *while the old stripe members stay put*. The catastrophe scenario: **garbage collection moves one block out of a stripe** — the parity equation now points at reclaimed space. So the central rule of SSD RAID is that **the whole stripe garbage-collects together**: written together, moved together, erased together. Like the chained warships at Red Cliffs — stable in formation, but inflexible (unfinished stripes must be padded before sleep → extra write amplification; sometimes a stripe full of valid data must be collected wholesale) — and sharing fate by design.

### 3.4.5 Data randomization

Write raw user data straight to flash and errors climb, because **flash is pattern-sensitive**: long runs of 0s or 1s create **charge imbalance** that degrades noise margins. Randomization fixes two physical problems:

1. **Cleaner state separation** — scrambled data keeps every Vt bell tight and isolated; patterned data fattens some bells until, with drift, they invade their neighbors.
2. **Evened-out coupling** — a cell's threshold is most disturbed by its four direct neighbors; random data statistically balances those influences.

So a **randomizer** (vendors often suggest AES simply as a good scrambler) sits in the write path, keeping the physical bit stream near 50/50. Order of operations: ECC parity is computed, then the whole payload is randomized just before hitting flash (some designs swap the two stages).

---

## 3.5 Modern NAND: two BiCS8-era innovations

*The first edition ends at §3.4. These two topics arrived with recent flash generations and complete the picture — both matter enormously in current firmware work.*

### 3.5.1 Independent plane operations (IPR / AIPR) ⭐

**The classic constraint** (§3.1.3, §3.2.4): multi-plane operations run in lockstep — same command, same page address, issued together — and the die is "the basic unit that executes a command," one operation at a time.

**Modern NAND relaxes this — for reads.** From roughly the BiCS5 / 6th-gen V-NAND era, standard by BiCS8, chips support **Independent Plane Read (IPR)**, usually in asynchronous form (**AIPR**): each plane executes its *own* read at its *own* address, *started at its own time*. A 4-plane die behaves like four smaller dies — **for reads**.

**Why reads only?** Reads are short and dominate QoS; programs are long, power-hungry, and share the die's charge-pump budget. So programs stay lockstep while reads go independent.

**Why it matters:**

- **Random-read IOPS and tail latency.** The classic collision — a read queued behind another read on the same die — now happens only when both target the same *plane*. The unit of read parallelism drops from die to **plane**, extending Chapter 2's ladder: channels × dies × *planes-for-reads*. (Toggle AIPR on in the §3.2.5 timing-lab animation and watch the read bars unstack.)
- **Firmware implications:** the flash scheduler tracks *per-plane* busy state; hot data wants to be **striped across planes** so reads don't collide; cache-read pipelining (§3.1.3's two registers) operates per plane.

### 3.5.2 Peripheral circuits: beside → under → bonded ⭐

A NAND die isn't just the array — it needs **peripheral CMOS**: charge pumps (the ~20 V of §3.1.4), sense amplifiers, page buffers, IO circuits, the command state machine. *Where that periphery lives* has become a defining architectural choice:

- **Generation 1 — periphery beside the array** (2D and early 3D): CMOS sits next to the array, spending die area — array efficiency only ~70%.
- **Generation 2 — CuA (CMOS under Array**; Micron from 64L, Samsung's "COP"): build the CMOS first, stack the array on top. Efficiency jumps — but the array's high-temperature process steps now *cook the finished CMOS*, degrading it, and it worsens as layer counts (and thermal budget) climb. The periphery is hostage to the array's process.
- **Generation 3 — wafer bonding: CBA (CMOS Bonded to Array).** Build the **CMOS wafer and the array wafer separately**, each on its own optimal process, then bond them face-to-face through millions of micron-scale copper contacts. YMTC pioneered it as "Xtacking"; **KIOXIA/WD's CBA debuts with BiCS8 (218 layers)** — the first wafer-bonded NAND from that alliance. The wins: the CMOS is never cooked (BiCS8's headline ~3,600 MT/s interface speed comes straight from this), array efficiency approaches ideal (periphery takes no array-side area — leading bit density *without* the tallest stack), and the two wafers scale on independent roadmaps.

**The takeaway:** the competitive lever in NAND is shifting from raw layer count to *architecture* — periphery placement, bonding, IO speed. BiCS8's spec sheet (moderate 218 layers, top-tier density and interface speed) only makes sense once you know CBA is under the hood.

---

## Key takeaways

1. **Two physical facts rule everything:** erase-before-write (→ FTL, GC) and finite erase cycles (→ wear leveling, ECC). The rest of the book is corollary.
2. **The Vt distribution is the master diagram.** Wear widens the bells, retention slides them left, read disturb slides them right, and every recovery trick (Read Retry, stronger ECC) is a way of still telling the bells apart.
3. **Know the ladder**: cell → page/wordline → block (erase unit, shared substrate) → plane (registers) → die (command unit) → chip — and that modern flash breaks the "one op per die" rule for reads (AIPR).
4. **MLC's ordering rules have teeth**: Lower-Page corruption breaks "written means safe," and enterprise capacitors exist largely because of it.
5. **The integrity stack layers cheap-to-expensive**: randomize always, ECC every read, Retry when references drift, RAID-rebuild when ECC fails — and scrub in the background before any of it is needed.
6. **The medium keeps getting worse as density rises; the system keeps getting better.** 3D stacking, charge trap, and wafer bonding are how the industry keeps that bargain going.

---

## Key vocabulary

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
9. With AIPR, what replaces the die as the unit of read parallelism — and what new data-placement concern does that create for firmware?

---

??? info "📖 Book page map — for readers of 《深入淺出SSD》"

    This chapter follows Chapter 3 of《深入淺出SSD》(SSDFans, 2018);
    §3.5 covers 2nd-edition additions (their §5.4.3 and §5.5.4). Original
    figures by section:

    | Section | Book pages | Key figures/tables |
    |---|---|---|
    | 3.1.1–3.1.2 Cell & Vt | pp. 1–5 | Figs 3-1…3-5, Table 3-2 |
    | 3.1.3–3.1.4 Hierarchy & voltages | pp. 5–12 | Figs 3-6…3-11 |
    | 3.1.5 3D flash | pp. 13–21 | Figs 3-12…3-19 |
    | 3.1.6 Charge trap | pp. 21–24 | Figs 3-20…3-23 |
    | 3.1.7 PCM / 3D XPoint | pp. 24–32 | Figs 3-25…3-30, Table 3-3 |
    | 3.2 Protocols | pp. 32–44 | Figs 3-31…3-42, Tables 3-5/3-6 |
    | 3.3 Failure modes | pp. 44–58 | Figs 3-43…3-52 |
    | 3.4 Integrity stack | pp. 58–69 | Figs 3-53…3-62 |

*Next: [Chapter 4 — The FTL](ch4-ftl.md) — how firmware turns this fragile, can't-overwrite, wears-out medium into a reliable disk.*
