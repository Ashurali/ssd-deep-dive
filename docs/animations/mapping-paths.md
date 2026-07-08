---
title: "Mapping Lookup Paths"
tags: [animations, ftl, mapping, ufs, hpb]
---

# Mapping Lookup Paths

Four architectures race the same 4 KB random read: DRAM drive (map in DRAM), DRAM-less (two flash accesses on a miss — the Fig 4-13 penalty as two long bars), HMB (a PCIe hop into borrowed host RAM), and HPB (the host supplies the physical address). Switch to sequential and watch DRAM-less catch up. Warm-up scene: block mapping's read-modify-write pain.

**Book anchor:** Realizes Figs 4-3→4-13 (CH4 pp. 5–14) plus Supplement B's HPB — atlas Cluster F.

[Open full-screen ↗](files/mapping_paths.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/mapping_paths.html" width="100%" height="720"
        style="border:1px solid #26304d;border-radius:12px;background:#0b1020"
        loading="lazy" title="Mapping Lookup Paths"></iframe>
