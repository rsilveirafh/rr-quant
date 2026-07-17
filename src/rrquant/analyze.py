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

import warnings
from dataclasses import dataclass, field

import numpy as np
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
    "BRL=X": "USD/BRL",
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
    leitura: str           # interpretação do estado de hoje
    porque: str = ""       # importância / mecanismo (por que isso importa)


@dataclass
class Placar:
    prob: float               # P(Ibov sobe no próximo pregão), em %
    base: float               # taxa-base histórica, em %
    acuracia: float           # acerto fora da amostra, em %
    n: int                    # dias usados no ajuste
    classe: str               # 'up' | 'down' | 'flat' (viés do placar)
    drivers: list[tuple[str, str, str]] = field(default_factory=list)   # (nome, seta, 'favor'|'contra')
    contribs: list[tuple[str, float]] = field(default_factory=list)     # contribuição de hoje (log-odds)
    pesos: list[tuple[str, float]] = field(default_factory=list)        # |coef padronizado| (peso no modelo)


@dataclass
class Analise:
    placar: Placar | None = None
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
    sparks: dict[str, list[float]] = field(default_factory=dict)
    hist_prob: list[tuple[str, float, bool]] = field(default_factory=list)  # (data, prob%, subiu)
    hist_acerto: tuple[int, int] = (0, 0)                                   # (acertos, total) walk-forward
    hist_ok: bool = False


# ---------- helpers ----------

def _dir(v: float | None, forte: float = 1.0) -> str:
    """Frase standalone: 'em alta' / 'em forte queda' / 'de lado' / 'sem dado'."""
    if v is None:
        return "sem dado"
    if abs(v) < 0.1:
        return "de lado"
    intens = "forte " if abs(v) >= forte else ""
    return f"em {intens}alta" if v > 0 else f"em {intens}queda"


def _pct(v: float) -> str:
    """Variação formatada em pt-BR: '+1,23%' / '-0,45%'."""
    return f"{v:+.2f}%".replace(".", ",")


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
            f"Brent {_dir(brent)}; Petrobras costuma acompanhar{corr_txt(c_pb)}. "
            + (f"Hoje Petrobras {_dir(petr)} — {'coerente' if coerente else 'divergindo'} com o petróleo."
               if petr is not None else "Petrobras sem dado.")
        )
        analise.cadeia.append(Passo(
            "Petróleo → Petrobras", f"Brent {_pct(brent)}", leitura,
            porque="Petrobras é um dos maiores pesos do Ibovespa e segue o petróleo; via "
                   "combustível, o Brent ainda mexe na inflação."))

    # 2. Minério/cobre → Vale
    if cobre is not None:
        leitura = (
            f"Cobre ('Dr. Copper', termômetro de crescimento) {_dir(cobre)}; "
            f"puxa a leitura de Vale{corr_txt(c_vc)}. "
            + (f"Vale hoje {_dir(vale)}." if vale is not None else "Vale sem dado.")
        )
        analise.cadeia.append(Passo(
            "Metais → Vale", f"Cobre {_pct(cobre)}", leitura,
            porque="Vale é o maior peso do Ibovespa; sua receita vem de minério/metais "
                   "atrelados ao crescimento global (sobretudo China)."))

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
            analise.cadeia.append(Passo(
                "Inflação → juros (BR)", f"Selic {_c(selic)}%", leitura,
                porque="A Selic é o principal fator da leitura de índice e dólar: define o "
                       "custo do dinheiro e o fluxo entre bolsa e renda fixa."))

    # 4. Juros global → risco
    if y10 is not None:
        leitura = (
            f"Treasury 10a com yield {_dir(y10)}. "
            + ("Juro global subindo encarece o dinheiro e pressiona bolsas/emergentes."
               if y10 > 0 else
               "Juro global cedendo tende a aliviar ativos de risco e favorecer o Ibov.")
        )
        analise.cadeia.append(Passo(
            "Juros global → risco", f"10a {_pct(y10)}", leitura,
            porque="O Treasury de 10 anos é o retorno 'sem risco' de referência do mundo; "
                   "quando sobe, capital sai de ativos de risco e de emergentes."))

    # 4. DXY → real / emergentes
    if dxy is not None:
        leitura = (
            f"DXY (dólar no mundo) {_dir(dxy)}{corr_txt(c_bd)}. "
            + ("Dólar forte lá fora pressiona emergentes e o real — vento contra o Ibov."
               if dxy > 0 else
               "Dólar fraco lá fora costuma beneficiar emergentes e o real — vento a favor.")
            + (f" USD/BRL hoje {_dir(usdbrl)}." if usdbrl is not None else "")
        )
        analise.cadeia.append(Passo(
            "DXY → real / emergentes", f"DXY {_pct(dxy)}", leitura,
            porque="O DXY (dólar contra as principais moedas) é o termômetro de risco dos "
                   "emergentes: dita o fluxo estrangeiro pra bolsa brasileira e o valor do real."))


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
            f"EWZ (ações brasileiras negociadas em NY) fechou {_dir(ewz)} ({ewz:+.2f}%) — "
            "prévia dolarizada; sinaliza o humor externo sobre o Brasil antes da abertura aqui."
        )


