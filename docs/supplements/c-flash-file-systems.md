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

# Supplement C — Flash File Systems (EXT4 & F2FS)

This supplement climbs one layer *above* the drive: the **operating-system filesystem** that decides how files map onto the block device an SSD presents. (It reconstructs a 2nd-edition topic from the Linux kernel documentation and the F2FS research literature.)

The payoff, stated up front: **everything [Chapter 4](../core/ch4-ftl.md) taught about the FTL, F2FS re-implements at the filesystem layer.** Its "cleaning" *is* garbage collection. Its multi-head logging *is* hot/cold separation. Its Node Address Table *is* a mapping-table indirection. Its checkpoint *is* the power-loss snapshot. So this chapter is largely *Chapter 4 seen from the host's side of the interface* — an easy read if you know the concepts, and an illuminating one: you'll watch the same problem get solved twice, at two layers, and see why that double-solving is itself a problem that ZNS finally fixes.

**The framing question.** Classic filesystems (EXT4 and its ancestors) were designed for **hard drives**: they assume in-place overwrite is cheap and optimize for *seek locality*. On flash both assumptions are wrong — there is no head to park near the data, and in-place overwrite is physically impossible ([Ch 3](../core/ch3-nand-flash.md)). Two responses emerged: **(a)** retrofit the HDD filesystem with flash awareness (EXT4 + Trim + alignment — works, still dominant, suboptimal), or **(b)** design a flash-native filesystem from scratch — **F2FS**, the interesting one.

**A taxonomy to orient by** — three kinds of "flash-related" filesystems, at different layers:

| Category | Examples | Manages raw NAND? | Assumes an FTL below? |
|---|---|---|---|
| HDD filesystem (retrofitted) | EXT4, XFS, NTFS | No | Yes — treats the SSD as a black box |
| Flash-native, FTL-based | **F2FS** | No | **Yes** — cooperates with the FTL |
| Raw-flash filesystem | JFFS2, UBIFS, YAFFS | **Yes** — own WL/ECC | No — talks to bare NAND |

This supplement covers the first two; the third gets a short coda (§C.3) for embedded context.

!!! abstract "In this supplement"
    - **EXT4** ⭐ — block groups, inodes, extents, journaling — and its five failures on flash (§C.1)
    - **F2FS** ⭐⭐ — the log-structured design; SIT/NAT/SSA; multi-head logging; cleaning; checkpoints — each mapped to its Chapter-4 twin (§C.2)
    - **The log-on-log problem and the ZNS fix** ⭐ — the deep cross-layer insight (§C.2.5)
    - **Raw-flash filesystems** — when there is no FTL to cooperate with (§C.3)

---

## C.1 EXT4: the HDD-era filesystem ⭐

### C.1.1 Lineage

The **ext** family is Linux's historical default: **ext2** (1993 — classic inodes + bitmaps, no journaling) → **ext3** (2001 — added journaling) → **ext4** (2008 — extents, volumes to 1 EiB, delayed allocation). It remains the default or fallback on most Linux systems and many Android boot/recovery partitions. Hold one fact: EXT4 was engineered in and for the **rotational-disk era** — its goals were short seeks and cheap in-place updates, exactly the properties flash lacks.

### C.1.2 On-disk structure

The volume divides into **block groups**:

```
┌──────────┬────────────┬────────┬────────┬────────────┬──────────────┐
│ Super    │ Group      │ Block  │ Inode  │ Inode      │ Data         │
│ block    │ Descriptors│ Bitmap │ Bitmap │ Table      │ Blocks       │
│ (copy)   │            │        │        │            │              │
└──────────┴────────────┴────────┴────────┴────────────┴──────────────┘
```

- **Superblock** — filesystem-wide metadata, replicated across groups.
- **Group descriptors** — where each group's bitmaps and inode table live.
- **Block / inode bitmaps** — one bit per block/inode: free or used.
- **Inode table** — the array of **inodes**: fixed-size (typically 256 B) per-file records holding permissions, owner, timestamps, size, and — crucially — **pointers to the file's data blocks**.
- **Data blocks** — the contents. (Modern EXT4's "flex block groups" cluster several groups' metadata together — a seek-locality optimization, i.e., an HDD instinct.)

### C.1.3 In-memory structure

