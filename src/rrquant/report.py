"""Gera o dashboard HTML da varredura diária (arquivo estático, self-contained).

Layout largo, KPIs chamativos com gauge/sparklines, gráficos de barra em SVG/CSS.
MODO DALTÔNICO acessível: toda info crítica é redundante (cor + seta ▲▼ + sinal
+/−) e o botão troca p/ paleta colorblind-safe; gráficos herdam as cores via CSS.
"""

from __future__ import annotations

import html

from .collect import Cotacao
from .analyze import Analise
from .tickers import INVERSOS
from . import porques, charts


def _fmt_preco(v: float | None) -> str:
    if v is None:
        return "&mdash;"
    if abs(v) >= 1000:
        return f"{v:,.0f}".replace(",", ".")
    if abs(v) >= 1:
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{v:.4f}".replace(".", ",")


def _fmt_var(v: float | None) -> str:
    if v is None:
        return "&mdash;"
    return f"{v:+.2f}%".replace(".", ",")


def _classe(v: float | None) -> str:
    if v is None:
        return "na"
    if abs(v) < 0.01:
        return "flat"
    return "up" if v > 0 else "down"


def _seta(v: float | None) -> str:
    if v is None or abs(v) < 0.01:
        return ""
    return "▲" if v > 0 else "▼"


def _linha(c: Cotacao) -> str:
    v = c.var_pct
    inv = (' <span class="inv" title="alta aqui costuma indicar aversão a risco">*</span>'
           if c.ticker in INVERSOS else "")
    return (
        f'<tr class="{_classe(v)}">'
        f'<td class="nome">{html.escape(c.nome)}{inv}</td>'
        f'<td class="tk">{html.escape(c.ticker)}</td>'
        f'<td class="px">{_fmt_preco(c.ultimo)}</td>'
        f'<td class="var">{_seta(v)} {_fmt_var(v)}</td>'
        f"</tr>"
    )


def _bloco_html(nome: str, cotacoes: list[Cotacao], i: int) -> str:
    linhas = "\n".join(_linha(c) for c in cotacoes)
    sub = porques.BLOCO.get(nome, "")
    sub_html = f'<div class="bloco-sub">{html.escape(sub)}</div>' if sub else ""
    return f"""<section class="bloco b{i}">
  <h2>{html.escape(nome)}</h2>
  {sub_html}
  <table>
    <thead><tr><th>Ativo</th><th>Ticker</th><th>Últ.</th><th>Var. dia</th></tr></thead>
    <tbody>
{linhas}
    </tbody>
  </table>
</section>"""


def _passos_html(passos) -> str:
    out = []
    for p in passos:
        why = f'<div class="passo-why">💡 {html.escape(p.porque)}</div>' if p.porque else ""
        out.append(
            f'<div class="passo"><div class="passo-top">'
            f'<span class="passo-tit">{html.escape(p.titulo)}</span>'
            f'<span class="passo-num">{html.escape(p.numero)}</span></div>'
            f'<div class="passo-txt">{html.escape(p.leitura)}</div>{why}</div>'
        )
    return "".join(out)


def _fmt_ind(i) -> str:
    if not i.ok:
        return "&mdash;"
    if i.unidade == "mil":
        return f"{i.valor:.0f} mil"
    if "%" in i.unidade:
        s = f"{i.valor:.2f}%".replace(".", ",")
        return s + (" a.a." if "a.a." in i.unidade else "")
    return f"{i.valor:.2f}".replace(".", ",")


def _painel_ind(titulo: str, indicadores) -> str:
    itens = []
    for i in indicadores:
        extra = f' <span class="hint">({html.escape(i.extra)})</span>' if i.extra else ""
        why = f'<div class="ind-why">{html.escape(i.porque)}</div>' if i.porque else ""
        itens.append(
            f'<div class="ind"><div class="ind-top">'
            f'<span class="ind-nome">{html.escape(i.nome)}{extra}</span>'
            f'<span class="ind-val">{_fmt_ind(i)}</span></div>{why}</div>'
        )
    return f'<div class="macro-col"><h4>{html.escape(titulo)}</h4>{"".join(itens)}</div>'


