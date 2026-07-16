"""Gera o dashboard HTML da varredura diaria (arquivo estatico, self-contained)."""

from __future__ import annotations

import html

from .collect import Cotacao
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
    inv = ' <span class="inv" title="alta aqui costuma ser aversao a risco">*</span>' if c.ticker in INVERSOS else ""
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
    <thead><tr><th>Ativo</th><th>Ticker</th><th>Ult.</th><th>Var. dia</th></tr></thead>
    <tbody>
{linhas}
    </tbody>
  </table>
</section>"""


def gerar_html(blocos: dict[str, list[Cotacao]], gerado_em: str, data_dados: str | None) -> str:
    secoes = "\n".join(_bloco_html(nome, cs) for nome, cs in blocos.items())
    todos = [c for cs in blocos.values() for c in cs]
    ok = sum(1 for c in todos if c.ok)
    rodape = (
        f"{ok}/{len(todos)} ativos com dado &middot; "
        f"ultimo fechamento em torno de {data_dados or 'n/d'} &middot; "
        f"gerado {gerado_em}"
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
  header {{ max-width:1100px; margin:0 auto 20px; }}
  h1 {{ font-size:20px; margin:0 0 4px; letter-spacing:.3px; }}
  .sub {{ color:var(--dim); font-size:13px; }}
  .grid {{ max-width:1100px; margin:0 auto; display:grid;
    grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px; }}
  .bloco {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:14px 16px; }}
  h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.8px; color:var(--dim);
    margin:0 0 10px; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; font-size:11px; color:var(--dim); font-weight:600;
    padding:0 0 6px; border-bottom:1px solid var(--line); }}
  th:nth-child(3),th:nth-child(4),td.px,td.var {{ text-align:right; }}
  td {{ padding:6px 0; border-bottom:1px solid var(--line); font-variant-numeric:tabular-nums; }}
  tr:last-child td {{ border-bottom:0; }}
  .nome {{ font-weight:500; }}
  .tk {{ color:var(--dim); font-size:12px; }}
  .var {{ font-weight:700; white-space:nowrap; }}
  tr.up .var {{ color:var(--up); }}
  tr.down .var {{ color:var(--down); }}
  tr.flat .var, tr.na .var {{ color:var(--flat); }}
  tr.na td {{ opacity:.5; }}
  .inv {{ color:var(--dim); cursor:help; }}
  footer {{ max-width:1100px; margin:22px auto 0; color:var(--dim); font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>rr-quant &middot; varredura do dia</h1>
  <div class="sub">Snapshot macro de mercados &mdash; estrutura da leitura pre-mercado (Rebecca Parriao). Variacao = ultimo fechamento vs. anterior. <span class="inv">*</span> = alta costuma ser aversao a risco (juros/vol/USD-BRL).</div>
</header>
<main class="grid">
{secoes}
</main>
<footer>{rodape}</footer>
</body>
</html>"""
