#!/usr/bin/env python3
"""Generate docs/assets/figures/supp-a/soft-read.svg (Supplement A §A.7).

A soft read. Two neighbouring threshold-voltage states overlap; a hard read
tests one reference, and four extra strobes around it split the axis into
six bins. Every bin's LLR, ln P(bin | stores 0) / P(bin | stores 1), is
computed from the two Gaussians drawn and rounded the way a decoder
quantizes it, so the numbers in the figure are the figure's own. An
original drawing.
Re-run after editing: python scripts/figures/soft_read.py
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = (Path(__file__).resolve().parents[2]
       / "docs" / "assets" / "figures" / "supp-a" / "soft-read.svg")

INK, MUTE, LINE = "#e8eeff", "#a3abc4", "#7d86a3"
CYAN, VIOLET, AMBER, RED = "#4dd0c4", "#a78bfa", "#f2b13c", "#ff7b72"

X0, X1 = 12, 388        # the voltage axis
BASE, PEAK = 150, 92    # axis y, bell height
MID = 200               # the hard-read reference
D, SIGMA = 60, 30       # bell centres sit at MID - D and MID + D
STEP = 22               # spacing of the soft strobes
SPAN = 3.2              # how far a drawn bell extends, in sigmas
TOP = 56                # where the strobe lines stop
STROBES = [MID + k * STEP for k in (-2, -1, 0, 1, 2)]
MU1, MU0 = MID - D, MID + D   # cells storing 1, cells storing 0


def cdf(x: float, mu: float) -> float:
    if math.isinf(x):
        return 1.0 if x > 0 else 0.0
    return 0.5 * (1 + math.erf((x - mu) / (SIGMA * math.sqrt(2))))


def llr(lo: float, hi: float) -> float:
    p0 = cdf(hi, MU0) - cdf(lo, MU0)
    p1 = cdf(hi, MU1) - cdf(lo, MU1)
    return math.log(p0 / p1)


def bell(mu: float, x0: float, x1: float) -> str:
    pts, x = [], x0
    while x <= x1 + 1e-9:
        y = BASE - PEAK * math.exp(-0.5 * ((x - mu) / SIGMA) ** 2)
        pts.append(f"{x:.1f},{y:.1f}")
        x += 2
    return (f"M{x0:.1f},{BASE} L" + " ".join(pts) + f" L{x1:.1f},{BASE} Z")


def bins(edges: list[float], y: float) -> list[str]:
    out = []
    for lo, hi in zip(edges, edges[1:]):
        value = llr(-math.inf if lo == X0 else lo, math.inf if hi == X1 else hi)
        q = round(value)
        cls, col = ("f-cyan-t", CYAN) if q > 0 else ("f-violet-t", VIOLET)
        out.append(
            f'<rect class="{cls}" x="{lo}" y="{y}" width="{hi - lo}" '
            f'height="24" fill="{col}" opacity="{0.1 + 0.35 * min(abs(q), 8) / 8:.2f}"/>')
        out.append(
            f'<rect class="f-line" x="{lo}" y="{y}" width="{hi - lo}" '
            f'height="24" fill="none" stroke="{LINE}"/>')
        label = f"+{q}" if q > 0 else f"−{-q}"
        out.append(
            f'<text class="f-ink" x="{(lo + hi) / 2:g}" y="{y + 17}" '
            f'text-anchor="middle" font-weight="700" fill="{INK}">{label}</text>')
        print(f"  bin {lo:>5}-{hi:<5} LLR {value:+.2f} -> {label}")
    return out


def main() -> None:
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 304" '
        'font-family="IBM Plex Sans, sans-serif" font-size="13">',
        "<title>A soft read turns strobes into log-likelihood ratios</title>",
        "<desc>Two overlapping threshold-voltage bells: cells storing 1 on "
        "the left, cells storing 0 on the right. A dashed hard-read "
        "reference sits between them, and the cells of each bell that fall "
        "on the wrong side of it are shaded as read wrong. Four more strobes, "
        "two on each side of the reference, split the voltage axis into six "
        "bins. Below the axis, two rows give the log-likelihood ratio, the "
        "LLR, that each read assigns. The hard read alone gives every cell "
        "minus 4 or plus 4. The five strobes give, from left to right, minus "
        "8, minus 4, minus 1, plus 1, plus 4 and plus 8: the cells near the "
        "reference, where the misread cells sit, get small values that tell "
        "the decoder they are unsure.</desc>",
    ]
    for mu, cls, col, name in ((MU1, "f-violet", VIOLET, "stores 1"),
                               (MU0, "f-cyan", CYAN, "stores 0")):
        lo, hi = mu - SPAN * SIGMA, mu + SPAN * SIGMA
        out.append(f'<path class="{cls}" d="{bell(mu, lo, hi)}" fill="{col}" '
                   f'fill-opacity=".22" stroke="{col}" stroke-width="1.5"/>')
        wrong = (MID, hi) if mu < MID else (lo, MID)
        out.append(f'<path class="f-red-t" d="{bell(mu, *wrong)}" '
                   f'fill="{RED}" opacity=".6"/>')
        out.append(f'<text class="f-ink" x="{mu}" y="{BASE - PEAK - 14}" '
                   f'text-anchor="middle" fill="{INK}">{name}</text>')
    for x in STROBES:
        hard = x == MID
        cls, col = ("f-amber-l", AMBER) if hard else ("f-violet-l", VIOLET)
        out.append(
            f'<line class="{cls} f-dash" x1="{x}" y1="{BASE}" x2="{x}" '
            f'y2="{TOP}" stroke="{col}" stroke-width="{2 if hard else 1.5}" '
            'stroke-dasharray="4 3"/>')
    out.append(f'<line class="f-line" x1="{X0}" y1="{BASE}" x2="{X1}" '
               f'y2="{BASE}" stroke="{LINE}" stroke-width="1.2"/>')

    print("hard read alone:")
    out.append(f'<text class="f-mute" x="{X0}" y="{BASE + 20}" '
               f'fill="{MUTE}">LLR from the hard read alone</text>')
    out += bins([X0, MID, X1], BASE + 26)
    print("hard read plus four soft strobes:")
    out.append(f'<text class="f-mute" x="{X0}" y="{BASE + 72}" '
               f'fill="{MUTE}">LLR from all five strobes</text>')
    out += bins([X0, *STROBES, X1], BASE + 78)

    ly = BASE + 124
    out += [
        f'<line class="f-amber-l f-dash" x1="{X0}" y1="{ly - 4}" x2="30" '
        f'y2="{ly - 4}" stroke="{AMBER}" stroke-width="2" stroke-dasharray="4 3"/>',
        f'<text class="f-mute" x="36" y="{ly}" fill="{MUTE}">hard-read reference</text>',
        f'<line class="f-violet-l f-dash" x1="212" y1="{ly - 4}" x2="230" '
        f'y2="{ly - 4}" stroke="{VIOLET}" stroke-width="1.5" stroke-dasharray="4 3"/>',
        f'<text class="f-mute" x="236" y="{ly}" fill="{MUTE}">soft-read strobes</text>',
        f'<rect class="f-red-t" x="{X0}" y="{ly + 9}" width="18" height="12" '
        f'fill="{RED}" opacity=".6"/>',
        f'<text class="f-mute" x="36" y="{ly + 20}" fill="{MUTE}">read wrong by the hard read</text>',
        f'<text class="f-mute" x="{X1}" y="{ly + 20}" text-anchor="end" '
        f'fill="{MUTE}">Vt →</text>',
        "</svg>",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
