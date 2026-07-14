---
title: "Ch 6 — NVMe"
tags:
  - nvme
  - queues
  - prp-sgl
  - namespaces
  - nvme-of
  - zns
source_anchor: "CH6 file, pp. 1–68"
---

# Chapter 6 — NVMe

[Chapter 5](ch5-pcie.md) built the *road* between host and SSD. But PCIe is agnostic about what travels on it — **NVMe** is the traffic system on top: the command protocol defining how host and drive actually converse — queues, doorbells, addressing, data protection. This is where the interface of Chapter 5 finally meets the SSD front end of [Chapter 2](ch2-controllers-afa.md).

This is also the most playfully written subject in the book, taught almost entirely through analogies — the Three Kingdoms strategist, the "three treasures," the elephant in the fridge, the courier who both delivers and collects, the data bodyguard. The analogies *are* the pedagogy — they make an abstract protocol stick — so they stay, each with the mechanism spelled out underneath.

!!! abstract "In this chapter"
    - **From AHCI to NVMe** ⭐ — why the protocol had to change when the media stopped being the bottleneck (§6.1)
    - **The command model** ⭐⭐ — Admin vs I/O commands, and the 8-step flow (§6.2)
    - **The three treasures** ⭐⭐ — SQ, CQ, doorbells; rings, phase tags, and who owns which pointer (§6.3)
    - **PRP vs SGL** ⭐ — the two ways to hand the SSD a memory address (§6.4)
    - **A real trace** ⭐ — the whole read as raw PCIe TLPs; Chapters 5 and 6 shake hands (§6.5)
    - **End-to-end protection** (§6.6) · **Namespaces, multi-controller, dual-port** (§6.7) · **NVMe over Fabrics** (§6.8)
    - **The modern era** — NVMe 2.x restructuring, NVMe/TCP (§6.9); ZNS mechanics, CMB, Key-Value (§6.10)

    Short on time? §6.2–6.4 are the heart.

---

## 6.1 From AHCI to NVMe ⭐

**The old world: SATA + AHCI.** Hard disks and early SSDs spoke **AHCI** (an Intel-led standard) over SATA. Its headline feature was **NCQ** — Native Command Queuing — with a maximum queue depth of **32**: thirty-two commands in flight, a big step up from one-at-a-time.

**Why it had to change.** In the HDD era the *disk* was the bottleneck — milliseconds of seek time made protocol overhead irrelevant. Flash removed the media bottleneck, and the bottleneck **moved up the stack** into the interface and protocol. So in late 2009, an Intel-led coalition (Micron, Dell, Samsung, Marvell…) created **NVMe**: a protocol designed *for* solid-state media — any solid-state media; it suits 3D XPoint as well as flash — free of HDD-era baggage. First product: Samsung XS1715 (2013); first consumer drive: Intel 750 (2015); Apple has shipped NVMe in iPhones since the 6s.

**Three advantages over AHCI:**

1. **Lower latency.** Latency = media + controller + software. Media: flash wins. Controller: a native PCIe device talks *directly* to the CPU, no southbridge detour. Software: NVMe shortens the command path — fewer register accesses, **MSI-X** interrupts, and a parallel design that eliminates cross-core lock contention.
2. **Higher IOPS.** Roughly, **IOPS = queue depth ÷ latency** — depth matters. AHCI: **1 queue × 32 deep**. NVMe: up to **64K queues × 64K deep**. Combined with PCIe bandwidth, there is no contest.
3. **Lower power** — richer autonomous power states and transitions ([Supplement D](../supplements/d-power-management.md) covers the machinery).

---

## 6.2 NVMe overview: the command model ⭐⭐

**Where NVMe sits.** At the top of the stack — the command/application layer. The classic metaphor: **NVMe is the strategist Zhuge Liang** — *plans made in the tent decide victories a thousand li away* — **and PCIe is the general who executes.** NVMe could ride other transports, but NVMe + PCIe is the alliance that works. The counter-image explains history: running fast PCIe hardware under old AHCI is brilliant generals commanded by the hapless Liu Bei. It's also why every SATA SSD in existence plateaus at ~560 MB/s: not a flash limit — a SATA 3.0 limit, and there will never be a SATA 4.0.

