---
title: "Ch 4 — FTL"
tags:
  - ftl
  - mapping
  - garbage-collection
  - write-amplification
  - over-provisioning
  - trim
  - wear-leveling
  - power-loss-recovery
  - bad-blocks
  - slc-cache
  - zns
  - fdp
source_anchor: "CH4 file, pp. 1–72"
---

# SSD Deep Dive — Chapter 4: The Core Technology — FTL (Flash Translation Layer)
## English Study Companion

**Where we are:** Chapter 3 left you with a fragile medium — flash that can't be overwritten, wears out, disturbs its own neighbors, and forgets over time. This chapter is about the software that tames it. The **FTL (Flash Translation Layer)** is what turns that unruly medium into something that looks, from the outside, like an ordinary reliable disk. The book calls it "the core of SSD firmware," and it's the longest, most important chapter in the book. Chapter 4 runs pages 1–72 of your file (p. 73 is empty website comments).

**How to use this guide:** Section numbers match the book. Page references like *(p. 22, Fig 4-19)* point into your CH4 file so you can view the original diagram beside the explanation. Because you asked for more depth, I've (a) worked through the book's numerical examples step by step, and (b) added a large **"Modern developments"** section at the end — the book (2018) *previews* host-managed flash with Baidu's research project, and that idea has since become two real, standardized product categories (**ZNS** and **FDP**). That supplement is drawn from current industry sources and attributed inline. Glossary and self-quiz at the very end.

**The chapter's shape:** 4.1 frames the whole problem. Then each section is one FTL job: **4.2 mapping**, **4.3 garbage collection** (+ write amplification + over-provisioning — the conceptual heart), **4.4 Trim**, **4.5 wear leveling**, **4.6 power-loss recovery**, **4.7 bad-block management**, **4.8 SLC cache**, **4.9 read-disturb & retention handling**, **4.10 host-based FTL**, **4.11 wrap-up**. If your time is limited, **4.2, 4.3, and 4.6** are the ones to know cold.

---

## 4.1 FTL overview — pp. 1–4 ⭐ *the framing for everything*

**What the FTL is:** it translates the host's **logical address space** into the flash's **physical address space** — i.e., it maintains a mapping. Every time the SSD writes a chunk of user data to flash, it records the logical→physical mapping; on read, it looks up the mapping and fetches from the right place. That's the *original, basic* job. But because of flash's quirks, the FTL ends up doing far more.

**The seven flash facts that create FTL work (p. 1–3)** — this list is the "why" behind the entire chapter:

