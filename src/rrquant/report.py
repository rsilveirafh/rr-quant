"""Gera o dashboard HTML da varredura diária (arquivo estático, self-contained).

Cores vibrantes por bloco + MODO DALTÔNICO acessível:
- toda informação crítica é redundante (cor + seta ▲▼ + sinal +/−), então nunca
  depende só da cor;
- botão no topo alterna p/ paleta colorblind-safe (azul/laranja no lugar de
  verde/vermelho; acentos da paleta Okabe-Ito) e persiste em localStorage.
"""

from __future__ import annotations

import html

from .collect import Cotacao
from .analyze import Analise
from .tickers import INVERSOS
from . import porques


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


def _classe(c: Cotacao) -> str:
    v = c.var_pct
    if v is None:
        return "na"
    if abs(v) < 0.01:
        return "flat"
    return "up" if v > 0 else "down"


def _linha(c: Cotacao) -> str:
    seta = ""
    v = c.var_pct
    if v is not None and abs(v) >= 0.01:
        seta = "▲" if v > 0 else "▼"
    inv = (' <span class="inv" title="alta aqui costuma indicar aversão a risco">*</span>'
           if c.ticker in INVERSOS else "")
    return (
        f'<tr class="{_classe(c)}">'
        f'<td class="nome">{html.escape(c.nome)}{inv}</td>'
        f'<td class="tk">{html.escape(c.ticker)}</td>'
        f'<td class="px">{_fmt_preco(c.ultimo)}</td>'
        f'<td class="var">{seta} {_fmt_var(v)}</td>'
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


def _prob_html(p) -> str:
    lift = p.lift
    sinal = "positivo" if lift > 1 else ("negativo" if lift < -1 else "neutro")
    corr = f' · corr {p.corr:+.2f}'.replace(".", ",") if p.corr is not None else ""
    return (
        f'<div class="prob {sinal}">'
        f'<div class="prob-num">{p.p_cond:.0f}%</div>'
        f'<div class="prob-desc">{html.escape(p.descricao)}.'
        f'<span class="prob-meta"> base {p.base:.0f}% · '
        f'{p.lift:+.0f} p.p. · n={p.n}{corr}</span></div>'
        f'</div>'
    )


def _leitura_html(a: Analise) -> str:
    bullets = "".join(f"<li>{html.escape(b)}</li>" for b in a.regime_bullets)
    cadeia = _passos_html(a.cadeia)
    commodities = _passos_html(a.commodities)
    probs = "".join(_prob_html(p) for p in a.probs)
    correls = "".join(
        f'<tr><td>{html.escape(rot)}</td><td class="c">{c:+.2f}</td></tr>'.replace(".", ",")
        for rot, c in a.correls
    )
    notas = "".join(f"<li>{html.escape(n)}</li>" for n in a.notas)

    probs_bloco = f"""<div class="sub-card">
      <h3>Bolsas mundiais → Ibovespa <span class="hint">(co-movimento histórico, 2 anos)</span></h3>
      <div class="probs">{probs}</div>
    </div>""" if probs else ""

    correl_bloco = f"""<div class="sub-card">
      <h3>Correlações-chave <span class="hint">(retornos diários, 2 anos)</span></h3>
      <table class="correl"><tbody>{correls}</tbody></table>
    </div>""" if correls else ""

    notas_bloco = (f'<div class="sub-card"><h3>Prévia externa</h3>'
                   f'<ul class="notas">{notas}</ul></div>') if notas else ""

    p = a.placar
    if p:
        drivers = ", ".join(
            f"{html.escape(n)} {seta} (a {fav})" for n, seta, fav in p.drivers) or "&mdash;"
        vies = ("viés de alta" if p.classe == "up"
                else "viés de baixa" if p.classe == "down" else "sem viés claro")
        hero = f"""<div class="placar">
      <div class="placar-num">{p.prob:.0f}%</div>
      <div class="placar-lbl">de chance de o <b>Ibovespa fechar em alta</b> no próximo pregão &mdash; {vies}
        <span class="placar-meta">base histórica {p.base:.0f}% &middot; acerto fora da amostra ~{p.acuracia:.0f}% &middot; regressão logística sobre {p.n} dias &middot; estimativa estatística, não garantia</span>
      </div>
    </div>
    <div class="placar-drivers">Principais vieses de hoje: {drivers}</div>"""
        top_classe = p.classe
    else:
        hero = ""
        top_classe = a.regime_classe

    return f"""<section class="leitura">
  <div class="regime {top_classe}">
    {hero}
    <div class="regime-head">
      <span class="badge">{html.escape(a.regime_rotulo)}</span>
      <span class="amp">{html.escape(a.amplitude)}</span>
    </div>
    <ul class="regime-bullets">{bullets}</ul>
  </div>
  <div class="sub-card cadeia">
    <h3>Cadeia de correlação <span class="hint">(o porquê)</span></h3>
    {cadeia}
  </div>
  {_macro_html(a.macro)}
  <div class="sub-card cadeia">
    <h3>Commodities → setores <span class="hint">(read-through)</span></h3>
    {commodities}
  </div>
  {probs_bloco}
  {correl_bloco}
  {notas_bloco}
</section>"""


def gerar_html(blocos: dict[str, list[Cotacao]], analise: Analise,
               gerado_em: str, data_dados: str | None) -> str:
    secoes = "\n".join(_bloco_html(nome, cs, i) for i, (nome, cs) in enumerate(blocos.items()))
    todos = [c for cs in blocos.values() for c in cs]
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
    /* acentos vibrantes por bloco (modo colorido) */
    --b0:#ff5d8f; --b1:#9b5cff; --b2:#00c2d8; --b3:#ffb020;
    --b4:#ff7a2f; --b5:#12d19e; --b6:#ff4d6d; --b7:#4d7dff;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{ --bg:#f4f6fa; --card:#fff; --ink:#161a21; --dim:#5d6b7d; --line:#e3e7ee;
      --up:#0f9d58; --down:#e02f44; }}
  }}
  /* MODO DALTÔNICO — paleta colorblind-safe (azul/laranja + Okabe-Ito) */
  html[data-cb="1"] {{
    --up:#0072B2; --down:#E69F00;
    --b0:#E69F00; --b1:#56B4E9; --b2:#009E73; --b3:#F0E442;
    --b4:#D55E00; --b5:#0072B2; --b6:#CC79A7; --b7:#999999;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.45 -apple-system,Segoe UI,Roboto,sans-serif; padding:24px; }}
  header, .leitura, .grid, footer {{ max-width:1160px; margin-left:auto; margin-right:auto; }}
  header {{ margin-bottom:18px; display:flex; justify-content:space-between; align-items:flex-start; gap:16px; flex-wrap:wrap; }}
  h1 {{ font-size:21px; margin:0 0 4px; letter-spacing:.3px;
    background:linear-gradient(90deg,var(--b0),var(--b2),var(--b5));
    -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
  .sub {{ color:var(--dim); font-size:13px; max-width:720px; }}
  #cbtoggle {{ cursor:pointer; border:1px solid var(--line); background:var(--card);
    color:var(--ink); font-size:13px; font-weight:600; padding:8px 14px; border-radius:8px;
    white-space:nowrap; }}
  #cbtoggle:hover {{ border-color:var(--up); }}

  /* --- Leitura do dia --- */
  .leitura {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
    gap:14px; margin-bottom:22px; }}
  .regime {{ grid-column:1/-1; background:var(--card); border:1px solid var(--line);
    border-left:6px solid var(--flat); border-radius:12px; padding:14px 18px; }}
  .regime.up {{ border-left-color:var(--up); }}
  .regime.down {{ border-left-color:var(--down); }}
  .placar {{ display:flex; align-items:center; gap:16px; margin-bottom:10px; }}
  .placar-num {{ font-size:46px; font-weight:800; line-height:1; font-variant-numeric:tabular-nums; }}
  .regime.up .placar-num {{ color:var(--up); }}
  .regime.down .placar-num {{ color:var(--down); }}
  .regime.flat .placar-num {{ color:var(--flat); }}
  .placar-lbl {{ font-size:15px; }}
  .placar-meta {{ display:block; color:var(--dim); font-size:12px; margin-top:3px; }}
  .placar-drivers {{ font-size:13px; opacity:.92; margin-bottom:10px; }}
  .regime-head {{ display:flex; align-items:center; gap:12px; margin-bottom:8px; }}
  .badge {{ font-size:16px; font-weight:800; letter-spacing:1px; padding:4px 14px;
    border-radius:7px; background:var(--flat); color:#fff; }}
  .regime.up .badge {{ background:var(--up); }}
  .regime.down .badge {{ background:var(--down); }}
  .amp {{ color:var(--dim); font-size:13px; }}
  .regime-bullets {{ margin:0; padding-left:18px; }}
  .regime-bullets li {{ margin:2px 0; }}
  .sub-card {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:14px 16px; }}
  .sub-card h3 {{ font-size:13px; margin:0 0 10px; text-transform:uppercase;
    letter-spacing:.6px; color:var(--dim); }}
  .hint {{ text-transform:none; letter-spacing:0; font-weight:400; opacity:.8; }}
  .cadeia {{ grid-column:1/-1; }}
  .passo {{ padding:9px 0; border-bottom:1px solid var(--line); }}
  .passo:last-child {{ border-bottom:0; }}
  .passo-top {{ display:flex; justify-content:space-between; gap:10px; }}
  .passo-tit {{ font-weight:700; }}
  .passo-num {{ font-variant-numeric:tabular-nums; color:var(--dim); }}
  .passo-txt {{ opacity:.95; font-size:14px; margin-top:2px; }}
  .passo-why {{ color:var(--dim); font-size:12.5px; margin-top:3px; font-style:italic; }}
  .probs {{ display:grid; gap:10px; }}
  .prob {{ display:flex; align-items:baseline; gap:10px; }}
  .prob-num {{ font-size:23px; font-weight:800; min-width:58px; }}
  .prob.positivo .prob-num {{ color:var(--up); }}
  .prob.negativo .prob-num {{ color:var(--down); }}
  .prob-desc {{ font-size:14px; }}
  .prob-meta {{ color:var(--dim); font-size:12px; }}
  table.correl {{ width:100%; border-collapse:collapse; }}
  table.correl td {{ padding:5px 0; border-bottom:1px solid var(--line); font-size:14px; }}
  table.correl td.c {{ text-align:right; font-weight:700; font-variant-numeric:tabular-nums; }}
  table.correl tr:last-child td {{ border-bottom:0; }}
  .notas {{ margin:8px 0 0; padding-left:18px; opacity:.95; font-size:14px; }}
  .macro {{ grid-column:1/-1; }}
  .macro-cols {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:22px; }}
  .macro-col h4 {{ font-size:12px; margin:0 0 6px; color:var(--dim); text-transform:uppercase;
    letter-spacing:.5px; }}
  .ind {{ padding:8px 0; border-bottom:1px solid var(--line); }}
  .ind:last-child {{ border-bottom:0; }}
  .ind-top {{ display:flex; justify-content:space-between; gap:10px; align-items:baseline; }}
  .ind-nome {{ font-weight:600; }}
  .ind-val {{ font-variant-numeric:tabular-nums; font-weight:700; }}
  .ind-why {{ color:var(--dim); font-size:12.5px; margin-top:2px; }}
  .jr {{ float:right; text-transform:none; letter-spacing:0; font-weight:700;
    background:var(--line); padding:2px 10px; border-radius:6px; font-size:12px; }}

  /* --- Grid de blocos --- */
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:16px; }}
  .bloco {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:14px 16px; border-top:4px solid var(--accent, var(--flat)); }}
  .b0 {{ --accent:var(--b0); }} .b1 {{ --accent:var(--b1); }} .b2 {{ --accent:var(--b2); }}
  .b3 {{ --accent:var(--b3); }} .b4 {{ --accent:var(--b4); }} .b5 {{ --accent:var(--b5); }}
  .b6 {{ --accent:var(--b6); }} .b7 {{ --accent:var(--b7); }}
  .bloco h2 {{ font-size:14px; letter-spacing:.4px; margin:0 0 4px; color:var(--accent); font-weight:700; }}
  .bloco-sub {{ color:var(--dim); font-size:11.5px; margin:0 0 10px; line-height:1.35; }}
  .bloco table {{ width:100%; border-collapse:collapse; }}
  .bloco th {{ text-align:left; font-size:11px; color:var(--dim); font-weight:600;
    padding:0 0 6px; border-bottom:1px solid var(--line); }}
  .bloco th:nth-child(3), .bloco th:nth-child(4), td.px, td.var {{ text-align:right; }}
  .bloco td {{ padding:6px 0; border-bottom:1px solid var(--line);
    font-variant-numeric:tabular-nums; }}
  .bloco tr:last-child td {{ border-bottom:0; }}
  .nome {{ font-weight:500; }}
  .tk {{ color:var(--dim); font-size:12px; }}
  .var {{ font-weight:700; white-space:nowrap; }}
  tr.up .var {{ color:var(--up); }}
  tr.down .var {{ color:var(--down); }}
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
  function toggleCB() {{
    applyCB(document.documentElement.getAttribute('data-cb') !== '1');
  }}
  try {{ applyCB(localStorage.getItem('rrq-cb') === '1'); }} catch (e) {{}}
</script>
</body>
</html>"""