**Two command classes** (deliberately few commands — ATA accumulated decades of HDD-compatibility bloat NVMe refused to inherit):

- **Admin commands** — manage the drive: create queues, Identify, Get/Set Features…
- **I/O commands** — move data: Read, Write, and friends.

**How commands get delivered — the "three treasures" (吉祥三寶):**

- **SQ (Submission Queue)** — lives in **host memory**; the host writes commands here.
- **CQ (Completion Queue)** — lives in **host memory**; the SSD writes results here.
- **DB (Doorbell register)** — lives **on the SSD**; the host rings it.

Note the asymmetry: the host never pushes commands to the drive. It stages them in *its own* RAM and rings the doorbell — "orders are ready, come collect." The SSD fetches them over PCIe itself.

**The 8-step command flow — the spine of the whole protocol.** (How many steps to put an elephant in a fridge? Three. To process an NVMe command? Eight.)

1. Host writes the command into the **SQ**.
2. Host writes the **SQ Tail doorbell** — "new work."
3. SSD **fetches** the command from the SQ.
4. SSD **executes** it.
5. SSD writes the result into the **CQ**.
6. SSD **interrupts** the host.
7. Host **processes** the completion.
8. Host writes the **CQ Head doorbell** — "completions handled, thanks."

Memorize the eight; §6.5 will replay them as raw PCIe packets.

---

## 6.3 The three treasures in detail ⭐⭐

??? example "🎬 Animate this — The NVMe Ring Machine"

    The SQ/CQ/doorbell dance as a working machine — submit commands, watch the phase tag flip on wraparound.

    [Animation page](../animations/nvme-ring-machine.md) · [open full-screen ↗](../animations/files/nvme_ring_machine.html)

    <iframe src="../../animations/files/nvme_ring_machine.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The NVMe Ring Machine"></iframe>


**Pairing.** SQs and CQs come in cause-and-effect pairs — 1:1 or many-SQ:1-CQ. Two tiers:

