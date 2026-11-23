#!/usr/bin/env python3
"""Generate docs/assets/figures/ch3/vt-bells.svg (Ch 3 §3.1.2).

Threshold-voltage distributions for SLC, MLC and TLC, drawn as true Gaussians
so the shrinking margins are honest rather than sketched. An original drawing
built from the chapter's own description; nothing is traced from any book.
Re-run after editing: python scripts/figures/vt_bells.py
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = (Path(__file__).resolve().parents[2]
       / "docs" / "assets" / "figures" / "ch3" / "vt-bells.svg")

W = 400
PANEL_H = 128
PEAK = 60          # bell height
TAIL = 2.6         # where a bell's visible tail ends, in sigmas

# (name, subtitle, [(label, centre, sigma, erased?)])
PANELS = [
    ("SLC", "1 bit per cell · 2 states",
     [("1", 95, 22, True), ("0", 290, 15, False)]),
    ("MLC", "2 bits per cell · 4 states",
     [("E", 66, 16, True), ("P1", 170, 11, False), ("P2", 255, 11, False),
      ("P3", 340, 11, False)]),
    ("TLC", "3 bits per cell · 8 states",
     [("E", 50, 12, True)]
     + [(f"P{i}", 108 + (i - 1) * 43, 7.5, False) for i in range(1, 8)]),
]

INK, MUTE, LINE = "#e8eeff", "#a3abc4", "#7d86a3"
CYAN, VIOLET, AMBER = "#4dd0c4", "#a78bfa", "#f2b13c"


def bell(c: float, s: float, base: float) -> str:
    pts = []
    x = c - 3.2 * s
    while x <= c + 3.2 * s + 1e-9:
        y = base - PEAK * math.exp(-0.5 * ((x - c) / s) ** 2)
        pts.append(f"{x:.1f},{y:.1f}")
        x += max(0.5, s / 8)
    return f"M{c - 3.2 * s:.1f},{base:.1f} L" + " ".join(pts) + " Z"


def main() -> None:
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 404" '
        'font-family="IBM Plex Sans, sans-serif" font-size="13">',
        "<title>Threshold-voltage distributions for SLC, MLC and TLC</title>",
        "<desc>Three panels share one threshold-voltage axis. SLC: two "
        "bell curves, erased (1) and programmed (0), far apart, with one read "
        "reference at 0 V inside a wide margin. MLC: four bells, E and P1 to "
        "P3, with three read references. TLC: eight narrow bells, E and P1 to "
        "P7, with seven read references; the margins between neighbours are "
        "thin slivers.</desc>",
    ]
    for i, (name, sub, states) in enumerate(PANELS):
        y0 = 8 + i * PANEL_H
        base = y0 + 108
        out.append(
            f'<text x="12" y="{y0 + 16}" font-size="14">'
            f'<tspan class="f-ink" fill="{INK}" font-weight="700">{name}</tspan>'
            f'<tspan class="f-mute" fill="{MUTE}"> · {sub}</tspan></text>')
        # margins (bands between neighbouring tails) and read references
        for (_, c1, s1, _), (_, c2, s2, _) in zip(states, states[1:]):
            lo, hi = c1 + TAIL * s1, c2 - TAIL * s2
            out.append(
                f'<rect class="f-amber-b" x="{lo:.1f}" y="{base - PEAK - 4}" '
                f'width="{hi - lo:.1f}" height="{PEAK + 4}" fill="{AMBER}" '
                'fill-opacity=".12"/>')
            ref = (c1 * s2 + c2 * s1) / (s1 + s2)  # equal z-score point
            out.append(
                f'<line class="f-amber-l f-dash" x1="{ref:.1f}" y1="{base}" '
                f'x2="{ref:.1f}" y2="{base - PEAK - 4}" stroke="{AMBER}" '
                'stroke-width="1.5" stroke-dasharray="4 3"/>')
            if name == "SLC":
                out.append(
                    f'<text class="f-amber-t" x="{ref - 6:.1f}" '
                    f'y="{base - PEAK + 14}" text-anchor="end" '
                    f'fill="{AMBER}">margin</text>')
                out.append(
                    f'<text class="f-mute" x="{ref:.1f}" y="{base + 15}" '
                    f'text-anchor="middle" fill="{MUTE}">read at 0 V</text>')
        for label, c, s, erased in states:
            cls, col = ("f-violet", VIOLET) if erased else ("f-cyan", CYAN)
            out.append(
                f'<path class="{cls}" d="{bell(c, s, base)}" fill="{col}" '
                f'fill-opacity=".22" stroke="{col}" stroke-width="1.5"/>')
            out.append(
                f'<text class="f-ink" x="{c}" y="{base - PEAK - 9}" '
                f'text-anchor="middle" fill="{INK}">{label}</text>')
        out.append(
            f'<line class="f-line" x1="12" y1="{base}" x2="392" y2="{base}" '
            f'stroke="{LINE}" stroke-width="1.2"/>')
    out.append(
        f'<text class="f-mute" x="392" y="{8 + 2 * PANEL_H + 108 + 18}" '
        f'text-anchor="end" fill="{MUTE}">threshold voltage (Vt) →</text>')
    out.append("</svg>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