def _commodities(analise: Analise, idx: dict[str, Cotacao]) -> None:
    """Read-through de cada commodity → setor que ela sinaliza (3 estados + importância)."""
    from . import porques

    # (chave em porques.COMMODITY, variação de hoje)
    itens: list[tuple[str, float | None]] = [
        ("BZ=F", _var(idx, "BZ=F")),
        ("HG=F", _var(idx, "HG=F")),
        ("GC=F", _var(idx, "GC=F")),
        ("SI=F", _var(idx, "SI=F")),
    ]
    pa, pl = _var(idx, "PA=F"), _var(idx, "PL=F")
    medias = [x for x in (pa, pl) if x is not None]
    itens.append(("PLPA", (sum(medias) / len(medias)) if medias else None))

    for chave, v in itens:
        if v is None:
            continue
        info = porques.COMMODITY[chave]
        est = porques.estado(v)  # 'alta' | 'lado' | 'queda'
        analise.commodities.append(
            Passo(info["titulo"], _pct(v), info[est], porque=info["importancia"])
        )


# ---------- Placar do Ibovespa (regressão logística sobre os sinais) ----------

# Fatores que ANTECEDEM a abertura do Ibov (sem vazamento): Ásia já fechou,
# Europa está abrindo, e S&P/EWZ entram pelo FECHAMENTO DE ONTEM em NY (que
# negociam junto/depois do Ibov no mesmo dia — por isso defasados 1 dia).
_FATORES = ["Ásia", "Europa", "S&P 500 (ont.)", "EWZ (ont.)", "DXY"]