1. **Can't overwrite in place** → forces a **mapping table** (new data goes to a new location) *and* **garbage collection** (old locations become invalid garbage that must be reclaimed).
2. **Blocks have limited erase (P/E) life** → forces **wear leveling** (spread erases evenly so no block dies early).
3. **Reads are limited (read disturb)** → forces read-disturb handling (refresh a block before its read count corrupts data).
4. **Data retention (charge leaks over time)** → forces retention handling (when powered on, scan and rewrite aging data before it's lost — and note: if the SSD is *never* powered on, the FTL is helpless).
5. **Factory + growing bad blocks** → forces **bad-block management**.
6. **MLC/TLC Lower-Page corruption** → forces mechanisms to avoid losing already-committed data on power loss.
7. **MLC/TLC can run in faster SLC mode** → lets a good FTL use **SLC cache** to improve speed and reliability.

**Where the FTL lives (p. 3–4, Figs 4-1/4-2):** **Host-Based** (FTL runs on the host's CPU/RAM — e.g., the famous Fusion-IO) vs **Device-Based** (FTL runs on the SSD's own controller/RAM). **Almost all modern SSDs are Device-Based**, so the whole chapter assumes that unless stated (host-based gets its own treatment in 4.10, and my modern supplement picks up that thread).

---

## 4.2 Mapping management — pp. 4–15 ⭐

### 4.2.1 Mapping granularity (p. 4–8, Figs 4-3/4-4/4-5, Table 4-1)

Three schemes, trading table size against performance:

- **Block mapping (p. 5)** — map at *block* granularity. Tiny table, but **terrible for small writes**: to change even one logical page, you must read the whole physical block, modify that page, and rewrite the entire block. Good for big sequential transfers only. *This is what USB drives use* — which is exactly why USB drives have awful random performance ("don't complain about USB random speed — use an SSD for your OS").
- **Page mapping (p. 6)** — map at *page* granularity. Every logical page maps to any physical page. Much bigger table, but **great performance, especially random writes.** **SSDs use page mapping** for performance.
- **Hybrid mapping (p. 6–7)** — block-map across blocks, page-map within a block. Table size and performance sit between the two.

The rest of the chapter assumes **page mapping**.

### 4.2.2 How mapping works, and the DRAM question (p. 8–12, Figs 4-6 to 4-9) ⭐

The host addresses the SSD by **LBA (Logical Block Address)**; each LBA is a **logical page** (512 B / 4 KB / 8 KB…). Internally the controller reads/writes flash in **physical pages**. Every write creates or updates one entry in the **map table**; every read looks up that table then fetches from flash. (Since a physical page is usually bigger than a logical page, several logical pages actually pack into one physical page — the logical page maps to a *sub*-physical-page.)

**How big is the map table? (p. 9–10) — worth memorizing the rule.** For a 256 GB SSD with 4 KB logical pages: 256 GB ÷ 4 KB = 64M logical pages. At 4 bytes per entry: 64M × 4 B = **256 MB**. The rule of thumb: **the map table is ~1/1000 of SSD capacity** (precisely 1/1024, given 4 KB pages and 4-byte addresses). This is why most SSDs carry **onboard DRAM roughly 1 GB per 1 TB** — to hold the whole table for fast lookups *(p. 10, Fig 4-7)*.

**DRAM-less designs (p. 10–12, Figs 4-8/4-9).** Entry-level SSDs and mobile storage (eMMC, UFS) skip DRAM for cost/power. Where does the table go? **Two-level mapping (L2P):** a small first-level table lives in on-chip **SRAM**; the large second-level table lives mostly **in flash**, with a small piece cached in SRAM. The cost: a DRAM SSD needs **one** flash access per read (map is in DRAM), but a DRAM-less SSD, on a cache miss, needs **two** (first read the mapping from flash, then read the data) — halving effective bandwidth. **Sequential reads** stay fast (one map-chunk load serves many contiguous pages), but **random reads** suffer (each needs its own map load → two flash accesses).

### 4.2.3 HMB — Host Memory Buffer (p. 12–15, Figs 4-10 to 4-13) ⭐

A key **NVMe 1.2+** feature: the host carves out a slice of *its own* system RAM and lends it to the SSD, which uses it like onboard DRAM — for the map table and/or user-data cache. Performance lands **between** DRAM and DRAM-less designs: accessing host RAM (over PCIe) is slower than onboard DRAM but far faster than reading flash (~40 μs). Marvell's 88NV1140 (CES 2016) was the first controller to implement it; Longsys's tiny P900 supports it. Firmware complexity: an HMB drive must still work correctly even if the host *doesn't* grant HMB.

> **Modern note (post-book):** HMB is no longer exotic — it's now *standard* in mainstream consumer NVMe SSDs. The entire budget/mid-range NVMe market is essentially DRAM-less-with-HMB, precisely the design path this section forecast.

### 4.2.4 Flushing the map table (p. 15)

The table must be written to flash before power-off, and reloaded on power-up. But to survive *unexpected* power loss, firmware doesn't only flush at shutdown — it periodically writes the table to flash during operation, so a crash loses only a small recent slice (fast to rebuild). Triggers: enough new mappings accumulated, enough user data written, enough blocks filled, etc. Strategies: **full update** (write the whole table — simpler firmware, but more write traffic → higher latency and write amplification) vs **incremental update** (write only the changed/"dirty" mappings — less traffic, but firmware must track what's dirty). *(This directly foreshadows the "checkpoint/snapshot" mechanism in 4.6.)*

---

## 4.3 Garbage collection — pp. 16–43 ⭐⭐ *the conceptual heart of the book*

This is the single most important section. It introduces **GC** and the two concepts welded to it: **Write Amplification (WA)** and **Over-Provisioning (OP)**.

### 4.3.1 GC principle, via a toy SSD (p. 16–26, Figs 4-14 to 4-22)

The book builds a tiny fictional SSD to make this concrete — follow it, because the intuition transfers exactly to real drives:
- 4 channels (CH0–CH3), each with 1 die (dies on different channels operate in parallel).
- Each die has 6 blocks (Block 0–5); each block has 9 small squares (each square = one logical page).
- Total 24 blocks. **20 blocks = user capacity** (what the host sees); **4 blocks = OP** (the reserve beyond user capacity).

The walk-through:
1. **Sequential writes stripe across the 4 dies** *(p. 18, Fig 4-15)* — data goes to different channels/dies in parallel to maximize write speed. Keep writing until the *user* space is full *(p. 19, Fig 4-16)* — but the flash isn't full yet, because OP exists.
2. **Overwrite logical pages 1–4** *(p. 19–20, Figs 4-17/4-18)* — since flash can't overwrite in place, the new copies go to fresh (OP) space, and the *old* copies become **garbage** (dark squares). Keep going until **all** flash is full of a mix of valid and garbage data.
3. Now the host wants to write more, but there's no free space. **This is when GC must run.**

**GC itself (p. 21–23, Figs 4-19/4-20):** pick a block with garbage, **read out its still-valid data, rewrite that valid data to a fresh block, then erase the original block** — yielding a free block. In Fig 4-19, valid data A/B/C (from Block x) and D/E/F/G (from Block y) are consolidated into a fresh Block z, so x and y can be erased.

**Sequential vs random — why "SSDs get slower as they fill" (p. 23–26, Figs 4-21/4-22):**
- With **sequential** writes, garbage clusters together (whole blocks go invalid at once), so GC is cheap — sometimes just an erase, no data movement. Even a full sequential drive performs well.
- With **random** writes, garbage scatters across all blocks. GC must pick the **most-garbage blocks** (fewest valid pages → least data to move → fastest to free) — and this is inherently slower.
- The folk wisdom "SSDs slow down with use" is real science: early on there's free space so **no GC runs** (fast); once full, **every write triggers GC** (slower). Performance depends on your write pattern.

