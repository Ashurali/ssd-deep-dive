#!/usr/bin/env python3
"""Generate docs/assets/figures/ch3/vt-shifts.svg (Ch 3 §3.4.1).

How flash's failure modes move the threshold-voltage bells: retention slides
the programmed bell left, read disturb slides the erased bell right, and wear
widens both until their tails overlap. Bits whose cells cross the read
reference are shaded as errors. Drawn as true Gaussians, like vt_bells.py; an
original drawing built from the chapter's own description.
Re-run after editing: python scripts/figures/vt_shifts.py
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = (Path(__file__).resolve().parents[2]
       / "docs" / "assets" / "figures" / "ch3" / "vt-shifts.svg")

PANEL_H = 104
PEAK = 44
SPAN = 3.2         # how far a drawn bell extends, in sigmas
FRESH = {"E": (110, 20), "P": (290, 16)}

INK, MUTE, LINE = "#e8eeff", "#a3abc4", "#7d86a3"
CYAN, VIOLET, AMBER, RED, GREEN = ("#4dd0c4", "#a78bfa", "#f2b13c",
                                   "#ff7b72", "#7ee2a8")

# (title, subtitle, {state: (centre, sigma)}, note below the axis)
PANELS = [
    ("Fresh", "bells well apart", FRESH, None),
    ("Retention", "charge leaks out, P slides left",
     {"E": (110, 20), "P": (232, 19)}, "retry"),
    ("Read disturb", "charge creeps in, E slides right",
     {"E": (172, 21), "P": (290, 16)}, None),
    ("Wear", "both bells widen",
     {"E": (140, 34), "P": (268, 30)}, "overlap"),
]


def curve(c: float, s: float, base: float, x0: float, x1: float) -> list[str]:
    pts, x, step = [], x0, max(0.5, s / 8)
    while x <= x1 + 1e-9:
        y = base - PEAK * math.exp(-0.5 * ((x - c) / s) ** 2)
        pts.append(f"{x:.1f},{y:.1f}")
        x += step
    return pts


def area(c: float, s: float, base: float, x0: float, x1: float) -> str:
    return (f"M{x0:.1f},{base:.1f} L" + " ".join(curve(c, s, base, x0, x1))
            + f" L{x1:.1f},{base:.1f} Z")


def ref_of(e: tuple[float, float], p: tuple[float, float]) -> float:
    (c1, s1), (c2, s2) = e, p
    return (c1 * s2 + c2 * s1) / (s1 + s2)  # equal z-score point


def main() -> None:
    ref = ref_of(FRESH["E"], FRESH["P"])
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 470" '
        'font-family="IBM Plex Sans, sans-serif" font-size="13">',
        "<title>How retention, read disturb and wear move the bells</title>",
        "<desc>Four panels, each with an erased bell (E), a programmed bell "
        "(P) and a dashed read reference between them. Fresh: the bells are "
        "far apart. Retention: the P bell slides left toward the reference, "
        "and the cells that cross it read wrong; a Read Retry reference "
        "placed in the new gap reads them all correctly again. Read disturb: "
        "the E bell slides right and its tail crosses the reference. Wear: "
        "both bells widen until their tails overlap, so some cells read "
        "wrong wherever the reference sits, and only ECC can fix them. "
        "Dashed outlines show where each moved bell began.</desc>",
    ]
    for i, (name, sub, states, note) in enumerate(PANELS):
        y0 = 8 + i * PANEL_H
        base = y0 + 84
        out.append(
            f'<text x="12" y="{y0 + 16}" font-size="14">'
            f'<tspan class="f-ink" fill="{INK}" font-weight="700">{name}</tspan>'
            f'<tspan class="f-mute" fill="{MUTE}"> · {sub}</tspan></text>')
        for key, (c, s) in states.items():
            fc, fs = FRESH[key]
            if (fc, fs) != (c, s):  # where the bell began
                out.append(
                    f'<path class="f-line f-dash" d="{area(fc, fs, base, fc - SPAN * fs, fc + SPAN * fs)}" '
                    f'fill="none" stroke="{LINE}" stroke-width="1.2" stroke-dasharray="4 3"/>')
        for key, (c, s) in states.items():
            cls, col = ("f-violet", VIOLET) if key == "E" else ("f-cyan", CYAN)
            lo, hi = c - SPAN * s, c + SPAN * s
            out.append(
                f'<path class="{cls}" d="{area(c, s, base, lo, hi)}" fill="{col}" '
                f'fill-opacity=".22" stroke="{col}" stroke-width="1.5"/>')
            # cells on the wrong side of the read reference
            if key == "E" and hi > ref:
                out.append(
                    f'<path class="f-red-t" d="{area(c, s, base, ref, hi)}" '
                    f'fill="{RED}" opacity=".6"/>')
            if key == "P" and lo < ref:
                out.append(
                    f'<path class="f-red-t" d="{area(c, s, base, lo, ref)}" '
                    f'fill="{RED}" opacity=".6"/>')
            out.append(
                f'<text class="f-ink" x="{c}" y="{base - PEAK - 7}" '
                f'text-anchor="middle" fill="{INK}">{key}</text>')
        out.append(
            f'<line class="f-amber-l f-dash" x1="{ref:.1f}" y1="{base}" '
            f'x2="{ref:.1f}" y2="{base - PEAK - 4}" stroke="{AMBER}" '
            'stroke-width="1.5" stroke-dasharray="4 3"/>')
        if i == 0:
            out.append(
                f'<text class="f-amber-t" x="{ref:.1f}" y="{base + 15}" '
                f'text-anchor="middle" fill="{AMBER}">read reference</text>')
        if note == "retry":
            retry = ref_of(states["E"], states["P"])
            out.append(
                f'<line class="f-green-l f-dash" x1="{retry:.1f}" y1="{base}" '
                f'x2="{retry:.1f}" y2="{base - PEAK - 4}" stroke="{GREEN}" '
                'stroke-width="2" stroke-dasharray="4 3"/>')
            out.append(
                f'<text class="f-green-t" x="{retry:.1f}" y="{base + 15}" '
                f'text-anchor="middle" fill="{GREEN}">Read Retry reference</text>')
        if note == "overlap":
            out.append(
                f'<text class="f-red-t" x="{ref:.1f}" y="{base + 15}" '
                f'text-anchor="middle" fill="{RED}">tails overlap: only ECC can fix these</text>')
        out.append(
            f'<line class="f-line" x1="12" y1="{base}" x2="392" y2="{base}" '
            f'stroke="{LINE}" stroke-width="1.2"/>')
    ly = 8 + 4 * PANEL_H + 18
    out += [
        f'<rect class="f-red-t" x="12" y="{ly - 11}" width="14" height="12" '
        f'fill="{RED}" opacity=".6"/>',
        f'<text class="f-mute" x="32" y="{ly}" fill="{MUTE}">cells read wrong</text>',
        f'<rect class="f-line f-dash" x="160" y="{ly - 11}" width="14" height="12" '
        f'fill="none" stroke="{LINE}" stroke-dasharray="4 3"/>',
        f'<text class="f-mute" x="180" y="{ly}" fill="{MUTE}">where the bell began</text>',
        f'<text class="f-mute" x="392" y="{ly + 20}" text-anchor="end" '
        f'fill="{MUTE}">threshold voltage (Vt) →</text>',
        "</svg>",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
