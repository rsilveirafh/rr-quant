"""Gera o dashboard HTML da varredura diária (arquivo estático, self-contained)."""

from __future__ import annotations

import html

from .collect import Cotacao
from .analyze import Analise
from .tickers import INVERSOS


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


def _bloco_html(nome: str, cotacoes: list[Cotacao]) -> str:
    linhas = "\n".join(_linha(c) for c in cotacoes)
    return f"""<section class="bloco">
  <h2>{html.escape(nome)}</h2>
  <table>
    <thead><tr><th>Ativo</th><th>Ticker</th><th>Últ.</th><th>Var. dia</th></tr></thead>
    <tbody>
{linhas}
    </tbody>
  </table>
</section>"""


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
    cadeia = "".join(
        f'<div class="passo"><div class="passo-top"><span class="passo-tit">{html.escape(p.titulo)}</span>'
        f'<span class="passo-num">{html.escape(p.numero)}</span></div>'
        f'<div class="passo-txt">{html.escape(p.leitura)}</div></div>'
        for p in a.cadeia
    )
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

    notas_bloco = f'<div class="sub-card"><h3>Prévia externa</h3><ul class="notas">{notas}</ul></div>' if notas else ""

    return f"""<section class="leitura">
  <div class="regime {a.regime_classe}">
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
  {probs_bloco}
  {correl_bloco}
  {notas_bloco}
</section>"""


def gerar_html(blocos: dict[str, list[Cotacao]], analise: Analise,
               gerado_em: str, data_dados: str | None) -> str:
    secoes = "\n".join(_bloco_html(nome, cs) for nome, cs in blocos.items())
    todos = [c for cs in blocos.values() for c in cs]
    ok = sum(1 for c in todos if c.ok)
    rodape = (
        f"{ok}/{len(todos)} ativos com dado &middot; "
        f"último fechamento em torno de {data_dados or 'n/d'} &middot; "
        f"gerado {gerado_em} &middot; correlações e probabilidades são co-movimento "
        f"histórico (não previsão)"
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>rr-quant &middot; varredura do dia</title>
<style>
  :root {{
    --bg:#0e1116; --card:#171b22; --ink:#e6e9ef; --dim:#8b94a3; --line:#242a33;
    --up:#26a269; --down:#e0483e; --flat:#8b94a3;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{ --bg:#f5f6f8; --card:#fff; --ink:#1a1d23; --dim:#697586; --line:#e3e6ea; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.45 -apple-system,Segoe UI,Roboto,sans-serif; padding:24px; }}
  header, .leitura, .grid, footer {{ max-width:1100px; margin-left:auto; margin-right:auto; }}
  header {{ margin-bottom:18px; }}
  h1 {{ font-size:20px; margin:0 0 4px; letter-spacing:.3px; }}
  .sub {{ color:var(--dim); font-size:13px; }}

  /* --- Leitura do dia --- */
  .leitura {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
    gap:14px; margin-bottom:22px; }}
  .regime {{ grid-column:1/-1; background:var(--card); border:1px solid var(--line);
    border-left:5px solid var(--flat); border-radius:12px; padding:14px 18px; }}
  .regime.up {{ border-left-color:var(--up); }}
  .regime.down {{ border-left-color:var(--down); }}
  .regime-head {{ display:flex; align-items:center; gap:12px; margin-bottom:8px; }}
  .badge {{ font-size:15px; font-weight:800; letter-spacing:1px; padding:3px 12px;
    border-radius:6px; background:var(--flat); color:#fff; }}
  .regime.up .badge {{ background:var(--up); }}
  .regime.down .badge {{ background:var(--down); }}
  .amp {{ color:var(--dim); font-size:13px; }}
  .regime-bullets {{ margin:0; padding-left:18px; color:var(--ink); }}
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
  .passo-txt {{ color:var(--ink); opacity:.92; font-size:14px; margin-top:2px; }}
  .probs {{ display:grid; gap:10px; }}
  .prob {{ display:flex; align-items:baseline; gap:10px; }}
  .prob-num {{ font-size:22px; font-weight:800; min-width:56px; }}
  .prob.positivo .prob-num {{ color:var(--up); }}
  .prob.negativo .prob-num {{ color:var(--down); }}
  .prob-desc {{ font-size:14px; }}
  .prob-meta {{ color:var(--dim); font-size:12px; }}
  table.correl {{ width:100%; border-collapse:collapse; }}
  table.correl td {{ padding:5px 0; border-bottom:1px solid var(--line); font-size:14px; }}
  table.correl td.c {{ text-align:right; font-weight:700; font-variant-numeric:tabular-nums; }}
  table.correl tr:last-child td {{ border-bottom:0; }}
  .notas {{ margin:0; padding-left:18px; color:var(--ink); opacity:.92; font-size:14px; }}

  /* --- Grid de blocos --- */
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px; }}
  .bloco {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:14px 16px; }}
  .bloco h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.8px; color:var(--dim);
    margin:0 0 10px; }}
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
  <h1>rr-quant &middot; varredura do dia</h1>
  <div class="sub">Snapshot macro de mercados &mdash; variação do último fechamento vs. o anterior. <span class="inv">*</span> = alta costuma indicar aversão a risco (juros, volatilidade, USD/BRL).</div>
</header>
{_leitura_html(analise)}
<main class="grid">
{secoes}
</main>
<footer>{rodape}</footer>
</body>
</html>"""