### 4.3.2 Write Amplification (p. 27–30, Figs 4-23 to 4-25) ⭐ *know this cold*

Because GC does extra internal writes, the SSD writes **more** to flash than the host sent. That ratio is **Write Amplification (WA)**:

> **WA = (data written to flash) ÷ (data written by the host)**

- **Empty drive (no GC): WA ≈ 1.** (Before SandForce, 1 was the floor.)
- **SandForce broke below 1** using real-time compression: 8 KB compressed to 4 KB before writing → WA as low as 0.5 (absent GC).
- **After GC kicks in, WA > 1.** The book's worked example *(p. 27–28, Figs 4-23/4-24)*: a reclaimed block set has 36 squares, of which **12 are valid** and must be rewritten. After GC, you can write **24** new user squares. But to write those 24, the SSD actually wrote 12 (moved valid data) + 24 (new) = **36**. So **WA = 36 ÷ 24 = 1.5**.

**Why WA matters:** higher WA means (a) more flash wear → shorter lifespan, and (b) more back-end bandwidth consumed → worse performance. **A core design goal is to keep WA low.** Levers: compression (controller-dependent), sequential writes (workload-dependent, "can't be counted on"), and **more OP** (controllable).

**Why more OP lowers WA (p. 28–29) — follow the arithmetic, it's the key insight.** Define **OP ratio = (flash space − user space) ÷ user space.** Using a 180-square user capacity:
- **OP = 36 squares** → flash = 216 squares, OP ratio = 36/180 = **20%**. Spread 180 valid squares over 216: each square averages 180/216 = 0.83 valid → a 9-square block holds ~7.5 valid + 1.5 garbage. To write 1.5 new squares you write 9 (7.5 moved + 1.5 new) → **WA = 9/1.5 = 6.**
- **OP = 72 squares** (sacrifice user space to 144) → flash still 216, OP ratio = **50%**. Now each square averages 144/216 = 0.67 valid → a block holds ~6 valid + 3 garbage. To write 3 new squares you write 9 (6 + 3) → **WA = 9/3 = 3.**

So **bigger OP → lower WA** (more garbage per block → less valid data to move per reclaim) → *and* better full-drive write performance. *(These are worst-case numbers assuming garbage is spread evenly; real GC picks the most-garbage blocks, so real WA is lower than the formula.)* The OP-vs-WA-vs-endurance relationship is in *(p. 29, Fig 4-25)*.

**Summary (p. 30):** WA smaller = better (less wear, more lifetime writes); OP larger = better (lower WA, better write performance). **Factors that raise WA:** low OP, random write patterns, poor GC block-selection, wear leveling (data movement), read-disturb/retention handling (data movement), no compression, and **no Trim**.

### 4.3.3 GC implementation — three steps (p. 30–42, Figs 4-26 to 4-33)