def _macro_html(m) -> str:
    if m is None or not m.ok:
        return ""
    jr = (f'<span class="jr">juro real BR ~{m.juro_real:.1f}%</span>'.replace(".", ",")
          if m.juro_real is not None else "")
    leitura = "".join(f"<li>{html.escape(l)}</li>" for l in m.leitura)
    return f"""<div class="sub-card macro">
      <h3>Macro &mdash; inflação e juros <span class="hint">(FRED / BCB)</span> {jr}</h3>
      <div class="macro-cols">
        {_painel_ind("Estados Unidos", m.eua)}
        {_painel_ind("Brasil", m.brasil)}
      </div>
      <ul class="notas">{leitura}</ul>
    </div>"""


def _barras_prob(probs) -> str:
    """Probabilidades condicionais como barras horizontais com marcador da base."""
    rows = []
    for p in probs:
        sinal = "positivo" if p.lift > 1 else ("negativo" if p.lift < -1 else "neutro")
        rows.append(f"""<div class="bar-row">
      <div class="bar-lbl">{html.escape(p.descricao)}
        <span class="hint">base {p.base:.0f}% · {p.lift:+.0f} p.p. · n={p.n}</span></div>
      <div class="bar-track">
        <div class="bar-fill {sinal}" style="width:{p.p_cond:.0f}%"></div>
        <div class="bar-base" style="left:{p.base:.0f}%" title="base histórica {p.base:.0f}%"></div>
      </div>
      <div class="bar-val">{p.p_cond:.0f}%</div>
    </div>""")
    return f'<div class="barchart">{"".join(rows)}</div>'


def _barras_corr(correls) -> str:
    """Correlações como barras divergentes (0 no centro; + à direita, − à esquerda)."""
    rows = []
    for rot, c in correls:
        cc = max(-1.0, min(1.0, c))
        if cc >= 0:
            left, width, cls = 50.0, cc * 50.0, "pos"
        else:
            left, width, cls = 50.0 + cc * 50.0, -cc * 50.0, "neg"
        val = f"{c:+.2f}".replace(".", ",")
        rows.append(f"""<div class="bar-row">
      <div class="bar-lbl">{html.escape(rot)}</div>
      <div class="bar-track diverg">
        <div class="bar-zero"></div>
        <div class="bar-fill {cls}" style="left:{left:.1f}%;width:{width:.1f}%"></div>
      </div>
      <div class="bar-val">{val}</div>
    </div>""")
    return f'<div class="barchart">{"".join(rows)}</div>'


def _tile_ativo(idx, tk, titulo, ti, sparks, nota="") -> str | None:
    c = idx.get(tk)
    if not c or not c.ok:
        return None
    v = c.var_pct
    spark = charts.sparkline(sparks.get(tk, []), f"var(--b{ti})")
    nota_html = f' <span class="hint">{nota}</span>' if nota else ""
    return f"""<div class="kpi t{ti}">
    <div class="kpi-tit">{html.escape(titulo)}</div>
    <div class="kpi-big">{_fmt_preco(c.ultimo)}</div>
    <div class="kpi-var {_classe(v)}">{_seta(v)} {_fmt_var(v)}{nota_html}</div>
    {spark}
  </div>"""


def _kpis_html(idx, a: Analise) -> str:
    tiles = []
    # Placar (gauge) — o resumo-mor
    if a.placar:
        p = a.placar
        cor = {"up": "var(--up)", "down": "var(--down)", "flat": "var(--flat)"}[p.classe]
        vies = ("viés de alta" if p.classe == "up"
                else "viés de baixa" if p.classe == "down" else "sem viés claro")
        tiles.append(f"""<div class="kpi t0 wide">
    <div class="kpi-tit">Ibovespa &middot; próximo pregão</div>
    {charts.gauge(p.prob, cor)}
    <div class="kpi-sub">chance de fechar em alta &middot; {vies}<br>
      <span class="hint">base {p.base:.0f}% · acerto fora da amostra ~{p.acuracia:.0f}%</span></div>
  </div>""")
    # Regime
    tiles.append(f"""<div class="kpi t1">
    <div class="kpi-tit">Regime do dia</div>
    <div class="kpi-badge {a.regime_classe}">{html.escape(a.regime_rotulo)}</div>
    <div class="kpi-sub">{html.escape(a.amplitude)}</div>
  </div>""")
    # Ativos-chave
    for tk, titulo, ti, nota in [
        ("^VIX", "VIX · volatilidade", 2, "medo do mercado"),
        ("BRL=X", "USD/BRL · dólar", 3, ""),
        ("BZ=F", "Petróleo Brent", 4, ""),
    ]:
        t = _tile_ativo(idx, tk, titulo, ti, a.sparks, nota)
        if t:
            tiles.append(t)
    # Juro real
    if a.macro and a.macro.juro_real is not None:
        jr = f"{a.macro.juro_real:.1f}%".replace(".", ",")
        tiles.append(f"""<div class="kpi t5">
    <div class="kpi-tit">Juro real · Brasil</div>
    <div class="kpi-big">{jr}</div>
    <div class="kpi-sub">Selic &minus; IPCA 12m &middot; atrai renda fixa</div>
  </div>""")
    return f'<section class="kpis">{"".join(tiles)}</section>'


