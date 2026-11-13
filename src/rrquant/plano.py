"""Plano do dia: o operacional (docs/meu-operacional.md) aplicado à manhã de hoje.

Junta numa tela só o que o operacional pede antes da abertura do WIN:
- seção 2: agenda e leitura da manhã (viés);
- seção 3: mapa de liquidez (PDH/PDL, PWH/PWL, PMH/PML, EQH/EQL) e zonas do macro;
- seções 1, 10 e 11: risco, checklist do setup central e quando não operar.

Fonte dos níveis (win.py): o próprio WIN sempre que possível, do Profit local (completo) ou
da brapi (só diário). Sem nenhum dos dois, cai para o Ibovespa à vista do yfinance.

Por que o Ibovespa é só reserva: o futuro negocia com um prêmio sobre o índice (mediana mensal entre 250 e 3.000 pontos em 2024-2026), então o preço
absoluto não bate. Das 11h às 16h os dois andam juntos (correlação de 0,99 por hora). Mas o WIN
negocia das 9h às 18h, e em quase metade dos dias a máxima ou a mínima dele sai fora do horário
do à vista: a distância até PDH/PDL difere em até ~190 pontos na metade dos dias e em até
~650 pontos em 90% deles. É um mapa aproximado; o preço de verdade se marca no Profit.

Nada de look-ahead: os níveis usam só pregões completos anteriores a hoje.
"""

from __future__ import annotations

import csv
import datetime as dt
import html
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

TZ = ZoneInfo("America/Sao_Paulo")
STOP_MAX = 300          # pontos (seção 1)
ALVO_MIN_R = 3          # alvo >= 3R (seção 1)
ALCANCE = 10 * STOP_MAX # EQH/EQL e zonas além disso não entram no plano do dia
FECHAMENTO = 18         # depois dessa hora, o plano é do próximo pregão
AGENDA = Path(__file__).resolve().parents[2] / "data" / "agenda.csv"


@dataclass
class Nivel:
    nome: str        # 'PDH', 'PWL', 'EQH 1h'...
    preco: float
    descricao: str
    dist: float = 0.0  # preço do nível - último fechamento da mesma série (pontos)
    escala: str = ""   # vazio = a série dos níveis do dia; 'Ibov' = veio de outra série


@dataclass
class Zona:
    rotulo: str      # 'OB de compra 1h', 'FVG de baixa 15 min'
    topo: float
    base: float
    lado: str        # 'acima' | 'abaixo' | 'dentro'
    dist: float      # pontos até a borda mais próxima


@dataclass
class Sinal:
    fonte: str
    leitura: str
    voto: int        # +1 favorece compra, -1 favorece venda, 0 neutro


@dataclass
class Evento:
    quando: str      # 'hoje 10:30', 'qua 09/12 16:00'
    evento: str
    hoje: bool


@dataclass
class Plano:
    hoje: dt.date
    pregao_ref: str            # último pregão completo usado nos níveis
    preco: float
    niveis: list[Nivel] = field(default_factory=list)
    zonas: list[Zona] = field(default_factory=list)
    sinais: list[Sinal] = field(default_factory=list)
    vies: str = "neutro"       # 'compra' | 'venda' | 'neutro'
    vies_motivo: str = ""
    agenda: list[Evento] = field(default_factory=list)
    fonte_diario: str = "Ibovespa à vista (yfinance)"
    fonte_intra: str = "Ibovespa à vista (yfinance)"
    mesma_escala: bool = True


# ---------------------------------------------------------------- níveis