def _sigmoide(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def _fit_logit(X, y, iters=800, lr=0.5, l2=1.0):
    """Regressão logística simples (gradiente descendente + L2). X já padronizado."""
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(iters):
        p = _sigmoide(X @ w + b)
        g = p - y
        w -= lr * (X.T @ g / n + l2 * w / n)
        b -= lr * g.mean()
    return w, b


def _placar(analise: Analise, rets: pd.DataFrame) -> None:
    need = ["^N225", "^HSI", "^KS11", "^GDAXI", "^STOXX50E", "^GSPC", "EWZ", "DX-Y.NYB", "^BVSP"]
    if any(c not in rets for c in need):
        return
    df = rets[need].dropna()
    if len(df) < 120:
        return

    asia = df[["^N225", "^HSI", "^KS11"]].mean(axis=1)
    europa = df[["^GDAXI", "^STOXX50E"]].mean(axis=1)
    # S&P e EWZ negociam junto/depois do Ibov → usar o FECHAMENTO DE ONTEM (shift 1)
    feat = pd.DataFrame({
        "Ásia":            asia,
        "Europa":          europa,
        "S&P 500 (ont.)":  df["^GSPC"].shift(1),
        "EWZ (ont.)":      df["EWZ"].shift(1),
        "DXY":             df["DX-Y.NYB"],
    })
    ibov_ret = df["^BVSP"]                       # retorno do Ibov na sessão (alvo)
    dados = feat.copy()
    dados["y"] = (ibov_ret > 0).astype(float)
    dados = dados.dropna()
    if len(dados) < 120:
        return

    Xall = dados[feat.columns].values
    yall = dados["y"].values
    mu, sd = Xall.mean(0), Xall.std(0)
    sd[sd == 0] = 1.0
    Xs = (Xall - mu) / sd

    # Acurácia HONESTA: split cronológico 80/20 (fora da amostra).
    k = int(len(Xs) * 0.8)
    if k >= 60 and (len(Xs) - k) >= 20:
        w0, b0 = _fit_logit(Xs[:k], yall[:k])
        pred = _sigmoide(Xs[k:] @ w0 + b0) > 0.5
        acc = float((pred == (yall[k:] > 0.5)).mean()) * 100
    else:
        acc = float("nan")

    # Modelo final treina em tudo
    w, b = _fit_logit(Xs, yall)
    base = float(yall.mean()) * 100

    # Previsão p/ o PRÓXIMO pregão: usa os leads mais recentes (Ásia/Europa/DXY de
    # hoje + fechamento de hoje em NY, que será o "de ontem" na próxima sessão).
    leads = np.array([
        asia.iloc[-1], europa.iloc[-1], df["^GSPC"].iloc[-1],
        df["EWZ"].iloc[-1], df["DX-Y.NYB"].iloc[-1],
    ], dtype=float)
    x_hoje = (leads - mu) / sd
    prob = float(_sigmoide(x_hoje @ w + b)) * 100

    classe = "up" if prob >= 53 else ("down" if prob <= 47 else "flat")

    # Vieses: relação UNIVARIADA (lead → sessão do Ibov). Estável e intuitiva.
    pares = []
    for j, nome in enumerate(_FATORES):
        c = dados[nome].corr(pd.Series(dados["y"].values, index=dados.index)
                             .replace({0: -1}))  # sinal do lead vs alta/baixa
        hoje = float(leads[j])
        if abs(hoje) < 1e-9 or pd.isna(c) or abs(c) < 0.05:
            continue
        seta = "▲" if hoje > 0 else "▼"
        favor = "favor" if (hoje > 0) == (c > 0) else "contra"
        pares.append((abs(c), nome, seta, favor))
    pares.sort(reverse=True)
    drivers = [(nome, seta, favor) for _c, nome, seta, favor in pares[:3]]

    # Decomposição do score de hoje: contribuição = peso × fator padronizado
    contribs = [(_FATORES[j], float(w[j] * x_hoje[j])) for j in range(len(_FATORES))]
    pesos = [(_FATORES[j], float(abs(w[j]))) for j in range(len(_FATORES))]

    analise.placar = Placar(prob, base, acc, int(len(dados)), classe,
                            drivers, contribs, pesos)


def _historico_prob(rets: pd.DataFrame, janela: int = 60) -> tuple[list, tuple[int, int]]:
    """Série walk-forward da probabilidade: p/ cada dia da janela, treina SÓ com o
    passado e prevê aquele dia. Devolve [(data, prob%, subiu?)] e (acertos, total)."""
    need = ["^N225", "^HSI", "^KS11", "^GDAXI", "^STOXX50E", "^GSPC", "EWZ", "DX-Y.NYB", "^BVSP"]
    if any(c not in rets for c in need):
        return [], (0, 0)
    df = rets[need].dropna()
    feat = pd.DataFrame({
        "Ásia":            df[["^N225", "^HSI", "^KS11"]].mean(axis=1),
        "Europa":          df[["^GDAXI", "^STOXX50E"]].mean(axis=1),
        "S&P 500 (ont.)":  df["^GSPC"].shift(1),
        "EWZ (ont.)":      df["EWZ"].shift(1),
        "DXY":             df["DX-Y.NYB"],
    })
    dados = feat.copy()
    dados["y"] = (df["^BVSP"] > 0).astype(float)
    dados = dados.dropna()
    X = dados[feat.columns].values
    yv = dados["y"].values
    datas = [d.strftime("%d/%m") for d in dados.index]
    n = len(X)

    janela = min(janela, n - 120)   # exige treino mínimo antes da janela
    if janela < 10:
        return [], (0, 0)

    pontos, hits = [], 0
    for i in range(n - janela, n):
        mu, sd = X[:i].mean(0), X[:i].std(0)
        sd[sd == 0] = 1.0
        w, b = _fit_logit((X[:i] - mu) / sd, yv[:i])
        p = float(_sigmoide(((X[i] - mu) / sd) @ w + b)) * 100
        subiu = bool(yv[i] > 0.5)
        pontos.append((datas[i], p, subiu))
        if (p >= 50) == subiu:
            hits += 1
    return pontos, (hits, janela)


def analisar(cotacoes: list[Cotacao], macro: Macro | None = None,
             periodo_hist: str = "2y") -> Analise:
    analise = Analise()
    analise.macro = macro
    idx = _idx(cotacoes)
    rets = carregar_retornos(periodo_hist)
    analise.hist_ok = rets is not None and len(rets) > 40

    _regime(analise, idx, cotacoes)
    if analise.hist_ok:
        _placar(analise, rets)
        analise.hist_prob, analise.hist_acerto = _historico_prob(rets)
        # sparklines: últimos ~30 pregões (retorno acumulado normalizado)
        for tk in ("^BVSP", "BZ=F", "BRL=X", "^VIX", "GC=F"):
            if tk in rets:
                serie = (1 + rets[tk].dropna().tail(30)).cumprod()
                if len(serie) >= 2:
                    analise.sparks[tk] = [float(x) for x in serie.values]
    _cadeia(analise, idx, rets if analise.hist_ok else None)
    _commodities(analise, idx)
    _read_through(analise, idx, rets if analise.hist_ok else None)

    if not analise.hist_ok:
        analise.notas.append(
            "Histórico indisponível nesta execução — correlações e probabilidades foram puladas."
        )
    return analise
