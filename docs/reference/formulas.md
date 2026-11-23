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

**Map size with a larger indirection unit** — capacity drives map in units
larger than 4 KiB to keep the table small, at the cost of amplifying small
writes. *Explained in [Supp I §I.7](../supplements/i-data-center.md#i7-the-capacity-race-qlc-large-indirection-units-and-fdp).*

$$ \text{map table} \approx \frac{\text{Capacity}}{\text{indirection unit}} \times \text{entry size} $$

**Inherent over-provisioning from units** — a drive sold in decimal
gigabytes but built from binary gibibytes of flash keeps the difference.
*Derived in [Ch 0 §0.1](../core/ch0-foundations.md#01-units-bits-bytes-and-the-two-kinds-of-kilo).*

$$ OP_{inherent} = \frac{2^{30}}{10^{9}} - 1 \approx 7.4\% $$

## Performance

**IOPS ceiling from link bandwidth** — an interface can never deliver more
I/Os per second than its usable bandwidth divided by the transfer size.
*Context in [Ch 1 §1.5.2](../core/ch1-overview.md#152-performance) and
[Ch 5 §5.13](../core/ch5-pcie.md#513-pcie-link-performance-loss-analysis)
(why the realized number is always lower).*

$$ IOPS_{max} = \frac{\text{link bandwidth}}{\text{block size}} $$

**Throughput from IOPS** — the data rate is the operation rate times the
transfer size. *Derived in [Ch 0 §0.5](../core/ch0-foundations.md#05-latency-throughput-and-iops).*

$$ \text{throughput} = IOPS \times \text{transfer size} $$

**Little's law** — the number of operations in flight equals the operation
rate times the latency; it sets the queue depth a target IOPS needs.
*Same section, [Ch 0 §0.5](../core/ch0-foundations.md#05-latency-throughput-and-iops).*

$$ \text{queue depth} = IOPS \times \text{latency} $$

**Tail fan-out** — if a request touches \( n \) drives and each is slow with
probability \( p \), the chance that the request waits on a slow drive.
*From [Supp I §I.1](../supplements/i-data-center.md#i1-what-data-centers-want-consistent-latency).*

$$ P(\text{slow request}) = 1 - (1 - p)^{n} $$

## Power and reliability

**Power-loss-protection energy** — capacitors charged to \( V_1 \) must
deliver the energy to finish in-flight writes, \( P \times t \), before
falling to the lowest usable voltage \( V_2 \).
*Worked in [Ch 2 §2.8.3](../core/ch2-controllers-afa.md#283-power-loss-protection-capacitors-that-buy-milliseconds).*

$$ \tfrac{1}{2}\, C \left(V_1^{2} - V_2^{2}\right) \ge P \times t $$

**Expected errors** — an error rate means something only multiplied by the
number of bits handled. *Derived in [Ch 0 §0.11](../core/ch0-foundations.md#011-error-rates-and-big-exponents).*

$$ \text{expected errors} = \text{bits handled} \times \text{error rate} $$

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
*Defined in [Supp A §A.3](../supplements/a-ecc-coding-theory.md#a3-the-foundations).*

$$ R = \frac{k}{n} $$

**Minimum distance ↔ correction capability** — a code with minimum Hamming
distance \( d_{min} \) detects \( d_{min}-1 \) errors and corrects
\( t \) of them.
*Derived in [Supp A §A.3.1](../supplements/a-ecc-coding-theory.md#a31-hamming-distance-the-concept-everything-rests-on).*

$$ t = \left\lfloor \frac{d_{min}-1}{2} \right\rfloor $$

**Syndrome** — depends only on the error pattern, not the data; zero means
"no detectable error".
*Machinery in [Supp A §A.3.3](../supplements/a-ecc-coding-theory.md#a33-the-generator-matrix-g-and-parity-check-matrix-h).*

$$ s = H \cdot r^{T} $$