def niveis_anteriores(diario: pd.DataFrame, hoje: dt.date) -> tuple[list[Nivel], str, float] | None:
    """PDH/PDL, PWH/PWL e PMH/PML válidos para o pregão de `hoje`, só com barras anteriores."""
    d = diario[diario.index.date < hoje]
    d = d[(d.High > 0) & (d.Low > 0) & (d.Close > 0)]   # o yfinance às vezes devolve barra zerada
    if len(d) < 25:
        return None
    ult = d.iloc[-1]
    ref = d.index[-1].date()
    out = [Nivel("PDH", float(ult.High), f"máxima de {ref:%d/%m}"),
           Nivel("PDL", float(ult.Low), f"mínima de {ref:%d/%m}")]

    sem = d.index.to_period("W")
    ant = pd.Period(hoje, "W") - 1
    w = d[sem == ant]
    if len(w):
        rot = f"semana de {w.index[0]:%d/%m}"
        out += [Nivel("PWH", float(w.High.max()), f"máxima da {rot}"),
                Nivel("PWL", float(w.Low.min()), f"mínima da {rot}")]

    mes = d.index.to_period("M")
    antm = pd.Period(hoje, "M") - 1
    m = d[mes == antm]
    if len(m):
        rot = f"{m.index[0]:%m/%Y}"
        out += [Nivel("PMH", float(m.High.max()), f"máxima de {rot}"),
                Nivel("PML", float(m.Low.min()), f"mínima de {rot}")]
    return out, f"{ref:%d/%m/%Y}", float(ult.Close)


def _liquidez_smc(smc, rotulo: str) -> list[Nivel]:
    """Topos/fundos nivelados ainda não varridos, do motor SMC."""
    if smc is None:
        return []
    out = []
    for q in smc.liquidez:
        if q.varrido:
            continue
        nome = "EQH" if q.tipo == "BSL" else "EQL"
        lado = "topos" if q.tipo == "BSL" else "fundos"
        out.append(Nivel(f"{nome} {rotulo}", q.nivel, f"{lado} nivelados até {q.data}, não varridos"))
    return out


def _zonas_smc(smc, rotulo: str, preco: float) -> list[Zona]:
    """Order blocks e FVGs ainda não mitigados no tempo gráfico do macro."""
    if smc is None:
        return []
    brutas = [(f"OB de {b.tipo} {rotulo}", b.topo, b.base) for b in smc.obs if not b.mitigado]
    brutas += [(f"FVG de {f.tipo} {rotulo}", f.topo, f.base) for f in smc.fvgs if not f.mitigado]
    out = []
    for r, topo, base in brutas:
        if base > preco:
            out.append(Zona(r, topo, base, "acima", base - preco))
        elif topo < preco:
            out.append(Zona(r, topo, base, "abaixo", topo - preco))
        else:
            out.append(Zona(r, topo, base, "dentro", 0.0))
    return out


def _sem_duplicata(niveis: list[Nivel], tol: float = 40.0) -> list[Nivel]:
    """EQH/EQL a menos de `tol` pontos de um nível já listado somem. Os de dia, semana e
    mês têm prioridade; entre EQH/EQL, fica o do tempo gráfico maior (vem antes na lista).
    Só compara níveis da mesma série: preço do WIN e do Ibov não se comparam."""
    out = [n for n in niveis if " " not in n.nome]
    for n in niveis:
        if " " in n.nome and all(abs(n.preco - f.preco) > tol for f in out
                                 if f.escala == n.escala):
            out.append(n)
    return out


def dia_do_plano(agora: dt.datetime) -> dt.date:
    """Pregão a que o plano se refere: hoje até o fechamento, depois o próximo dia útil.
    Feriados da B3 não entram na conta."""
    d = agora.date() + dt.timedelta(days=1 if agora.hour >= FECHAMENTO else 0)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


# ---------------------------------------------------------------- leitura da manhã

def _var(idx: dict, tk: str) -> float | None:
    c = idx.get(tk)
    return c.var_pct if c is not None and c.ok else None


