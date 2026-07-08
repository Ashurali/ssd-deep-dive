---
title: "Supp C — Flash File Systems"
tags:
  - filesystems
  - f2fs
  - ext4
  - zns
  - garbage-collection
source_anchor: "supplement (no book chapter)"
---

# SSD Deep Dive — Supplement C: Flash File Systems (EXT4 & F2FS)
## English Study Companion (2nd-edition topic, reconstructed from standard references)

**Why this exists:** This is the **2nd edition's Chapter 12**, not in your PDFs. It's about the layer *above* the SSD — the **operating-system filesystem** that decides how files map onto the block device the SSD presents. I've reconstructed it from the Linux kernel documentation, the F2FS research literature, and current sources, in your usual format.

**Why it's worth your time — the payoff up front:** Everything you learned about the FTL in Chapter 4, **F2FS re-implements at the filesystem layer.** F2FS's "cleaning" *is* garbage collection. Its multi-head logging *is* hot/cold wear-leveling separation. Its Node Address Table *is* a mapping-table indirection. Its checkpoint *is* the power-loss snapshot. So this chapter is largely **Chapter 4 seen from the host's side of the interface** — which makes it both an easy read (you know the concepts) and a genuinely illuminating one (you'll see the *same* problem solved twice, at two layers, and why that double-solving is itself a problem that ZNS fixes). For a NAND-company internship, understanding how the host filesystem cooperates (or fights) with your FTL is directly useful.

**The framing question:** A filesystem organizes files on a storage device. But classic filesystems (EXT4 and its ancestors) were designed for **hard drives** — they assume in-place overwrite is cheap and optimize for *seek locality* (keeping related data physically close so the disk head travels less). On flash, both assumptions are wrong: there's no head to seek, and in-place overwrite is impossible (Ch3). This mismatch causes excess **write amplification** and makes the filesystem fight the FTL. Two responses emerged:
- **(a) Retrofit an HDD filesystem** — take EXT4 and bolt on flash-awareness (Trim, alignment). Works, still dominant, but suboptimal.
- **(b) Design a flash-native filesystem** — **F2FS**, built from scratch around flash's characteristics. This is the interesting one.

**How to use this guide:** Follows the 2nd edition's structure (12.1 EXT4, 12.2 F2FS). No page refs (not from your PDF); instead I map each concept to its Chapter-4 analog. Glossary and self-quiz at the end. If short on time, **12.2 (F2FS) and the two-layer / log-on-log discussion** are the core.

**A taxonomy to orient you first** — there are *three* kinds of flash-related filesystems, and it matters which layer they sit at:

| Category | Examples | Manages raw NAND? | Assumes an FTL below? |
|---|---|---|---|
| HDD filesystem (retrofitted) | EXT4, XFS, NTFS | No | Yes — treats SSD as a black-box disk |
| Flash-native, FTL-based | **F2FS** | No | **Yes** — cooperates with the FTL |
| Raw-flash filesystem | JFFS2, UBIFS, YAFFS | **Yes** — does its own WL/ECC | No — talks to bare NAND chips |

This chapter is about the first two (block-device filesystems, which sit on top of an SSD/UFS/eMMC that has its own controller). The third category — raw-flash filesystems that replace the FTL entirely — I cover briefly at the end, since it's relevant to deeply-embedded systems without a controller.

---

## 12.1 EXT4 — the HDD-era filesystem ⭐

### 12.1.1 Development history (p. their 12.1.1)

The **ext** lineage is the historical default of Linux:
- **ext2** (1993) — the classic Unix filesystem structure (inodes + block bitmaps). No journaling.
- **ext3** (2001) — added **journaling** for crash consistency (below), otherwise similar to ext2.
- **ext4** (2008) — the current version: added **extents**, larger volume/file limits (up to 1 EiB / 16 TiB), delayed allocation, and many performance features. It remains the default or fallback filesystem on most Linux systems and many Android devices' *boot/recovery* partitions.

