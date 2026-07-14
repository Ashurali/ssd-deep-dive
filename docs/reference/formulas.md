---
title: "Formula Cheat Sheet"
---

# Formula cheat sheet

The recurring formulas of the whole corpus, each with one line of context and
a link to the section that derives it.

## FTL & endurance

**Write Amplification** — the ratio of what the SSD physically wrote vs what
the host asked for; GC's extra internal writes push it above 1.
*Derived in [Ch 4 §4.3.2](../core/ch4-ftl.md#432-write-amplification).*

$$ WA = \frac{\text{data written to flash}}{\text{data written by the host}} $$

**Over-Provisioning ratio** — the hidden reserve beyond user capacity; bigger
OP → more garbage per reclaimed block → lower WA.
*Same section, [Ch 4 §4.3.2](../core/ch4-ftl.md#432-write-amplification).*

$$ OP = \frac{\text{flash space} - \text{user space}}{\text{user space}} $$

**TBW** — total bytes writable over the drive's life, from capacity, NAND
endurance, and firmware quality (WA).
*Derived in [Ch 1 §1.5.3](../core/ch1-overview.md#153-endurance).*

$$ TBW \approx \frac{\text{Capacity} \times \text{P/E cycles}}{WA} $$

**DWPD** — full-drive writes per day sustainable over the warranty period;
the other face of TBW.
*Same section, [Ch 1 §1.5.3](../core/ch1-overview.md#153-endurance).*

$$ DWPD = \frac{TBW}{365 \times \text{years} \times \text{Capacity}} $$

**Map-table size rule of thumb** — with 4 KB logical pages and 4-byte
entries, the L2P table is ~1/1000 of capacity (why 1 TB drives carry ~1 GB
DRAM).
*Derived in [Ch 4 §4.2.2](../core/ch4-ftl.md#422-how-mapping-works-and-the-dram-question).*

$$ \text{map table} \approx \frac{\text{Capacity}}{1000} $$

## Performance

**IOPS ceiling from link bandwidth** — an interface can never deliver more
I/Os per second than its usable bandwidth divided by the transfer size.
*Context in [Ch 1 §1.5.2](../core/ch1-overview.md#152-performance) and
[Ch 5 §5.13](../core/ch5-pcie.md#513-pcie-link-performance-loss-analysis)
(why the realized number is always lower).*

$$ IOPS_{max} = \frac{\text{link bandwidth}}{\text{block size}} $$

## Endurance testing (JESD218A)

**Sample-size inequalities** — how many drives to test: SS must satisfy both,
using the looked-up Upper Confidence Limit (UCL = 0.92 at zero accepted
failures). Take the larger SS and round up.
*Worked through in [Ch 7 §7.8](../core/ch7-testing.md#78-endurance-testing).*

$$ UCL(\text{functional failures}) \le FFR \times SS $$

$$ UCL(\text{data errors}) \le \min(TBW, TBR) \times 8{\times}10^{12} \times UBER \times SS $$

## ECC (Supplement A)

**Code rate** — the fraction of transmitted bits that are actual data
(\( k \) data bits in an \( n \)-bit codeword).
*Defined in [Supp A §7.3](../supplements/a-ecc-coding-theory.md#a3-the-foundations).*

$$ R = \frac{k}{n} $$

**Minimum distance ↔ correction capability** — a code with minimum Hamming
distance \( d_{min} \) detects \( d_{min}-1 \) errors and corrects
\( t \) of them.
*Derived in [Supp A §7.3.1](../supplements/a-ecc-coding-theory.md#a31-hamming-distance-the-concept-everything-rests-on).*

$$ t = \left\lfloor \frac{d_{min}-1}{2} \right\rfloor $$

**Syndrome** — depends only on the error pattern, not the data; zero means
"no detectable error".
*Machinery in [Supp A §7.3.3](../supplements/a-ecc-coding-theory.md#a33-the-generator-matrix-g-and-parity-check-matrix-h).*

$$ s = H \cdot r^{T} $$
