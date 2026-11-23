#!/usr/bin/env python3
"""Generate docs/assets/figures/ch1/form-factors.svg (Ch 1 §1.6).

Common SSD form factors drawn to one scale (1.5 viewBox units per mm).
Outline dimensions, length × width:
  - 2.5-inch drive (SFF-8201; U.2 uses the same shell): 100.45 × 69.85 mm
  - EDSFF E3.S (SNIA SFF-TA-1008): 112.75 × 76 mm
  - EDSFF E1.S (SNIA SFF-TA-1006): about 112 × 32 mm (bare-PCB version)
  - M.2 (PCI-SIG): 22 mm wide; 80, 42 and 30 mm long (2280, 2242, 2230)
  - BGA SSD: 13 × 11.5 mm (the package described in §1.6.3)

Re-run after editing: python scripts/figures/form_factors.py
"""
from __future__ import annotations

from pathlib import Path

OUT = (Path(__file__).resolve().parents[2]
       / "docs" / "assets" / "figures" / "ch1" / "form-factors.svg")

K = 1.5  # viewBox units per millimetre
INK, MUTE, LINE = "#e8eeff", "#a3abc4", "#7d86a3"
KIND = {"both": ("f-amber", "#f2b13c"), "client": ("f-cyan", "#4dd0c4"),
        "dc": ("f-violet", "#a78bfa")}

# (name, size label, drawn width mm, drawn height mm, kind)
ROW1 = [
    ("2.5″ / U.2", "100 × 70 mm", 100.45, 69.85, "both"),
    ("E3.S", "76 × 113 mm", 76.0, 112.75, "dc"),
    ("E1.S", "≈ 32 × 112", 31.5, 111.5, "dc"),
]
ROW2 = [
    ("M.2 2280", "22 × 80 mm", 80.0, 22.0, "client"),
    ("2242", "22 × 42", 42.0, 22.0, "client"),
    ("2230", "22 × 30", 30.0, 22.0, "client"),
    ("BGA", "11.5 × 13", 13.0, 11.5, "client"),
]


def row(items: list, top: float, gap: float) -> tuple[list[str], float]:
    """Shapes bottom-aligned on one baseline, centred; returns (svg, bottom)."""
    widths = [w * K for _, _, w, _, _ in items]
    tallest = max(h * K for _, _, _, h, _ in items)
    x = (400 - sum(widths) - gap * (len(items) - 1)) / 2
    bottom = top + tallest
    out = []
    for (name, size, w, h, kind), wu in zip(items, widths):
        hu = h * K
        cls, col = KIND[kind]
        out.append(
            f'<rect class="{cls}" x="{x:.1f}" y="{bottom - hu:.1f}" '
            f'width="{wu:.1f}" height="{hu:.1f}" rx="3" fill="{col}" '
            f'fill-opacity=".22" stroke="{col}" stroke-width="1.5"/>')
        cx = x + wu / 2
        out.append(f'<text class="f-ink" x="{cx:.1f}" y="{bottom + 18:.1f}" '
                   f'text-anchor="middle" fill="{INK}">{name}</text>')
        out.append(f'<text class="f-mute" x="{cx:.1f}" y="{bottom + 34:.1f}" '
                   f'text-anchor="middle" fill="{MUTE}">{size}</text>')
        x += wu + gap
    return out, bottom


def main() -> None:
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 372" '
        'font-family="IBM Plex Sans, sans-serif" font-size="13">',
        "<title>SSD form factors drawn to one scale</title>",
        "<desc>Outlines drawn to the same scale. Top row: a 2.5-inch drive "
        "(100 by 70 mm, the shell U.2 drives also use), an EDSFF E3.S drive "
        "(76 by 113 mm) and an EDSFF E1.S drive (about 32 by 112 mm). Bottom "
        "row: M.2 cards 22 mm wide and 80, 42 or 30 mm long, and a BGA SSD "
        "package of 11.5 by 13 mm. Client form factors are cyan, data-center "
        "ones violet, and the 2.5-inch shell, used by both, amber.</desc>",
        f'<text class="f-mute" x="12" y="18" fill="{MUTE}">'
        "All outlines drawn to the same scale</text>",
    ]
    shapes, bottom1 = row(ROW1, 32, 20)
    out += shapes
    shapes, bottom2 = row(ROW2, bottom1 + 58, 28)
    out += shapes

    y = bottom2 + 62
    x = 24
    for label, kind in (("client", "client"), ("data center", "dc"),
                        ("both", "both")):
        cls, col = KIND[kind]
        out.append(f'<rect class="{cls}" x="{x}" y="{y - 10}" width="10" '
                   f'height="10" fill="{col}" fill-opacity=".22" '
                   f'stroke="{col}" stroke-width="1.5"/>')
        out.append(f'<text class="f-ink" x="{x + 16}" y="{y}" '
                   f'fill="{INK}">{label}</text>')
        x += 16 + len(label) * 7.5 + 18
    # scale bar: 10 mm
    bar = 10 * K
    x0 = 376 - bar
    out.append(f'<path class="f-line" d="M{x0:.1f},{y - 8} v6 H{x0 + bar:.1f} '
               f'v-6" fill="none" stroke="{LINE}" stroke-width="1.5"/>')
    out.append(f'<text class="f-mute" x="{x0 - 6:.1f}" y="{y}" '
               f'text-anchor="end" fill="{MUTE}">10 mm</text>')
    out.append("</svg>")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}  (height used: {y + 6:.0f} of 372)")


if __name__ == "__main__":
    main()