- **Admin SQ/CQ** — exactly one pair per controller, 1:1, Admin commands only. Depth 2–4K.
- **I/O SQ/CQ** — up to **65,535** pairs, created *by* Admin commands (they don't exist at boot — you build them). Depth 2–64K.

Queue count and depth are both configurable — NVMe is a shapeshifter: fat or thin, tall or short, as the workload likes. (AHCI's fixed 1×32 simply can't compete.) Entry sizes: **64 B** per SQ command, **16 B** per CQ completion.

**Why multiple SQs per core?** (1) **Performance** — one SQ per thread means no lock contention; (2) **QoS** — the classic example: video call in front, torrent in back. Put the video's commands in a high-priority SQ and the download's in a low-priority one; the video never stutters, and nobody mourns a slow download.

**They are ring buffers — producer/consumer.** Every queue has a **head** and a **tail**: producer writes at the tail, consumer reads from the head.

- **SQ:** producer = host, consumer = SSD.
- **CQ:** producer = SSD, consumer = host.

A concrete run: queues start Head = Tail = 0. Host writes 3 commands → rings **SQ Tail DB = 3**. SSD fetches all three → its **SQ Head** advances to 3. SSD completes two → writes 2 CQ entries → **CQ Tail = 2** → interrupts. Host processes both → writes **CQ Head DB = 2**.

**Who maintains which doorbell** falls straight out of the roles: the tail belongs to the producer, the head to the consumer. So the host maintains **SQ Tail** and **CQ Head**; the SSD maintains **SQ Head** and **CQ Tail** — and the two host-written doorbells double as the notifications ("new work" / "completions absorbed").

**The clever wrinkle: the host may *write* doorbells but never *read* them.** How does it track the pointers it doesn't own?

- **SQ Head** (how far has the SSD consumed?): the SSD **piggybacks the current SQ Head value inside every 16-byte completion entry**. Each completion is also a progress report.
- **CQ Tail** (where do new completions end?): the **Phase Tag** bit. Every CQ entry starts P = 0; the SSD writes new completions with **P = 1**, and flips the sense on each wraparound. The CQ is host memory, so the host just scans until the phase bit stops matching — no doorbell read required. (Watch the flip happen in the ring machine above.)

---

## 6.4 The addressing duo: PRP and SGL ⭐

Data has three questions: *who am I, where from, where to?* For NVMe the answers are short — between host memory and SSD — but one insight organizes everything: **the host is passive; the SSD is active.** On a write the SSD *reaches into* host memory and pulls; on a read it *pushes*. **The SSD is a courier who both delivers to your door and collects from it** — and either way, the courier needs your address. Two address formats exist:

**PRP — Physical Region Page.** Host memory is treated as **physical pages** (4 KB and up). A **PRP entry** is a 64-bit physical address = page base + offset. One entry describes one page; longer transfers chain entries into a **PRP List**, where every entry must have **offset 0** (whole pages only) and no duplicates. Each command carries **PRP1 and PRP2**, which may point at data *or* at a PRP List — pointers or pointers-to-pointers, exactly like C; the SSD dereferences until it hits data. **Admin commands may only use PRP.**

**SGL — Scatter/Gather List** (added in NVMe 1.1). A **linked list** of memory regions: **segments** made of 16-byte **descriptors** — Data Block (a real region), Segment (pointer to the next segment), Last Segment (heads-up that the list is ending), and **Bit Bucket** ("skip this much of the read data — don't send it").

**The one difference that matters:** PRP describes **whole aligned pages**; **SGL describes arbitrary regions** — any address, any length. Example: read 13 KB but keep only 11 KB, scattered into 3/4/4 KB buffers — trivially an SGL, impossible as PRP. Command DW0[15:14] selects the format. Rules: over PCIe, Admin = PRP only, I/O = either; **over Fabrics, everything is SGL** (§6.8).

---

## 6.5 Trace analysis: a real read, as PCIe packets ⭐

The payoff section: the 8-step flow replayed as actual TLPs, welding Chapter 5 to Chapter 6. The courier analogy has one more use: **PCIe's Transaction Layer wraps whatever NVMe hands it — command, data, status — into TLPs without caring what's inside.**

!!! note "Two meanings of 'completion' — keep them apart"
    A **PCIe Completion TLP** answers any Non-Posted TLP ([Ch 5 §5.4](ch5-pcie.md#54-tlp-types)). An **NVMe Completion** is a 16-byte CQ entry answering a command. Different layers, unrelated lifecycles.

The trace: read 128 DW (512 B) from SLBA 0x20E0448 into host buffer 0x14ACCB000, on queue pair #3:

- **Step 2 — ring the doorbell:** a host **Memory Write TLP** to the SQ Tail DB. How does the host address a register inside the SSD? Chapter 5 already answered it: at enumeration the SSD's registers were **BAR-mapped** into host address space ([Ch 5 §5.6](ch5-pcie.md#56-config-space-and-bars)) — the host writes to the mapped address.
- **Step 3 — fetch:** the SSD issues a **Memory Read TLP** for 16 DW (one 64-byte command); the host answers with a PCIe Completion (reads are Non-Posted).
- **Step 4 — data:** the SSD reads flash into cache (internal — invisible on the PCIe trace), then **Memory Write TLPs** push 128 DW to the host, 32 DW at a time = 4 writes, no replies (Posted).
- **Step 5 — completion:** one **Memory Write TLP** places the 16-byte entry in the CQ.
- **Step 6 — interrupt:** **MSI-X** — which is *itself just a Memory Write TLP* to a special address; no physical interrupt pin exists.
- **Step 8 — CQ Head DB:** one last host **Memory Write TLP**.

Total inventory for an entire NVMe read: **Memory Read × 1** (the command fetch) and **Memory Write** for everything else. Two TLP types carry the whole protocol.

---

## 6.6 End-to-end data protection

**The threat model.** "End to end" = host memory ↔ flash. In between: the PCIe wire (noise), the controller's DRAM/SRAM (rare bit flips), the flash path. NVMe's protection ensures what arrives is what was sent — in both directions.

**The mechanism: give the data a bodyguard.** Each logical block (512–4096 B, chosen at format) can carry metadata; with protection on, 8 of those bytes become **PI (Protection Information)**:

- **Guard** — a 16-bit **CRC** over the block: detects corruption.
- **Application Tag** — host-private; the controller doesn't look.
- **Reference Tag** — binds the data to its **LBA**: catches *mix-ups*, where you asked for LBA x and received a perfectly valid block that happens to be LBA y — internally consistent, externally wrong; a CRC alone cannot see it.

Metadata can travel **inline** with the block (the close-body bodyguard) or in a **separate buffer** (the nearby bodyguard); Fabrics requires inline.

**When to skip it.** The bodyguard costs ≥8 B per block (bandwidth, worse at small blocks) plus CRC time (latency) — and PCIe already carries LCRC/ECRC underneath. For expendable data, skip: an ordinary person needs no bodyguard — can't afford one, nobody's hunting them, and it's peacetime.

**Full-path vs half-path.**

- **Full:** host generates PI → controller verifies on arrival (errors reported to host) → PI stored with the data → verified on the way out → host verifies after transfer.
- **Half-path:** host↔controller trusts PCIe's own CRCs; the *controller* generates PI before flash and checks after. Why bother when flash already has ECC ([Ch 3 §3.4.3](ch3-nand-flash.md#343-ecc-error-correcting-codes))? Because between controller and flash the data sits in **DRAM/SRAM**, where flips happen *outside* the flash ECC's jurisdiction — and because the Reference Tag catches firmware-induced address mix-ups no checksum sees.

**Essence:** append CRC + LBA to every block; verify at every hop. Eight bytes and a few cycles against silent corruption — cheap.

---

## 6.7 Namespaces

**What a namespace is.** Carve the drive's flash into independent logical spaces, each with its own LBA range 0…N−1 — each is a **Namespace (NS)** with a unique **NSID**, described by a 4 KB structure (size, LBA format, protection settings, owning controllers). Every I/O command names its NS — otherwise "LBA 0" is ambiguous. (*"Texas" — the US state, or 德州 Dezhou, Shandong? Without the country, who knows.*)

**Why it matters.** To the OS, each NS is an **independent disk**. Mostly an enterprise feature: one physical SSD split into several logical drives with different block sizes and protection for different tenants. The headline use is **SR-IOV**: one SSD exposes a **Physical Function** plus many **Virtual Functions**, each VF assigned its own private NS — VMs get near-native drive access with no hypervisor in the data path.

**Bigger structures: multi-controller and dual-port.** An NVMe *subsystem* may contain **multiple controllers** (full NVMe controllers, not CPU cores), with namespaces **private** to one controller or **shared** (shared access must be atomic). It may also have **multiple PCIe ports** — including **dual-port**, which SATA never had; the only connector wired for it is **U.2** ([Ch 1 §1.6.5](ch1-overview.md#16-form-factors)). The point is **redundancy**: port A dies, the host reaches the shared NS through port B; pair dual ports with dual *hosts* and even a host crash fails over. First dual-port drive: OCZ Z-Drive 6000 (2015); the customers are banking, OLTP/OLAP, HPC. Multi-NS × multi-controller × multi-port is infrastructure — what you build with it is up to your imagination.

---

## 6.8 NVMe over Fabrics

**The problem.** One NVMe SSD does hundreds of thousands of IOPS — often more than its host needs. The natural home for many of them is a pooled array — but **PCIe doesn't scale out** to hundreds of drives across racks. The traditional workaround, iSCSI, re-imposes ~100 µs of protocol latency on a device that answers in <10 µs — *a Ferrari parked on the Xizhimen overpass at rush hour*. **NVMe-oF** exists to extend NVMe across a network without surrendering its latency.

**What it defines:** NVMe bindings over general transports — **RDMA, Fibre Channel, PCIe fabrics** — grouped by interface style (memory-type, message-type, hybrid), since different interconnects have different capabilities and costs.

**RDMA, the flagship transport.** **Remote Direct Memory Access** moves data into a remote machine's memory with **zero copies and zero kernel involvement** — user-space app → local NIC → wire → remote NIC → remote memory. Low latency, low jitter, low CPU load, hardware offload — semantically close enough to local DMA that NVMe maps onto it naturally.

**What NVMe-oF had to change vs local NVMe:**

- **Capsules carry more.** Locally, SQ entries hold only descriptors — the hardware DMAs the real data/SGLs from host memory (~1 µs, who cares). Over a network, round-trips are expensive, so capsules may **embed the data and SGLs directly**, collapsing interactions.
- **No CQ flow control** — the host must guarantee CQ space before sending.
- **SQ:CQ is strictly 1:1**, and queues aren't created via Admin commands.
- **Five new Fabrics commands:** **Connect** (builds a queue pair; carries Host NQN, Subsystem NQN, Host Identifier — NQN = NVMe Qualified Name), **Property Get/Set** (replaces the BAR0 register access that a network doesn't have), **Authentication Send/Receive**.
- **Discovery service** — a Discovery Log Page lets initiators find subsystems, their namespaces, and multiple paths to them.

Result: the same command model you learned in §6.2–6.3, projected across a data center.

---

## 6.9 Modern developments: the NVMe 2.x era

*The first edition is written against NVMe 1.2. Two later changes matter most: the specification restructured itself, and one new transport changed Fabrics' economics.*

**NVMe 2.0 (June 2021) — the refactoring.** The monolithic spec became a **modular library**: a Base specification, separate **Command Set** specs, separate **Transport** specs, plus Management Interface and Boot. Two consequences extend this book directly:

- **NVMe is no longer block-only.** The 2.0 family added command sets for **Zoned Namespaces (ZNS)** and **Key-Value** — the same protocol now speaks block, zoned, and key-addressed storage (§6.10).
- **NVMe-oF dissolved into the family.** The standalone Fabrics spec of §6.8 no longer exists as a separate document; RDMA, Fibre Channel, and TCP are now peer **transport specifications** under one roof.

**ZNS closes the Chapter-4 loop.** The write-amplification lineage from [Ch 4 §4.11](ch4-ftl.md#411-modern-developments-from-sdf-to-zns-and-fdp) — SDF → Open-Channel → ZNS — landed *here*, as a first-class NVMe command set: zoned namespaces align host writes to the flash's erase geometry, per NVM Express improving performance and usable capacity while shrinking the DRAM and OP bills. **FDP**, the backward-compatible alternative from the same lineage, arrived in the NVMe 2.1 generation (August 2024) alongside features like live controller migration.

**NVMe/TCP — the transport that democratized Fabrics.** §6.8's RDMA needs special NICs — a genuine adoption barrier. **NVMe/TCP** runs NVMe-oF over **plain TCP/IP on ordinary Ethernet**, implementable purely in software; the current transport spec bakes in **TLS 1.3**. That's why NVMe-oF finally spread: every data center already owns Ethernet. Today's practical menu: **RDMA** (lowest latency, special NICs), **Fibre Channel** (existing SAN estates), **TCP** (runs anywhere).

**Where the spec stands (2024–2026):** NVMe 2.3 (August 2025) spans Base; NVM, ZNS, Key-Value, and Computational Programs command sets; PCIe, RDMA, TCP, and FC transports; Boot; and Management Interface. NVMe became the one interface across every SSD form factor — U.2, M.2, add-in card, EDSFF — exactly the shapeshifter this chapter described, now formalized. And the fundamentals you just learned — SQ/CQ/doorbell, PRP/SGL, the 8 steps — are untouched: 2.x modularized *around* them, not through them.

---

## 6.10 Three newer features: ZNS mechanics, CMB, Key-Value

*Second-edition topics. §6.9 gave ZNS's* why *(the WA lineage); here is the* how *— plus two features worth knowing.*

### 6.10.1 ZNS mechanics: zones, states, and Zone Append ⭐

**The zone model.** A zoned namespace divides into fixed-size **zones**, each with a **write pointer**: writes must land *exactly at* the pointer (strictly sequential per zone); to rewrite a zone you **reset** it (its erase). Two sizes per zone: **ZSZE** (the LBA-range size, a power of two) vs **ZCAP** (the actually writable capacity, ≤ ZSZE — typically the underlying flash superblock).

**The state machine.** Empty → (implicitly/explicitly) Opened → Closed → Full, plus Read-Only and Offline for failing zones. States exist because **open zones consume real resources** — write buffers, XOR/RAID stripe contexts ([Ch 3 §3.4.4](ch3-nand-flash.md#344-raid-inside-the-ssd)'s chained warships) — so drives enforce **max-open / max-active limits** that hosts must budget.

**Three new commands:**

- **Zone Management Send** — Open / Close / Finish / **Reset** ("erase and rewind the pointer").
- **Zone Management Receive** — **Report Zones**: enumerate states and write pointers.
- **Zone Append** ⭐ — the clever one. The host writes *to a zone*, not to an LBA; the **controller places the data at the write pointer and returns the assigned LBA in the completion.** Why it matters: strict sequential writes clash with NVMe's deep queues — out-of-order arrival of parallel writes would violate the pointer, forcing queue depth 1 per zone. Append makes arrival order irrelevant, restoring full-queue-depth throughput. It reconciles ZNS's discipline with everything §6.3 taught.

### 6.10.2 CMB — the mirror image of HMB ⭐

You know **HMB** ([Ch 4 §4.2.3](ch4-ftl.md#423-hmb-host-memory-buffer)): the host lends DRAM to a poor drive. **CMB (Controller Memory Buffer)** is the reverse: the *drive* exposes some of **its own memory** through a PCIe **BAR** ([Ch 5 §5.6](ch5-pcie.md#56-config-space-and-bars)), and the host may place **SQs, CQs, even data buffers** there.

Why? Look back at step 3 of the 8-step flow: normally the SSD must *fetch* each command from host memory — a PCIe Memory Read plus completion round-trip. Queues in CMB turn the fetch into a local read: **lower latency**. The bigger win is Fabrics targets: an RDMA NIC can deposit incoming data **straight into the SSD's CMB**, skipping host DRAM entirely — one less hop on the data path.

**Mnemonic: HMB = host helps a DRAM-less drive; CMB = drive helps the host (and the fabric).**

### 6.10.3 The Key-Value command set

**KV namespaces** store objects by **key** (≤16 bytes) instead of LBA — commands: Store, Retrieve, Delete, Exist, List. The motivation is the same layer-collapsing thread running through all the modern material: a RocksDB-style engine today translates objects → files → blocks → (FTL) pages, translation stacked on translation ([Supplement C](../supplements/c-flash-file-systems.md)'s log-on-log problem in another costume). A KV drive lets the application hand the object to the hardware and deletes the middle layers. Niche so far — but conceptually of a piece with ZNS and FDP: *remove redundant indirection*.

---

## Key takeaways

1. **The bottleneck moved up the stack** — flash killed the media bottleneck, so the protocol had to die too: AHCI's 1×32 queues gave way to NVMe's 64K×64K.
2. **Three treasures, eight steps.** SQ and CQ live in host memory, doorbells on the drive; the host stages and rings, the SSD fetches and reports. Producer owns the tail, consumer owns the head.
3. **Two elegant tricks make the rings work without doorbell reads:** SQ-head piggybacked in every completion, and the Phase Tag flip marking the CQ frontier.
4. **PRP = whole aligned pages; SGL = arbitrary regions.** Admin commands are PRP-only over PCIe; Fabrics is SGL-only.
5. **On the wire, NVMe is just two TLP types** — one Memory Read (the command fetch) and Memory Writes for everything else, doorbells and MSI-X included.
6. **PI = CRC + LBA binding per block, checked at every hop** — the Reference Tag catches the mix-ups a checksum can't.
7. **Namespaces, multi-controller, dual-port** are the enterprise toolkit: multi-tenant carving, SR-IOV, and no-single-point-of-failure paths.
8. **Fabrics extends the same model across the network** — and NVMe/TCP made it affordable. The 2.x era added zoned and key-value semantics without touching the fundamentals.

---

## Key vocabulary

| 中文 | English |
|---|---|
| 提交隊列 (SQ) | Submission Queue |
| 完成隊列 (CQ) | Completion Queue |
| 門鈴寄存器 (DB) | Doorbell Register |
| 隊列深度 | queue depth |
| 環形隊列 | ring / circular queue |
| 頭部 / 尾部 | head / tail |
| 生產者 / 消費者 | producer / consumer |
| 取指 | fetch (a command) |
| 中斷 | interrupt |
| 命令集 | command set |
| 管理命令 | Admin command |
| 邏輯塊地址 (LBA) | Logical Block Address |
| 物理區域頁 (PRP) | Physical Region Page |
| 分散聚集列表 (SGL) | Scatter/Gather List |
| 描述符 | descriptor |
| 段 | segment |
| 位桶 | bit bucket |
| 端到端數據保護 | end-to-end data protection |
| 保護信息 (PI) | Protection Information |
| 元數據 | metadata |
| 循環冗餘校驗 (CRC) | Cyclic Redundancy Check |
| 參考標籤 | Reference Tag |
| 命名空間 (NS) | Namespace |
| 原子操作 | atomic operation |
| 雙端口 | dual port |
| 冗餘容錯 | redundancy / fault tolerance |
| 相位標籤 | Phase Tag |
| 遠程直接內存訪問 | RDMA |
| 發現服務 | discovery service |
| 多路徑 | multipath |

---

## Check yourself

1. Why did AHCI become the bottleneck for SSDs when it was fine for HDDs? Give AHCI's queue count and depth vs NVMe's.
2. Name the "three treasures" and say which two live in host memory and which lives on the SSD.
3. List the 8 steps of NVMe command processing in order.
4. In the producer/consumer model, who is the producer and consumer for an SQ, and for a CQ? Which doorbell does each side maintain, and why?
5. The host can only *write* doorbells, never read them. So how does the host learn (a) how far the SSD has consumed the SQ, and (b) where the new CQ tail is?
6. What's the fundamental difference between PRP and SGL, and which one can NVMe-oF use?
7. In the read trace, only two PCIe TLP types carry the entire NVMe transaction. Which two, and which step uses the Memory Read?
8. Name the three fields of Protection Information and what each protects against. Why is the Reference Tag needed on top of the CRC?
9. Why is a Namespace ID required on every I/O command? (Use the "Texas" intuition.)
10. What's the main purpose of a dual-port SSD, and what's the only form factor that provides it?
11. Why doesn't PCIe scale out for large flash pools, and what latency problem does putting NVMe SSDs behind iSCSI create?
12. **(Modern)** What did NVMe 2.0's "refactoring" do, and name the two non-block command sets it enabled.
13. **(Modern)** The book's Fabrics chapter focuses on RDMA, which needs special NICs. What transport added after the book removed that barrier, and why does it matter?
14. **(Modern)** Zone Append returns the written LBA in the completion instead of taking one in the command. What queue-depth problem does this solve?

---

??? info "📖 Book page map — for readers of 《深入淺出SSD》"

    This chapter follows Chapter 6 of《深入淺出SSD》(SSDFans, 2018), pp. 1–68;
    §6.9 is a post-2018 supplement and §6.10 covers 2nd-edition topics
    (their §9.10–9.12). Original figures by section:

    | Section | Book pages | Key figures/tables |
    |---|---|---|
    | 6.1 AHCI → NVMe | pp. 1–4 | — |
    | 6.2 Overview | pp. 4–13 | Fig 6-10 (8-step flow) |
    | 6.3 SQ/CQ/DB | pp. 13–23 | Figs 6-12…6-20 |
    | 6.4 PRP & SGL | pp. 23–32 | Figs 6-22…6-28, Table 6-4 |
    | 6.5 Trace | pp. 32–40 | Figs 6-31…6-39 |
    | 6.6 E2E protection | pp. 40–47 | Figs 6-41…6-49 |
    | 6.7 Namespaces | pp. 47–56 | Figs 6-52…6-58 |
    | 6.8 NVMe-oF | pp. 56–68 | Figs 6-61…6-63 |

*Next: [Chapter 7 — SSD Testing](ch7-testing.md). Protocol gives way to practice: how drives are actually validated — FIO, JEDEC endurance math, test equipment, and certification.*
