---
title: "Ch 5 — PCIe"
tags:
  - pcie
  - tlp
  - link-layer
source_anchor: "CH5 file, pp. 1–74"
---

# SSD Deep Dive — Chapter 5: PCIe
## English Study Companion

**Where we are:** Chapters 3–4 were about flash and the firmware that tames it. Now the book pivots completely: **PCIe** is the high-speed *interface* — the road between the host and the SSD. This chapter has nothing to do with flash physics; it's about how bits travel across a serial link: the topology, the layered protocol, the packet formats, and how a packet finds its destination. Chapter 5 runs pages 1–74 of your file (p. 75 is empty website comments).

**How to use this guide:** Section numbers match the book. Page references like *(p. 20, Fig 5-17)* point into your CH5 file so you can view the original diagram beside the explanation. The book leans on a few running analogies that genuinely help — highway lanes, phone-vs-walkie-talkie, and "getting dressed/undressed" for how packets are wrapped and unwrapped — and I've kept them. Because you asked for the Chapter-4 treatment, I've worked through the bandwidth and performance math, and added a **"Modern developments"** section at the end: the book stops at **PCIe 3.0** (noting 4.0 had just been announced in 2017), and PCIe has since advanced to **7.0** — with a major architectural change along the way that's worth knowing. Glossary and self-quiz at the very end.

**The chapter's shape:** 5.1 speed/why-PCIe. 5.2 topology (tree of RC/Switch/Endpoint). 5.3 the three-layer stack. 5.4–5.5 TLPs (the packets that carry your data) — types and structure. 5.6 config space and BARs (how devices get addressed). 5.7 routing (how a packet finds its target). 5.8 data-link layer (ACK/NAK, flow control). 5.9 physical layer (differential signaling, encoding). 5.10 resets. 5.11 payload-size tuning. 5.12 hot-plug (U.2). 5.13 performance-loss analysis. If your time is limited, **5.1, 5.2, 5.3, and 5.4** give you the mental model; the rest is depth.

---

## 5.1 Starting with speed — pp. 1–7 ⭐

??? example "🎬 Animate this — The SSD Calculator Bundle"

    This section's formulas as live sliders — move an input and watch the answer (and the curve) recompute.

    [Animation page](../animations/ssd-calculators.md) · [open full-screen ↗](../animations/files/ssd_calculators.html)

    <iframe src="../../animations/files/ssd_calculators.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The SSD Calculator Bundle"></iframe>


**Why PCIe for SSDs? Because it's fast — faster than SATA.** The chapter opens by building up the bandwidth numbers *(p. 1–2, Table 5-1)*.

**Lanes = highway lanes (p. 1–2, Figs 5-1/5-2).** A PCIe link's width is its number of **Lanes** (×1, ×2, ×4… up to ×32), exactly like a highway with 1, 2, or 4 lanes. A connection between two devices is a **Link**. Each Lane has *separate* send and receive wires, so data flows both directions **simultaneously** — the spec calls this **Dual-Simplex** (effectively full-duplex).

**PCIe vs SATA = phone vs walkie-talkie (p. 3).** SATA also has separate send/receive wires, but only *one direction* can transmit at a time — **half-duplex**. PCIe is a phone call (both talk at once); SATA is a walkie-talkie (one talks, the other only listens).

**The bandwidth math (p. 3–5) — worth understanding once.** The quoted bandwidth is *bidirectional* (read+write combined); halve it for one direction. PCIe is a serial bus, and the per-generation line rates and encodings are:

| Gen | Line rate | Encoding | Per-lane bidirectional | (per direction) |
|---|---|---|---|---|
| PCIe 1.0 | 2.5 GT/s | 8b/10b | 0.5 GB/s | 0.25 GB/s |
| PCIe 2.0 | 5 GT/s | 8b/10b | 1 GB/s | 0.5 GB/s |
| PCIe 3.0 | 8 GT/s | 128b/130b | ~2 GB/s | ~1 GB/s |

- **8b/10b encoding** (Gen1/2): every 8 data bits are sent as 10 bits on the wire (2 bits of overhead for DC balance + embedded clock). So Gen1 ×1 = (2.5 Gbps × 2 directions) ÷ 10 = **0.5 GB/s**. Multiply by lane count.
- **Gen3 broke the pattern:** instead of doubling the line rate to 10 GT/s, it went to 8 GT/s *but switched to 128b/130b encoding* (only 2 bits overhead per 128) — so effective bandwidth still doubled vs Gen2 despite the line rate not doubling. Gen3 ×1 = (8 Gbps × 2 × 128/130) ÷ 8 ≈ **2 GB/s**.
- **Key point:** the GB/s figures already account for encoding overhead, so don't subtract it again.

**More lanes = more speed, but more cost/space/power.** Theoretical max is PCIe 3.0 ×32 = **64 GB/s** ("a terrifying number"), but real PCIe SSDs use at most **×4** — e.g., **PCIe 3.0 ×4 = 8 GB/s bidirectional, 4 GB/s read or write** *(p. 4–5, Fig 5-4, Intel 750 datasheet)*.

**The IOPS ceiling — a great practical takeaway (p. 5).** At 4 GB/s per direction, a PCIe 3.0 ×4 link can move at most 4 GB ÷ 4 KB = **1M 4 KB IOPS**, ignoring protocol overhead. So **no SSD on this interface can exceed ~1000K IOPS — regardless of whether the media is flash or 3D XPoint.** The interface itself is the ceiling.