Mounted, EXT4 keeps hot structures in RAM: cached inodes, the **dentry cache** (name → inode), the page cache, in-memory bitmaps and superblock. Writes buffer in RAM and flush later — which is why sudden power loss can lose recent writes: the same buffering hazard as [Ch 4 §4.6](../core/ch4-ftl.md#46-power-loss-recovery), one layer up. The **VFS** sits above everything, giving applications one API whatever filesystem lies beneath.

### C.1.4 Extents ⭐

EXT4's headline improvement — and a perfect parallel to [Ch 4 §4.2.1](../core/ch4-ftl.md#421-mapping-granularity)'s mapping-granularity trade-off:

- **ext2/3: indirect block mapping** — one pointer per data block, with single/double/triple indirect pointer blocks for large files. Fine-grained and flexible, but a 1 GB file needs ~256K pointers chased through indirection. *The filesystem's version of page mapping: flexible, big tables.*
- **ext4: extents** — one record `(logical start, physical start, length)` describes a contiguous run up to 128 MB, stored in a B-tree. A large contiguous file needs a handful of extents. *The filesystem's version of block/hybrid mapping: compact, wants contiguity.*

Both layers face the identical choice — fine granularity (big metadata, any layout) vs coarse contiguity (tiny metadata, needs order) — and both chose according to their workload.

### C.1.5 Allocation strategy

EXT4 fights hard for contiguity (an HDD instinct — fewer seeks): **delayed allocation** (assign physical blocks at flush time, when the full size is known), **multiblock allocation** (grab runs, not single blocks), **persistent preallocation** (reserve ahead for known-size files). The irony on flash: all this *physical*-locality effort targets a device whose FTL **scatters the data anyway** ([Ch 4 §4.2](../core/ch4-ftl.md#42-mapping-management)). Contiguous *logical* layout still helps — fewer extents, cleaner Trim, bigger sequential transfers — but the seek-avoidance rationale evaporates.

### C.1.6 Journaling ⭐

EXT4's crash consistency = a **journal** (JBD2): write intentions durably first; replay on remount after a crash. Three modes — **journal** (data + metadata journaled; safest, everything written twice), **ordered** (default: metadata journaled, data forced down *first* so metadata never points at garbage), **writeback** (metadata only, no ordering; fastest, least safe) — plus metadata/journal checksums. Conceptually this *is* [Ch 4 §4.6](../core/ch4-ftl.md#46-power-loss-recovery)'s recovery machinery at the filesystem layer. But note the price: journaling writes some data **twice** — filesystem-level write amplification, stacked on top of the device's own.

### C.1.7 Why flash deserves better ⭐

EXT4 *works* on SSDs — as a rotational design under protest:

1. **In-place update model** — every overwrite becomes an out-of-place write + garbage inside the FTL: WA and wear, manufactured at the source.
2. **Journaling doubles writes** — compounding the FTL's own amplification.
3. **Seek-locality optimizations are pointless** — effort spent on a problem flash doesn't have.
4. **Zero FTL awareness** — EXT4 knows nothing of erase-block sizes, GC units, or hot/cold sensitivity; it can't cooperate.
5. **Random-write-heavy metadata** — bitmaps, inodes, journal commits scatter small random writes, flash's worst diet ([Ch 4 §4.3.1](../core/ch4-ftl.md#431-the-gc-principle-via-a-toy-ssd)).

Five failures; one purpose-built answer.

---

## C.2 F2FS: the flash-native filesystem ⭐⭐

**F2FS (Flash-Friendly File System)** was created by **Jaegeuk Kim at Samsung** — first patch October 2012, merged in **Linux 3.8** that December, and still maintained by Kim today. It is now the **default userdata filesystem on billions of Android devices** (Pixel, most Galaxy since the Note 10, Xiaomi, OPPO, OnePlus, Huawei…).

**The one defining decision: F2FS is log-structured.** All writes are **sequential appends** to an active log; nothing is overwritten in place; old locations go stale and await cleaning. Stop and notice — *that is exactly how flash itself behaves* ([Ch 3](../core/ch3-nand-flash.md#311-how-a-flash-cell-works)) *and exactly how the FTL manages it* ([Ch 4](../core/ch4-ftl.md#43-garbage-collection)). F2FS makes the filesystem move the way the medium moves, converting EXT4's random in-place writes into the sequential appends flash loves — eliminating the problem *at the source*, before it ever crosses the interface.

Classic LFS (Sprite, 1992) had two notorious problems; F2FS's cleverness is fixing both, and both fixes are Chapter-4 ideas wearing filesystem clothes.

### C.2.1 Disk layout ⭐

F2FS divides the volume into **2 MB segments** (512 × 4 KB blocks), grouped into **sections**, grouped into **zones** — and here's the cooperation EXT4 never offered: **the section size is set to match the FTL's GC unit, and zones align to the device's internal parallel structure.** Filesystem and FTL pull in the same direction by construction.

Six areas:

```
 ┌────────────┬────────────┬─────────────┬─────────────┬────────────┬──────────┐
 │ Superblock │ Checkpoint │ Segment     │ Node Address│ Segment    │  Main    │
 │   (SB)     │   (CP)     │ Info Table  │ Table (NAT) │ Summary    │  Area    │
 │ (2 copies) │ (2 copies) │   (SIT)     │             │ Area (SSA) │(nodes+data)
 └────────────┴────────────┴─────────────┴─────────────┴────────────┴──────────┘
```

- **SB** — partition basics, duplicated.
- **CP (Checkpoint)** — the consistent snapshot; F2FS's power-loss recovery (§C.2.2).
- **SIT** — per-segment **valid-block count + bitmap**. *The exact twin of the FTL's VPC/VPBM from [Ch 4 §4.3.3](../core/ch4-ftl.md#433-gc-implementation-three-steps)* — how cleaning finds its victims.
- **NAT** — node ID → physical address. *The mapping-table indirection, one layer up* (the wandering-tree fix, below).
- **SSA** — which node owns each block. *The twin of the FTL's P2L table* — how cleaning finds a moved block's owner.
- **Main area** — the append-only logs of nodes and data.

(The metadata areas need random-write access — which is why F2FS on a purely sequential zoned device keeps them in a small conventional region. That detail returns in §C.2.5.)

### C.2.2 The four algorithms ⭐⭐

Each with its Chapter-4 twin:

**(1) Multi-head logging = hot/cold separation.** Up to **six active logs** at once, split by temperature × type (hot/warm/cold × node/data). Hot data streams into one log, cold into another — so a reclaimed segment's contents tend to die *together* (cheap cleaning) and cold data stops being dragged around with hot neighbors. *This is [Ch 4 §4.5](../core/ch4-ftl.md#45-wear-leveling)'s cold/hot separation and the multi-stream/FDP idea of [§4.11](../core/ch4-ftl.md#411-modern-developments-from-sdf-to-zns-and-fdp), implemented in the filesystem.*

**(2) Cleaning = garbage collection.** Literally, with the same design menu as [Ch 4 §4.3](../core/ch4-ftl.md#43-garbage-collection):

- **Victim selection:** **greedy** (fewest valid blocks) for foreground urgency; **cost-benefit** (valid count weighed against segment age, favoring old cold segments) for background work.
- **Foreground vs background** cleaning — reactive under pressure, proactive when idle.
- **The mechanics:** SIT finds the low-validity victim → SSA identifies each valid block's owner → copy valid blocks to a free log → update NAT → the victim frees after the next checkpoint. Step for step, SSD GC.
- **The pragmatic hybrid:** default **copy-and-compaction** while free segments are plentiful; switch to **threaded logging** (write into holes of dirty segments — no cleaning required) when the volume fills and cleaning costs would spike. LFS's classic high-utilization weakness, patched with a mode switch.

**(3) The NAT kills the wandering tree.** The naive-LFS disease: move a data block → its inode's pointer must change → the inode moves → the directory pointing at it must change → the directory moves → … a cascade to the root on every write. F2FS interposes the **Node Address Table**: nodes reference each other by **node ID**, and only the NAT maps IDs to physical addresses. A node moves? One NAT entry updates; every parent still holds the same ID. **The snowball stops at the NAT** — *precisely why the FTL's mapping table exists* ([Ch 4 §4.2](../core/ch4-ftl.md#42-mapping-management)): an indirection layer so data can relocate freely without dragging its referrers along. Same disease, same cure, one layer up.

**(4) Checkpoints = power-loss snapshots.** Periodic consistent snapshots into the CP area, with a **shadow-copy** discipline: two copies of CP/NAT/SIT, one always last-known-good, so an interrupted checkpoint can't corrupt the survivor. After a crash: roll back to the stable checkpoint, then **roll forward** through recent logged writes. *[Ch 4 §4.6](../core/ch4-ftl.md#46-power-loss-recovery)'s snapshot + tail-replay, verbatim.*

### C.2.3 The scorecard

Why F2FS beats EXT4 on flash, in one list: sequential-only writes (random writes eliminated at the source) · FTL-aligned layout (cooperation, not opacity) · hot/cold separation (cheaper cleaning, lower device WA) · NAT indirection (no wandering tree) · **no double-write journal** (checkpoint + roll-forward instead) · lower total write amplification, hence longer flash life — Chapter 4's goal, pursued from above.

Measured (the FAST 2015 paper): up to **3.1×** over EXT4 on iozone and **2×** on SQLite on mobile; up to **40%** faster realistic workloads; up to **2.5×** on SATA SSDs server-side.

### C.2.4 Since then: compression and encryption

- **Transparent compression** — per-file/directory **LZ4** (Linux 5.6), **zstd** (5.7), LZO. Android uses it aggressively: flash reads are fast enough that decompression is nearly free, so capacity is saved — and *writes shrink*, which is endurance (Chapter 4's goal yet again). Recent kernels keep refining it (on-demand compress/decompress ioctls).
- **Inline encryption** (fscrypt) with hardware inline-crypto support — a reason Google adopted F2FS for the Pixel line — plus inline small files/directories stored directly in the inode.

### C.2.5 The log-on-log problem — and the ZNS fix ⭐

The deepest insight in this supplement. Run F2FS on a normal SSD and look at the layers:

```
   F2FS  = log-structured   (appends, own mapping, own cleaning/GC)
     │        ▼
    FTL   = log-structured   (out-of-place writes, own mapping, own GC)
     │        ▼
   NAND
```

**A log running on top of a log.** Two independent layers both writing out-of-place, both keeping maps, both garbage-collecting — neither aware of the other. F2FS cleans a segment (rewriting valid data to new logical addresses); the FTL sees fresh writes, relocates them again internally, and schedules its own GC. The two collectors interfere, and write amplification **multiplies**: filesystem WA × device WA. Solving the same problem twice, and paying twice.

**Zoned storage collapses the two logs into one.** F2FS supports zoned block devices — SMR HDDs (kernel 4.10) and **NVMe ZNS SSDs (5.16+)**. On a zoned device ([Ch 4 §4.11](../core/ch4-ftl.md#411-modern-developments-from-sdf-to-zns-and-fdp), [Ch 6 §6.10.1](../core/ch6-nvme.md#6101-zns-mechanics-zones-states-and-zone-append)), the drive exposes its zones directly and abandons internal placement/GC; **F2FS's log segments map straight onto the zones.** One log. F2FS *is* the flash manager; the device just obeys. Filesystem WA and device WA merge, WAF approaches 1, the mapping DRAM shrinks, QLC gets easier — and **F2FS is the reference filesystem for driving ZNS**, the natural host-side ending of the SDF → ZNS story. Recent kernels keep investing (large-section ZNS support for Android in 6.9; research on host/device co-designed defragmentation reporting up to ~70% fragmentation reduction).

**Android adoption, precisely stated:** F2FS dominates the **userdata** partition on modern flagships; EXT4 persists on boot/recovery partitions and budget devices. "F2FS won userdata," not "F2FS replaced EXT4 everywhere."

**Caveats, for balance:** F2FS's fsck and power-loss recovery are less battle-hardened than EXT4's journaling — under frequent brutal power cycling it can recover slowly or, rarely, lose data where EXT4 wouldn't; it caps at 16 TiB; no native RAID5/6. Flash-optimized performance and endurance vs decades of maturity: the ecosystem sensibly uses both.

---

## C.3 The third category: raw-flash filesystems

For completeness and embedded context: **JFFS2, UBIFS, YAFFS** run on **bare NAND with no controller at all** — doing their own wear leveling, bad-block management, and ECC against raw chips. Their home is deeply embedded systems (routers, IoT, microcontrollers) where flash is soldered raw to the board.

The contrast is the point: F2FS and JFFS2 both "understand flash," **at different layers**. JFFS2 *replaces* the FTL; F2FS *cooperates with* one. Anything with a SATA/NVMe/UFS/eMMC interface has a controller, so F2FS (or EXT4) is the right layer there; raw-flash filesystems appear only where no controller exists.

---

## Key takeaways

1. **EXT4 is a rotational design on parole**: in-place updates, double-write journaling, seek optimizations, and FTL-blindness — five ways it manufactures write amplification on flash.
2. **F2FS's whole design is one decision** — log-structured, like the medium — plus the machinery to make LFS livable: NAT (kills the wandering tree), multi-head logs (hot/cold), greedy/cost-benefit cleaning, shadow-copied checkpoints.
3. **Every F2FS structure has a Chapter-4 twin**: SIT ≈ VPC/VPBM, SSA ≈ P2L, NAT ≈ the mapping table, checkpoint ≈ the power-loss snapshot, cleaning ≈ GC. Same problems, one layer up.
4. **Log-on-log is the hidden tax** of a flash-native filesystem on a conventional SSD — two mappers, two collectors, multiplied WA. **ZNS collapses the logs into one**, and F2FS is the filesystem built to hold the pen.
5. **Layer determines tool**: raw NAND → JFFS2/UBIFS; managed device → F2FS or EXT4; zoned device → F2FS as the single log.

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

??? info "📖 Provenance"

    Flash file systems are a 2nd-edition topic (their Chapter 12), not in the
    1st edition of《深入淺出SSD》. This supplement reconstructs the material
    from the Linux kernel documentation, the F2FS FAST 2015 paper, and
    current kernel sources, organized around the Chapter-4 concept mapping.

*Next: [Supplement D — SSD Power Management](d-power-management.md): ASPM, NVMe power states, DevSleep and friends — the machinery the core chapters kept deferring to "the power chapter."*
