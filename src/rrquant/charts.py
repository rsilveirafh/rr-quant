"""Gráficos em SVG inline (sem dependência externa, funciona offline).

Usam variáveis CSS (var(--up), var(--down), var(--accent)…) e currentColor, então
herdam o tema claro/escuro E o modo daltônico automaticamente.
"""

from __future__ import annotations

import math


def _pt(p: float) -> tuple[float, float]:
    """Ponto no semicírculo p/ a posição p (0=esq … 100=dir)."""
    a = math.radians(180 * (1 - p / 100))
    return 100 + 90 * math.cos(a), 100 - 90 * math.sin(a)


def gauge(pct: float, cor: str = "var(--up)",
          z_baixa: float = 47, z_alta: float = 53) -> str:
    """Medidor de viés semicircular: baixa (esq) → estável (meio) → alta (dir).

    As zonas são coloridas (vermelho/cinza/verde, ou azul/cinza/laranja no modo
    daltônico) e um marcador aponta a probabilidade de o Ibov fechar em alta.
    """
    pct = max(0.0, min(100.0, pct))

    def arco(p0, p1, color, w=14, op=1.0):
        x0, y0 = _pt(p0)
        x1, y1 = _pt(p1)
        return (f'<path d="M{x0:.1f},{y0:.1f} A90,90 0 0 1 {x1:.1f},{y1:.1f}" '
                f'fill="none" stroke="{color}" stroke-width="{w}" opacity="{op}"/>')

    zonas = (arco(0, z_baixa, "var(--down)")
             + arco(z_baixa, z_alta, "var(--flat)")
             + arco(z_alta, 100, "var(--up)"))
    mx, my = _pt(pct)
    marcador = (f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="8" fill="var(--ink)" '
                f'stroke="var(--card)" stroke-width="3"/>')
    val = f"{pct:.0f}%"
    labels = ('<text x="4" y="114" class="g-lbl" text-anchor="start">baixa</text>'
              '<text x="100" y="12" class="g-lbl" text-anchor="middle">estável</text>'
              '<text x="196" y="114" class="g-lbl" text-anchor="end">alta</text>')
    return f"""<svg class="gauge" viewBox="0 0 200 120" role="img" aria-label="probabilidade {val}">
  {zonas}{marcador}
  <text x="100" y="84" text-anchor="middle" class="gauge-val" fill="{cor}">{val}</text>
  {labels}
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
