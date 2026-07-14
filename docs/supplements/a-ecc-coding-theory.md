---
title: "Supp A — ECC Coding Theory"
tags:
  - ecc
  - bch
  - ldpc
  - soft-decision
  - patents
source_anchor: "2nd-edition Ch 7 topics, reconstructed"
---

# Supplement A — ECC Coding Theory

The core chapters treated error correction *conceptually*: [Chapter 3](../core/ch3-nand-flash.md#343-ecc-error-correcting-codes) showed the escalation Hamming → BCH → LDPC, why denser NAND needs stronger codes, and how soft-decision LDPC became the production standard. This supplement supplies the *mathematics underneath* — reconstructed from standard coding-theory references (the book's 2nd edition devotes a chapter to this material), with every concept worked as a concrete numerical example you can trace by hand and check against the [BCH & LDPC animation](../animations/ecc-bch-ldpc.md).

One note on the 🔬 marks: LDPC decoding is among the most **patent-active** areas in the entire SSD stack — decoder variants, LLR-generation schemes, and soft-read strategies are filed constantly. For readers doing patent or literature research, 🔬 flags the areas where filings concentrate; understanding the math here is what lets you *read* those patents instead of bouncing off them.

!!! abstract "In this supplement"
    - **The framing** — storage as a communication problem: signal, noise, channel (§A.1–A.2)
    - **The foundations** ⭐⭐ — Hamming distance, parity, the G and H matrices, syndromes — with Hamming(7,4) worked by hand (§A.3)
    - **LDPC** ⭐⭐ — sparse matrices and the Tanner-graph picture (§A.4); bit-flipping and sum-product decoding, both worked (§A.5)
    - **Encoding** — why LDPC's weak spot is manageable: QC-LDPC (§A.6)
    - **Inside the drive** ⭐⭐ — hard vs soft reads, LLRs from multiple strobes, the escalation ladder (§A.7)
    - **The modern landscape** — min-sum variants, LLR optimization, and where the patents cluster (§A.8)

    Short on time? §A.3 and §A.5 are the core.

---

## A.1 Signal and noise: the framing ⭐

Everything about ECC starts from one reframe: **storing data in flash is a communication problem.** Writing a bit and reading it later is exactly like transmitting it through a noisy channel — the "channel" being the flash cell *over time*. [Chapter 3](../core/ch3-nand-flash.md#331-the-five-problems-a-catalog-to-know-cold) catalogued the noise: P/E wear, read disturb, program disturb, cell coupling, charge leakage. Each nudges a cell's threshold voltage; a big enough nudge and a 0 reads as 1 — a **bit flip**.

So the cell is a noisy channel, the raw flip probability is the **RBER** of [Chapter 1](../core/ch1-overview.md#154-data-reliability), and ECC's job is to add structured **redundancy** so the original data survives some flips — driving the user-visible **UBER** far below the raw rate. The whole field is one optimization: maximum correction power for minimum redundancy.

## A.2 The communication-system model

The standard model maps directly onto an SSD:

```
  data          codeword         noisy codeword      corrected data
   u    ─────►    c     ─────►      r = c ⊕ e   ─────►     û
       ENCODER        CHANNEL                   DECODER
      (add parity)   (flash: adds              (use parity to
                      error vector e)           find & fix e)
```

- **u** — the k user bits. **Encoder** — produces an n-bit **codeword c** (n > k); the extra n−k bits are **parity**.
- **Channel** — the flash, which XORs in an **error vector e**: the read-back word is r = c ⊕ e.
- **Decoder** — uses the parity structure to deduce e and recover û.

Two ratios rule everything:

- **Code rate R = k/n** — the fraction that's real data. Higher rate = less overhead, weaker protection. In flash terms, parity lives in the page's **spare area** ([Ch 3 §3.4.3](../core/ch3-nand-flash.md#343-ecc-error-correcting-codes)), so spare-area size caps correction strength.
- **Correction capability t** — flips fixable per codeword.

The game: **maximize t at a given R.** BCH and LDPC are two answers.

---

## A.3 The foundations ⭐⭐

### A.3.1 Hamming distance — the concept everything rests on

The **Hamming distance** between two codewords = the number of positions where they differ (`10110` vs `10011` → positions 3 and 4 → distance 2; equivalently, the count of 1s in their XOR).

A code's **minimum distance d\_min** — the smallest distance between any two valid codewords — single-handedly determines its power:

- **Detection:** up to **d\_min − 1** errors (fewer flips can't accidentally land on another valid codeword).
- **Correction:** up to **t = ⌊(d\_min − 1)/2⌋** errors.

**The geometric picture — this is the "aha":** every n-bit word is a point in space; valid codewords are scattered among them. Draw a ball of radius t around each codeword. If d\_min ≥ 2t + 1, the balls don't overlap — so any received word with ≤ t flips falls inside *exactly one* ball, and decoding is just snapping to the nearest codeword. Designing a good code = **packing codewords far apart** while keeping enough of them to carry data. Everything that follows — parity matrices, BCH, LDPC — is machinery for buying large d\_min cheaply.

### A.3.2 Parity: the cornerstone

??? example "🎬 Animate this — How ECC finds and fixes a bit — Hamming visualizer"

    Flip a bit and watch the parity checks announce its location — the syndrome idea made tangible.

    [Animation page](../animations/ecc-bit-correction.md) · [open full-screen ↗](../animations/files/ecc_bit_correction.html)

    <iframe src="../../animations/files/ecc_bit_correction.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="How ECC finds and fixes a bit — Hamming visualizer"></iframe>


The simplest code: **one parity bit** — append the bit that makes the total count of 1s even. Data `1011` (three 1s) → codeword `10111`. Any single flip makes the parity odd → detected. But d\_min = 2, so t = ⌊1/2⌋ = 0: you know *a* bit flipped, never *which* — and two flips cancel invisibly.

The leap to real codes: use **several parity bits, each over a different, overlapping subset** of the data. Then the *pattern* of failed checks pinpoints the flipped bit — correction, not just detection. The machinery for expressing this is two matrices.

### A.3.3 The generator matrix G and parity-check matrix H ⭐⭐

A **linear block code** is defined over GF(2) — binary arithmetic where + is XOR — by:

**The generator matrix G (k × n)**, which encodes: **c = u·G** (mod 2). In **systematic form** G = [I\_k | P]: an identity block (the first k codeword bits *are* the data) followed by the parity-generating block P.

**The parity-check matrix H ((n−k) × n)**, which verifies: **H·cᵀ = 0** for every valid codeword. Given G = [I\_k | P], the matching H = [Pᵀ | I\_{n−k}]. Each *row* of H is one parity equation: "these bits must XOR to zero."

**The syndrome — how errors announce themselves.** For a received r = c ⊕ e:

```
s = H·rᵀ = H·(c ⊕ e)ᵀ = H·cᵀ ⊕ H·eᵀ = 0 ⊕ H·eᵀ = H·eᵀ
```

**The syndrome depends only on the error, never on the data.** s = 0 → clean. s ≠ 0 → for a single-bit error, **s equals the column of H at the flipped position** — look up the matching column, flip that bit back, done.

!!! example "Worked example — Hamming(7,4), traced by hand"
    k = 4 data bits, n = 7, three parity bits, rate 4/7, d\_min = 3 → corrects t = 1.

    ```
         ┌ 1 0 0 0 │ 1 1 0 ┐            ┌ 1 1 0 1 │ 1 0 0 ┐
    G =  │ 0 1 0 0 │ 1 0 1 │       H =  │ 1 0 1 1 │ 0 1 0 │
         │ 0 0 1 0 │ 0 1 1 │            └ 0 1 1 1 │ 0 0 1 ┘
         └ 0 0 0 1 │ 1 1 1 ┘
    ```

    **Encode** u = [1 0 1 1]: bits 1–4 = the data; bit 5 = 1⊕0⊕0⊕1 = **0**; bit 6 = 1⊕0⊕1⊕1 = **1**; bit 7 = 0⊕0⊕1⊕1 = **0** → **c = `1011 010`** (and H·cᵀ = 0 ✓).

    **Channel flips bit 3** → r = `10`**`0`**`1 010`.

    **Syndrome** s = H·rᵀ: row 1 = 1⊕1 = **0**; row 2 = 1⊕1⊕1 = **1**; row 3 = 1 = **1** → **s = [0,1,1]**.

    **Locate:** which column of H reads [0,1,1] top-to-bottom? **Column 3.** Flip bit 3 → `1011010` → data bits 1–4 = **1011** ✓ recovered.

    That's the entire mechanism of linear block codes. (The Hamming visualizer above runs exactly this loop interactively.)

### A.3.4 Where BCH fits

**BCH codes** (Bose–Chaudhuri–Hocquenghem) generalize Hamming to **multiple** errors: cyclic linear codes built over the finite field **GF(2^m)**, with H constructed from powers of a primitive element α so the code has a *designed* minimum distance for a chosen t. Decoding is **algebraic and deterministic**: from the syndrome, build the **error-locator polynomial** (Berlekamp–Massey), find its roots (Chien search) to locate the errors, flip them. It is **hard-decision**: bits in, and either success (≤ t errors) or declared failure (> t).

BCH's ceiling — and why NAND outgrew it: more correction needs rapidly more parity and hardware, and **BCH cannot use soft information.** It knows "this bit is 0," never "this bit is *probably* 0 but I'm unsure." As TLC/QLC RBER climbed, that discarded confidence became unaffordable. Enter LDPC.

---

## A.4 LDPC and the Tanner graph ⭐⭐

### A.4.1 What LDPC is

An **LDPC code** is *also* just a linear block code with a parity-check matrix H — with one special property: **H is sparse** ("low-density": a handful of 1s per row and column, regardless of code length). That single structural choice is the entire secret — it's what makes near-optimal **iterative, soft-decision decoding** computationally feasible.

The history is a great story: **Robert Gallager invented LDPC in his 1962 MIT PhD thesis** — and it was **forgotten for 35 years** because 1960s hardware couldn't afford the decoding. Rediscovered in the mid-1990s (MacKay and others), it swept communications — Wi-Fi, 5G, satellite — then HDDs, then SSDs. It is now the ECC standard for high-density NAND.

Traits worth knowing: **regular** LDPC has uniform row/column weights, **irregular** varies them (and performs better — production uses irregular); LDPC shines at **long codewords** (thousands of bits — flash pages oblige); and it decodes **iteratively with soft inputs** — the payoff of §A.5.

### A.4.2 The Tanner graph

Sparse H has a beautiful picture — the **Tanner graph**, bipartite:

- **Variable nodes (VN)** — one per codeword bit ("the bits").
- **Check nodes (CN)** — one per row of H ("the constraints").
- An **edge** joins VN *i* to CN *j* iff H[j][i] = 1.

"Low density" = **few edges**; decoding is message-passing along them, and sparsity keeps that cheap (and keeps short cycles — which degrade decoding — rare).

!!! example "Worked example — a small Tanner graph"
    A sparse 4×6 H (6 bits, 4 checks; column weight 2, row weight 3):

    ```
          v1 v2 v3 v4 v5 v6
     c1 ┌  1  1  0  1  0  0 ┐      c1: v1 ⊕ v2 ⊕ v4 = 0
     c2 │  0  1  1  0  1  0 │      c2: v2 ⊕ v3 ⊕ v5 = 0
     c3 │  1  0  0  0  1  1 │      c3: v1 ⊕ v5 ⊕ v6 = 0
     c4 └  0  0  1  1  0  1 ┘      c4: v3 ⊕ v4 ⊕ v6 = 0
    ```

    Every bit touches exactly 2 checks, every check ties 3 bits — a regular (2,3) LDPC code. §A.5 decodes on this exact graph.

---

## A.5 LDPC decoding ⭐⭐

??? example "🎬 Animate this — Stronger ECC in action — BCH & LDPC"

    BCH's algebraic error hunt and an LDPC Tanner graph converging by message passing, side by side.

    [Animation page](../animations/ecc-bch-ldpc.md) · [open full-screen ↗](../animations/files/ecc_bch_ldpc.html)

    <iframe src="../../animations/files/ecc_bch_ldpc.html" width="100%" height="640" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="Stronger ECC in action — BCH & LDPC"></iframe>


Decoding runs on the Tanner graph by **message passing** (belief propagation): nodes exchange messages along edges, refining beliefs until every check is satisfied. Two flavors — hard-decision (bit-flipping, cheap) and soft-decision (sum-product, powerful). Both are 🔬 territory: the message-update rules and their approximations are what most LDPC patents optimize.

### A.5.1 Bit-flipping (hard decision) ⭐

Intuition: **a bit sitting in many failed checks is probably the liar — flip it.**

1. Load the hard bits into the variable nodes.
2. Each check node XORs its connected bits: 0 = satisfied, 1 = unsatisfied (the set of results is the syndrome).
3. All satisfied → done.
4. Otherwise, count each bit's unsatisfied checks.
5. Flip the bit(s) with the highest count; repeat from 2 (up to an iteration cap).

!!! example "Worked example — bit-flipping on the small graph"
    All-zero codeword sent; **bit 3 flips** → received `0 0 1 0 0 0`.

    **Iteration 1:** c1 = 0 ✓ · c2 = v2⊕v3⊕v5 = **1 ✗** · c3 = 0 ✓ · c4 = v3⊕v4⊕v6 = **1 ✗**

    | bit | in checks | # unsatisfied |
    |---|---|---|
    | v1 | c1, c3 | 0 |
    | v2 | c1, c2 | 1 |
    | **v3** | **c2, c4** | **2 ← max** |
    | v4 | c1, c4 | 1 |
    | v5 | c2, c3 | 1 |
    | v6 | c3, c4 | 1 |

    Flip v3 → `000000`. **Iteration 2:** all checks pass → done. Corrected.

Fast and cheap — but hard-decision: it discards the knowledge that some bits were read confidently and others were borderline. Using that confidence is the next algorithm, and it is dramatically stronger.

### A.5.2 Sum-product / belief propagation (soft decision) ⭐⭐

LDPC's superpower. Each variable node starts not with a bit but with a **Log-Likelihood Ratio**:

\[
L(\text{bit}) = \log \frac{P(\text{bit}=0 \mid \text{reading})}{P(\text{bit}=1 \mid \text{reading})}
\]

- **Sign** = the hard guess (positive → probably 0).
- **Magnitude** = the **confidence** (|L| large → sure; |L| ≈ 0 → coin flip).

A cell read far from any threshold yields a confident, large-|L| value; a cell read *at* the boundary yields L ≈ 0. **This is exactly the information BCH throws away.**

The decoder passes LLR messages around the Tanner graph in two half-steps per iteration:

1. **Variable → check:** each bit tells each of its checks its best current belief — channel LLR plus everything heard from its *other* checks (never echoing back what that check just said):
   `q(i→j) = L(cᵢ) + Σ r(j′→i) over j′ ≠ j`
2. **Check → variable:** each check tells each of its bits what value would satisfy the parity, given the *other* bits:
   `r(j→i) = 2·atanh( ∏ tanh(q(i′→j)/2) ) over i′ ≠ i`
   The **sign** works out to the XOR of the other bits' signs (parity logic); the **magnitude** is dominated by the *least confident* sibling — a chain as strong as its weakest link. (Hold that thought for min-sum.)

After each iteration: total LLR per bit = channel + all incoming check messages; take signs as the tentative word; test H·ĉᵀ = 0; stop on success or iterate to a cap.

The magic is **propagation**: a confidently-read bit lends its certainty, through shared checks, to uncertain neighbors; over iterations the constraint network pulls borderline bits into global consistency — correcting error rates that defeat any hard-decision scheme at the same code rate. This is why LDPC keeps UBER at spec even as NAND RBER climbs.

**Min-sum 🔬 — what production actually ships.** The tanh/atanh product is exact but hardware-hostile. **Min-sum** approximates the check update as: *sign = product of the other signs; magnitude = minimum of the other magnitudes* — pure comparisons, no transcendentals, and it directly encodes the weakest-link insight. Plain min-sum slightly overestimates confidence, so real decoders correct it — **normalized min-sum** (scale < 1), **offset min-sum** (subtract a constant), and **layered** schedules for faster convergence. **This family is where a large share of SSD ECC patents live** — the exact scalings, offsets, quantizations, and schedules are endlessly optimized and filed.

---

## A.6 LDPC encoding

The asymmetry worth understanding: decoding is elegant *because H is sparse* — but the derived G is generally **dense**, making naive c = u·G an expensive multiply over thousands of bits. Practical fixes:

- **Approximate lower-triangular form** (Richardson–Urbanke): permute H nearly triangular so parity bits fall out by cheap back-substitution.
- **QC-LDPC (quasi-cyclic)** 🔬 — build H from small **circulant** blocks (cyclically shifted identities). This is what real hardware uses: the block structure makes encoding *and* decoding parallel and compact (the code stores as a table of shift values). QC-LDPC construction is its own patent-active corner.

Net: **LDPC trades harder encoding for much stronger, soft-capable decoding** — the right trade for flash, where the decoder works on every single read.

---

## A.7 The LDPC codec inside the SSD ⭐⭐

The math lands in the drive through one central distinction: **hard-decision vs soft-decision reads.**

**Hard read (the fast path).** Read each cell at the normal reference voltage(s), get hard bits, decode. One flash read; works fine while RBER is low. Modern decoders even assign coarse fixed-magnitude LLRs to hard bits and run soft-*style* decoding — free correction margin. This is attempt #1 on every read the drive ever does.

**Soft read (the strong path).** When hard decoding fails to converge — the flash has aged; retention or read disturb has shifted the distributions ([Ch 3 §3.4.1](../core/ch3-nand-flash.md#341-sources-of-read-error-consolidated)) — the controller escalates: **re-read the same cells at several shifted reference voltages** to localize each cell's threshold precisely. This extends Chapter 3's **Read Retry**, but instead of hunting one better threshold, the multiple strobes build a **fine-grained LLR per bit**:

```
        state 0          state 1
          ╱▔▔╲           ╱▔▔╲
         ╱    ╲         ╱    ╲          cells far from the boundary
        ╱      ╲       ╱      ╲         → high-confidence LLR
   ────╱────────╲─────╱────────╲────►  threshold voltage
                 ╲   ╱
              ┌────┴─┴────┐
              │ overlap    │   cells in the overlap → LLR ≈ 0;
              │ region     │   the extra strobes pin down exactly
              └────────────┘   HOW uncertain each one is
       ▲    ▲    ▲    ▲    ▲
       multiple read strobes at shifted voltages
```

Graded LLRs into the min-sum decoder correct error rates no hard scheme touches — **which is precisely why LDPC, not BCH, owns TLC and QLC**: more bits per cell = more states in the same voltage window = more overlap = soft decoding stops being optional. (QLC's sixteen levels make it the enabling technology.)

**The cost 🔬.** Every extra strobe is another flash read — latency, plus a little self-inflicted read disturb. So controllers run a **tiered escalation**, and managing the ladder — how many strobes, at which offsets, when to escalate, how to quantize LLRs, how to adapt per-block as wear accumulates — is both a rich engineering problem and one of the hottest filing areas (recent examples: seven-strobe soft-read schemes, self-correcting min-sum tweaks, QLC LLR optimization).

**The full ladder, end to end:**

```
   read ─► hard decode ─► ok? ─► done            (fast — the common case)
             │ fail
             ▼
   read-retry / soft strobes ─► build LLRs ─► soft decode
             │ fail
             ▼
   more strobes / stronger decode / die-RAID rebuild   (Ch 3 §3.4.4)
             │ fail
             ▼
   UECC reported to host — the UBER event              (Ch 1 §1.5.4)
```

This is the coding theory of this supplement running live inside every read a drive serves — the thread that connects Chapter 1 (RBER/UBER), Chapter 3 (noise, retry, RAID), and the mathematics here.

---

## A.8 Modern developments & the patent landscape

*The current state of practice, and where the innovation concentrates — useful both as an update and as a map for patent or literature research.*

**Min-sum variants are the production reality.** No shipping SSD runs exact tanh sum-product at flash throughput. The workhorses are normalized/offset min-sum and especially **layered normalized min-sum (LNMS)** — check nodes updated in layers for faster convergence and lower latency. Research is making these *adaptive*, tuning the decoder per block from the codeword's reliability profile. 🔬 Scaling factors, offsets, layer schedules, message quantization: the crux of most modern decoder patents.

**LLR generation is the other battleground.** A decoder is only as good as its input LLRs, and LLR accuracy decays as the NAND ages and distributions drift. Hence a whole class of filings on **LLR optimization**: threshold-voltage models of the specific NAND, clever quantization, amplifying the near-zero LLRs that matter most to min-sum, deriving soft information from neighboring cells or XORed internal soft-bit reads (a standard QLC technique). Representative directions from recent filings: per-decoder dynamic LLR control tracking rising RBER, and self-corrected min-sum protecting the least-confident variable nodes — worth ~1% extra QLC correction on seven-strobe reads, which at fleet scale is real endurance.

**Read-performance-aware decoding.** Soft strobes cost latency, so a research thread minimizes them: cumulative-distribution-based LLR schemes, hiding soft-read latency in idle time and channel parallelism — with reported 50–80% read-performance gains over naive soft decoding. 🔬 "Minimum sensing, maximum correction" is both practically vital (QoS!) and heavily filed.

**Beyond LDPC?** **Polar codes** (5G's control-channel code) have been studied for storage but haven't displaced LDPC in NAND. The near-term reality: **LDPC plus ever-smarter soft-read/LLR strategies**, hardening in step with QLC and researched PLC (5 bits/cell) — where the voltage window is sliced so finely that soft decoding *is* the product. The patent action isn't about replacing LDPC; it's about squeezing it: better LLRs, cheaper decoders, fewer strobes.

---

## Key takeaways

1. **Flash storage is a noisy channel**; ECC is communication theory wearing a storage badge. RBER in, UBER out, spare area as the budget.
2. **d\_min decides everything**: detect d\_min − 1, correct ⌊(d\_min−1)/2⌋. Code design is packing codewords far apart.
3. **G encodes, H checks, the syndrome fingers the error** — and depends only on the error, never the data. Hamming(7,4) is the whole mechanism in miniature.
4. **BCH = algebraic, deterministic, hard-decision** — it cannot use confidence, and that ceiling is why NAND outgrew it.
5. **LDPC = sparse H + Tanner graph + message passing.** Bit-flipping shows the idea; sum-product with LLRs is the power; min-sum variants are what ships.
6. **Soft reads turn Read Retry into LLR generation** — multiple strobes map each cell's uncertainty, and the escalation ladder (hard → soft → RAID → UECC) governs every read a drive serves.
7. **The patent map 🔬**: min-sum message rules, LLR generation/quantization, strobe-minimization, QC-LDPC construction — that's where the field files.

---

## Key vocabulary

| Term | Meaning |
|---|---|
| RBER / UBER | raw / uncorrectable bit error rate (Ch1) |
| redundancy / parity | extra bits added to enable correction |
| code rate R = k/n | data bits ÷ total bits |
| Hamming distance | # positions two codewords differ |
| minimum distance dmin | smallest distance between any two codewords |
| correction capability t | ⌊(dmin−1)/2⌋ errors correctable |
| GF(2) | binary field; `+` is XOR |
| generator matrix G | encodes: c = u·G |
| parity-check matrix H | checks: H·cᵀ = 0 |
| systematic form | G = [I \| P]; data appears uncoded in codeword |
| syndrome s = H·rᵀ | depends only on the error; = 0 if no error |
| BCH code | algebraic multi-error-correcting cyclic code (hard-decision) |
| error-locator polynomial | BCH: its roots locate the errors |
| LDPC | linear code with a **sparse** parity-check matrix |
| regular / irregular | uniform vs varied row/column weights |
| QC-LDPC | quasi-cyclic LDPC built from circulant blocks (HW-friendly) |
| Tanner graph | bipartite graph of variable nodes ↔ check nodes |
| variable node (VN) | one per codeword bit |
| check node (CN) | one per parity equation (row of H) |
| bit-flipping | hard-decision iterative decoder |
| belief propagation / sum-product | soft-decision iterative decoder |
| LLR | log-likelihood ratio; sign = guess, magnitude = confidence |
| min-sum | hardware-friendly approximation of sum-product |
| normalized / offset min-sum | corrected min-sum variants |
| hard / soft decision read | single read vs multiple-strobe read for LLRs |
| read retry | Ch3 mechanism; the basis of soft reads |
| UECC | uncorrectable ECC error → UBER event |

---

## Check yourself

1. Why is storing data in flash mathematically the same problem as transmitting over a noisy channel? Name the "noise sources" (from Chapter 3).
2. A code has dmin = 5. How many errors can it detect? How many can it correct? Show the formulas.
3. Explain the "balls around codewords" geometric picture. Why does larger dmin mean more correction power?
4. Why can a single parity bit *detect* one error but not *correct* it? (Answer in terms of dmin.)
5. Given the Hamming(7,4) G above, encode `u = [1 1 0 0]`. Then flip bit 6 and show that the syndrome points to bit 6.
6. What is a syndrome, and why is it so useful that it "depends only on the error, not the data"?
7. What single structural property makes a code "LDPC," and what does that property buy you at decoding time?
8. Draw (or describe) the Tanner graph for this H: rows `[1 1 1 0]`, `[0 1 1 1]`. How many variable nodes, how many check nodes, and which bits does each check tie together?
9. Run one iteration of bit-flipping: on the 6-bit example code, the all-zero word is sent and **bit 5** flips. Which checks fail, which bit has the most failed checks, and what gets flipped?
10. In an LLR, what does the sign encode and what does the magnitude encode? Why is a cell read *at* a state boundary given an LLR near zero?
11. In the sum-product check-node update, why does the outgoing message's magnitude depend most on the *least* confident incoming bit? How does min-sum exploit this?
12. Why can BCH *not* use soft information, and why does that make LDPC the standard for TLC/QLC specifically?
13. Trace the SSD's ECC escalation ladder from a fast hard read all the way to a UECC event. Where do soft reads fit, and what do they cost?
14. **(Patent-relevant)** Name two distinct areas where LDPC-in-SSD patents concentrate, and explain what each is trying to improve.

---

??? info "📖 Provenance"

    The core chapters of《深入淺出SSD》(1st edition) treat ECC conceptually;
    the 2nd edition adds a full mathematics chapter. This supplement
    reconstructs that material from standard coding-theory references
    (Gallager's thesis; MacKay; Richardson–Urbanke) in the same worked-example
    style as the rest of this site, tied to the two ECC animations.

*Next: [Supplement B — UFS](b-ufs.md), the phone-world counterpart to NVMe — the UFS stack, UPIU packets, RPMB, WriteBooster, and HPB.*