def leitura_manha(idx: dict, placar, dec) -> tuple[list[Sinal], str, str]:
    """Sinais da seção 2, cada um votando compra (+1), venda (-1) ou nada (0).

    A soma é uma contagem, não um modelo: se esse filtro melhora o resultado é a
    pergunta 4 da seção 12, ainda sem resposta no backtest.
    """
    s: list[Sinal] = []

    def var_sinal(tk, nome, inverso=False, lim=0.3):
        v = _var(idx, tk)
        if v is None:
            return
        voto = 0 if abs(v) < lim else (1 if v > 0 else -1)
        if inverso:
            voto = -voto
        s.append(Sinal(nome, f"{v:+.2f}%".replace(".", ","), voto))

    var_sinal("^DJI", "Dow Jones (fechamento)")
    var_sinal("EWZ", "EWZ (ponte NY → B3)")
    var_sinal("DX-Y.NYB", "DXY (dólar global)", inverso=True)
    var_sinal("^TNX", "Treasury 10 anos", inverso=True, lim=1.0)
    var_sinal("BZ=F", "Petróleo Brent (Petrobras)", lim=1.0)

    vix = idx.get("^VIX")
    if vix is not None and vix.ultimo is not None:
        alto = vix.ultimo > 20
        s.append(Sinal("VIX", f"{vix.ultimo:.1f}".replace(".", ",")
                       + (" (acima de 20: alerta de realização)" if alto else " (abaixo de 20)"),
                       -1 if alto else 0))

    if placar is not None:
        dif = placar.prob - placar.base
        voto = 1 if dif >= 3 else -1 if dif <= -3 else 0
        s.append(Sinal("Placar do Ibovespa",
                       f"{placar.prob:.0f}% de alta (base {placar.base:.0f}%, "
                       f"acerto fora da amostra ~{placar.acuracia:.0f}%)", voto))

    estrutura = 0
    if dec is not None:
        estrutura = {"COMPRAR": 1, "VENDER": -1}.get(dec.acao, 0)
        s.append(Sinal("Estrutura semanal × diário", dec.acao.lower()
                       + (" (conflito)" if dec.conflito else ""), estrutura))

    saldo = sum(x.voto for x in s)
    if saldo >= 2 and estrutura >= 0:
        vies, motivo = "compra", f"saldo de {saldo:+d} sinais e estrutura sem veto"
    elif saldo <= -2 and estrutura <= 0:
        vies, motivo = "venda", f"saldo de {saldo:+d} sinais e estrutura sem veto"
    else:
        vies = "neutro"
        motivo = (f"saldo de {saldo:+d} sinais" if estrutura == 0 or abs(saldo) < 2
                  else f"saldo de {saldo:+d}, mas a estrutura aponta o outro lado")
    return s, vies, motivo


# ---------------------------------------------------------------- agenda

def _primeira_sexta(d: dt.date) -> dt.date:
    p = d.replace(day=1)
    return p + dt.timedelta(days=(4 - p.weekday()) % 7)


def agenda(hoje: dt.date, dias: int = 7, arquivo: Path = AGENDA) -> list[Evento]:
    """Eventos de hoje até `dias` à frente: o arquivo editado à mão mais o payroll por regra."""
    itens: list[tuple[dt.date, str, str]] = []
    if arquivo.exists():
        linhas = [l for l in arquivo.read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.startswith("#")]
        for r in csv.DictReader(linhas, delimiter=";"):
            try:
                itens.append((dt.date.fromisoformat(r["data"]), r.get("hora_brt") or "", r["evento"]))
            except (KeyError, ValueError):
                continue
    for mes in (hoje, (hoje.replace(day=1) + dt.timedelta(days=32))):
        sexta = _primeira_sexta(mes)
        hora = dt.datetime.combine(sexta, dt.time(8, 30), ZoneInfo("America/New_York")).astimezone(TZ)
        itens.append((sexta, f"{hora:%H:%M}", "Payroll (EUA), 1ª sexta do mês: confirmar a data"))

    dias_sem = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    out = []
    for d, hora, ev in sorted(set(itens)):
        if not (hoje <= d <= hoje + dt.timedelta(days=dias)):
            continue
        quando = "hoje" if d == hoje else f"{dias_sem[d.weekday()]} {d:%d/%m}"
        out.append(Evento(f"{quando} {hora}".strip(), ev, d == hoje))
    return out


# ---------------------------------------------------------------- montagem