**Step 1: pick the source block.** The common **Greedy algorithm** picks the block with the **least valid data** (least to move → lowest WA). To find it instantly among many blocks, firmware **maintains a valid-data count per block**: writing a page to a new block increments that block's count by 1, and decrements the *old* block's count (since that page's old copy is now invalid) *(p. 31–34, Tables 4-3 to 4-6)*. A refinement folds **wear leveling** into GC by also weighting each block's **erase count** — you'd like to pick both the least-valid *and* the least-worn block, but those rarely coincide, so a weight factor balances them. Upside: no separate wear-leveling pass needed. Downside: you may pick a block with more valid data → higher WA, slower GC.

**Step 2: find and read the valid data.** Three approaches, trading firmware complexity against GC speed:
- **Per-block valid-page Bitmap (p. 35–39, Figs 4-29/4-30, Tables 4-7 to 4-9):** a bitmap marks which pages are valid, so GC reads *only* valid data. Fast GC, but the bitmap costs RAM — fine for DRAM SSDs, painful for DRAM-less ones (real blocks have thousands of pages, so bitmaps get large and must themselves be swapped in/out of SRAM).
- **Read everything + check via metadata (p. 40–42, Fig 4-33):** each user-data write is packed with **metadata** (its logical address, length, timestamp). GC reads all data, extracts each LBA, looks it up in the map table — if the map points back to this location, it's valid; otherwise garbage. Simple firmware (no extra structures), but slow (reads even invalid data, and DRAM-less drives must fetch mappings from flash — "a disaster").
- **P2L table (middle ground) (p. 42):** besides the L2P map, keep a **P2L (Physical-to-Logical)** table recording which LBAs a block holds, stored with the block. On reclaim, load the P2L, check each LBA against the map to decide validity. Avoids reading all data, but still needs map lookups. Performance and cost sit between the other two.

**Step 3: rewrite the valid data** to a fresh block.

### 4.3.4 When GC runs (p. 42–43, Fig 4-34)

- **Foreground GC** — reactive: when free blocks drop below a threshold *during* host writes, GC runs to make room (this is what hurts user-write latency).
- **Background GC** — proactive: the SSD does GC when **idle**, so free blocks are ready when writes arrive (better write performance). But some SSDs skip background GC to save power (go to sleep instead).
- **Host-managed GC (HMS)** — a preview of what's coming: OCZ's Saber 1000 HMS (2015) let the *host* control when SSD background tasks (like GC) run, so an enterprise admin could schedule GC during idle windows for **stable, predictable latency**. *(Hold this thought — 4.10 and my modern supplement are the full realization of "let the host manage the flash.")*

---

## 4.4 Trim — pp. 43–46, Figs 4-35 to 4-37 ⭐

**The problem:** when you delete a file, the OS just cuts *your* access to those addresses — but inside the SSD, the logical→physical mappings still exist and the data is still marked **valid**. Without Trim, the SSD has no idea the data is dead, so **GC keeps dutifully moving that dead data around** — hurting both GC performance and lifespan (higher WA).

**The fix:** **Trim** is an ATA command (Data Set Management) built for SSDs. When you delete a file, the OS (Windows 7+) sends Trim telling the SSD which data is now invalid. GC can then simply discard it instead of relocating it — better performance *and* longer life. (The equivalent commands: **SCSI = UNMAP, NVMe = Deallocate** — same function.)

**The three FTL tables Trim touches (p. 45, Fig 4-36):** the **FTL map table** (LBA → physical page), the **VPBM — Valid Page Bit Map** (which pages in a block are valid), and the **VPC — Valid Page Count** (valid-page count per block, used by GC to sort candidates). On Trim, firmware updates these to mark the data invalid *(p. 46, Fig 4-37)*. Important: **Trim does not itself trigger GC** — it just marks data dead so future GC skips it.

---

## 4.5 Wear leveling — pp. 46–51, Figs 4-38 to 4-42 ⭐

**Goal:** keep every block's erase (wear) count roughly equal, so no block dies prematurely. Without it, a few hot blocks burn through their P/E budget and become bad blocks; as more accumulate, the SSD dies before its warranty. Spreading writes across *all* blocks maximizes total data written. (And this matters more every generation: SLC ~100K cycles → MLC ~few K → TLC ~1–2K or even hundreds *(p. 47, Fig 4-38)*.)

**Four concepts first (p. 47):**
- **Cold data** — rarely updated (OS files, read-only files, movies).
- **Hot data** — frequently updated (generates lots of garbage as old copies invalidate).
- **Old block** — high erase count. **Young block** — low erase count. (The SSD knows which is which from each block's **EC — Erase Count**.)

**Two algorithms (p. 47–48):**
- **Dynamic WL** — put **hot data on young blocks**: when grabbing a fresh block to write, pick a low-erase-count one. Straightforward — it stops you from always hammering the same worn blocks.
- **Static WL** — put **cold data on old blocks.** This is the subtle one, and why it's needed: cold data, once written, just *sits there*, so its blocks' erase counts never rise, while every other block keeps getting cycled. That creates imbalance. Static WL deliberately **moves cold data onto worn (old) blocks** — letting those veteran blocks "rest" while freeing young blocks to absorb new writes. It's implemented like GC, except the source block is chosen because it holds **cold data** (not because it has the least valid data).

**The cold/hot mixing problem (p. 48–50, Figs 4-39 to 4-42).** Static WL can end up writing cold data into the same block as fresh user data or GC data. That's bad: cold data is usually *valid* data, so when that block is later GC'd, the cold data gets **relocated again and again** — extra writes → higher WA. **Solution:** during static WL, write cold data to **dedicated** blocks (not shared with user/GC writes), so those blocks won't be picked as GC sources and the cold data stops migrating. Whether to bother depends on your priorities: mixing is simpler but raises WA; separating cold/hot is better if WA-sensitive.

---

## 4.6 Power-loss recovery — pp. 51–56, Figs 4-43 to 4-46 ⭐⭐ *know this cold*

Two kinds of power loss, and the SSD must recover from both.

**Normal (graceful) power-off (p. 51).** The host warns the SSD first (e.g., SATA *Idle Immediately*). The SSD then: flushes buffered user data to flash, flushes the map table to flash, writes block info (which block is being written, where, which blocks are used/invalid…), and writes other state. Only then does the host cut power. No data loss; on next boot the SSD reloads that state and resumes.

**Abnormal (unexpected) power loss (p. 51–55) — the hard case.** Power is cut with no warning (or before the SSD finished the above). Two dangers:
1. **Buffered-but-unwritten user data is lost.** Recall non-FUA writes: the SSD returns "success" once data is in its RAM buffer, *before* it reaches flash. On sudden power loss, that RAM data is gone — and the host thinks it was saved. *(The book's parable: I had ¥10, deposited ¥1,000,000, but power died before the bank wrote it to the database — next day the ATM still shows ¥10. I fainted.)*
2. **Lower-Page corruption (from Chapter 3):** losing power mid-Upper-Page write can destroy the **already-committed Lower Page** — so even previously-safe data can vanish.

**Why an SSD — made of non-volatile flash — fears power loss at all (p. 52):** because besides flash, it has **volatile RAM/SRAM/DRAM** holding buffered data and the **map table**. Power loss wipes RAM. Mitigations: enterprise SSDs use a **capacitor** — on detecting power loss, it discharges long enough to flush RAM to flash (though a capacitor can't *guarantee* everything flushes, so you still need recovery firmware). A forward-looking option: replace volatile RAM with fast **non-volatile** memory like **3D XPoint** (flash-like persistence + RAM-like speed), making the whole SSD non-volatile.

**Rebuilding the map table (p. 53–55, Figs 4-43/4-44) — the core of recovery.** User data is lost for good, but the **map table can be rebuilt**, because every user-data write was packed with **metadata** (its logical address + timestamp). So reading physical location Pa x yields both the data *and* its logical address La x — giving the mapping La x → Pa x. **Full-scan the entire flash and you recover every mapping.** Two wrinkles:
- **New vs old data:** the same LBA may have been written many times (many stale copies, one current). The **timestamp** resolves it — largest timestamp = most recent. During the scan, La 2 → Pa 2 gets *overwritten* by La 2 → Pa 8 once the newer timestamp is seen.
- **Speed:** a full scan takes time proportional to capacity — **minutes to tens of minutes** on a TB-class drive. Unacceptable.

**The fix — Checkpoints / Snapshots (p. 55–56, Figs 4-45/4-46).** Periodically write RAM state (map table + cached data) *and* SSD status (erase counts, read counts, block info) to flash — like the graceful-shutdown flush, done repeatedly. If power dies at point X after snapshot C, on reboot the SSD loads snapshot C and only needs to **rescan the small region between C and X** — recovering in a fraction of the full-scan time. *(This is the same idea as 4.2.4's incremental map flush, applied to crash recovery.)*

---

## 4.7 Bad-block management — pp. 56–61, Figs 4-47 to 4-51

**Sources (p. 56):** **factory bad blocks** (present from manufacture) and **grown bad blocks** (good blocks that fail later, mainly from erase/write wear).

**Identifying them (p. 57–59, Figs 4-47/4-48):**
- **Factory bad blocks** are marked by the vendor. Fresh flash is erased to all-0xFF; the vendor writes a **non-0xFF marker** at specific spots on bad blocks (e.g., Toshiba marks the first byte of the data area and spare area of the first and last page). On first use, you scan all blocks per the datasheet and build a **bad-block table**. Some vendors instead store bad-block info in a special persistent region (e.g., Micron's **OTP** area), so you just read that region instead of scanning.
- **Grown bad blocks** announce themselves via operation failures: **UECC** (ECC-uncorrectable read), erase failure, or program failure. Add them to the table and stop using them.

**Two management strategies (p. 59–61, Figs 4-49 to 4-51):**
- **Skip strategy** — when writing hits a bad block, skip it and write the next block. Simple, but **unstable performance**: with 4 dies, skipping can drop parallelism to anywhere from 1 to 4 dies.
- **Replace strategy** — each die reserves spare good blocks; a bad block is replaced by a spare on the *same* die (via a **Remap Table**: bad → replacement). Parallelism stays at 4 dies (stable performance), but it has a **bucket effect** — if one die is low-quality, the whole SSD's usable blocks are limited by that worst die.

---

## 4.8 SLC Cache — pp. 61–64, Table 4-10

**The idea:** SLC is faster and more durable than MLC/TLC. "SLC cache" doesn't mean adding separate SLC chips — it means **configuring some MLC/TLC blocks to run in SLC mode** (storing 1 bit/cell), which most MLC/TLC supports. Those blocks become fast, durable cache for **burst performance**.

**Why use it (p. 62–63):** (1) speed — writes to SLC are much faster; (2) **avoids Lower-Page corruption** — SLC mode has no Upper Page to corrupt the Lower Page; (3) sidesteps a flash defect where a partially-written MLC/TLC block can give ECC errors on read; (4) more endurance.

**Who uses it (p. 63):** **consumer SSDs and mobile storage** (they want burst speed and usually lack a capacitor, so SLC mode protects Lower-Page data). **Enterprise SSDs generally don't** — they want *steady* performance (not a burst that then collapses when the SLC cache fills and writes fall back to TLC), and they have capacitors, so they don't need SLC mode for data protection.

**Write policies (p. 63):**
- **Forced SLC** — all writes go to SLC first, then GC migrates them to MLC/TLC. Protects Lower-Page data, but slower sustained performance (must both migrate out *and* write in). *(Subtlety: migration to MLC/TLC still risks Lower-Page corruption — but if you don't erase the SLC source until the MLC/TLC target block is full, you can still recover from the SLC copy.)*
- **Non-forced SLC** — write to SLC if available, else straight to MLC/TLC. Better late-stage performance (when SLC is exhausted, skip it), but doesn't protect Lower-Page data.

**Sourcing the SLC blocks (p. 64):** **static** (dedicated blocks), **dynamic** (any MLC/TLC block can be borrowed as SLC cache), or **hybrid**.

> **Modern note:** SLC cache is now universal in consumer TLC and QLC drives, and the "burst then collapse" behavior the book warns about is exactly why reviewers test *sustained* write speed — a QLC drive can write at GB/s into its SLC cache, then fall to ~100 MB/s once it's full. As drives moved to TLC/QLC, dynamic SLC caches (which can be many times larger than a static cache when the drive is near-empty) became the norm.

---

## 4.9 RD & DR — Read Disturb and Data Retention handling — pp. 64–66

Two failure modes from Chapter 3, revisited from the FTL's perspective — both cause data loss, but by opposite mechanisms and needing distinct handling.

**RD — Read Disturb (p. 64–65).** Reading a page puts higher voltage on the block's *other* wordlines to keep them conducting — a slight "program" that, over many reads, injects electrons and flips bits **1→0**; past ECC's power, data is lost. It accumulates slowly, so the fix is preventive: **track each block's read count**; when it nears a threshold, **refresh** the block (move its data elsewhere, or rewrite in place) before bits flip. After the rewrite, the read count resets. Read counts are saved to flash on power-off. Refinements:
- **Avoid over-refreshing:** hitting the read threshold doesn't guarantee many flipped bits yet — so some FTLs first *check* the actual flip count, and if it's still low, set a *higher* threshold and defer the refresh (refreshing costs time and P/E cycles).
- **Dynamic thresholds:** old FTLs used one fixed threshold for the drive's whole life ("crude but simple"). But RD immunity **drops with age** (higher PE → more vulnerable), so the correct approach is a **PE-dependent threshold** — the more worn the block, the *lower* the read threshold.
- **Non-blocking refresh:** refresh should run *interleaved* with normal I/O (non-blocking), not by freezing everything (blocking) — blocking causes long command latency, worse as block sizes grow. Modern FTLs use non-blocking refresh.

**DR — Data Retention (p. 65–66).** "No wall is truly windproof; no insulator truly traps every electron." Over time electrons leak out of the floating gate, flipping bits **0→1** (note: *opposite* direction to RD's 1→0); past ECC's power, data is lost. **This is why a drive left unpowered for a long time may fail to boot or boot slowly** (the FTL is fixing DR-induced errors). The fix: on power-up and during idle operation, the FTL **periodically scans** flash and, when flip counts exceed a threshold, **refreshes** the data — same as RD handling. The catch: **if the SSD is never powered on, the FTL never gets to run**, and the electrons leak away unopposed. *(This is the concrete reason SSDs are poor for cold, offline archival — a fact worth remembering.)*

---

## 4.10 Host-Based FTL — pp. 66–72, Figs 4-52 to 4-57 ⭐ *the bridge to the modern era*

The book closes the chapter by revisiting the Host-Based vs Device-Based split — and this section is the seed of everything in my "Modern developments" supplement below.

**Device-Based recap and its limits (p. 66–68, Fig 4-52).** A Device-Based system has three logical layers: **host driver** (read/write API for apps; talks NVMe etc. to the SSD), **onboard controller** (executes host commands, runs the whole FTL — GC, wear leveling, etc., and drives flash timing), and the **flash array**. This is a beautifully standardized division of labor — CPU makers provide PCIe/SATA, board makers provide slots, OS makers provide standard drivers, SSD makers just build to spec. **Perfect for vendors — but not always for users.** The SSD revolution matters *because* flash is unlike an HDD: it's many chips that read/write in parallel, and some users want to manage that parallelism themselves for their specific workload. Device-Based FTL's drawbacks:
- Generic FTL — no per-application customization.
- Controller chips are complex, hard, and expensive to design.
- Flash changes yearly with new quirks, but re-spinning a controller ASIC is costly.
- Enterprise needs high performance/capacity that a generic controller caps.
- Diverse enterprise needs require special controller features a generic chip can't offer.

**Host-Based FTL architecture (p. 68–69, Fig 4-53).** Expose the flash's raw read/write interface directly to the host driver, which then manages the flash internals itself. The controller becomes simple — often an **FPGA** doing just **ECC and flash-timing/protocol conversion**. The famous example is **Fusion-IO**; large internet companies (Google, Microsoft, Baidu) also build their own to match their storage architectures.

**Case study — Baidu's Software-Defined Flash (SDF) (p. 69–72, Figs 4-54 to 4-57).** Presented at ASPLOS'14. Hyperscalers (Baidu, Tencent, Alibaba, Google, Facebook) each run ~100K+ servers, so they can't buy expensive vendor gear — they build cheap custom hardware, including custom SSDs. SDF's radical simplifications:
1. **No garbage collection.** SDF's users write in **integer multiples of the erase-block size** (e.g., 8 MB), so a block is either all-live or all-garbage — just erase before writing. Benefits: no internal GC (higher bandwidth), **no OP needed (frees the ~20% reserve)**, and **no internal data movement → no write amplification → longer life.**
2. **No internal RAID.** Internet data already has 3 replicas, so intra-SSD redundancy is unnecessary.
3. **Minimal FPGA controller** — only ECC, bad-block management, address translation, and *dynamic* wear leveling (a Virtex-5 does PCIe/DMA, a Spartan does flash control).
4. **Every channel exposed to the user** — the app picks which channel to write.
5. **Radically simplified software stack** *(Fig 4-57)*: skip the filesystem, block layer, I/O scheduler, and SATA protocol; the app sends synchronous writes straight to the PCIe driver via IOCTL. **Software latency drops from 12 μs to 2–4 μs** (just the PCIe interrupt). SDF stores Baidu's own ~8 MB log-structured-filesystem blocks.

The takeaway the book leaves you with: by tailoring the SSD to one known workload and keeping *only* the essential functions, you save enormous resources and slash latency. **This is exactly the philosophy that the industry then standardized — see below.**

---

## 4.11 Wrap-up (p. 72)

The chapter ends by pointing readers to SSDFans for more. So let me use that opening to bring the book's ideas up to date.

---

## 📌 Modern developments (post-2018 supplement)

*The book ends its FTL discussion with Baidu's research prototype. In the years since, that "let the host manage the flash" idea became two ratified NVMe standards that are now shipping products. This section connects the book's concepts to today; it's drawn from current industry and standards sources, attributed inline. This material is not in your book.*

**The lineage.** The book's host-based examples sit on one branch of a family tree that has since grown up:

**Baidu SDF / Fusion-IO (≈2014, the book) → Open-Channel SSD → ZNS (NVMe 2.0, ~2020–2021) → FDP (NVMe TP4146, ratified Dec 2022)**

Each step keeps the book's core insight — *the host knows things about the data that the blind, general-purpose FTL can't* — while making it progressively easier to adopt.

### Why this happened: the FTL's costs at hyperscale

Everything in this chapter (mapping, GC, OP, wear leveling) is the FTL doing its job well — but at data-center scale those same mechanisms became a liability. Industry sources put concrete numbers on the three costs this chapter taught you:

- **Write amplification.** Enterprise workloads commonly run **WA of about 2–5×**, per Western Digital and academic measurements — meaning 2–5× the flash wear and bandwidth the host actually asked for. Lab tests of random-write workloads have measured GC-induced write amplification as high as ~15× with minimal over-provisioning. Since NAND has a fixed P/E budget, hyperscalers running thousands of drives care enormously about pushing WA toward 1.
- **Over-provisioning.** Conventional SSDs reserve roughly **7–28% of capacity** as OP for GC — capacity the customer pays for but can't use.
- **DRAM.** The book's ~1 GB-DRAM-per-1 TB rule (its 1/1000 figure) is confirmed by NVM Express as an industry norm — a real cost in dollars and power, and it scales linearly with capacity.

The realization, in Western Digital's framing, was that the local optimizations the FTL evolved had become *detrimental* at scale. So a group including Alibaba, Microsoft, NetApp, and Western Digital pushed the NVMe working group toward host-directed data placement.

### ZNS — Zoned Namespaces (NVMe 2.0)

ZNS is the direct, standardized descendant of Open-Channel SSD (which was itself the descendant of Baidu's SDF). The drive is divided into **zones**; **writes must be sequential within a zone, and a zone must be reset (erased) before rewriting** — which, as the arXiv survey of ZNS puts it, pushes data-placement and garbage-collection decisions **out of the device and up to the host.** Because the host writes each zone sequentially and resets whole zones, the drive's *internal* GC nearly vanishes. The payoffs map exactly onto this chapter's cost list:

- **Write amplification** inside the SSD drops to **near zero** (the host's sequential-write discipline means the drive rarely has to relocate anything), per AnandTech's ZNS explainer.
- **Over-provisioning** shrinks dramatically (little internal GC → little reserve needed).
- **DRAM** collapses: instead of a 4 KB-granularity map needing ~1 GB/TB, the drive tracks whole **zones of hundreds of MB**, so even a tens-of-TB drive can do it in on-controller **SRAM** — no DRAM required. (AnandTech notes ZNS doesn't *fully* eliminate DRAM, since per-zone metadata is larger per unit, but the reduction is drastic.)
- **QLC becomes viable** for more workloads: with the SSD causing almost no write amplification, the endurance hit of QLC-vs-TLC is offset.

**The catch — and why ZNS adoption stayed limited.** ZNS's append-only, sequential-write model imposes real **upfront software-engineering cost**: applications that aren't naturally log-structured must be rewritten to stage random writes into sequential ones, and the host must implement its own garbage collection. A ZNS-written drive also can't be read by a non-ZNS-aware host. This friction (the same friction that limited Open-Channel before it) kept ZNS from going mainstream despite its impressive numbers — a lesson the next standard took to heart.

### FDP — Flexible Data Placement (NVMe TP4146, Dec 2022)

FDP is the industry's answer to "ZNS is great but too disruptive." It was **driven by Google and Meta** (merging Google's *SmartFTL* and Meta's *Direct Placement Mode* proposals), with Samsung, and fast-tracked to ratification. The design goal, per Samsung's documentation, was to capture most of the write-amplification benefit **without** re-engineering the application:

- **Backward compatible.** The host addresses the drive with ordinary LBAs plus an *optional placement hint*; an FDP drive **keeps** device-side logical-to-physical mapping, garbage collection, and bad-block management, just like a conventional SSD. An app can run **unchanged**. Critically, an FDP-written drive can be read by a host that knows nothing about FDP — unlike ZNS.
- **The mechanism.** The host groups related data into a **Reclaim Unit (RU)** — a set of NAND blocks (often a superblock) that will be filled and reclaimed together — via a **Reclaim Unit Handle (RUH)**. This borrows directly from the older *multi-stream SSD* idea. The point is to stop the "I/O blender": without FDP, data from many applications is interleaved across all blocks (so deleting one app's data leaves garbage scattered everywhere, forcing GC); with FDP, each app's data lands in its own reclaim unit, so it tends to become invalid *together*.
- **The payoff, in hyperscaler terms.** Samsung's TP4146 lead author frames FDP as potentially eliminating ~28% OP, enabling ~2× drive size at the same application write density, roughly doubling drive lifetime, and doubling application write rate — with **WAF ≈ 1 as the new normal**. Micron's Aerospike and CacheLib tests show real WA reductions from segregating an application's data streams. Ecosystem support (Linux kernel I/O via passthrough since 6.2, SPDK, xNVMe, CacheLib) arrived quickly *because* FDP is easy to bolt on.

### ZNS vs FDP — how to think about the trade

The clean mental model from the industry sources:

- **ZNS** gives the strictest control and the best theoretical WAF (≈1 guaranteed) but demands a **sequential-write, log-structured host** and host-side GC — best for systems *designed from scratch* around sequential writes.
- **FDP** gives *most* of the benefit with *minimal* engineering because it's backward compatible and leaves GC/mapping on the device — best for the vast majority of existing software stacks that just want lower WAF without a rewrite.

Analysts differ on whether both survive or one wins; momentum in 2023–2024 clearly shifted toward FDP for general adoption precisely because of the low engineering cost, while ZNS remains attractive for purpose-built sequential systems. Either way, the **through-line from this chapter is intact**: the fundamental lever is still moving data-placement knowledge from the blind FTL to the informed host, to drive write amplification toward 1 — exactly the problem section 4.3 taught you to care about.

### One more modern note: QLC and beyond

The book treats TLC as the frontier and mentions QLC only in passing. Today **QLC (4 bits/cell) is mainstream** in consumer and read-intensive enterprise drives, and **PLC (5 bits/cell)** has been researched. Everything this chapter says gets *harder* with more bits per cell — shorter endurance, slower writes, tighter voltage margins, worse retention — which is precisely *why* the write-amplification-reduction techniques above (bigger SLC caches, ZNS/FDP, stronger LDPC from Chapter 3) matter more with each generation. The FTL's job doesn't get easier; the medium gets harder and the software has to compensate.

---

## Key vocabulary — for decoding the original figures

| 中文 | English |
|---|---|
| 閃存轉換層 | Flash Translation Layer (FTL) |
| 映射 / 映射表 | mapping / map table |
| 邏輯地址 / 物理地址 | logical / physical address |
| 邏輯頁 / 物理頁 | logical page / physical page |
| 塊映射 / 頁映射 / 混合映射 | block / page / hybrid mapping |
| 二級映射 | two-level mapping (L2P) |
| 垃圾回收 | garbage collection (GC) |
| 寫放大 | write amplification (WA) |
| 預留空間 | over-provisioning (OP) |
| 有效數據 / 無效(垃圾)數據 | valid data / invalid (garbage) data |
| 源閃存塊 / 目標閃存塊 | source block / destination block |
| 前臺/後臺垃圾回收 | foreground / background GC |
| 磨損平衡 | wear leveling |
| 動態/靜態磨損平衡 | dynamic / static wear leveling |
| 冷數據 / 熱數據 | cold data / hot data |
| 擦除次數 | erase count (EC) |
| 掉電恢復 | power-loss recovery |
| 正常/異常掉電 | normal / abnormal power loss |
| 元數據 | metadata |
| 時間戳 | timestamp |
| 快照 / 檢查點 | snapshot / checkpoint |
| 壞塊 | bad block |
| 出廠/增長壞塊 | factory / grown bad block |
| 略過 / 替換策略 | skip / replace strategy |
| 重映射表 | remap table |
| 突發性能 | burst performance |
| 主機端 / 設備端 | host-based / device-based |
| 軟件定義閃存 | software-defined flash (SDF) |

---

## Check yourself

1. Name the two physical facts about flash that force the FTL to exist, and the FTL job each one directly creates.
2. Why do SSDs use *page* mapping instead of *block* mapping, and what's the concrete downside (the reason USB drives use block mapping)?
3. State the map-table size rule of thumb, and compute the table size for a 1 TB SSD with 4 KB pages and 4-byte entries.
4. Define write amplification. A GC pass reclaims a block set with 20 valid squares, after which 40 new user squares can be written. What's the WA?
5. Explain in one sentence *why* increasing OP lowers write amplification.
6. Without Trim, what does the SSD wrongly keep doing to deleted data, and what two things does that hurt?
7. Static wear leveling deliberately moves *cold* data onto *worn* blocks. Why is that necessary — what problem does cold data create if left alone?
8. After an unexpected power loss, user data in the RAM buffer is gone forever, but the map table can be rebuilt. What packed-in information makes rebuilding possible, and what specifically resolves multiple stale copies of the same LBA?
9. What is a checkpoint/snapshot, and what problem with map-table rebuilding does it solve?
10. Read Disturb flips bits one way; Data Retention flips them the other way. State both directions, and explain why a drive left unpowered for a year may fail to boot.
11. Trace the lineage from Baidu's SDF to today's FDP. What single problem are all of these attacking, and what's the fundamental thing they all move from the device to the host?
12. ZNS achieves near-zero internal write amplification but saw limited adoption; FDP achieves *most* of the benefit and adopted faster. What's the key architectural difference that explains the adoption gap?

---

*Next up: Chapter 5 — PCIe. We leave flash behind and move to the high-speed interface: topology, layered protocol, TLPs, and how data actually travels between host and SSD over PCI Express.*
