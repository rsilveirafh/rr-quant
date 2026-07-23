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


def _barras_diverg(items) -> str:
    """Barras divergentes (0 no centro) normalizadas pelo maior |valor|.
    Positivo → direita (alta); negativo → esquerda (baixa)."""
    if not items:
        return ""
    maxabs = max(abs(v) for _n, v in items) or 1.0
    rows = []
    for nome, v in sorted(items, key=lambda t: -abs(t[1])):
        frac = v / maxabs
        if frac >= 0:
            left, width, cls, lado = 50.0, frac * 50.0, "pos", "↑ alta"
        else:
            left, width, cls, lado = 50.0 + frac * 50.0, -frac * 50.0, "neg", "↓ baixa"
        rows.append(f"""<div class="bar-row">
      <div class="bar-lbl">{html.escape(nome)}</div>
      <div class="bar-track diverg">
        <div class="bar-zero"></div>
        <div class="bar-fill {cls}" style="left:{left:.1f}%;width:{max(width,0.6):.1f}%"></div>
      </div>
      <div class="bar-val {cls}">{lado}</div>
    </div>""")
    return f'<div class="barchart">{"".join(rows)}</div>'


def _barras_peso(pesos) -> str:
    """Barras simples do peso (|coeficiente|) de cada variável no modelo."""
    if not pesos:
        return ""
    mx = max(v for _n, v in pesos) or 1.0
    rows = []
    for nome, v in sorted(pesos, key=lambda t: -t[1]):
        val = f"{v:.2f}".replace(".", ",")
        rows.append(f"""<div class="bar-row">
      <div class="bar-lbl">{html.escape(nome)}</div>
      <div class="bar-track"><div class="bar-fill neutro" style="width:{v / mx * 100:.0f}%"></div></div>
      <div class="bar-val">{val}</div>
    </div>""")
    return f'<div class="barchart">{"".join(rows)}</div>'


def _historico_html(a: Analise) -> str:
    if not a.hist_prob:
        return ""
    hits, total = a.hist_acerto
    pct = (hits / total * 100) if total else 0
    return f"""<div class="sub-card full">
    <h3>Histórico da probabilidade <span class="hint">(walk-forward: cada dia previsto só com o passado &middot; {total} pregões)</span></h3>
    {charts.hist_prob(a.hist_prob)}
    <div class="hist-legend">
      <span><span class="dot up"></span> Ibovespa subiu no dia</span>
      <span><span class="dot down"></span> Ibovespa caiu</span>
      <span class="hint">linha 50% = moeda ao ar &middot; acertou <b>{hits}/{total}</b> ({pct:.0f}%) — se a linha fica alta nos dias verdes e baixa nos vermelhos, há sinal</span>
    </div>
  </div>"""


def _analise_placar_html(a: Analise) -> str:
    """Card que explica COMO o placar chegou no número de hoje + histórico."""
    p = a.placar
    if not p or not p.contribs:
        return ""
    return f"""<section class="analise">
  <div class="sub-card full">
    <h3>Como o placar chegou nos {p.prob:.0f}% <span class="hint">(contribuição de cada variável hoje, em log-odds)</span></h3>
    {_barras_diverg(p.contribs)}
    <div class="analise-nota">À direita, a variável empurra a probabilidade para <b>alta</b>; à esquerda, para <b>baixa</b>. Os sinais saem do modelo conjunto (regressão logística), então podem diferir da leitura isolada de cada fator. Veja a aba <b>Metodologia</b> para como tudo é construído.</div>
  </div>
  {_historico_html(a)}
</section>"""