def _leitura_html(a: Analise) -> str:
    bullets = "".join(f"<li>{html.escape(b)}</li>" for b in a.regime_bullets)
    cadeia = _passos_html(a.cadeia)
    commodities = _passos_html(a.commodities)
    notas = "".join(f"<li>{html.escape(n)}</li>" for n in a.notas)

    probs_bloco = f"""<div class="sub-card">
      <h3>Bolsas mundiais → Ibovespa <span class="hint">(co-movimento histórico, 2 anos)</span></h3>
      {_barras_prob(a.probs)}
    </div>""" if a.probs else ""

    correl_bloco = f"""<div class="sub-card">
      <h3>Correlações-chave <span class="hint">(retornos diários, 2 anos)</span></h3>
      {_barras_corr(a.correls)}
    </div>""" if a.correls else ""

    notas_bloco = (f'<div class="sub-card"><h3>Prévia externa &amp; contexto</h3>'
                   f'<ul class="notas">{bullets}{notas}</ul></div>')

    return f"""<section class="leitura">
  <div class="sub-card cadeia">
    <h3>Cadeia de correlação <span class="hint">(o porquê)</span></h3>
    {cadeia}
  </div>
  <div class="sub-card cadeia">
    <h3>Commodities → setores <span class="hint">(read-through)</span></h3>
    {commodities}
  </div>
  {_macro_html(a.macro)}
  {probs_bloco}
  {correl_bloco}
  {notas_bloco}
</section>"""


