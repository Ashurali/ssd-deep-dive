---
title: "How ECC finds and fixes a bit — Hamming visualizer"
tags: [animations, ecc]
---

# How ECC finds and fixes a bit — Hamming visualizer

A Hamming(12,8) code at work: flip a bit, and the parity checks that fail spell out its position.

## What you'll learn

- How each parity bit guards a different subset of the data bits.
- How the pattern of failing checks (the syndrome) gives the position of a single flipped bit.
- Why a Hamming code corrects only one error, and how SSD codes scale the idea up.

## Try this

1. Press *Encode →*, then click any bit to flip it (or press *Flip a random bit*).
2. Press *Decode & correct*, or *Step ▸* through the parity checks one at a time.
3. Read *From this toy to what's inside your SSD* below the code.

[Open full-screen ↗](files/ecc_bit_correction.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/ecc_bit_correction.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="How ECC finds and fixes a bit — Hamming visualizer"></iframe>

## Where it appears

- Supplement A, [§A.3.2 Parity: the cornerstone](../supplements/a-ecc-coding-theory.md#a32-parity-the-cornerstone)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It accompanies Supplement A §A.3 (Hamming distance, parity, the generator and parity-check matrices) and reproduces no book figure.