def _metodo_html(a: Analise) -> str:
    p = a.placar
    pesos = _barras_peso(p.pesos) if p and p.pesos else "<p class='hint'>Modelo indisponível nesta execução.</p>"
    n = p.n if p else "—"
    acc = f"{p.acuracia:.0f}%" if p else "—"
    base = f"{p.base:.0f}%" if p else "—"
    return f"""<section class="tab metodo" id="tab-metodo" hidden>
  <div class="sub-card full">
    <h3>Como o placar do próximo pregão é medido</h3>
    <p><b>O que é o "próximo pregão".</b> É a próxima sessão de negociação do Ibovespa.
    Se você roda o dashboard <i>depois</i> do fechamento, é o dia seguinte; se roda de manhã
    <i>antes</i> da abertura, é a sessão que vai abrir. O alvo do modelo é uma pergunta
    simples: <b>qual a probabilidade de o Ibovespa fechar em alta nessa sessão?</b></p>

    <p><b>Por que não é "adivinhar o futuro".</b> Prever a direção do Ibov <i>amanhã</i> a
    partir dos dados de <i>hoje</i> não funciona (testamos: dá ~45% fora da amostra, pior que
    cara-ou-coroa). O que funciona é ler os <b>sinais que ANTECEDEM a abertura</b> — o "tape"
    global que já aconteceu antes do Ibov negociar.</p>

    <h4>As {len(a.placar.pesos) if a.placar and a.placar.pesos else 5} variáveis levadas em conta</h4>
    <ul class="metodo-vars">
      <li><b>Ásia</b> (Nikkei, Hang Seng, Kospi) — fecham de madrugada, antes do Ibov abrir. Primeiro humor do dia.</li>
      <li><b>Europa</b> (DAX, Eurostoxx 50) — abrem na nossa manhã, ainda antes do Ibov.</li>
      <li><b>S&P 500 (ontem)</b> — o fechamento de <i>ontem</i> em NY. Entra defasado 1 dia porque NY negocia junto/depois do Ibov (usar o de hoje seria "espiar o futuro").</li>
      <li><b>EWZ (ontem)</b> — ações brasileiras negociadas em NY; prévia dolarizada, também do fechamento de ontem.</li>
      <li><b>DXY</b> — força do dólar no mundo; dólar forte tira fluxo de emergentes.</li>
    </ul>

    <h4>Peso de cada variável no modelo</h4>
    <p class="hint">Quanto cada fator influencia a probabilidade (|coeficiente padronizado| da regressão logística). Quanto maior, mais o modelo se apoia nele.</p>
    {pesos}

    <h4>O modelo</h4>
    <p>Uma <b>regressão logística</b> (o método padrão de econometria para prever direção
    sobe/desce) treinada em <b>{n} pregões</b> (~2 anos) sobre essas 5 variáveis. Ela aprende
    o peso de cada sinal e devolve uma probabilidade de 0 a 100%. Implementada direto com
    numpy; equivalente ao que <code>statsmodels</code>/<code>scikit-learn</code> (Python) ou
    <code>glm</code> (R) fazem.</p>

    <h4>Validação honesta</h4>
    <p>A acurácia mostrada é <b>fora da amostra</b> (split cronológico 80/20: treina nos
    primeiros 80% dos dias, testa nos 20% finais que o modelo nunca viu). Hoje: <b>~{acc}</b>,
    contra uma base de <b>{base}</b> (a frequência histórica de dias de alta). O <i>edge</i> é
    pequeno e real — não é bola de cristal. <b>É estimativa estatística, não garantia.</b></p>

    <h4>Como ler o medidor</h4>
    <p>O semicírculo é um <b>medidor de viés</b>: <span class="z-down">esquerda = viés de
    baixa</span>, <span class="z-flat">meio = estável</span>, <span class="z-up">direita =
    viés de alta</span>. O marcador aponta a probabilidade estimada; 50% é moeda ao ar.</p>

    <h4>Fontes de dados</h4>
    <p class="hint">Preços e índices: yfinance (Yahoo Finance). Macro EUA: FRED. Macro Brasil
    (Selic, CDI, IPCA): Banco Central (SGS). Tudo via API pública, dados de fechamento (EOD).</p>
  </div>
</section>"""


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

    notas_bloco = (f'<div class="sub-card full"><h3>Prévia externa &amp; contexto</h3>'
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


def _smc_html(smc) -> str:
    if smc is None:
        return ('<section class="tab smc" id="tab-smc" hidden><div class="sub-card full">'
                '<p class="hint">Sem dados OHLC para a análise SMC nesta execução.</p></div></section>')
    tcls, trot = {"alta": ("up", "ALTISTA"), "baixa": ("down", "BAIXISTA")}.get(
        smc.trend, ("flat", "NEUTRA"))
    ult = smc.df.index[-1].strftime("%d/%m/%Y")
    n_bos = sum(1 for e in smc.eventos if e.tipo == "BOS")
    n_choch = sum(1 for e in smc.eventos if e.tipo == "CHoCH")
    ob_fresh = sum(1 for b in smc.obs if not b.mitigado)
    fvg_open = sum(1 for f in smc.fvgs if not f.mitigado)
    return f"""<section class="tab smc hide-fvg" id="tab-smc" hidden>
  <div class="sub-card full">
    <h3>Estrutura de mercado &mdash; {html.escape(smc.nome)}
      <span class="hint">({html.escape(smc.timeframe)} · swings + BOS/CHoCH + OB/FVG/liquidez · força {smc.forca})</span></h3>
    <div class="smc-head">
      <span class="smc-badge {tcls}">Tendência estrutural: {trot}</span>
      <span class="hint">último candle {ult} &middot; {n_bos} BOS · {n_choch} CHoCH &middot;
        {ob_fresh} OB frescos · {fvg_open} FVG abertos na janela</span>
    </div>
    <div class="smc-toggles">
      <span class="tgl-lbl">Camadas</span>
      <label><input type="checkbox" checked onchange="tglLayer('swings',this.checked)"> swings</label>
      <label><input type="checkbox" checked onchange="tglLayer('estrutura',this.checked)"> BOS/CHoCH</label>
      <label><input type="checkbox" checked onchange="tglLayer('ob',this.checked)"> Order Blocks</label>
      <label><input type="checkbox" onchange="tglLayer('fvg',this.checked)"> FVG</label>
      <label><input type="checkbox" checked onchange="tglLayer('liq',this.checked)"> Liquidez</label>
    </div>
    {charts.candles(smc)}
    <div class="smc-legend">
      <span><span class="sw-dot"></span> swing point</span>
      <span><span class="ev-dash up"></span> rompimento alta</span>
      <span><span class="ev-dash down"></span> rompimento baixa</span>
      <span><span class="z-swatch" style="background:var(--smc-demand)"></span> OB compra (demanda)</span>
      <span><span class="z-swatch" style="background:var(--smc-supply)"></span> OB venda (oferta)</span>
      <span><span class="z-swatch" style="background:var(--smc-fvg)"></span> FVG</span>
      <span><span class="z-swatch" style="background:var(--smc-liq)"></span> liquidez (BSL/SSL)</span>
    </div>
    <div class="analise-nota">
      <b>Como ler:</b> <b>BOS</b> = rompimento a favor da tendência (continuação); <b>CHoCH</b>
      = primeiro rompimento contra (possível virada); gatilho por <b>fechamento</b>, não pavio.
      <b>Order Block</b> = último candle contrário antes do deslocamento que rompeu estrutura
      (compra/demanda em roxo, venda/oferta em marrom) — apagado = já mitigado. <b>FVG</b> =
      desequilíbrio de 3 candles (zona azul), some quando o preço volta e preenche.
      <b>Liquidez</b> = topos/fundos iguais (linha amarela; <b>✗</b> = já varrida). As zonas se
      estendem até a direita porque continuam válidas até o preço as tocar. Últimos
      <b>{smc.provisorios} candles</b> provisórios. <b>Próxima fatia:</b> timeframe maior
      (semanal) + a regra do conflito HTF×LTF + caixa "o que eu faria agora".
    </div>
  </div>
</section>"""


def gerar_html(blocos: dict[str, list[Cotacao]], analise: Analise,
               gerado_em: str, data_dados: str | None, smc=None) -> str:
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
    --smc-supply:#b06a2c; --smc-demand:#9b5cff; --smc-fvg:#4d7dff; --smc-liq:#ffb020;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{ --bg:#f4f6fa; --card:#fff; --ink:#161a21; --dim:#5d6b7d; --line:#e3e7ee;
      --up:#0f9d58; --down:#e02f44; }}
  }}
  html[data-cb="1"] {{
    --up:#0072B2; --down:#E69F00;
    --b0:#E69F00; --b1:#56B4E9; --b2:#009E73; --b3:#F0E442;
    --b4:#D55E00; --b5:#0072B2; --b6:#CC79A7; --b7:#999999;
    --smc-supply:#D55E00; --smc-demand:#CC79A7; --smc-fvg:#56B4E9; --smc-liq:#F0E442;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:15px/1.45 -apple-system,Segoe UI,Roboto,sans-serif; padding:22px 28px; }}
  header, .tabbar, .kpis, .analise, .leitura, .grid, .metodo, .smc, footer {{ max-width:min(1600px, 96vw); margin-left:auto; margin-right:auto; }}
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
  .g-lbl {{ fill:var(--dim); font-size:11px; font-weight:600; }}

  /* --- Abas + análise + metodologia --- */
  .tabbar {{ display:flex; gap:8px; margin-bottom:16px; }}
  .tabbtn {{ cursor:pointer; border:1px solid var(--line); background:var(--card); color:var(--dim);
    font-weight:600; padding:8px 16px; border-radius:9px; font-size:14px; }}
  .tabbtn.active {{ color:var(--ink); border-color:var(--b2); box-shadow:inset 0 -3px 0 var(--b2); }}
  .tab[hidden] {{ display:none; }}
  .analise {{ margin-bottom:20px; }}
  .analise-nota {{ font-size:12.5px; color:var(--dim); margin-top:10px; }}
  .metodo p {{ font-size:14px; line-height:1.55; opacity:.95; }}
  .metodo h4 {{ margin:18px 0 6px; font-size:15px; }}
  .metodo-vars {{ font-size:14px; line-height:1.5; margin:6px 0; }}
  .metodo-vars li {{ margin:5px 0; }}
  .z-up {{ color:var(--up); font-weight:700; }}
  .z-down {{ color:var(--down); font-weight:700; }}
  .z-flat {{ color:var(--flat); font-weight:700; }}

  /* --- Leitura --- */
  .leitura {{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr));
    gap:14px; margin-bottom:22px; align-items:start; }}
  @media (max-width:900px) {{ .leitura {{ grid-template-columns:1fr; }} }}
  .sub-card.full {{ grid-column:1/-1; }}
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
  .histchart {{ width:100%; height:auto; margin-top:4px; }}
  .ax {{ fill:var(--dim); font-size:10px; }}
  .hist-legend {{ display:flex; gap:16px; flex-wrap:wrap; align-items:center; margin-top:8px;
    font-size:12.5px; color:var(--dim); }}
  .dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:4px; }}
  .dot.up {{ background:var(--up); }} .dot.down {{ background:var(--down); }}

  /* --- SMC (candlestick + estrutura) --- */
  .candles {{ width:100%; height:auto; margin:6px 0 2px; }}
  .candles .wick {{ stroke-width:1; }}
  .candles .wick.up {{ stroke:var(--up); }} .candles .wick.down {{ stroke:var(--down); }}
  .candles .body.up {{ fill:var(--up); stroke:var(--up); }}
  .candles .body.down {{ fill:var(--down); stroke:var(--down); }}
  .candles .sw-h, .candles .sw-l {{ fill:var(--dim); }}
  .candles .ev {{ stroke-width:1.5; }}
  .candles .ev.up {{ stroke:var(--up); }} .candles .ev.down {{ stroke:var(--down); }}
  .candles .ev-lbl {{ font-size:11px; font-weight:700; }}
  .candles .ev-lbl.up {{ fill:var(--up); }} .candles .ev-lbl.down {{ fill:var(--down); }}
  .candles .ob.demand {{ fill:var(--smc-demand); }}
  .candles .ob.supply {{ fill:var(--smc-supply); }}
  .candles .ob.ativo {{ stroke-width:1.4; }}
  .candles .ob.demand.ativo {{ stroke:var(--smc-demand); }}
  .candles .ob.supply.ativo {{ stroke:var(--smc-supply); }}
  .candles .fvg {{ fill:var(--smc-fvg); }}
  .candles .liq {{ stroke:var(--smc-liq); stroke-width:1.4; }}
  .candles .liq-lbl {{ fill:var(--smc-liq); font-size:10.5px; font-weight:700; }}
  .candles .zlbl {{ font-size:10px; font-weight:700; }}
  .candles .zlbl.demand {{ fill:var(--smc-demand); }}
  .candles .zlbl.supply {{ fill:var(--smc-supply); }}
  .z-swatch {{ display:inline-block; width:11px; height:11px; border-radius:3px;
    margin-right:4px; vertical-align:middle; opacity:.85; }}
  .smc-toggles {{ display:flex; gap:14px; flex-wrap:wrap; align-items:center; margin:4px 0 6px;
    font-size:13px; padding:8px 12px; background:var(--card); border:1px solid var(--line); border-radius:10px; }}
  .smc-toggles .tgl-lbl {{ color:var(--dim); font-weight:600; text-transform:uppercase;
    font-size:11px; letter-spacing:.5px; }}
  .smc-toggles label {{ display:inline-flex; align-items:center; gap:5px; cursor:pointer; user-select:none; }}
  .smc-toggles input {{ accent-color:var(--b2); cursor:pointer; }}
  .smc.hide-swings .lyr-swings, .smc.hide-estrutura .lyr-estrutura,
  .smc.hide-ob .lyr-ob, .smc.hide-fvg .lyr-fvg, .smc.hide-liq .lyr-liq {{ display:none; }}
  .smc-head {{ display:flex; gap:14px; align-items:center; flex-wrap:wrap; margin-bottom:6px; }}
  .smc-badge {{ font-weight:800; letter-spacing:.5px; padding:4px 12px; border-radius:8px;
    background:var(--flat); color:#fff; font-size:13px; }}
  .smc-badge.up {{ background:var(--up); }} .smc-badge.down {{ background:var(--down); }}
  .smc-legend {{ display:flex; gap:16px; flex-wrap:wrap; align-items:center; margin-top:8px;
    font-size:12.5px; color:var(--dim); }}
  .sw-dot {{ display:inline-block; width:8px; height:8px; border-radius:50%;
    background:var(--dim); margin-right:4px; vertical-align:middle; }}
  .ev-dash {{ display:inline-block; width:16px; border-top:2px dashed var(--flat);
    margin-right:4px; vertical-align:middle; }}
  .ev-dash.up {{ border-top-color:var(--up); }} .ev-dash.down {{ border-top-color:var(--down); }}

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
<nav class="tabbar">
  <button class="tabbtn active" data-tab="dash" onclick="showTab('dash')">📊 Dashboard</button>
  <button class="tabbtn" data-tab="smc" onclick="showTab('smc')">📈 SMC</button>
  <button class="tabbtn" data-tab="metodo" onclick="showTab('metodo')">📖 Metodologia</button>
</nav>
<section class="tab" id="tab-dash">
{_kpis_html(idx, analise)}
{_analise_placar_html(analise)}
{_leitura_html(analise)}
<main class="grid">
{secoes}
</main>
</section>
{_smc_html(smc)}
{_metodo_html(analise)}
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
  function showTab(name) {{
    document.querySelectorAll('.tab').forEach(function (t) {{ t.hidden = (t.id !== 'tab-' + name); }});
    document.querySelectorAll('.tabbtn').forEach(function (b) {{ b.classList.toggle('active', b.dataset.tab === name); }});
  }}
  function tglLayer(name, on) {{
    var s = document.getElementById('tab-smc');
    if (s) s.classList.toggle('hide-' + name, !on);
  }}
</script>
</body>
</html>"""
