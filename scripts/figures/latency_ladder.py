#!/usr/bin/env python3
"""Generate docs/assets/figures/ch0/latency-ladder.svg (Ch 0 §0.5).

Typical latencies of the memory and storage hierarchy on one logarithmic
axis, from a cache hit to a hard-disk seek. The values are orders of
magnitude for 2020s hardware, not measurements of any one product; each
bar's end sits at log10 of its value, so equal steps are equal ratios.
Re-run after editing: python scripts/figures/latency_ladder.py
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = (Path(__file__).resolve().parents[2]
       / "docs" / "assets" / "figures" / "ch0" / "latency-ladder.svg")

INK, MUTE, LINE = "#e8eeff", "#a3abc4", "#7d86a3"
COLORS = {"f-violet": "#a78bfa", "f-cyan": "#4dd0c4",
          "f-amber": "#f2b13c", "f-red": "#ff7b72"}

X0 = 16                 # where 0.1 ns sits
DECADE = 38             # width of one power of ten
ROW = 32
TOP = 10

# (label, value in ns, colour class)
ITEMS = [
    ("CPU cache hit · ~1 ns", 1, "f-violet"),
    ("DRAM read · ~100 ns", 100, "f-violet"),
    ("NAND page read · ~50 µs", 50_000, "f-cyan"),
    ("SSD 4 KiB random read · ~100 µs", 100_000, "f-cyan"),
    ("NAND page program · ~1 ms", 1_000_000, "f-amber"),
    ("NAND block erase · ~4 ms", 4_000_000, "f-amber"),
    ("hard-disk random read · ~8 ms", 8_000_000, "f-red"),
]
TICKS = [(1, "1 ns"), (1_000, "1 µs"), (1_000_000, "1 ms"), (100_000_000, "100 ms")]


def x_of(ns: float) -> float:
    return X0 + DECADE * math.log10(ns / 0.1)


def main() -> None:
    height = TOP + ROW * len(ITEMS) + 40
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 {height}" '
        'font-family="IBM Plex Sans, sans-serif" font-size="13">',
        "<title>The latency ladder</title>",
        "<desc>Typical latencies on a logarithmic scale, where each step of "
        "the axis is ten times the last: a CPU cache hit takes about 1 "
        "nanosecond; a DRAM read about 100 nanoseconds; a NAND flash page "
        "read about 50 microseconds; a 4 KiB random read from an SSD about "
        "100 microseconds; a NAND page program about 1 millisecond; a NAND "
        "block erase about 4 milliseconds; and a hard-disk random read about "
        "8 milliseconds. An SSD read is about a thousand times slower than "
        "DRAM and about a hundred times faster than a hard disk.</desc>",
    ]
    for i, (label, ns, cls) in enumerate(ITEMS):
        y = TOP + i * ROW
        out.append(f'<text class="f-ink" x="{X0}" y="{y + 12}" fill="{INK}">{label}</text>')
        out.append(
            f'<rect class="{cls}" x="{X0}" y="{y + 17}" width="{x_of(ns) - X0:.1f}" '
            f'height="9" fill="{COLORS[cls]}" fill-opacity=".22" '
            f'stroke="{COLORS[cls]}" stroke-width="1.5"/>')
    axis = TOP + ROW * len(ITEMS) + 6
    out.append(f'<line class="f-line" x1="{X0}" y1="{axis}" x2="384" y2="{axis}" '
               f'stroke="{LINE}" stroke-width="1.2"/>')
    for ns, label in TICKS:
        x = x_of(ns)
        out.append(f'<line class="f-line" x1="{x:.1f}" y1="{axis}" x2="{x:.1f}" '
                   f'y2="{axis + 5}" stroke="{LINE}" stroke-width="1.2"/>')
        out.append(f'<text class="f-mute" x="{x:.1f}" y="{axis + 20}" '
                   f'text-anchor="middle" fill="{MUTE}">{label}</text>')
    out.append("</svg>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    for label, ns, _ in ITEMS:
        print(f"  {label:36} ends at x = {x_of(ns):6.1f}")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
