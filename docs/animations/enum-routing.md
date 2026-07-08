---
title: "The Enumeration & Routing Explorer"
tags: [animations, pcie, tlp]
---

# The Enumeration & Routing Explorer

A live PCIe tree: replay enumeration step by step — read BAR0, write all-1s, read back the stuck bits, decode the size, allocate a base — and watch the host memory map fill in. Then fire TLPs at chosen addresses and watch each switch port check its [Base, Limit] window; aim outside every window and the packet dies as an Unsupported Request.

**Book anchor:** Realizes Figs 5-6→5-10, 5-27→5-48 (CH5 pp. 7–10, 29–46) — atlas Cluster I.

[Open full-screen ↗](files/enum_routing.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/enum_routing.html" width="100%" height="720"
        style="border:1px solid #26304d;border-radius:12px;background:#0b1020"
        loading="lazy" title="The Enumeration & Routing Explorer"></iframe>