def montar(diario: pd.DataFrame | None, idx: dict, placar=None, dec=None,
           smc_1h=None, smc_15m=None, hoje: dt.date | None = None,
           fonte_diario: str = "Ibovespa à vista (yfinance)",
           fonte_intra: str | None = None) -> Plano | None:
    """`fonte_intra` diferente de `fonte_diario` quer dizer que EQH/EQL e zonas vêm de
    outra série (o Ibov, quando o WIN só tem diário): cada item mede a distância a partir
    do preço da própria série, e a tabela marca a origem."""
    hoje = hoje or dia_do_plano(dt.datetime.now(TZ))
    if diario is None:
        return None
    base = niveis_anteriores(diario, hoje)
    if base is None:
        return None
    niveis, ref, preco = base
    fonte_intra = fonte_intra or fonte_diario
    mesma = fonte_intra == fonte_diario
    preco_intra = preco
    for s in (smc_15m, smc_1h):
        if not mesma and s is not None:
            barras = s.df[s.df.index.date < hoje]
            if len(barras):
                preco_intra = float(barras["Close"].iloc[-1])
                break
    extras = _liquidez_smc(smc_1h, "1h") + _liquidez_smc(smc_15m, "15 min")
    for n in extras:
        n.escala = "" if mesma else "Ibov"
        n.dist = n.preco - preco_intra
    for n in niveis:
        n.dist = n.preco - preco
    niveis = _sem_duplicata(niveis + extras)
    niveis = [n for n in niveis if " " not in n.nome or abs(n.dist) <= ALCANCE]
    niveis.sort(key=lambda n: -n.dist)

    zonas = [z for z in _zonas_smc(smc_1h, "1h", preco_intra) + _zonas_smc(smc_15m, "15 min", preco_intra)
             if abs(z.dist) <= ALCANCE]
    acima = sorted((z for z in zonas if z.lado == "acima"), key=lambda z: z.dist)[:3]
    abaixo = sorted((z for z in zonas if z.lado == "abaixo"), key=lambda z: -z.dist)[:3]
    dentro = [z for z in zonas if z.lado == "dentro"]

    sinais, vies, motivo = leitura_manha(idx, placar, dec)
    return Plano(hoje, ref, preco, niveis, acima[::-1] + dentro + abaixo, sinais, vies, motivo,
                 agenda(hoje), fonte_diario, fonte_intra, mesma)


# ---------------------------------------------------------------- HTML

def _pts(v: float) -> str:
    return f"{v:+,.0f}".replace(",", ".")


