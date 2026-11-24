---
title: "Stronger ECC in action — BCH & LDPC"
tags: [animations, ecc, bch, ldpc, soft-decision]
---

# Stronger ECC in action — BCH & LDPC

The two codes SSDs actually ship: BCH, which locates errors algebraically, and LDPC, which corrects them by passing messages on a graph.

## What you'll learn

- How a BCH(15,7) decoder finds up to two errors: syndromes, the error-locator polynomial (Berlekamp–Massey) and the Chien search.
- How an LDPC decoder corrects round by round on a Tanner graph: checks report, then bits flip.
- Where each decoder runs out of strength.

## Try this

1. On the **BCH** tab, press *Encode →*, choose *2 bits* and press *Flip randomly*, then *Step ▸* through the decode.
2. On the **LDPC** tab, press *Flip randomly*, then *Step round ▸*, and watch the checks report and the bits flip.
3. Read *How the toys scale to a real drive* at the bottom.

[Open full-screen ↗](files/ecc_bch_ldpc.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/ecc_bch_ldpc.html" width="100%" height="720"
        class="sdd-anim"
        loading="lazy" title="Stronger ECC in action — BCH & LDPC"></iframe>

## Where it appears

- Chapter 3, [§3.4.3 ECC: error-correcting codes](../core/ch3-nand-flash.md#343-ecc-error-correcting-codes)
- Supplement A, [§A.5 LDPC decoding](../supplements/a-ecc-coding-theory.md#a5-ldpc-decoding)

??? info "📖 Provenance"

    An original interactive drawing made for this site; it reproduces no book
    figure. It accompanies Supplement A §A.3.4–§A.5 (where BCH fits, LDPC and the Tanner graph, LDPC decoding) and Chapter 3's ECC section, and reproduces no book figure.
