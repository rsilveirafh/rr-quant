"""Camada de leitura/avaliação — o "porquê" por trás dos números.

Reproduz o tipo de raciocínio da leitura pré-mercado:
- regime do dia (risk-on / risk-off / misto) a partir de volatilidade,
  amplitude das bolsas e ativos de proteção;
- cadeia de correlação (petróleo→Petrobras, juros→risco, DXY→real/emergentes);
- read-through de bolsas mundiais → Ibovespa via PROBABILIDADE CONDICIONAL
  histórica (ex.: quando a Ásia fecha em alta, com que frequência o Ibov segue);
- commodities → ações BR (Brent→Petrobras, cobre→Vale);
- ADRs / EWZ como prévia da abertura doméstica.

As estatísticas são CO-MOVIMENTO histórico (correlação e taxa de acerto), não
previsão — os textos são redigidos com esse cuidado.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field

import pandas as pd
import yfinance as yf

from .collect import Cotacao
from .macro import Macro
from . import tickers as T

warnings.filterwarnings("ignore")

# Conjunto curado p/ histórico (correlações e probabilidades). Menor que os 46
# do snapshot — só o que entra em alguma leitura.
HIST = {
    "^BVSP": "Ibovespa",
    "^N225": "Nikkei",
    "^HSI": "Hang Seng",
    "^KS11": "Kospi",
    "^GDAXI": "DAX",
    "^STOXX50E": "Eurostoxx 50",
    "^DJI": "Dow Jones",
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "EWZ": "EWZ",
    "DX-Y.NYB": "DXY",
    "BZ=F": "Brent",
    "HG=F": "Cobre",
    "GC=F": "Ouro",
    "^VIX": "VIX",
    "^TNX": "Treasury 10a",
    "PETR4.SA": "Petrobras",
    "VALE3.SA": "Vale",
}

ASIA = ["^N225", "^HSI", "^KS11"]
EUROPA = ["^GDAXI", "^STOXX50E"]


@dataclass
class Prob:
    descricao: str
    p_cond: float          # P(alvo sobe | condição), em %
    base: float            # taxa-base P(alvo sobe), em %
    n: int                 # tamanho da amostra (dias)
    corr: float | None = None

    @property
    def lift(self) -> float:
        return self.p_cond - self.base


@dataclass
class Passo:
    titulo: str
    numero: str            # variação de hoje formatada
    leitura: str           # interpretação


@dataclass
class Analise:
    regime_rotulo: str = "—"
    regime_classe: str = "flat"
    regime_bullets: list[str] = field(default_factory=list)
    amplitude: str = ""
    cadeia: list[Passo] = field(default_factory=list)
    commodities: list[Passo] = field(default_factory=list)
    probs: list[Prob] = field(default_factory=list)
    correls: list[tuple[str, float]] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
    macro: Macro | None = None
    hist_ok: bool = False


# ---------- helpers ----------

def _dir(v: float | None, forte: float = 1.0) -> str:
    if v is None:
        return "sem dado"
    if abs(v) < 0.1:
        return "estável"
    intens = "forte " if abs(v) >= forte else ""
    return f"{intens}alta" if v > 0 else f"{intens}queda"


def _idx(cotacoes: list[Cotacao]) -> dict[str, Cotacao]:
    return {c.ticker: c for c in cotacoes}


def _var(idx: dict[str, Cotacao], tk: str) -> float | None:
    c = idx.get(tk)
    return c.var_pct if c else None


# ---------- histórico ----------

def carregar_retornos(periodo: str = "2y") -> pd.DataFrame | None:
    try:
        df = yf.download(
            list(HIST), period=periodo, interval="1d",
            progress=False, auto_adjust=True, threads=False,
        )
        fech = df["Close"] if "Close" in df.columns.get_level_values(0) else df
        rets = fech.pct_change().dropna(how="all")
        return rets
    except Exception:
        return None


def _prob_cond(rets, cond_cols, alvo, descricao) -> Prob | None:
    cols = [c for c in cond_cols if c in rets] + ([alvo] if alvo in rets else [])
    if alvo not in rets or len(cols) < 2:
        return None
    sub = rets[cols].dropna()
    if len(sub) < 40:
        return None
    up = sub > 0
    maioria = up[[c for c in cond_cols if c in sub]].sum(axis=1) >= (len(cond_cols) / 2)
    base = float(up[alvo].mean()) * 100
    sel = up.loc[maioria, alvo]
    if len(sel) < 20:
        return None
    p = float(sel.mean()) * 100
    corr = None
    if len(cond_cols) == 1 and cond_cols[0] in sub:
        corr = float(sub[cond_cols[0]].corr(sub[alvo]))
    return Prob(descricao, p, base, int(maioria.sum()), corr)


def _corr(rets, a, b) -> float | None:
    if a not in rets or b not in rets:
        return None
    sub = rets[[a, b]].dropna()
    if len(sub) < 40:
        return None
    return float(sub[a].corr(sub[b]))


# ---------- construção da leitura ----------

def _regime(analise: Analise, idx: dict[str, Cotacao], cotacoes: list[Cotacao]) -> None:
    # amplitude: fração de bolsas em alta
    bolsas = [
        c for c in cotacoes
        for bloco in T.BLOCOS_BOLSA
        if c.ticker in dict(T.BLOCOS[bloco])
    ]
    validas = [c for c in bolsas if c.ok]
    n_up = sum(1 for c in validas if (c.var_pct or 0) > 0)
    total = len(validas)
    frac = (n_up / total) if total else 0
    analise.amplitude = f"{n_up}/{total} bolsas em alta"

    vix = _var(idx, "^VIX")
    ouro = _var(idx, "GC=F")
    franco = _var(idx, "CHF=X")   # USD/CHF: alta = franco fraco
    y10 = _var(idx, "^TNX")

    pontos = 0  # >0 risk-on, <0 risk-off
    bullets: list[str] = []

    if total:
        if frac >= 0.6:
            pontos += 1
            bullets.append(f"Bolsas majoritariamente em alta ({n_up}/{total}).")
        elif frac <= 0.4:
            pontos -= 1
            bullets.append(f"Bolsas majoritariamente em queda ({total - n_up}/{total}).")
        else:
            bullets.append(f"Bolsas divididas ({n_up}/{total} em alta).")

    if vix is not None:
        if vix >= 3:
            pontos -= 1
            bullets.append(f"VIX disparando ({vix:+.1f}%) — medo em alta.")
        elif vix <= -3:
            pontos += 1
            bullets.append(f"VIX recuando ({vix:+.1f}%) — apetite a risco.")
        else:
            bullets.append(f"VIX estável ({vix:+.1f}%).")

    # proteção clássica: ouro + franco forte (USD/CHF em queda)
    protecao = []
    if ouro is not None and ouro > 0.3:
        protecao.append(f"ouro ({ouro:+.1f}%)")
    if franco is not None and franco < -0.3:
        protecao.append("franco suíço")
    if protecao:
        bullets.append("Procura por proteção: " + ", ".join(protecao) + ".")
    elif ouro is not None and ouro < -0.3:
        bullets.append(f"Ouro em queda ({ouro:+.1f}%) — sem fuga clássica p/ proteção.")

    if y10 is not None and abs(y10) >= 1:
        bullets.append(
            f"Treasury 10a {_dir(y10)} ({y10:+.1f}%) — "
            + ("juro subindo pressiona risco." if y10 > 0 else "juro cedendo alivia risco.")
        )

    if pontos >= 1 and (vix or 0) < 3:
        analise.regime_rotulo, analise.regime_classe = "RISK-ON", "up"
    elif pontos <= -1:
        analise.regime_rotulo, analise.regime_classe = "RISK-OFF", "down"
    else:
        analise.regime_rotulo, analise.regime_classe = "MISTO", "flat"
    analise.regime_bullets = bullets


def _cadeia(analise: Analise, idx: dict[str, Cotacao], rets) -> None:
    brent = _var(idx, "BZ=F")
    petr = _var(idx, "PETR4.SA")
    cobre = _var(idx, "HG=F")
    vale = _var(idx, "VALE3.SA")
    dxy = _var(idx, "DX-Y.NYB")
    usdbrl = _var(idx, "BRL=X")
    y10 = _var(idx, "^TNX")

    c_pb = _corr(rets, "PETR4.SA", "BZ=F") if rets is not None else None
    c_vc = _corr(rets, "VALE3.SA", "HG=F") if rets is not None else None
    c_bd = _corr(rets, "^BVSP", "DX-Y.NYB") if rets is not None else None

    def corr_txt(c):
        return f" (correlação histórica {c:+.2f})" if c is not None else ""

    # 1. Petróleo → Petrobras
    if brent is not None:
        coerente = (petr is not None and (brent > 0) == (petr > 0))
        leitura = (
            f"Brent em {_dir(brent)}; Petrobras costuma acompanhar{corr_txt(c_pb)}. "
            + (f"Hoje Petrobras em {_dir(petr)} — {'coerente' if coerente else 'divergindo'} com o petróleo."
               if petr is not None else "Petrobras sem dado.")
        )
        analise.cadeia.append(Passo("Petróleo → Petrobras", f"Brent {brent:+.2f}%", leitura))

    # 2. Minério/cobre → Vale
    if cobre is not None:
        leitura = (
            f"Cobre ('Dr. Copper', termômetro de crescimento) em {_dir(cobre)}; "
            f"puxa a leitura de Vale{corr_txt(c_vc)}. "
            + (f"Vale hoje em {_dir(vale)}." if vale is not None else "Vale sem dado.")
        )
        analise.cadeia.append(Passo("Metais → Vale", f"Cobre {cobre:+.2f}%", leitura))

    # 3. Inflação → juros (Brasil), com números reais do macro
    if analise.macro and analise.macro.ok:
        ipca12 = selic = jr = None
        for i in analise.macro.brasil:
            if i.nome == "IPCA" and i.extra == "acum. 12m" and i.ok:
                ipca12 = i.valor
            if i.nome == "Selic meta" and i.ok:
                selic = i.valor
        jr = analise.macro.juro_real
        if ipca12 is not None and selic is not None:
            _c = lambda x, d=2: f"{x:.{d}f}".replace(".", ",")
            leitura = (
                f"IPCA 12m {_c(ipca12)}% e Selic {_c(selic)}% a.a."
                + (f" → juro real ~{_c(jr, 1)}%." if jr is not None else ".")
                + " Juro real alto sustenta o real e atrai renda fixa, mas encarece "
                "o capital e pesa na bolsa."
            )
            analise.cadeia.append(
                Passo("Inflação → juros (BR)", f"Selic {_c(selic)}%", leitura))

    # 4. Juros global → risco
    if y10 is not None:
        leitura = (
            f"Treasury 10a com yield em {_dir(y10)}. "
            + ("Juro global subindo encarece o dinheiro e pressiona bolsas/emergentes."
               if y10 > 0 else
               "Juro global cedendo tende a aliviar ativos de risco e favorecer o Ibov.")
        )
        analise.cadeia.append(Passo("Juros global → risco", f"10a {y10:+.2f}%", leitura))

    # 4. DXY → real / emergentes
    if dxy is not None:
        leitura = (
            f"DXY (dólar no mundo) em {_dir(dxy)}{corr_txt(c_bd)}. "
            + ("Dólar forte lá fora pressiona emergentes e o real — vento contra o Ibov."
               if dxy > 0 else
               "Dólar fraco lá fora costuma beneficiar emergentes e o real — vento a favor.")
            + (f" USD/BRL hoje em {_dir(usdbrl)}." if usdbrl is not None else "")
        )
        analise.cadeia.append(Passo("DXY → real / emergentes", f"DXY {dxy:+.2f}%", leitura))


def _read_through(analise: Analise, idx: dict[str, Cotacao], rets) -> None:
    # Probabilidades condicionais (co-movimento histórico)
    if rets is not None:
        for cond, cols, desc in [
            ("asia", ASIA, "Quando a Ásia fecha majoritariamente em alta, o Ibovespa fecha em alta"),
            ("eur", EUROPA, "Quando a Europa fecha em alta, o Ibovespa fecha em alta"),
            ("spx", ["^GSPC"], "Quando o S&P 500 sobe no dia, o Ibovespa sobe"),
            ("ewz", ["EWZ"], "Quando o EWZ (Ibov em NY) sobe, o Ibovespa sobe"),
        ]:
            p = _prob_cond(rets, cols, "^BVSP", desc)
            if p:
                analise.probs.append(p)

        # Correlações-chave
        for a, b, rot in [
            ("^BVSP", "^DJI", "Ibovespa × Dow Jones"),
            ("^BVSP", "^GSPC", "Ibovespa × S&P 500"),
            ("^BVSP", "EWZ", "Ibovespa × EWZ"),
            ("^BVSP", "^N225", "Ibovespa × Nikkei"),
            ("^BVSP", "DX-Y.NYB", "Ibovespa × DXY"),
            ("PETR4.SA", "BZ=F", "Petrobras × Brent"),
            ("VALE3.SA", "HG=F", "Vale × Cobre"),
        ]:
            c = _corr(rets, a, b)
            if c is not None:
                analise.correls.append((rot, c))

    # ADRs / EWZ como prévia
    ewz = _var(idx, "EWZ")
    if ewz is not None:
        analise.notas.append(
            f"EWZ (ações brasileiras negociadas em NY) fechou em {_dir(ewz)} ({ewz:+.2f}%) — "
            "prévia dolarizada; sinaliza o humor externo sobre o Brasil antes da abertura aqui."
        )


def _commodities(analise: Analise, idx: dict[str, Cotacao]) -> None:
    """Read-through de cada commodity → setor/ativo que ela sinaliza."""
    def add(tk, titulo, leitura_alta, leitura_queda):
        v = _var(idx, tk)
        if v is None:
            return
        leitura = leitura_alta if v > 0 else leitura_queda
        analise.commodities.append(Passo(titulo, f"{v:+.2f}%", leitura))

    add("BZ=F", "Petróleo (Brent)",
        "Petróleo em alta pressiona a inflação global (combustível) e favorece Petrobras e petrolíferas.",
        "Petróleo em queda alivia inflação e pesa nas petrolíferas (Petrobras).")
    add("GC=F", "Ouro",
        "Ouro subindo = busca por refúgio / hedge contra inflação e juro real baixo — leitura de aversão a risco.",
        "Ouro caindo sugere apetite a risco ou dólar/juro real em alta tirando brilho do metal.")
    add("SI=F", "Prata",
        "Prata em alta: híbrido (refúgio + demanda industrial/solar) — acompanha ouro mas amplifica o ciclo.",
        "Prata em queda: enfraquece o lado industrial e o refúgio ao mesmo tempo.")
    add("HG=F", "Cobre (Dr. Copper)",
        "Cobre subindo é termômetro de CRESCIMENTO global — favorável a mineração (Vale) e a emergentes.",
        "Cobre caindo sinaliza desaceleração da demanda global — vento contra Vale e commodities.")
    pa = _var(idx, "PA=F")
    pl = _var(idx, "PL=F")
    if pa is not None or pl is not None:
        media = [x for x in (pa, pl) if x is not None]
        m = sum(media) / len(media)
        analise.commodities.append(Passo(
            "Platina / Paládio", f"{m:+.2f}%",
            "Metais de catalisador automotivo — proxy da indústria e do ciclo de autos "
            + ("(em alta: demanda industrial firme)." if m > 0 else "(em queda: indústria/autos fracos).")))


def analisar(cotacoes: list[Cotacao], macro: Macro | None = None,
             periodo_hist: str = "2y") -> Analise:
    analise = Analise()
    analise.macro = macro
    idx = _idx(cotacoes)
    rets = carregar_retornos(periodo_hist)
    analise.hist_ok = rets is not None and len(rets) > 40

    _regime(analise, idx, cotacoes)
    _cadeia(analise, idx, rets if analise.hist_ok else None)
    _commodities(analise, idx)
    _read_through(analise, idx, rets if analise.hist_ok else None)

    if not analise.hist_ok:
        analise.notas.append(
            "Histórico indisponível nesta execução — correlações e probabilidades foram puladas."
        )
    return analise