def _preco(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


def _r(dist: float) -> str:
    return f"{abs(dist) / STOP_MAX:.1f}R".replace(".", ",")


CHECKLIST = [
    ("1", "Captura de liquidez antes: PDL, PWL, PML, EQL ou fundo de lateral varrido", True),
    ("2", "CHoCH válido no micro (5 pernas, rompe o fundo de origem)", True),
    ("3", "Volume crescente na quebra", True),
    ("4", "Pullback corretivo (ABC, flat ou reacumulação), nunca em linha reta", True),
    ("4a", "Indução antes da entrada (fake BOS ou fake CHoCH)", True),
    ("4b", "Correção do tipo flat irregular ou regular", False),
    ("5", "Discount: retração de 61,8% a 79%", True),
    ("6", "Order block ou FVG na zona da retração (o gatilho)", True),
    ("7", "POC ou área de valor na mesma zona", False),
    ("8", "Fluxo alinhado (CHoCH também no macro)", False),
    ("9", "Viés da manhã a favor", False),
    ("alvo", "Alvo na próxima liquidez do macro (PDH, PWH, BSL) a pelo menos 3R", True),
]

NAO_OPERAR = [
    "Já foram 2 stops no dia, ou já foram 3 trades.",
    "Não houve captura de liquidez.",
    "O alvo até a próxima liquidez do macro não chega a 3R.",
    "O stop técnico passa de 300 pontos.",
    "O volume não confirma a quebra.",
    "Notícia forte nos próximos minutos (ver a agenda).",
    "Fora da janela em que consigo acompanhar com atenção total (cerca de 1 hora).",
    "O preço chegou à zona em linha reta e ainda não houve CHoCH no micro.",
    "A correção é uma flat clássica (liquidez dos dois lados).",
    "Canal de continuação com menos de 5 toques.",
]


def _tag(escala: str) -> str:
    return f' <span class="pl-tag">{html.escape(escala)}</span>' if escala else ""


def _nota_fonte(p: Plano) -> str:
    """Rodapé do mapa: de onde vieram os níveis e o quanto confiar neles."""
    if p.fonte_diario.startswith("WIN") and p.mesma_escala:
        return (f"Tudo do próprio WIN: {html.escape(p.fonte_diario)}. EQH e EQL são topos e fundos "
                "nivelados do 1h e do 15 min que ainda não foram varridos.")
    if p.fonte_diario.startswith("WIN"):
        return (f"PDH a PML do próprio WIN: {html.escape(p.fonte_diario)}, pregão completo, das 9h "
                "às 18h. Os itens marcados <b>Ibov</b> (EQH, EQL e as zonas abaixo) vêm do Ibovespa "
                "à vista de 15 min e 1h, porque essa fonte do WIN não tem intraday: preço na escala "
                "do Ibov e distância medida a partir do fechamento do Ibov. A distância é próxima da "
                "do WIN no meio do pregão, mas o à vista não vê o que o WIN faz das 9h às 10h e "
                "depois das 17h. Para tudo do WIN, deixe o Profit aberto no pregão e gere o "
                "dashboard no PC.")
    return ("Níveis do <b>Ibovespa à vista</b>, um mapa aproximado: nenhuma fonte do WIN respondeu "
            "nesta execução. O WIN negocia com prêmio e fica aberto das 9h às 18h, então em quase "
            "metade dos dias a máxima ou a mínima dele sai fora do horário do à vista. A distância "
            "até PDH/PDL difere em até ~190 pontos na metade dos dias e em até ~650 em 90% deles "
            "(2024-2026). Antes de operar, marque os níveis do WIN no Profit.")


def _tabela_niveis(p: Plano) -> str:
    linhas = []
    marcou_preco = False
    for n in p.niveis:
        if not marcou_preco and n.dist < 0:
            linhas.append(f'<tr class="pl-agora"><td>agora</td><td>{_preco(p.preco)}</td>'
                          f'<td colspan="3">fechamento de {p.pregao_ref}</td></tr>')
            marcou_preco = True
        alvo = abs(n.dist) >= ALVO_MIN_R * STOP_MAX
        cls = "up" if n.dist > 0 else "down"
        linhas.append(
            f'<tr><td><b>{html.escape(n.nome)}</b>{_tag(n.escala)}</td><td>{_preco(n.preco)}</td>'
            f'<td class="{cls}">{_pts(n.dist)}</td>'
            f'<td>{_r(n.dist)}{" ✓" if alvo else ""}</td>'
            f'<td class="hint">{html.escape(n.descricao)}</td></tr>')
    if not marcou_preco:
        linhas.append(f'<tr class="pl-agora"><td>agora</td><td>{_preco(p.preco)}</td>'
                      f'<td colspan="3">fechamento de {p.pregao_ref}</td></tr>')
    return ("<div class=\"pl-rolo\"><table class=\"pl-tab\"><thead><tr><th>nível</th><th>preço</th>"
            "<th>distância</th><th>em R*</th><th>o que é</th></tr></thead><tbody>"
            + "".join(linhas) + "</tbody></table></div>")


def _tabela_zonas(p: Plano) -> str:
    if not p.zonas:
        return '<p class="hint">Nenhum order block ou FVG em aberto no 1h e no 15 min.</p>'
    linhas = []
    for z in p.zonas:
        cls = {"acima": "up", "abaixo": "down"}.get(z.lado, "flat")
        dist = "preço dentro" if z.lado == "dentro" else _pts(z.dist)
        linhas.append(f'<tr><td>{html.escape(z.rotulo)}</td>'
                      f'<td>{_preco(z.base)} a {_preco(z.topo)}</td>'
                      f'<td class="{cls}">{dist}</td><td>{z.lado}</td></tr>')
    return ("<div class=\"pl-rolo\"><table class=\"pl-tab\"><thead><tr><th>zona</th><th>faixa</th>"
            "<th>distância</th><th>lado</th></tr></thead><tbody>"
            + "".join(linhas) + "</tbody></table></div>")


def plano_html(p: Plano | None) -> str:
    if p is None:
        return ('<section class="tab plano" id="tab-plano"><div class="sub-card">'
                '<h3>Plano do dia</h3><p>Sem dados do Ibovespa nesta execução.</p>'
                '</div></section>')

    cls_vies = {"compra": "up", "venda": "down"}.get(p.vies, "flat")
    sinais = "".join(
        f'<li><span class="pl-voto {"up" if s.voto > 0 else "down" if s.voto < 0 else "flat"}">'
        f'{"▲ compra" if s.voto > 0 else "▼ venda" if s.voto < 0 else "• neutro"}</span>'
        f' <b>{html.escape(s.fonte)}</b>: {html.escape(s.leitura)}</li>' for s in p.sinais)

    if p.agenda:
        ag = "".join(f'<li class="{"pl-hoje" if e.hoje else ""}"><b>{html.escape(e.quando)}</b> '
                     f'{html.escape(e.evento)}</li>' for e in p.agenda)
        tem_hoje = any(e.hoje for e in p.agenda)
        agenda = (f'<div class="sub-card {"pl-alerta" if tem_hoje else ""}"><h3>Agenda '
                  f'<span class="hint">(hoje e próximos 7 dias)</span></h3><ul class="pl-lista">{ag}</ul>'
                  + ('<p class="pl-nota">Tem evento hoje: cuidado com ordem pendurada perto do horário.</p>'
                     if tem_hoje else "")
                  + '<p class="hint">Copom e FOMC vêm de <code>data/agenda.csv</code>; '
                    'CPI, IPCA e outros entram à mão no mesmo arquivo.</p></div>')
    else:
        agenda = ('<div class="sub-card"><h3>Agenda</h3><p class="hint">Nada marcado para os '
                  'próximos 7 dias em <code>data/agenda.csv</code>.</p></div>')

    check = "".join(
        f'<li><label><input type="checkbox" data-k="{k}"> <span class="pl-num">{k}</span> '
        f'{html.escape(t)} <span class="pl-tag {"obr" if o else "soma"}">'
        f'{"obrigatória" if o else "soma"}</span></label></li>' for k, t, o in CHECKLIST)
    nao = "".join(f"<li>{html.escape(t)}</li>" for t in NAO_OPERAR)

    return f"""<section class="tab plano" id="tab-plano">
<div class="pl-topo">
  <div class="sub-card pl-vies {cls_vies}">
    <div class="pl-rot">Viés da manhã &middot; pregão de {p.hoje:%d/%m/%Y}</div>
    <div class="pl-grande {cls_vies}">{p.vies.upper()}</div>
    <div class="hint">{html.escape(p.vies_motivo)}. É uma contagem de sinais, não um modelo,
      e ainda não passou no backtest (seção 12, pergunta 4). O macro só filtra o lado: não é
      gatilho.</div>
  </div>
  {agenda}
</div>

<div class="leitura">
  <div class="sub-card">
    <h3>Leitura da manhã <span class="hint">(seção 2: macro filtra o viés)</span></h3>
    <ul class="pl-lista pl-sinais">{sinais}</ul>
  </div>
  <div class="sub-card">
    <h3>Risco <span class="hint">(seção 1: vale antes de tudo)</span></h3>
    <ul class="pl-lista">
      <li>Stop técnico de no máximo <b>{STOP_MAX} pontos</b>; alvo de pelo menos <b>3R</b>.</li>
      <li>No máximo <b>3 trades</b>; depois de <b>2 stops</b>, acabou o dia.</li>
      <li>Nenhuma parcial antes de 3R. Saída é stop, 0×0 técnico ou alvo.</li>
    </ul>
    <label class="pl-calc">Contratos de hoje
      <input type="number" id="pl-contratos" min="1" max="50" value="1"></label>
    <div id="pl-conta" class="hint"></div>
  </div>
</div>

<div class="sub-card">
  <h3>Mapa de liquidez <span class="hint">(seção 3: alvo antes de varrido, lugar de entrada depois)</span></h3>
  {_tabela_niveis(p)}
  <p class="hint">* Distância dividida por um stop de {STOP_MAX} pontos; ✓ = dá alvo de 3R com esse
    stop. {_nota_fonte(p)}</p>
</div>

<div class="sub-card">
  <h3>Zonas do macro mais próximas <span class="hint">(order blocks e FVGs em aberto, 1h e 15 min)</span>{"" if p.mesma_escala else _tag("Ibov")}</h3>
  {_tabela_zonas(p)}
  <p class="hint">Zona é lugar, não gatilho: só lugar não basta, precisa de evento (CHoCH no micro
    e pullback). Ver a aba SMC para os gráficos.</p>
</div>

<div class="leitura">
  <div class="sub-card">
    <h3>Checklist do setup central <span class="hint">(seção 10: compra; a venda é o espelho)</span></h3>
    <ul class="pl-check">{check}</ul>
    <p class="pl-nota" id="pl-veredito">Marque o que o gráfico mostra.</p>
    <button class="tabbtn" id="pl-limpar" type="button">Limpar</button>
    <p class="hint">Um único fator contra invalida, não importa quantas confluências somem. As
      marcações ficam neste navegador e zeram a cada dia.</p>
  </div>
  <div class="sub-card">
    <h3>Quando não operar <span class="hint">(seção 11)</span></h3>
    <ul class="pl-lista">{nao}</ul>
  </div>
</div>
</section>
<script>
(function () {{
  var DIA = '{p.hoje.isoformat()}', CH = 'rrquant-checklist';
  var boxes = Array.prototype.slice.call(document.querySelectorAll('.pl-check input'));
  var est = {{}};
  try {{ var s = JSON.parse(localStorage.getItem(CH) || '{{}}'); if (s.dia === DIA) est = s.k || {{}}; }} catch (e) {{}}
  function salvar() {{ try {{ localStorage.setItem(CH, JSON.stringify({{dia: DIA, k: est}})); }} catch (e) {{}} }}
  function veredito() {{
    var falta = boxes.filter(function (b) {{
      return !b.checked && b.closest('li').querySelector('.obr'); }}).map(function (b) {{ return b.dataset.k; }});
    var v = document.getElementById('pl-veredito');
    v.textContent = falta.length ? 'Falta a obrigatória: ' + falta.join(', ') + '. Sem isso, não tem entrada.'
                                 : 'Todas as obrigatórias marcadas. Confira a seção 11 antes de entrar.';
    v.className = 'pl-nota ' + (falta.length ? 'down' : 'up');
  }}
  boxes.forEach(function (b) {{
    b.checked = !!est[b.dataset.k];
    b.addEventListener('change', function () {{ est[b.dataset.k] = b.checked; salvar(); veredito(); }});
  }});
  document.getElementById('pl-limpar').addEventListener('click', function () {{
    est = {{}}; boxes.forEach(function (b) {{ b.checked = false; }}); salvar(); veredito(); }});
  veredito();
  var inp = document.getElementById('pl-contratos');
  function conta() {{
    var n = Math.max(1, parseInt(inp.value, 10) || 1), r = {STOP_MAX} * 0.2 * n;
    document.getElementById('pl-conta').textContent =
      '1R = R$ ' + r.toFixed(0) + ' · alvo de 3R = R$ ' + (3 * r).toFixed(0) +
      ' · pior dia (2 stops) = R$ ' + (2 * r).toFixed(0) + ' (WIN: R$ 0,20 por ponto por contrato)';
    try {{ localStorage.setItem('rrquant-contratos', String(n)); }} catch (e) {{}}
  }}
  try {{ var c = localStorage.getItem('rrquant-contratos'); if (c) inp.value = c; }} catch (e) {{}}
  inp.addEventListener('input', conta); conta();
}})();
</script>"""


PLANO_CSS = """
  /* --- Plano do dia --- */
  .plano .sub-card { margin-bottom:14px; }
  .pl-topo { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,2fr); gap:14px; }
  @media (max-width:900px) { .pl-topo { grid-template-columns:1fr; } }
  .pl-vies { border-top:4px solid var(--flat); }
  .pl-vies.up { border-top-color:var(--up); } .pl-vies.down { border-top-color:var(--down); }
  .pl-rot { font-size:12px; color:var(--dim); text-transform:uppercase; letter-spacing:.5px; }
  .pl-grande { font-size:30px; font-weight:800; margin:4px 0 8px; }
  .pl-grande.up, .plano td.up, .pl-voto.up, .pl-nota.up { color:var(--up); }
  .pl-grande.down, .plano td.down, .pl-voto.down, .pl-nota.down { color:var(--down); }
  .pl-grande.flat, .pl-voto.flat { color:var(--flat); }
  .pl-lista { margin:6px 0; padding-left:18px; } .pl-lista li { margin:4px 0; }
  .pl-sinais { list-style:none; padding-left:0; }
  .pl-rolo { overflow-x:auto; } .plano .sub-card { min-width:0; }
  .pl-hoje { font-weight:600; }
  .pl-alerta { border:1px solid var(--down); }
  .pl-nota { font-weight:600; margin:8px 0; }
  .pl-voto { display:inline-block; min-width:78px; font-size:12px; font-weight:700; }
  .pl-tab { width:100%; border-collapse:collapse; font-size:14px; font-variant-numeric:tabular-nums; }
  .pl-tab th { text-align:left; font-size:12px; color:var(--dim); font-weight:600;
    border-bottom:1px solid var(--line); padding:6px 8px; }
  .pl-tab td { padding:6px 8px; border-bottom:1px solid var(--line); }
  .pl-agora td { font-weight:700; background:var(--line); }
  .pl-check { list-style:none; padding:0; margin:6px 0; }
  .pl-check li { margin:6px 0; } .pl-check label { cursor:pointer; }
  .pl-num { display:inline-block; min-width:34px; font-weight:700; color:var(--dim); }
  .pl-tag { font-size:11px; padding:1px 7px; border-radius:10px; margin-left:4px;
    border:1px solid var(--line); color:var(--dim); }
  .pl-tag.obr { border-color:var(--down); color:var(--down); }
  .pl-calc { display:block; margin-top:10px; font-size:14px; }
  .pl-calc input { width:70px; margin-left:8px; padding:4px 6px; background:var(--bg);
    color:var(--ink); border:1px solid var(--line); border-radius:6px; }
  @media (max-width:600px) { .pl-tab td:last-child, .pl-tab th:last-child { display:none; } }
"""


def montar_do_dia(ohlc_ibov, idx: dict, placar=None, dec=None, smc_1h_ibov=None,
                  smc_15m_ibov=None) -> Plano | None:
    """Escolhe a fonte (win.py) e monta o plano. Com intraday do WIN (Profit), o motor SMC
    roda no próprio WIN; sem ele, EQH/EQL e zonas vêm do Ibov e a tela marca isso."""
    from . import smc as smc_mod, win as win_mod

    ibov = "Ibovespa à vista (yfinance)"
    dados = win_mod.carregar(dia_do_plano(dt.datetime.now(TZ)))
    if dados is None:
        return montar(ohlc_ibov, idx, placar, dec, smc_1h_ibov, smc_15m_ibov, fonte_diario=ibov)
    if dados.m15 is None:
        return montar(dados.diario, idx, placar, dec, smc_1h_ibov, smc_15m_ibov,
                      fonte_diario=dados.rotulo, fonte_intra=ibov)
    s15 = smc_mod.analisar("WIN", "WIN", dados.m15.iloc[-2400:], timeframe="15 min", forca=4, n_render=160)
    s1h = smc_mod.analisar("WIN", "WIN", dados.h1.iloc[-700:], timeframe="1 hora", forca=3, n_render=120)
    return montar(dados.diario, idx, placar, dec, s1h, s15, fonte_diario=dados.rotulo)