The key thing to hold: EXT4 was engineered in and for the **rotational-disk era.** Its design goals were minimizing seek distance and supporting cheap in-place updates — exactly the properties flash *doesn't* have.

### 12.1.2 On-disk (physical) structure (p. their 12.1.2)

EXT4 divides the volume into **block groups** (fixed-size chunks of blocks). Each block group contains:
```
┌──────────┬───────────┬────────┬────────┬────────────┬──────────────┐
│ Super    │ Group     │ Block  │ Inode  │ Inode      │ Data         │
│ block    │ Descriptors│ Bitmap │ Bitmap │ Table      │ Blocks       │
│ (copy)   │           │        │        │            │              │
└──────────┴───────────┴────────┴────────┴────────────┴──────────────┘
```
- **Superblock** — filesystem-wide metadata (block size, total blocks/inodes, state). Replicated across groups for safety.
- **Group descriptors** — locations of the bitmaps and inode table for each group.
- **Block bitmap / Inode bitmap** — one bit per block/inode marking free vs used (this is how allocation is tracked).
- **Inode table** — the array of **inodes.** An **inode** is the fixed-size (typically 256-byte) metadata record for one file: its permissions, owner, timestamps, size, and — crucially — **pointers to its data blocks.**
- **Data blocks** — the actual file contents.

*(Modern EXT4 uses "flex block groups" to cluster the bitmaps and inode tables of several groups together, improving locality — an HDD optimization.)*

### 12.1.3 In-memory structure (p. their 12.1.3)

When mounted, EXT4 keeps active structures in RAM for speed: cached inodes, the **dentry cache** (directory-entry lookups: name → inode), buffered data pages (the page cache), and in-memory copies of the bitmaps and superblock. Writes are buffered and flushed later (which is why sudden power loss can lose recent writes — the same buffering hazard you saw for SSDs in Ch4 §4.6, now at the filesystem layer). The VFS (Virtual File System) layer sits above, giving applications a uniform API regardless of which filesystem is underneath.

### 12.1.4 Extents — range mapping (p. their 12.1.4) ⭐ *a nice parallel to Chapter 4 mapping*

Here's EXT4's most important improvement over ext2/3, and it echoes the mapping-granularity tradeoff from Chapter 4 §4.2.

**The old way (ext2/3): indirect block mapping.** An inode held a list of direct block pointers (one per data block) plus single/double/triple *indirect* pointers (pointers to blocks of pointers) for large files. This is **fine-grained** — one pointer per block — but for a large contiguous file it's wasteful: a 1 GB file needs ~256K pointers, and reading them means chasing indirect blocks. *(This is directly analogous to page mapping in the FTL: fine granularity, big tables.)*

**The new way (ext4): extents.** An **extent** describes a *contiguous range* of blocks with just three numbers: (logical start, physical start, length). One extent can cover up to 128 MB of contiguous file data. So a large contiguous file needs just a handful of extents instead of hundreds of thousands of pointers — stored in an **extent tree** (a B-tree). *(This is directly analogous to block/hybrid mapping: coarse granularity, tiny tables — efficient when data is contiguous.)*

The parallel to Chapter 4 is exact: **both the filesystem and the FTL face the same choice** — map at fine granularity (flexible, big metadata) or coarse contiguous granularity (compact, needs contiguity). EXT4 chose extents for the same reason SSDs sometimes use hybrid mapping: most files are large and contiguous, so coarse mapping wins.

### 12.1.5 Allocation strategy (p. their 12.1.5)

EXT4 works hard to keep files **contiguous** (an HDD instinct — contiguity means fewer seeks):
- **Delayed allocation ("allocate-on-flush")** — don't assign physical blocks when the app writes; wait until the buffered data is flushed, by which point you know the full size and can allocate one contiguous run. Reduces fragmentation.
- **Multiblock allocation** — allocate many blocks in a single request rather than one at a time.
- **Persistent preallocation** — an app can reserve a contiguous region in advance (e.g., for a download of known size).