def gerar_html(blocos: dict[str, list[Cotacao]], analise: Analise,
               gerado_em: str, data_dados: str | None) -> str:
    idx = {c.ticker: c for cs in blocos.values() for c in cs}
    secoes = "\n".join(_bloco_html(nome, cs, i) for i, (nome, cs) in enumerate(blocos.items()))
    todos = list(idx.values())
    ok = sum(1 for c in todos if c.ok)
    rodape = (
        f"{ok}/{len(todos)} ativos com dado &middot; "
        f"último fechamento em torno de {data_dados or 'n/d'} &middot; "
        f"gerado {gerado_em} &middot; correlações e probabilidades são co-movimento "
        f"histórico (não previsão)"
    )
    return f"""<!doctype html>
<html lang="pt-BR" data-cb="0">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>rr-quant &middot; varredura do dia</title>
<style>
  :root {{
    --bg:#0d1017; --card:#161b24; --ink:#eef1f6; --dim:#8b94a3; --line:#252c37;
    --up:#1ed760; --down:#ff4b5c; --flat:#8b94a3;
    --b0:#ff5d8f; --b1:#9b5cff; --b2:#00c2d8; --b3:#ffb020;
    --b4:#ff7a2f; --b5:#12d19e; --b6:#ff4d6d; --b7:#4d7dff;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{ --bg:#f4f6fa; --card:#fff; --ink:#161a21; --dim:#5d6b7d; --line:#e3e7ee;
      --up:#0f9d58; --down:#e02f44; }}
  }}
  html[data-cb="1"] {{
    --up:#0072B2; --down:#E69F00;
    --b0:#E69F00; --b1:#56B4E9; --b2:#009E73; --b3:#F0E442;
    --b4:#D55E00; --b5:#0072B2; --b6:#CC79A7; --b7:#999999;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.45 -apple-system,Segoe UI,Roboto,sans-serif; padding:22px 28px; }}
  header, .kpis, .leitura, .grid, footer {{ max-width:min(1600px, 96vw); margin-left:auto; margin-right:auto; }}
  header {{ margin-bottom:18px; display:flex; justify-content:space-between; align-items:flex-start; gap:16px; flex-wrap:wrap; }}
  h1 {{ font-size:22px; margin:0 0 4px; letter-spacing:.3px;
    background:linear-gradient(90deg,var(--b0),var(--b2),var(--b5));
    -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
  .sub {{ color:var(--dim); font-size:13px; max-width:820px; }}
  #cbtoggle {{ cursor:pointer; border:1px solid var(--line); background:var(--card);
    color:var(--ink); font-size:13px; font-weight:600; padding:8px 14px; border-radius:8px; white-space:nowrap; }}
  #cbtoggle:hover {{ border-color:var(--up); }}

  /* --- KPIs (topo) --- */
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
    gap:14px; margin-bottom:20px; align-items:stretch; }}
  .kpi {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:14px 16px; border-top:4px solid var(--tc,var(--flat)); display:flex;
    flex-direction:column; }}
  .kpi.wide {{ grid-column:span 2; }}
  .kpi.t0 {{ --tc:var(--b0); }} .kpi.t1 {{ --tc:var(--b1); }} .kpi.t2 {{ --tc:var(--b2); }}
  .kpi.t3 {{ --tc:var(--b3); }} .kpi.t4 {{ --tc:var(--b4); }} .kpi.t5 {{ --tc:var(--b5); }}
  .kpi-tit {{ font-size:11px; text-transform:uppercase; letter-spacing:.6px; color:var(--dim);
    font-weight:600; margin-bottom:6px; }}
  .kpi-big {{ font-size:32px; font-weight:800; line-height:1; font-variant-numeric:tabular-nums; }}
  .kpi-var {{ font-size:13px; font-weight:700; margin-top:4px; }}
  .kpi-var.up {{ color:var(--up); }} .kpi-var.down {{ color:var(--down); }}
  .kpi-var.flat, .kpi-var.na {{ color:var(--flat); }}
  .kpi-sub {{ font-size:12.5px; color:var(--dim); margin-top:6px; }}
  .kpi-badge {{ display:inline-block; font-size:20px; font-weight:800; letter-spacing:1px;
    padding:4px 14px; border-radius:8px; background:var(--flat); color:#fff; align-self:flex-start; }}
  .kpi-badge.up {{ background:var(--up); }} .kpi-badge.down {{ background:var(--down); }}
  .gauge {{ width:100%; max-width:220px; height:auto; align-self:center; }}
  .gauge-val {{ fill:var(--ink); font-weight:800; font-size:40px; }}
  .spark {{ width:100%; height:34px; margin-top:8px; color:var(--tc); }}

  /* --- Leitura --- */
  .leitura {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr));
    gap:14px; margin-bottom:22px; align-items:start; }}
  .sub-card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px; }}
  .sub-card h3 {{ font-size:13px; margin:0 0 10px; text-transform:uppercase; letter-spacing:.6px; color:var(--dim); }}
  .hint {{ text-transform:none; letter-spacing:0; font-weight:400; opacity:.8; }}
  .cadeia, .macro {{ grid-column:span 1; }}
  .passo {{ padding:9px 0; border-bottom:1px solid var(--line); }}
  .passo:last-child {{ border-bottom:0; }}
  .passo-top {{ display:flex; justify-content:space-between; gap:10px; }}
  .passo-tit {{ font-weight:700; }}
  .passo-num {{ font-variant-numeric:tabular-nums; color:var(--dim); }}
  .passo-txt {{ opacity:.95; font-size:14px; margin-top:2px; }}
  .passo-why {{ color:var(--dim); font-size:12.5px; margin-top:3px; font-style:italic; }}
  .macro {{ grid-column:1/-1; }}
  .macro-cols {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:22px; }}
  .macro-col h4 {{ font-size:12px; margin:0 0 6px; color:var(--dim); text-transform:uppercase; letter-spacing:.5px; }}
  .ind {{ padding:8px 0; border-bottom:1px solid var(--line); }}
  .ind:last-child {{ border-bottom:0; }}
  .ind-top {{ display:flex; justify-content:space-between; gap:10px; align-items:baseline; }}
  .ind-nome {{ font-weight:600; }}
  .ind-val {{ font-variant-numeric:tabular-nums; font-weight:700; }}
  .ind-why {{ color:var(--dim); font-size:12.5px; margin-top:2px; }}
  .jr {{ float:right; text-transform:none; letter-spacing:0; font-weight:700;
    background:var(--line); padding:2px 10px; border-radius:6px; font-size:12px; }}
  .notas {{ margin:0; padding-left:18px; opacity:.95; font-size:14px; }}
  .notas li {{ margin:3px 0; }}

  /* --- Gráficos de barra --- */
  .barchart {{ display:flex; flex-direction:column; gap:11px; }}
  .bar-row {{ display:grid; grid-template-columns:minmax(150px,46%) 1fr auto; gap:12px; align-items:center; }}
  .bar-lbl {{ font-size:13px; }}
  .bar-track {{ position:relative; height:16px; background:var(--line); border-radius:8px; overflow:hidden; }}
  .bar-fill {{ position:absolute; top:0; height:100%; border-radius:8px; }}
  .bar-fill.positivo {{ background:var(--up); }}
  .bar-fill.negativo {{ background:var(--down); }}
  .bar-fill.neutro {{ background:var(--flat); }}
  .bar-fill.pos {{ background:var(--up); }}
  .bar-fill.neg {{ background:var(--down); }}
  .bar-base {{ position:absolute; top:-2px; width:2px; height:20px; background:var(--ink); opacity:.65; }}
  .bar-track.diverg {{ overflow:visible; }}
  .bar-zero {{ position:absolute; left:50%; top:-2px; width:1px; height:20px; background:var(--dim); }}
  .bar-val {{ font-variant-numeric:tabular-nums; font-weight:700; min-width:44px; text-align:right; }}

  /* --- Grid de blocos --- */
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:16px; }}
  .bloco {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:14px 16px; border-top:4px solid var(--accent, var(--flat)); }}
  .b0 {{ --accent:var(--b0); }} .b1 {{ --accent:var(--b1); }} .b2 {{ --accent:var(--b2); }}
  .b3 {{ --accent:var(--b3); }} .b4 {{ --accent:var(--b4); }} .b5 {{ --accent:var(--b5); }}
  .b6 {{ --accent:var(--b6); }} .b7 {{ --accent:var(--b7); }}
  .bloco h2 {{ font-size:14px; letter-spacing:.4px; margin:0 0 4px; color:var(--accent); font-weight:700; }}
  .bloco-sub {{ color:var(--dim); font-size:11.5px; margin:0 0 10px; line-height:1.35; }}
  .bloco table {{ width:100%; border-collapse:collapse; }}
  .bloco th {{ text-align:left; font-size:11px; color:var(--dim); font-weight:600; padding:0 0 6px; border-bottom:1px solid var(--line); }}
  .bloco th:nth-child(3), .bloco th:nth-child(4), td.px, td.var {{ text-align:right; }}
  .bloco td {{ padding:6px 0; border-bottom:1px solid var(--line); font-variant-numeric:tabular-nums; }}
  .bloco tr:last-child td {{ border-bottom:0; }}
  .nome {{ font-weight:500; }}
  .tk {{ color:var(--dim); font-size:12px; }}
  .var {{ font-weight:700; white-space:nowrap; }}
  tr.up .var {{ color:var(--up); }} tr.down .var {{ color:var(--down); }}
  tr.flat .var, tr.na .var {{ color:var(--flat); }}
  tr.na td {{ opacity:.5; }}
  .inv {{ color:var(--dim); cursor:help; }}
  footer {{ margin-top:22px; color:var(--dim); font-size:12px; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>rr-quant &middot; varredura do dia</h1>
    <div class="sub">Snapshot macro de mercados &mdash; variação do último fechamento vs. o anterior. Toda variação traz seta (▲▼) e sinal (+/−) além da cor. <span class="inv">*</span> = alta costuma indicar aversão a risco.</div>
  </div>
  <button id="cbtoggle" onclick="toggleCB()" aria-pressed="false">♿ Modo daltônico</button>
</header>
{_kpis_html(idx, analise)}
{_leitura_html(analise)}
<main class="grid">
{secoes}
</main>
<footer>{rodape}</footer>
<script>
  function applyCB(on) {{
    document.documentElement.setAttribute('data-cb', on ? '1' : '0');
    var b = document.getElementById('cbtoggle');
    b.textContent = on ? '🎨 Modo colorido' : '♿ Modo daltônico';
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    try {{ localStorage.setItem('rrq-cb', on ? '1' : '0'); }} catch (e) {{}}
  }}
  function toggleCB() {{ applyCB(document.documentElement.getAttribute('data-cb') !== '1'); }}
  try {{ applyCB(localStorage.getItem('rrq-cb') === '1'); }} catch (e) {{}}
</script>
</body>
</html>"""