**Why serial beats parallel (p. 5–7, Figs 5-5).** PCI was *parallel* (32/64 bits per clock); PCIe is *serial* (1 bit per lane per clock) — yet PCIe is faster. Why? At high clock speeds, parallel buses hit two walls: **flight-time skew** (the receiver must wait for the *slowest* bit line, and this worsens with wire length) and **clock skew** (the clock signal's own phase drift). PCIe sidesteps both: it has **no separate clock wire** — the clock is *embedded* in the data stream via the encoding, and the receiver recovers it — so wire length and frequency stop being limits, and there's no external clock to skew. (The catch: with multiple lanes, you reintroduce a mild version of skew — the receiver waits for the slowest *lane* — but PCIe handles that internally.)

---

## 5.2 Topology — the tree — pp. 7–11 ⭐

**PCI was a shared bus** *(p. 7–8, Fig 5-6)*: many devices hung off one bus, taking turns — whoever wants to talk must first win control of the bus. **PCIe is a tree** *(p. 8–10, Figs 5-7 to 5-10)* with three kinds of nodes:

- **Root Complex (RC)** — the root of the tree; it *speaks for the CPU*, connecting the CPU to memory and to the whole PCIe system. Internally it implements an internal bus (Bus 0) and fans out PCIe Ports via internal bridges. The spec doesn't pin down exactly what's inside — you just need the role.
- **Switch** — a branch. It **expands ports** (like a USB hub when your laptop doesn't have enough USB sockets) and provides **routing/forwarding** for everything below it. One **Upstream Port** (toward the RC) and several **Downstream Ports** (toward devices). Switches can chain into other switches. Internally, a switch is also an internal bus with several bridges fanning out downstream ports.
- **Endpoint (EP)** — a leaf: the actual devices (PCIe SSD, NIC, GPU…) that implement some **Function**.

**Point-to-point, not shared (p. 10–11).** Unlike PCI's shared bus, PCIe is **point-to-point** — every device gets its *own* dedicated lane bandwidth, so it's faster and more efficient. In theory any two Endpoints could talk directly, but in practice they rarely do (different vendors' data formats differ), so almost all traffic is **Endpoint ↔ RC**, or Endpoint → RC → Endpoint. (There are also **Bridges** that convert PCIe↔PCI — ignore them, not the focus.)

---

## 5.3 The three-layer stack — pp. 11–16 ⭐⭐ *the core mental model*

??? example "🎬 Animate this — The Packet Dresser & ACK/NAK Lab"

    Dress a TLP layer by layer, then let the Jammer corrupt the wire and watch ACK/NAK recover.

    [Animation page](../animations/packet-dresser.md) · [open full-screen ↗](../animations/files/packet_dresser.html)

    <iframe src="../../animations/files/packet_dresser.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Packet Dresser & ACK/NAK Lab"></iframe>


Like most buses, PCIe is layered *(p. 11–12, Figs 5-11/5-12)*. Three layers, each serving the one above:

1. **Transaction Layer** — creates/parses **TLPs** (Transaction Layer Packets); handles flow control, QoS, transaction ordering. *This is where your actual data lives.*
2. **Data Link Layer** — creates/parses **DLLPs**; runs the **ACK/NAK** protocol (link-level error detection/correction), flow control, power management.
3. **Physical Layer** (logical + electrical sub-blocks) — the actual signal transmission: splits data across Lanes (**Stripe**) and reassembles (**De-stripe**), scrambles/de-scrambles (spread 0s and 1s evenly to reduce EMI), and does 8b/10b or 128b/130b encoding.

**The "getting dressed" analogy (p. 12–14, Figs 5-13/5-14) — this is the key intuition.** Data flows top-to-bottom, each layer wrapping the previous one like putting on clothes:
- Upper layer (command/NVMe) hands **Data** to the Transaction Layer.
- Transaction Layer adds a **Header** (front) + **ECRC** (back) → a **TLP**.
- Data Link Layer adds a **Sequence Number** (front) + **LCRC** (back).
- Physical Layer adds **Start** (front) + **End** (back), splits across lanes, scrambles, encodes, transmits.

The receiver reverses it ("getting undressed for bed"): Physical strips Start/End → Data Link checks Sequence Number + LCRC (if bad, request retransmit; if good, strip them) → Transaction checks ECRC (if bad, discard; if good, strip it and deliver the data). "Unlike PCI's data running around naked, PCIe's data wears clothes."

**Every RC, every Switch Port, and every Endpoint implements all three layers (p. 14–16, Figs 5-15/5-16).** So when RC talks to EP1 through a Switch, there are *multiple* dress/undress cycles: RC dresses the data → Switch upstream port undresses it to read the destination address → re-dresses it → sends to the right downstream port → that port undresses/re-dresses → delivers to EP1. **Why must a Switch (whose job is just forwarding) implement the Transaction Layer too?** Because the *destination address is inside the TLP* — without parsing that layer, it couldn't route.

---

## 5.4 TLP types — pp. 16–21 ⭐

The Transaction Layer generates **four** request types *(p. 17)*:

- **Memory** — access memory space (the mainstream traffic).
- **IO** — access IO space (legacy only; new PCIe devices are memory-mapped only — *ignore IO to reduce learning load*).
- **Configuration** — access config space; **always initiated by the RC**, mostly only during power-on enumeration. Important but not everyday traffic.
- **Message** — interrupts, errors, power management. This is *new* to PCIe: PCI carried these on separate **sideband** wires, but PCIe removed those wires and moved everything **in-band** as packets.

**Posted vs Non-Posted — the postal-mail metaphor (p. 17–18, Tables 5-2/5-3).** "Post" = mailing a letter: you drop it in the box and hope it arrives.
- **Posted** = no response expected. **Only Memory Write and Message are Posted.**
- **Non-Posted** = response required. Everything else (Config read/write, IO, and crucially **Memory Read**).
- **Why is Memory Write Posted?** Because not waiting for a reply lets the sender fire off the *next* write immediately → better write performance. The small risk of an unacknowledged failed write is covered by the Data Link Layer's ACK/NAK. **Why is Memory Read Non-Posted?** Obviously — a read with no data returned is useless; the return of data *is* the response.
- **Memorize just this:** *only Memory Write and Message are Posted; all else is Non-Posted.*

**Completion TLPs (p. 19–21, Figs 5-17/5-18, Table 5-4).** Every Non-Posted request gets a **Completion TLP** in reply. For a **Read**, the completion carries the requested **data** (called **CplD** = Completion with Data). For a **Write** (only Config Write remains), the completion carries just **status**, no data. So: **all TLPs = Request TLPs + Completion TLPs.**

- **Memory Read example (p. 19–20, Fig 5-17):** Device C generates one **MRd** TLP → travels up to RC → RC fetches from memory → returns data via **CplD**, back down to C. Note: a single TLP carries **at most 4 KB** of data, so reading 16 KB means RC sends **4 CplDs** — but C still sent only **1 MRd**.
- **Memory Write example (p. 20–21, Fig 5-18):** RC generates an **MWr** TLP (data inside) → through Switch → to Device B. Since MWr is Posted, B sends **no** completion (doing so would be "drawing legs on a snake"). Writing 16 KB = **4 MWr** TLPs.

---

## 5.5 TLP structure — pp. 21–27

Every TLP (request or completion) has the same shape *(p. 21, Fig 5-19)*: **Header** (mandatory), **Data payload** (optional — a Memory Read has none), and **ECRC** (optional end-to-end CRC). A TLP is born at the sender's Transaction Layer and dies at the receiver's Transaction Layer. *"An animal can lack hands and feet but not a head"* — every TLP must have a Header.

**Header fields (p. 22–24, Figs 5-20, Table 5-5).** A Header is **3DW or 4DW** (DW = doubleword = 4 bytes). You don't need to memorize every field, but the important ones:
- **Fmt** — whether the TLP carries data, and 3DW vs 4DW.
- **Type** — the TLP type (MRd, MWr, CfgRd, CfgWr, Msg, Cpl…).
- **TC (Traffic Class)** — priority, 0–7; higher = served first (this is the QoS knob).
- **TD** — set if ECRC is present.
- **EP** — marks "poisoned" (bad) data — stay away.
- **Length** — payload length in DW, 10 bits → max 1024 DW = **4 KB** (why a TLP maxes at 4 KB).

**Header size rules (p. 23–24):** Config and Completion TLPs → always **3DW**; Message → always **4DW**; Memory TLPs → **3DW if the address space is <4 GB, 4DW if >4 GB** (a 32-bit address fits in 1DW; a 64-bit address needs 2DW).

**Source and destination — how a TLP is addressed (p. 24–27, Figs 5-21 to 5-26).** Different TLP types address differently:
- **Memory TLP:** *destination* = the memory address (the device's space mapped into host memory); *source* = the **Requester ID**. Every device has a unique ID = **Bus + Device + Function (BDF)**.
- **Configuration TLP:** targets a device by **Bus + Device + Function**, with **Ext Reg + Register Number** as the offset into config space. Type 0 = to an Endpoint, Type 1 = to a Switch.
- **Message TLP:** always 4DW; a **Message Code** field says what kind (interrupt, error, power…).
- **Completion TLP:** the responder simply copies the requester's ID as the destination. Carries a **Completion Status** field (success or various errors).

---

## 5.6 Config space and BARs — pp. 28–37 ⭐ *how devices become addressable*

??? example "🎬 Animate this — The Enumeration & Routing Explorer"

    The BAR all-1s sizing trick and Base/Limit routing, played out on a live tree.

    [Animation page](../animations/enum-routing.md) · [open full-screen ↗](../animations/files/enum_routing.html)

    <iframe src="../../animations/files/enum_routing.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Enumeration & Routing Explorer"></iframe>


**Config space (p. 28–29, Figs 5-27/5-28).** Every PCIe device has a standardized **configuration space** — a set of registers whose layout is fixed by the spec (so any vendor's device is readable the same way). PCI's config space was 256 B (a 64 B Header + 192 B of Capabilities); **PCIe extended it to 4 KB**, keeping the first 256 B backward-compatible.

**The Config Header (p. 29–30, Fig 5-29).** The 64 B Header comes in **Type 0** (Endpoint) and **Type 1** (Switch). Read-only registers like **Device ID, Vendor ID, Class Code, Revision ID** let the device tell the host "I'm this vendor's device, this ID, this type (NIC/GPU/bridge)." The important part is the **BAR**.

**BARs — Base Address Registers (p. 30–34, Figs 5-30 to 5-35) — the key concept.** An Endpoint has up to **6 BARs**; a Switch has **2**. Here's the problem they solve: the **CPU can only directly access host memory (and IO) space, not PCIe devices.** So how does the CPU read/write a device's internal space?

The solution is the RC + **memory-mapping**:
- At power-on, the system maps each device's exposed internal space into **host memory address space** (a PCIe region, *not* DRAM).
- When the CPU accesses that mapped address, the **RC notices** it belongs to a device and generates the appropriate TLP to read/write the device.
- To read a device: RC fetches the data via TLP into host memory, then the CPU reads it from memory. To write: CPU stages data in memory, RC writes it to the device via TLP. So the CPU accesses devices *indirectly*, through the RC.

**How the mapping is set up (p. 32–34):** A device ships with each internal space's *size and attributes* baked into its BAR registers. At boot, system software:
1. Reads BAR0 (gets the device's initial value).
2. Writes all-1s to BAR0.
3. Reads it back — the **bits that stayed fixed** reveal the space's size and attributes (the low bits are read-only, vendor-fixed). E.g., if the low 12 bits didn't change, the space is 2¹² = **4 KB**; the lowest 4 bits encode attributes (IO vs memory map? 32- vs 64-bit? prefetchable?). *Prefetch matters:* some registers clear themselves when read, so their space must be non-prefetchable.
4. Finds a free region in host memory of that size and writes the assigned **base address** back to BAR0.
5. Repeats for BAR1…BAR5.

**BDF and the enumeration math (p. 35–37, Figs 5-36/5-37).** A device may have multiple **Functions** (e.g., act as both a disk and a NIC), each with its own config space. The addressing unit is the **Function**, identified by **BDF**. The limits: up to **256 buses × 32 devices × 8 functions**, each with **4 KB** config space → the config space maps to **256 × 32 × 8 × 4 KB = 256 MB** of host memory address region (again, not DRAM). To read a config space, software accesses the corresponding mapped address; the RC sees it's a config-mapped address and generates a **Config Read TLP**. (You *can't* address config space via a BAR — the BAR lives *inside* config space, so you'd need to read config space first.) **Only the RC may initiate config access.**

---

## 5.7 TLP routing — pp. 37–47 ⭐

How does a TLP reach its destination? **Three routing methods** *(p. 37–38, Table 5-6)*: **address routing**, **ID routing (BDF)**, and **implicit routing**.

**1. Address routing (p. 38–41, Figs 5-39 to 5-42).** Used by Memory (and IO) TLPs. Routing info lives in the Switch's config space. A Switch has an upstream port and several downstream ports, each port being a **Bridge** with its own config describing the address range below it, via **Memory Base** and **Memory Limit** registers. The logic:
- **An Endpoint** compares the TLP's address against its own BARs — if it falls inside, accept; else ignore.
- **A Switch upstream port** receiving a downstream-bound TLP: first checks its own BARs (accept if matched); else checks whether the address falls within a downstream port's [Memory Base, Memory Limit] range — if so, **forward** to that port; else reject.
- **For a TLP traveling upstream** (toward RC): if the address matches the port's own BARs, accept; if it falls in a downstream range, **reject** (it shouldn't be going up); otherwise **pass it upstream**.

**2. ID routing (p. 42–45, Figs 5-43 to 5-46).** Used by Configuration and Completion TLPs (and Messages sometimes). Routes by **BDF**. The TLP Header carries the target BDF. An Endpoint compares its own ID; matches → accept, else reject. A Switch uses three registers in *each port's* config (**Primary / Secondary / Subordinate Bus Number**): the **Primary Bus** is the bus on the upstream side of a port, the **Secondary Bus** is the bus directly below it, and the **Subordinate Bus** is the highest-numbered bus anywhere below it. On receiving an ID-routed TLP: if the BDF matches the switch's own ID, accept; else if the TLP's Bus Number falls between the port's **Secondary and Subordinate** Bus Numbers, forward to that downstream port; else reject.

**3. Implicit routing (p. 45–47, Figs 5-47/5-48).** Only **Message TLPs** support it. Some Messages simply go to/from the RC, so there's no need to spell out an address or ID — the routing is *implied*. The Type field's low 3 bits (rrr) encode the routing: e.g., an Endpoint accepts a Message if it's an RC broadcast (011b) or terminates at it (100b); a Switch receiving an RC broadcast copies it to *every* downstream port. Messages can *also* use address or ID routing, but implicit is the main mode.

---

## 5.8 Data Link Layer — pp. 47–54 ⭐

??? example "🎬 Animate this — The Packet Dresser & ACK/NAK Lab"

    Dress a TLP layer by layer, then let the Jammer corrupt the wire and watch ACK/NAK recover.

    [Animation page](../animations/packet-dresser.md) · [open full-screen ↗](../animations/files/packet_dresser.html)

    <iframe src="../../animations/files/packet_dresser.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The Packet Dresser & ACK/NAK Lab"></iframe>


A TLP is born and dies at the Transaction Layer, but between sender and receiver it passes *through* the Data Link and Physical Layers on each side. The Data Link Layer's jobs *(p. 47–48)*:
- **Sender:** add **Sequence Number** + **LCRC** to each TLP, hand to Physical Layer.
- **Receiver:** check CRC and sequence number; if bad, reject (don't pass up) and tell the sender to retransmit; if good, strip them, pass to Transaction Layer, and acknowledge.

So the Data Link Layer guarantees reliable TLP delivery via a **handshake (ACK/NAK)** and **retransmission (Retry)**. It uses its own packets, **DLLPs**, which — unlike TLPs — travel **only between adjacent ports** (one hop), so DLLPs need no routing info *(p. 48–50, Figs 5-49/5-50, Table 5-7)*. A TLP can cross many Switches; a DLLP goes only RC↔Switch, or Switch-port↔Switch-port, or Switch↔EP. Four DLLP types: **ACK/NAK**, **flow-control**, **power-management**, and **vendor-specific**. A DLLP is **6 bytes** (8 on the wire with framing).

**ACK/NAK in detail (p. 50–53, Figs 5-51 to 5-53) — the reliability mechanism.** The sender keeps each transmitted TLP (with its sequence number + LCRC) in a **Replay Buffer** until acknowledged. The receiver checks each incoming TLP:
- **LCRC fails** → send **NAK** with the last-good sequence number; the sender clears the acknowledged ones from the Replay Buffer and **retransmits** the rest. (Transmission errors are usually transient, so a retransmit almost always succeeds.)
- **LCRC passes** → check the sequence number:
  - *Expected number* → maybe send an **ACK** (to cut DLLP traffic, an ACK may cover *several* TLPs, not one each); sender clears acknowledged TLPs from the Replay Buffer.
  - *Higher than expected* (e.g., got 13, wanted 12) → a TLP was **dropped**; send NAK with the last-good number; sender retransmits from the gap.
  - *Lower than expected* (e.g., got 10, wanted 12) → a **duplicate** (the sender's timeout re-sent buffered TLPs because an ACK was late); the receiver **silently discards** the duplicate and ACKs.

Only correctly-received TLPs get their sequence number + LCRC stripped and passed up. (If a *DLLP* itself is corrupted, the receiver discards it and recovers via the next good DLLP.)

**Flow control (p. 53–54, Figs 5-54/5-55) — Credit-based.** A sender must not overwhelm a slow receiver. PCIe uses **Credits**: the receiver periodically advertises, via flow-control DLLPs, how much TLP receive-buffer space it has; the sender only transmits a TLP if the receiver has room, else holds it. Note: **flow control governs TLPs, not DLLPs** — DLLPs are tiny (6 B) and un-flow-controlled (if DLLPs needed flow control, *who would flow-control the flow-control packets?*).

Power-management DLLPs are covered in the book's Chapter 8.

---

## 5.9 Physical Layer — pp. 54–59

The bottom layer — "the errand runner" that actually moves the bits. Two sub-blocks *(p. 54–55)*:

**Electrical block — the one thing to remember: "serial bus, differential signaling."** PCIe uses **differential signaling** — the *difference* between two wires' voltages encodes 0 or 1. Versus single-ended, differential is far more **noise-immune** (interference hits both wires nearly equally, so the difference is preserved), enabling higher speeds. Example: if diff > 0 means 1 and diff < 0 means 0, a common-mode noise spike on both wires cancels out — whereas a single-ended 0.8 V signal bumped to 1.5 V by noise would flip 0→1. The book's advice for SSD firmware developers: just remember *serial + differential* is why PCIe is fast; leave the rest to the spec.

**Logical block — the send path (p. 55–58, Figs 5-57/5-58):**
1. Take a TLP/DLLP from the Data Link Layer into the **Tx Buffer**.
2. Add **Start/End** framing (Gen3 has no End) so the receiver can delimit packets.
3. **Byte Stripping** — distribute the bytes across the Lanes (serial-to-parallel-ish).
4. **Scramble** each lane — XOR with a pseudo-random sequence to reduce EMI.
5. **Encode** — 8b/10b (Gen1/2) or 128b/130b (Gen3). This IBM-patented encoding balances 0s and 1s (DC balance) and **embeds the clock** so PCIe needs no separate clock wire.
6. Parallel-to-serial, transmit. The receiver does the reverse.

**Ordered Sets (OS) (p. 58–59, Table 5-8).** The Physical Layer has its *own* packet type too: **Ordered Sets**, used for **link management** — link training, changing link power states, etc. (TLPs carry app/command data; DLLPs handle ACK/flow/power; OSs manage the physical link.)

---

## 5.10 PCIe Reset — pp. 59–67

PCIe has a thicket of reset terms; the trick is the hierarchy *(p. 59–60, Table 5-9)*:

- **Conventional Reset** splits into:
  - **Fundamental Reset** (hardware-controlled; reinitializes almost all internal registers/state/state-machines):
    - **Cold Reset** — power the device's Vcc off/on (Vaux stays).
    - **Warm Reset** — system-triggered while Vcc stays on (spec doesn't define exactly how; left to the system).
  - **Non-Fundamental Reset** = **Hot Reset** — signaled *in-band* via TS1 ordered sets.
- **Function Level Reset (FLR)** — resets just *one* Function.

**Sticky bits (p. 60).** Some register fields are **Sticky** — no reset (not even Cold/Warm) clears them. These are invaluable for **debugging**: they preserve error state across a link reset so firmware/software can inspect what went wrong.

**How Fundamental Reset is triggered on an SSD (p. 61–62, Fig 5-59):** the system asserts **PERST#** (PCIe Reset). On power-up, once main power is stable a "Power Good" signal fires, and the chipset asserts PERST# to the SSD; the Power-Good transition on reboot drives PERST# assert/de-assert = a Cold Reset. A device that *doesn't* use PERST# must self-trigger a Fundamental Reset at power-on (e.g., on detecting supply voltage).

**Hot Reset (p. 62–63, Figs 5-60/5-61):** triggered by two consecutive TS1s with the Hot Reset bit set; after a 2 ms timeout the link's state machine (**LTSSM**) walks L0 → Recovery → Hot Reset → Detect, resetting everything except sticky bits. Software triggers it by writing 1 to the RC bridge's **Secondary Bus Reset** bit (then clearing it to bring the link back). There's also a **Link Disable** bit to shut a link down until re-enabled.

**FLR (p. 63–67, Figs 5-63 to 5-65).** *"A PCIe Link is a road; the Functions are different cars — if one car breaks down, don't reset the whole road, just fix that car."* FLR resets one Function's internal state/registers, **except** sticky bits, HwInit registers (loaded from EEPROM), and a few special registers (Captured Power, ASPM Control, Max Payload Size, Virtual Channel); it doesn't change the LTSSM state. **Timing:** FLR must complete within **100 ms**. The danger: pending **CplDs** from a *previous* transaction could get misdelivered to a *new* one after FLR → **data corruption**. So before FLR: ensure no other software accesses the Function, clear the Command Register, poll the **Transactions Pending** bit until clear (or wait out the completion timeout, else 100 ms), then do FLR and wait 100 ms before reconfiguring. On reset *exit*: link training must begin within 20 ms; software should wait ≥100 ms before sending Config Requests; if the device isn't ready it replies **CRS** (Configuration Retry Status); the device gets up to **1 second** (inherited from PCI) to become fully operational or the system declares it dead.

---

## 5.11 Max Payload Size & Max Read Request Size — pp. 67–68 ⭐ *a practical tuning lever*

Both live in the **Device Control Register** *(p. 67, Fig 5-66)*.

**Max Payload Size (MPS)** — the largest data length one TLP may carry. The spec allows up to 4 KB, **but every device on the path must use the *same* MPS, and it can't exceed any device's capability** — so the highest-capable device must *stoop* to the lowest. Plug a fancy SSD into an ancient motherboard with MPS=128 B, and your big payload is wasted. MPS is negotiated at enumeration: each device advertises its capability in the Device Capability Register; the OS driver picks the **lowest** and writes it to everyone's Device Control Register.

**Max Read Request Size** — the largest size of a single Memory Read (up to 4 KB). It **can exceed MPS**: a 512 B read request to an MPS=128 B SSD is answered with 4×128 B CplDs. The OS uses this to **balance throughput** across multiple SSDs so no one drive hogs the (e.g., 40-lane) system bandwidth. It also affects performance: too small a read request means the same data needs *more* request TLPs — and read-request TLPs carry no payload, so they're pure overhead. Example: transferring 64 KB with Read Request=128 B needs **512** read TLPs — a lot of overhead. So set it larger for big transfers.

---

## 5.12 PCIe SSD hot-plug — pp. 68–70

**Why it became necessary (p. 68–69).** Early PCIe SSDs (pioneered by Fusion-IO) were **add-in flash cards** used as data cache. But cards have limits: few PCIe slots, capacity limited by slot power, overheating/crash risk, and — critically — **no hot-plug**. Replacing a failed card meant stopping the service, powering down, opening the chassis — unacceptable at data-center scale.

**The fix: U.2 (SFF-8639) (p. 69–70, Fig 5-67).** A 2.5″-drive-style form factor you can **hot-swap from the server front panel**, like a SATA/SAS disk. Now servers can pack many U.2 SSDs (some chassis take 24 pure U.2 bays), store *critical* data (not just cache), build RAID across drives, and swap a failed one — identified by a front-panel indicator light — **without downtime or data loss**. Fewer high-density SSD servers replace many HDD-array servers, with far lower power and cooling, which matters as rent/land costs rise.

**Hot-plug implementation (p. 70).** Traditional SATA/SAS hot-plug is managed by the HBA; but PCIe SSDs connect *directly to the CPU's PCIe controller*, so the **driver** must manage hot-plug. It needs coordinated support from: the **SSD** (hardware to avoid inrush-current damage on insertion; controller detection of removal to avoid data loss), the **server backplane** (vendor must confirm U.2 hot-plug support), the **OS/BIOS** (which one handles it?), and the **driver** (heavily tested for hot-plug stability). Safe removal sequence: (1) stop all access to the target SSD, (2) `umount` its filesystems, (3) unload the driver / remove the block device if required, (4) pull the drive.

---

## 5.13 PCIe link performance-loss analysis — pp. 70–74 ⭐ *why you never get the theoretical number*

??? example "🎬 Animate this — The SSD Calculator Bundle"

    This section's formulas as live sliders — move an input and watch the answer (and the curve) recompute.

    [Animation page](../animations/ssd-calculators.md) · [open full-screen ↗](../animations/files/ssd_calculators.html)

    <iframe src="../../animations/files/ssd_calculators.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="The SSD Calculator Bundle"></iframe>


Six sources of overhead between raw link rate and real throughput:

1. **Encode/Decode (p. 71).** 8b/10b costs **20%** (Gen1/2). Gen3's 128b/130b makes this **negligible**.
2. **TLP packet overhead (p. 71).** Every TLP wraps the payload in Header + ECRC (Transaction), Sequence + LCRC (Data Link), Start + End (Physical) — roughly **20–30 bytes** of overhead per TLP.
3. **Traffic overhead (p. 71–72).** Periodic **SKP (Skip)** ordered sets for clock-drift compensation (like SATA's ALIGN) — 4 B (Gen1/2) or 16 B (Gen3), sent every ~1538 symbol-times, only *between* TLPs.
4. **Link protocol overhead (p. 72).** The ACK/NAK machinery itself costs bandwidth. Batching ACKs (one ACK per several TLPs) helps, but you can't batch too much — the Replay Buffer is finite, and once full, no new TLPs can send.
5. **Flow control (p. 72–73).** Periodic **UpdateFC** DLLPs consume bandwidth; sending them less often helps but needs a bigger receiver buffer.
6. **System parameters (p. 73).** MPS, Max Read Request Size, and **RCB (Read Completion Boundary)** — the last explains why a read request often comes back as many 64 B or 128 B CplDs: the RC may split a completion on **address-aligned** 64/128 B boundaries.

**The worked calculation (p. 73–74) — follow it once.** Given **200 MemWr TLPs, MPS=128, PCIe Gen1 ×8**:
- Symbol time: 2.5 Gbps → 1 byte takes **4 ns**; with 8 lanes, 8 bytes per 4 ns.
- TLP transfer time: (128 B payload + 20 B overhead) ÷ 8 B/clock × 4 ns = **74 ns**.
- DLLP transfer time: 8 B ÷ 8 × 4 ns = **4 ns**.
- Assume 1 ACK per 5 TLPs (→40 ACKs) and 1 FC Update per 4 TLPs (→50).
- Total data = 200 × 128 = **25,600 B**. Total time = 200×74 + 40×4 + 50×4 = **15,160 ns**.
- **Throughput = 25,600 B ÷ 15,160 ns ≈ 1689 MB/s.** Bumping **MPS to 512 B** raises it to **1912 MB/s** — "the old SATA SSD can retire." (For MemRd, it's similar but the CplD payload size is subject to RCB.)

---

## 📌 Modern developments (post-2018 supplement)

*The book stops at PCIe 3.0 and mentions 4.0 was "just released in 2017." Since then PCIe has advanced four generations to 7.0, with one major architectural break worth understanding. This section is drawn from current PCI-SIG and industry sources, attributed inline; it's not in your book.*

**The generation ladder as of 2026.** PCI-SIG has held to its "double the bandwidth every ~3 years" cadence:

| Gen | Year (spec) | Line rate | Signaling / encoding | Per-lane (per direction) | ×4 SSD (per direction) |
|---|---|---|---|---|---|
| 3.0 | 2010 | 8 GT/s | NRZ, 128b/130b | ~1 GB/s | ~4 GB/s *(book's ceiling)* |
| 4.0 | 2017 | 16 GT/s | NRZ, 128b/130b | ~2 GB/s | ~8 GB/s |
| 5.0 | 2019 | 32 GT/s | NRZ, 128b/130b | ~4 GB/s | ~16 GB/s |
| 6.0 | 2022 | 64 GT/s | **PAM4 + FLIT + FEC** | ~8 GB/s | ~32 GB/s |
| 7.0 | **2025** | 128 GT/s | PAM4 + FLIT + FEC | ~16 GB/s | ~64 GB/s |

<cite index="22-1">PCI-SIG officially released the PCIe 7.0 specification to members on June 11, 2025, reaching 128.0 GT/s</cite>, and <cite index="21-1">work on PCIe 8.0 has already begun, continuing the pace of doubling bandwidth every three years</cite>. <cite index="21-1">PCIe 7.0 delivers up to 512 GB/s of bi-directional throughput in a full ×16 configuration.</cite>

**The big architectural break — PCIe 6.0 (this is the part worth understanding).** Everything the book taught about encoding assumes **NRZ** signaling (two voltage levels = 1 bit per symbol) with **128b/130b** line encoding. Gens 4 and 5 just doubled the NRZ clock, keeping the book's model intact. But **NRZ ran out of headroom** — you can't keep doubling the frequency on copper forever. So PCIe 6.0 made three coordinated changes that supersede parts of §5.1 and §5.9:

- **PAM4 signaling** replaces NRZ. <cite index="24-1">PAM4 (Pulse Amplitude Modulation, 4 levels) encodes two bits per clock cycle, effectively doubling the data rate versus the NRZ signaling used in PCIe 4.0 and 5.0</cite> — so the line rate doubled (32→64 GT/s) *without* doubling the clock frequency. (Four voltage levels are more noise-sensitive, which is why the next two changes were needed.)
- **FLIT-based encoding** replaces the 128b/130b packet framing. <cite index="21-1">Introduced in PCIe 6.0, FLIT (flow control unit) encoding packages data in fixed-size units rather than variable-size packets.</cite> This changes the low-level picture from §5.3/§5.5: at Gen6+, the Start/End-framed variable TLP-on-the-wire model gives way to fixed-size flits.
- **FEC (Forward Error Correction)** is added. Because PAM4 has a higher raw error rate, a lightweight FEC is layered in to fix errors inline — complementing (not replacing) the ACK/NAK retransmission of §5.8. The design goal was low added latency.

So if you're reasoning about a *modern* Gen5 SSD, the book's model is still exactly right (NRZ, 128b/130b). For Gen6+, remember the three-part shift: **PAM4 + FLIT + FEC**.

**Where real SSDs are (2024–2026).** The interface ceiling the book computed (~1M IOPS, ~4 GB/s at Gen3 ×4) has moved up sharply:
- **Gen4 ×4** consumer SSDs run ~7–7.5 GB/s (mainstream today).
- **Gen5 ×4** SSDs run ~14 GB/s; <cite index="23-1">PCIe 5.0 SSDs deliver around 14.5 GB/s</cite>, and Gen5 controllers like Phison's E28 are the current high-end.
- **Gen6** is in demonstration/early enterprise: <cite index="23-1">at FMS 2024 Micron demonstrated a PCIe 6.0 SSD exceeding 26 GB/s, and interoperability demos have reached about 27 GB/s — nearly double PCIe 5.0</cite>.
- **Gen7** products are years out. <cite index="24-1">Even with the 7.0 spec finalized, PCIe 7.0 SSDs and GPUs are not expected on the market soon</cite> — the industry is still mid-transition to 6.0. The 7.0 spec is driven primarily by **AI/ML, hyperscale data centers, and 800G networking**, not consumer needs.

**Recompute the IOPS ceiling for a modern drive.** Using the book's own method: a **Gen5 ×4** link at ~14 GB/s per direction gives ~14 GB ÷ 4 KB ≈ **3.4M** 4 KB IOPS as the interface ceiling — versus the ~1M the book derived for Gen3 ×4. The lesson is unchanged: *the interface, not the flash, often sets the IOPS ceiling* — the number has just grown with each generation.

**One more note — U.2 is being displaced.** The book presents U.2 (§5.12) as the emerging hot-plug enterprise form factor. In current data centers, U.2 is increasingly giving way to **E1.S and E1.L (the EDSFF "ruler" formats)**, purpose-designed for NVMe density, hot-plug, and thermals in modern servers — the same hot-plug motivation the book describes, evolved into a newer physical standard. (Everything §5.12 says about *why* hot-plug matters still holds; only the connector has moved on.)

---

## Key vocabulary — for decoding the original figures

| 中文 | English |
|---|---|
| 通道 (Lane) | lane |
| 鏈路 (Link) | link |
| 雙單工 / 全雙工 / 半雙工 | dual-simplex / full-duplex / half-duplex |
| 串行 / 並行總線 | serial / parallel bus |
| 差分信號 | differential signaling |
| 帶寬 | bandwidth |
| 拓撲結構 | topology |
| 樹形結構 | tree structure |
| 根複合體 (RC) | Root Complex |
| 交換機 (Switch) | switch |
| 端點 (Endpoint) | endpoint |
| 上游 / 下游端口 | upstream / downstream port |
| 點到點 | point-to-point |
| 分層結構 | layered structure |
| 事務層 | Transaction Layer |
| 數據鏈路層 | Data Link Layer |
| 物理層 | Physical Layer |
| 數據包 | packet |
| 有效載荷 | payload |
| 序列號 | sequence number |
| 重傳 | retransmission (retry) |
| 流量控制 / 流控 | flow control |
| 配置空間 | configuration space |
| 基地址寄存器 (BAR) | Base Address Register |
| 內存映射 | memory mapping |
| 枚舉 | enumeration |
| 路由 | routing |
| 隱式路由 | implicit routing |
| 邊帶信號 | sideband signal |
| 帶內 | in-band |
| 加擾 / 去擾 | scramble / de-scramble |
| 編碼 / 解碼 | encode / decode |
| 熱插拔 | hot-plug |
| 性能損耗 | performance loss |

---

## Check yourself

1. Why is PCIe called "Express," and what fundamental physical-transmission difference lets serial PCIe beat parallel PCI at high speed? Name the two skew problems parallel buses hit.
2. PCIe 3.0 ×4 gives 4 GB/s per direction. Compute the theoretical 4 KB IOPS ceiling, and explain why the underlying media (flash vs 3D XPoint) can't change it.
3. Name the three PCIe layers top-to-bottom, and the packet type each one generates.
4. Which two TLP types are Posted, and what's the performance reason Memory Write is Posted?
5. A device needs to read 16 KB from host memory. How many request TLPs does it send, and how many completion TLPs come back? Why the asymmetry?
6. What does a BAR do, and walk through how system software discovers a device's memory-space size at boot (the write-all-1s trick).
7. What are the three TLP routing methods, and which method does each of Memory / Configuration / Message TLPs use?
8. In ACK/NAK, what is the Replay Buffer for, and what happens when the receiver gets a TLP with a *lower*-than-expected sequence number?
9. Why does flow control apply to TLPs but not DLLPs?
10. MPS must be identical across all devices on a path, and no higher than the weakest device. What practical failure does this cause when you put a fast SSD in an old motherboard?
11. Why does a PCIe SSD's hot-plug have to be managed by the driver, unlike a SATA/SAS disk?
12. **(Modern)** PCIe 6.0 made three coordinated changes to keep scaling past NRZ's limits. Name all three, and say which one directly doubled the data rate without doubling the clock.
13. **(Modern)** Recompute the interface IOPS ceiling for a Gen5 ×4 SSD (~14 GB/s per direction), and state the general lesson.

---

*Next up: Chapter 6 — NVMe. PCIe is the road; NVMe is the traffic system built on top of it — the command protocol (queues, doorbells, PRP/SGL) that lets the host and SSD actually talk. This is where the interface and the SSD's front end finally meet.*
