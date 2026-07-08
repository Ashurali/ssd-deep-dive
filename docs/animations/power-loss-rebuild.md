---
title: "Power-Loss Rebuild & Snapshots"
tags: [animations, ftl, power-loss-recovery]
---

# Power-Loss Rebuild & Snapshots

Every written page carries its passport (LBA + timestamp). Yank the power mid-run, then watch the reboot scan crawl the flash re-deriving the map — including the timestamp duel when the same LBA turns up twice. Turn snapshots on and the next rebuild loads the last snapshot and scans only the tail.

**Book anchor:** Realizes Figs 4-33, 4-43→4-46 (CH4 pp. 41, 53–56) — atlas Cluster G.

[Open full-screen ↗](files/power_loss_rebuild.html){ .md-button }

<!-- ../ because directory URLs render this page one level deeper -->
<iframe src="../files/power_loss_rebuild.html" width="100%" height="720"
        style="border:1px solid #26304d;border-radius:12px;background:#0b1020"
        loading="lazy" title="Power-Loss Rebuild & Snapshots"></iframe>