Note the irony for flash: all this contiguity effort is optimizing for *physical* locality, but the SSD's FTL **scatters the data across flash anyway** (Ch4) — the filesystem's "contiguous" logical blocks land wherever the FTL puts them. So the effort is partly wasted on flash, though contiguous *logical* layout still helps (fewer extents, better Trim, larger sequential transfers).

### 12.1.6 Reliability — journaling (p. their 12.1.6) ⭐

EXT4's crash-consistency mechanism is a **journal** (managed by JBD2). Before modifying the filesystem, it first writes the intended changes to a dedicated journal area; if power is lost mid-update, on remount it **replays** the journal to reach a consistent state. Three modes:
- **journal** — both data and metadata go to the journal first (safest, slowest — everything written twice).
- **ordered** (the default) — only *metadata* is journaled, but data blocks are forced to disk *before* the metadata commits (so metadata never points at garbage). Good balance.
- **writeback** — only metadata journaled, no ordering guarantee on data (fastest, least safe).

Plus **metadata and journal checksums** to detect corruption. *(Conceptually, journaling is the filesystem's version of the power-loss-recovery machinery from Ch4 §4.6 — write intentions durably first, replay after a crash. But note: journaling means some data is written **twice**, which is a source of filesystem-level write amplification — a problem F2FS avoids by design.)*

### 12.1.7 Limitations on flash (p. their 12.1.7) ⭐ *why F2FS exists*

EXT4 works on SSDs, but it's a rotational-disk design forced onto flash, with real downsides:
1. **In-place overwrite model.** EXT4 updates files *in place* (rewrite the same logical block). But flash can't overwrite (Ch3), so every in-place update becomes an out-of-place write + garbage in the FTL — driving up **write amplification** and wear.
2. **Journaling doubles writes.** The double-write of journaling compounds the FTL's own write amplification.
3. **Seek-locality optimizations are pointless** on flash (no seek time) — effort spent for no benefit.
4. **No FTL awareness.** EXT4 doesn't know the erase-block size, the FTL's GC unit, or flash's hot/cold sensitivity, so its allocation can't align with or help the device. It treats the SSD as an opaque disk.
5. **Random-write heavy.** Metadata updates (bitmaps, inodes, journal) scatter small random writes across the volume — the worst pattern for flash (Ch4: random writes → scattered garbage → high WA).

These five points are precisely what a flash-native filesystem sets out to fix.

---

## 12.2 F2FS — the flash-native filesystem ⭐⭐ *Chapter 4, at the filesystem layer*

**F2FS (Flash-Friendly File System)** was created by **Jaegeuk Kim at Samsung** — the initial patch hit the Linux kernel mailing list in October 2012 and merged into **Linux 3.8 in December 2012**. Kim has since moved through Huawei, Motorola, and Google, and **remains the primary maintainer** to this day. It's now the **default userdata-partition filesystem on billions of Android devices** (Google Pixel, most Samsung Galaxy since the Note 10, Xiaomi, OPPO, OnePlus, Huawei, Motorola, ZTE).

**The one design decision that defines it — it's log-structured.** F2FS is a **log-structured file system (LFS)**: *all writes are sequential appends to the end of an active log. Data is never overwritten in place — it lands at a new address, and the old location is marked stale, awaiting garbage collection.*

**Stop and notice:** that is *exactly* how flash itself works (Ch3: no overwrite, write to new location, old copy becomes garbage) and exactly how the FTL manages it (Ch4: out-of-place writes + mapping + GC). **F2FS makes the filesystem behave like the flash underneath it** — converting the random in-place writes that hurt EXT4 into the sequential appends flash loves. This single decision eliminates in-place random writes *at the source*, before they ever reach the device.

But classic LFS (the 1992 Sprite LFS) had two notorious problems, and F2FS's cleverness is in fixing both — the same two problems you already understand from Chapter 4:

### 12.2.1 Disk layout (p. their 12.2.1) ⭐

F2FS divides the volume into fixed **2 MB segments** (512 × 4 KB blocks). Segments group into **sections**, and sections into **zones**. Crucially — **F2FS sets the section size to match the FTL's garbage-collection unit, and aligns its zones with the FTL's mapping granularity.** This is the cooperation that EXT4 lacks: F2FS deliberately shapes its layout to fit the device's internal structure (Ch2's channels/dies, Ch4's GC unit), so the filesystem and FTL pull in the same direction.

The volume splits into **six areas**:
```
 |-> aligned to zone size          |-> aligned to segment size
 ┌────────────┬────────────┬─────────────┬─────────────┬────────────┬──────────┐
 │ Superblock │ Checkpoint │ Segment     │ Node Address│ Segment    │  Main    │
 │   (SB)     │   (CP)     │ Info Table  │ Table (NAT) │ Summary    │  Area    │
 │            │            │   (SIT)     │             │ Area (SSA) │          │
 └────────────┴────────────┴─────────────┴─────────────┴────────────┴──────────┘
   (2 copies)  (2 copies)                                            (nodes+data)
```
- **Superblock (SB)** — basic partition info; two copies for safety.
- **Checkpoint (CP)** — a consistent snapshot of filesystem state (valid bitmaps, orphan lists, active-segment summaries). **This is F2FS's power-loss-recovery mechanism** — see §12.2.2.
- **Segment Info Table (SIT)** — per-segment **valid-block count + validity bitmap.** *This is the exact analog of the SSD's VPC (Valid Page Count) and VPBM (Valid Page Bitmap) from Chapter 4 §4.3.3* — the structure GC uses to find the emptiest victims.
- **Node Address Table (NAT)** — maps node IDs → physical addresses. *This is the mapping-table indirection, at the filesystem layer* (see the wandering-tree fix below).
- **Segment Summary Area (SSA)** — records **which node owns each block** (block → parent node). *This is the exact analog of the SSD's P2L (Physical-to-Logical) table from Chapter 4 §4.3.3* — used during GC to find and update the owner of a block being moved.
- **Main Area** — where nodes and data actually live, organized as the append-only logs.

The metadata areas (SB, CP, SIT, NAT, SSA) need random-write access, which is why F2FS on a fully-sequential zoned device needs a conventional (randomly-writable) region for them — a detail that matters for ZNS (below).

### 12.2.2 The important algorithms (p. their 12.2.2) ⭐⭐

Four mechanisms, each with a direct Chapter-4 twin:

**(1) Multi-head logging — hot/cold separation.** Rather than one append log, F2FS keeps **up to 6 active logs simultaneously**, separating data by *temperature* and *type*: hot/warm/cold × node/data. Frequently-updated data (hot) goes to one log; rarely-touched data (cold) to another. *This is exactly the hot/cold data separation from wear leveling (Ch4 §4.5) and the multi-stream/FDP idea from the Chapter-4 supplement* — segregating data by update frequency so that when you reclaim a segment, its contents tend to become invalid *together* (low cleaning cost), and cold data isn't repeatedly dragged along with hot data. Same principle, same payoff, filesystem layer.

**(2) Cleaning — garbage collection.** Because it's log-structured, F2FS must reclaim stale space, and its "cleaning" is **literally garbage collection** with the same design choices you learned in Chapter 4 §4.3:
- **Victim selection:** **Greedy** (pick the segment with the fewest valid blocks — least to move) for foreground/urgent cleaning, or **Cost-Benefit** (weigh valid-block count *against* the segment's age, favoring old cold segments) for background cleaning. *These are the same greedy and cost-benefit victim-selection policies as SSD GC.*
- **Foreground vs background** cleaning — reactive (when free space is low, during writes) vs proactive (during idle). *Same as foreground/background GC in Ch4 §4.3.4.*
- **The process:** consult the SIT to find a low-validity victim → use the SSA to identify each valid block's owning node → copy valid blocks to a free log → update the NAT → invalidate the victim segment → erase it after the next checkpoint. *This is step-for-step the SSD GC process from Ch4* (find victim via valid-count, relocate valid data, update mapping, free the block).
- **Hybrid write scheme:** F2FS defaults to **copy-and-compaction** (classic LFS cleaning — great when free segments are plentiful) but switches to **threaded logging** (write into holes in existing dirty segments — no cleaning needed) when the disk gets full and cleaning overhead would spike. A pragmatic adaptation to the "LFS suffers under high utilization" problem.

**(3) The NAT — solving the "wandering tree" problem.** This is F2FS's cleverest fix, and it's the *same indirection idea as the FTL mapping table.* Here's the problem: in a naive LFS, when you write a data block it moves to a new address, so its inode pointer must update — but updating the inode moves *it* to a new address, so the directory pointing to the inode must update, which moves the directory... a "snowball" of updates cascading up to the filesystem root on *every single write*. This is the **wandering tree** problem, and it's crippling.

F2FS's solution: the **Node Address Table (NAT)** — a persistent indirection layer mapping each **node ID** to its current **physical address**. Nodes (inodes, direct nodes, indirect nodes) reference each other by *node ID*, not by physical address. So when a data block moves, only its direct-node's block pointer changes, and when a *node* moves, **only its NAT entry updates** — the parent nodes still reference it by the same unchanged node ID. **The snowball stops at the NAT.** *This is precisely why the FTL's mapping table exists (Ch4 §4.2): an indirection layer so data can relocate freely without forcing everything that references it to update.* Same problem, same solution, one layer up.

**(4) Checkpoint — power-loss recovery via shadow copies.** F2FS maintains consistency with **checkpoints** — periodic consistent snapshots of the filesystem state written to the CP area. On mount, F2FS finds the last valid checkpoint and recovers from it. It uses a **shadow-copy** scheme: **two copies** of the CP (and of NAT/SIT), one of which is always the last-known-good — so an interrupted checkpoint write can't corrupt the valid one. After a crash, F2FS rolls back to the last stable checkpoint, then **roll-forward recovers** recent writes logged since. *This is the direct analog of the SSD's snapshot/checkpoint mechanism from Chapter 4 §4.6* — periodically persist a consistent state, recover to it after power loss, replay the small tail. Same idea, filesystem layer.

### 12.2.3 Feature summary (p. their 12.2.3)

Why F2FS beats EXT4 on flash, in one list:
- **Sequential-only writes** — converts random writes to appends (flash's best case), the opposite of EXT4's in-place model.
- **FTL-aware layout** — sections align to the FTL's GC unit; logs align to zones — cooperation, not opacity.
- **Hot/cold separation** — reduces cleaning cost and device-side WA.
- **NAT indirection** — kills the wandering-tree write cascade.
- **No double-write journaling** — checkpoints + roll-forward instead of a data journal, so less write amplification than EXT4's journal.
- **Lower write amplification overall** — the whole design minimizes writes, extending flash life (the Chapter-4 goal, pursued from above).

The measured payoff (FAST 2015 paper): F2FS **outperformed EXT4 by up to 3.1× on iozone and 2× on SQLite** on mobile, cut realistic-workload elapsed time by up to **40%**, and won by up to **2.5× on SATA SSDs** on servers.

### 12.2.4 Latest progress (p. their 12.2.4) — *see the expanded modern section below*

The book's "latest progress" (compression, zoned support) has advanced substantially — covered next.

---

## 📌 Modern developments & the two-layer picture

*F2FS is actively developed (Jaegeuk Kim still maintains it, with updates in current kernels), so here's the current state plus the crucial cross-layer insight. Grounded in current kernel docs and sources.*

**Transparent compression.** F2FS gained per-file **compression** — **LZ4** (Linux 5.6), **zstd** (5.7), and LZO — applied at the file/directory level. Android uses it aggressively: sequential reads of compressed data on flash are fast enough that decompression overhead is usually negligible, so you get real capacity savings "for free." (Compression also *reduces writes*, helping endurance — the Chapter-4 goal again.) Recent kernels (6.9) continue fixing compression corner-cases and added on-demand compress/decompress ioctls.

**Inline encryption** (fscrypt, since Linux 4.2) — directory-level encryption with hardware inline-crypto support (which is why Google adopted F2FS on the Pixel 3), plus inline data/directories (small files stored directly in the inode, avoiding a separate block).

**The log-on-log problem — and why ZNS is the fix.** ⭐ This is the deep insight of the whole chapter, and it ties directly to your Chapter 4/6 supplements. Consider the layers when F2FS runs on a normal SSD:
```
   F2FS  = log-structured   (writes appends, does its own cleaning/GC)
     │        ▼
    FTL   = log-structured   (also writes out-of-place, also does GC)
     │        ▼
   NAND
```
**You have a log running on top of a log** — two independent layers *both* doing out-of-place writes, *both* maintaining mappings, *both* running garbage collection, neither aware of the other. F2FS cleans a segment (moving valid data to a new logical location); the FTL sees those as fresh writes and *also* relocates them internally and *also* garbage-collects. The two GCs interfere, and write amplification **compounds** (filesystem WA × device WA). This "log-on-log" inefficiency is a well-known problem in flash storage — doing the same work twice.

**Zoned storage (ZUFS/ZNS) collapses the two logs into one.** F2FS added **zoned block device support** — for SMR HDDs (kernel 4.10) and **NVMe ZNS SSDs (kernel 5.16+)**. On a zoned device, the device exposes its physical zones directly (Ch4/Ch6 supplements: ZNS/ZUFS), the FTL's placement/GC is minimized or eliminated, and **F2FS's log segments map straight onto the device's zones.** Now there's *one* log — F2FS *is* the flash manager, writing sequentially into zones and cleaning them, with the device just obeying. The double-logging vanishes: filesystem WA and device WA merge, WAF approaches 1, DRAM shrinks (Ch4 supplement), and QLC becomes more viable. **F2FS is the reference flash-native filesystem for ZNS**, which is exactly why it's the natural host-side counterpart to the ZNS/FDP story you already traced — F2FS is *the* filesystem that knows how to drive a zoned device. (Recent kernels, e.g. 6.9, specifically improved ZNS support for large-section devices used in Android.) There's even a 2024 research direction on host/controller co-design to coordinate F2FS and the device for proactive defragmentation — reducing fragmentation up to ~70% — the same host↔device cooperation theme.

**Android adoption, precisely stated.** F2FS is the dominant choice for the **userdata partition** on modern Android flagships (Pixel, most Galaxy, Xiaomi, OPPO, OnePlus, etc.). EXT4 still persists for **boot/recovery partitions**, budget devices, and some OEM configs — so the accurate statement is "F2FS dominates userdata on modern Android," not "F2FS replaced EXT4 everywhere."

**Caveats worth knowing (for balance).** F2FS's **fsck and power-loss recovery are weaker** than EXT4's mature journaling — under frequent sudden power loss, F2FS can recover more slowly or (rarely) lose data if fsck fails. It also caps at **16 TiB** and lacks native RAID5/6. So F2FS wins decisively on flash-optimized *performance and endurance*, while EXT4 retains an edge in *maturity and robustness* — which is why the ecosystem uses both, each where it fits.

---

## The third category — raw-flash filesystems (brief, for embedded context)

Worth knowing since it's relevant to deeply-embedded systems (and to a NAND company): **JFFS2, UBIFS, and YAFFS** are filesystems that run on **bare NAND with no controller/FTL** — they manage the raw flash *themselves*, doing their own wear leveling, bad-block management, and ECC directly. They're used in small embedded devices (routers, IoT, microcontrollers) where the flash is soldered raw to the board with no controller chip.

The contrast is the key point: **F2FS and JFFS2 both "know about flash," but at different layers.** JFFS2 *replaces* the FTL (talks to raw NAND); F2FS *cooperates with* the FTL (talks to a managed device — SSD/UFS/eMMC — that has its own controller). This is why F2FS explicitly assumes an FTL underneath and is *not* meant for raw NAND. For most modern storage (anything with a SCSI/SATA/NVMe/UFS interface), there's a controller, so F2FS (or EXT4) is the right layer; raw-flash filesystems only appear where there's no controller at all.

---

## Key vocabulary

| Term | Meaning |
|---|---|
| filesystem | OS layer mapping files onto a block device |
| VFS | Virtual File System (uniform kernel API above all filesystems) |
| block group | EXT4's fixed volume subdivision |
| inode | fixed-size per-file metadata record (attrs + block pointers) |
| block / inode bitmap | free/used tracking in EXT4 |
| extent | contiguous block range (start, start, length) — EXT4 range mapping |
| indirect blocks | ext2/3 per-block pointer scheme (fine-grained mapping) |
| delayed allocation | allocate blocks at flush time, not write time |
| journaling | write intentions durably before applying (crash consistency) |
| ordered / writeback / journal mode | EXT4 journaling modes |
| LFS | log-structured file system (append-only writes) |
| F2FS | Flash-Friendly File System (flash-native LFS) |
| segment / section / zone | F2FS allocation units (2 MB / group / group of sections) |
| superblock (SB) | filesystem-wide metadata |
| checkpoint (CP) | F2FS consistent snapshot (power-loss recovery) |
| shadow copy | two-copy scheme; one always valid |
| SIT (Segment Info Table) | valid-block counts/bitmaps (≈ SSD VPC/VPBM, Ch4) |
| NAT (Node Address Table) | node ID → physical address indirection (≈ FTL map, Ch4) |
| SSA (Segment Summary Area) | block → owning node (≈ SSD P2L, Ch4) |
| node | F2FS metadata unit: inode / direct node / indirect node |
| wandering tree | LFS cascade of pointer updates; solved by NAT |
| multi-head logging | 6 logs separating hot/warm/cold data (≈ WL hot/cold, Ch4) |
| cleaning | F2FS garbage collection (greedy / cost-benefit victim; ≈ SSD GC, Ch4) |
| copy-and-compaction / threaded logging | F2FS's two write schemes |
| log-on-log | inefficiency of a log-structured FS atop a log-structured FTL |
| ZUFS / zoned F2FS | F2FS on a zoned device (ZNS/ZUFS) — collapses the double log |
| raw-flash FS (JFFS2/UBIFS) | filesystems that replace the FTL, managing bare NAND |

---

## Check yourself

1. Why is a filesystem designed for hard drives (like EXT4) a poor fit for flash? Name at least three of the five limitations.
2. What is an inode, and what's the difference between EXT2/3's indirect-block mapping and EXT4's extents? Which Chapter-4 mapping tradeoff does this parallel?
3. Explain EXT4 journaling and its three modes. Why does journaling contribute to write amplification on flash?
4. What single design decision defines F2FS, and why does it make the filesystem "match" the flash underneath it?
5. F2FS's SIT and SSA are the filesystem-layer twins of which two SSD-FTL structures from Chapter 4? What is each used for during cleaning?
6. Describe the "wandering tree" problem in a naive log-structured filesystem, and explain precisely how the NAT solves it. Which FTL structure is the NAT analogous to, and why?
7. F2FS "cleaning" is which Chapter-4 mechanism? Name its two victim-selection policies and which is used foreground vs background.
8. What is F2FS multi-head logging, and which Chapter-4 wear-leveling concept does it implement?
9. How does F2FS achieve power-loss recovery, and how is its checkpoint+shadow-copy scheme analogous to something in Chapter 4 §4.6?
10. **(The key insight)** Explain the "log-on-log" problem when F2FS runs on a normal SSD. What compounds, and why?
11. **(Modern)** How does running F2FS on a ZNS/zoned device fix the log-on-log problem? What happens to write amplification and DRAM, and why is F2FS the natural filesystem for ZNS?
12. Distinguish F2FS from JFFS2/UBIFS. Both "know about flash" — what's the crucial difference in *which layer* they operate at, and when would you use each?

---

*Next up (your list of 5): **SSD power management** — ASPM (PCIe's link power states), NVMe dynamic power management, and the DevSleep/HIBERN8 states — the topic your Chapter guides kept deferring to "the book's power chapter." Then aerospace storage to finish the set.*
