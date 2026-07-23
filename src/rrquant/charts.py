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


def hist_prob(pontos: list[tuple[str, float, bool]]) -> str:
    """Linha da probabilidade prevista ao longo dos dias (walk-forward).

    Pontos = [(data, prob%, subiu?)]. A linha é a probabilidade; cada ponto é
    colorido pelo que o Ibov REALMENTE fez naquele dia (verde=subiu, vermelho=caiu).
    Se a linha fica alta nos dias verdes e baixa nos vermelhos, há sinal.
    """
    if len(pontos) < 2:
        return ""
    W, H = 840.0, 220.0
    pl, pr, pt, pb = 34.0, 12.0, 14.0, 24.0
    n = len(pontos)
    xs = [pl + (W - pl - pr) * i / (n - 1) for i in range(n)]

    def yy(p):
        return pt + (H - pt - pb) * (1 - p / 100.0)

    probs = [q for _d, q, _u in pontos]
    linha = " ".join(f"{x:.1f},{yy(q):.1f}" for x, q in zip(xs, probs))
    area = f"{xs[0]:.1f},{yy(probs[0]):.1f} " + linha + f" {xs[-1]:.1f},{H - pb:.1f} {xs[0]:.1f},{H - pb:.1f}"

    grid = ""
    for gv in (0, 50, 100):
        y = yy(gv)
        dash = ' stroke-dasharray="5,4"' if gv == 50 else ""
        grid += (f'<line x1="{pl}" y1="{y:.1f}" x2="{W - pr}" y2="{y:.1f}" '
                 f'stroke="var(--line)" stroke-width="1"{dash}/>'
                 f'<text x="{pl - 6}" y="{y + 3:.1f}" text-anchor="end" class="ax">{gv}</text>')

    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{yy(q):.1f}" r="3.2" '
        f'fill="{"var(--up)" if u else "var(--down)"}"/>'
        for x, (_d, q, u) in zip(xs, pontos)
    )
    d0, d1 = pontos[0][0], pontos[-1][0]
    eixo_x = (f'<text x="{pl}" y="{H - 4:.0f}" text-anchor="start" class="ax">{d0}</text>'
              f'<text x="{W - pr}" y="{H - 4:.0f}" text-anchor="end" class="ax">{d1}</text>')
    return f"""<svg class="histchart" viewBox="0 0 {W:.0f} {H:.0f}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="histórico da probabilidade">
  {grid}
  <polygon points="{area}" fill="var(--b0)" opacity="0.10"/>
  <polyline points="{linha}" fill="none" stroke="var(--b0)" stroke-width="2" stroke-linejoin="round"/>
  {dots}
  {eixo_x}
</svg>"""


def _fmt_px(v: float) -> str:
    if abs(v) >= 1000:
        return f"{v:,.0f}".replace(",", ".")
    if abs(v) >= 1:
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{v:.4f}".replace(".", ",")


def candles(smc) -> str:
    """Candlestick em SVG com a estrutura SMC desenhada por cima: marcadores de
    swing (fractais) e linhas tracejadas de BOS/CHoCH no nível rompido, rotuladas
    e coloridas por direção (herdam --up/--down, logo o modo daltônico)."""
    df = smc.df
    o, h = df["Open"].values, df["High"].values
    l, c = df["Low"].values, df["Close"].values
    n = len(df)
    if n < 2:
        return ""

    W, H = 1520.0, 470.0
    pl, pr, pt, pb = 10.0, 74.0, 16.0, 30.0
    lo, hi = float(l.min()), float(h.max())
    span = (hi - lo) or 1.0
    lo -= span * 0.06
    hi += span * 0.06

    def X(i):
        return pl + (W - pl - pr) * (i + 0.5) / n

    def Y(p):
        return pt + (H - pt - pb) * (1 - (p - lo) / (hi - lo))

    cw = max(1.4, (W - pl - pr) / n * 0.62)

    grade = ""
    for k in range(5):
        pv = lo + (hi - lo) * k / 4
        y = Y(pv)
        grade += (f'<line x1="{pl}" y1="{y:.1f}" x2="{W - pr}" y2="{y:.1f}" stroke="var(--line)" stroke-width="1"/>'
                  f'<text x="{W - pr + 6}" y="{y + 3:.1f}" class="ax" text-anchor="start">{_fmt_px(pv)}</text>')

    velas = []
    for i in range(n):
        x = X(i)
        cls = "up" if c[i] >= o[i] else "down"
        yo, yc = Y(o[i]), Y(c[i])
        top, alt = min(yo, yc), max(1.0, abs(yc - yo))
        velas.append(
            f'<line x1="{x:.1f}" y1="{Y(h[i]):.1f}" x2="{x:.1f}" y2="{Y(l[i]):.1f}" class="wick {cls}"/>'
            f'<rect x="{x - cw / 2:.1f}" y="{top:.1f}" width="{cw:.1f}" height="{alt:.1f}" class="body {cls}"/>'
        )

    sw = []
    for s in smc.swings:
        x = X(s.idx)
        if s.tipo == "H":
            sw.append(f'<circle cx="{x:.1f}" cy="{Y(s.preco) - 7:.1f}" r="2.6" class="sw-h"/>')
        else:
            sw.append(f'<circle cx="{x:.1f}" cy="{Y(s.preco) + 7:.1f}" r="2.6" class="sw-l"/>')

    ev = []
    for e in smc.eventos:
        x0, x1, y = X(e.origem), X(e.idx), Y(e.nivel)
        cls = "up" if e.direcao == "alta" else "down"
        ev.append(
            f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" class="ev {cls}" stroke-dasharray="4,3"/>'
            f'<text x="{x1 + 3:.1f}" y="{y - 4:.1f}" class="ev-lbl {cls}">{e.tipo}</text>'
        )

    d0 = df.index[0].strftime("%d/%m")
    d1 = df.index[-1].strftime("%d/%m")
    eixo = (f'<text x="{pl}" y="{H - 8:.0f}" class="ax" text-anchor="start">{d0}</text>'
            f'<text x="{W - pr}" y="{H - 8:.0f}" class="ax" text-anchor="end">{d1}</text>')

    return f"""<svg class="candles" viewBox="0 0 {W:.0f} {H:.0f}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="candlestick com estrutura SMC">
  {grade}
  {''.join(velas)}
  {''.join(sw)}
  {''.join(ev)}
  {eixo}
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
