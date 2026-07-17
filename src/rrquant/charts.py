"""Gráficos em SVG inline (sem dependência externa, funciona offline).

Usam variáveis CSS (var(--up), var(--down), var(--accent)…) e currentColor, então
herdam o tema claro/escuro E o modo daltônico automaticamente.
"""

from __future__ import annotations

import math


def gauge(pct: float, cor: str = "var(--up)") -> str:
    """Medidor semicircular 0–100 com o valor em destaque no centro."""
    pct = max(0.0, min(100.0, pct))
    a = math.radians(180 * (1 - pct / 100))          # 180°=esq(0) … 0°=dir(100)
    x = 100 + 90 * math.cos(a)
    y = 100 - 90 * math.sin(a)
    val = f"{pct:.0f}%"
    return f"""<svg class="gauge" viewBox="0 0 200 116" role="img" aria-label="{val}">
  <path d="M10,100 A90,90 0 0 1 190,100" fill="none" stroke="var(--line)" stroke-width="15" stroke-linecap="round"/>
  <path d="M10,100 A90,90 0 0 1 {x:.1f},{y:.1f}" fill="none" stroke="{cor}" stroke-width="15" stroke-linecap="round"/>
  <text x="100" y="92" text-anchor="middle" class="gauge-val">{val}</text>
</svg>"""


def sparkline(vals: list[float], cor: str = "currentColor") -> str:
    """Mini-linha (últimos N pontos), normalizada, com área suave."""
    if not vals or len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    w, h, pad = 120.0, 30.0, 3.0
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = pad + (w - 2 * pad) * i / (n - 1)
        yv = pad + (h - 2 * pad) * (1 - (v - lo) / rng)
        pts.append((x, yv))
    linha = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pts[0][0]:.1f},{h} " + linha + f" {pts[-1][0]:.1f},{h}"
    return f"""<svg class="spark" viewBox="0 0 {w:.0f} {h:.0f}" preserveAspectRatio="none" aria-hidden="true">
  <polygon points="{area}" fill="{cor}" opacity="0.12"/>
  <polyline points="{linha}" fill="none" stroke="{cor}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>
</svg>"""
