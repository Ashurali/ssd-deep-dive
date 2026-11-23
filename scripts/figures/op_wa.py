#!/usr/bin/env python3
"""Generate docs/assets/figures/ch4/op-wa.svg (Ch 4 §4.3.2).

Write amplification against over-provisioning, computed from two models
rather than copied from any chart:

- Garbage spread evenly (the chapter's worst case): every victim block holds
  the average valid fraction u = 1 / (1 + OP), so WA = 1 / (1 - u)
  = (1 + OP) / OP. This gives the worked points 20% -> 6 and 50% -> 3.
- Uniform random writes with oldest-block-first cleaning: a page survives
  until its block is cleaned with probability x = exp(-(1 + OP)(1 - x)),
  and WA = 1 / (1 - x). Greedy victim choice does better still.

Re-run after editing: python scripts/figures/op_wa.py
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = (Path(__file__).resolve().parents[2]
       / "docs" / "assets" / "figures" / "ch4" / "op-wa.svg")

X0, X1, Y0, Y1 = 64, 380, 32, 248      # plot area
OP_MAX, WA_MAX = 1.0, 12.0
INK, MUTE, LINE, FAINT = "#e8eeff", "#a3abc4", "#7d86a3", "#2a3150"
CYAN, AMBER = "#4dd0c4", "#f2b13c"


def px(op: float) -> float:
    return X0 + (X1 - X0) * op / OP_MAX


def py(wa: float) -> float:
    return Y1 - (Y1 - Y0) * (wa - 1) / (WA_MAX - 1)


def worst(op: float) -> float:
    return (1 + op) / op


def fifo(op: float) -> float:
    x = 0.5
    for _ in range(200):  # fixed point of x = exp(-(1 + OP)(1 - x))
        x = math.exp(-(1 + op) * (1 - x))
    return 1 / (1 - x)


def path(fn) -> str:
    pts, op = [], 0.02
    while op <= OP_MAX + 1e-9:
        wa = fn(op)
        if wa <= WA_MAX:
            pts.append(f"{px(op):.1f},{py(wa):.1f}")
        op += 0.005
    return "M" + " L".join(pts)


def main() -> None:
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 344" '
        'font-family="IBM Plex Sans, sans-serif" font-size="13">',
        "<title>Write amplification falls as over-provisioning grows</title>",
        "<desc>A chart of write amplification (WA, vertical, 1 to 12) against "
        "over-provisioning (OP, horizontal, 0 to 100 percent). Two curves fall "
        "steeply at small OP and flatten toward 1 as OP grows. The upper "
        "curve assumes garbage is spread evenly over every block, the "
        "chapter's worst case: WA = (1 + OP) / OP, which passes through "
        "WA 6 at 20 percent OP and WA 3 at 50 percent. The lower curve is "
        "a model of uniform random writes with the oldest block cleaned "
        "first; it sits well below the worst case, and greedy victim "
        "selection does better still.</desc>",
    ]
    for wa in (1, 3, 6, 9, 12):
        y = py(wa)
        out.append(f'<line class="f-faint" x1="{X0}" y1="{y:.1f}" x2="{X1}" '
                   f'y2="{y:.1f}" stroke="{FAINT}"/>')
        out.append(f'<text class="f-mute" x="{X0 - 8}" y="{y + 4.5:.1f}" '
                   f'text-anchor="end" fill="{MUTE}">{wa}</text>')
    for op in (0, 0.25, 0.5, 0.75, 1.0):
        x = px(op)
        out.append(f'<text class="f-mute" x="{x:.1f}" y="{Y1 + 22}" '
                   f'text-anchor="middle" fill="{MUTE}">{round(op * 100)}%</text>')
    out += [
        f'<line class="f-line" x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" '
        f'stroke="{LINE}" stroke-width="1.2"/>',
        f'<line class="f-line" x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" '
        f'stroke="{LINE}" stroke-width="1.2"/>',
        f'<text class="f-mute" x="{(X0 + X1) / 2:.0f}" y="{Y1 + 42}" '
        f'text-anchor="middle" fill="{MUTE}">over-provisioning (OP)</text>',
        f'<text class="f-mute" x="16" y="20" fill="{MUTE}">write amplification (WA)</text>',
        f'<path class="f-amber-l" d="{path(worst)}" fill="none" '
        f'stroke="{AMBER}" stroke-width="2.5"/>',
        f'<path class="f-cyan-l" d="{path(fifo)}" fill="none" '
        f'stroke="{CYAN}" stroke-width="2.5"/>',
    ]
    for op, label, dx in ((0.2, "20% → WA 6", 10), (0.5, "50% → WA 3", 10)):
        x, y = px(op), py(worst(op))
        out.append(f'<circle class="f-amber-t" cx="{x:.1f}" cy="{y:.1f}" r="4" '
                   f'fill="{AMBER}"/>')
        out.append(f'<text class="f-amber-t" x="{x + dx:.1f}" y="{y - 8:.1f}" '
                   f'fill="{AMBER}">{label}</text>')
    ly = Y1 + 64
    out += [
        f'<line class="f-amber-l" x1="16" y1="{ly - 4}" x2="36" y2="{ly - 4}" '
        f'stroke="{AMBER}" stroke-width="2.5"/>',
        f'<text class="f-mute" x="42" y="{ly}" fill="{MUTE}">garbage spread evenly (worst case)</text>',
        f'<line class="f-cyan-l" x1="16" y1="{ly + 14}" x2="36" y2="{ly + 14}" '
        f'stroke="{CYAN}" stroke-width="2.5"/>',
        f'<text class="f-mute" x="42" y="{ly + 18}" fill="{MUTE}">random writes, oldest block cleaned first</text>',
        "</svg>",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT}; fifo WA at 7/20/28/50%: "
          + ", ".join(f"{fifo(o):.2f}" for o in (0.07, 0.2, 0.28, 0.5)))


if __name__ == "__main__":
    main()
