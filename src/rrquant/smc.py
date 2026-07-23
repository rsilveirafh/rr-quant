"""Motor SMC (Smart Money Concepts) determinístico sobre OHLC.

Fatia 1 da aba SMC: detecção de **swing points** (fractais) e de **estrutura**
de mercado — BOS (Break of Structure) e CHoCH (Change of Character) — por regras
explícitas, sem mandar nada pra IA. Tudo reproduzível e offline, no espírito do
resto do rr-quant (nada é "previsão"; é leitura de estrutura passada).

Ordem do método (ver [[areas/financas/trade/CLAUDE]] no vault): a estrutura é a
base de tudo o que vem depois (Order Blocks, FVG, liquidez, decisão). Aqui só a
base — swings + BOS/CHoCH. O resto entra nas próximas fatias.

CAVEAT honesto: um swing só é *confirmado* `forca` candles depois de formado, então
os últimos `forca` candles são **provisórios** — a estrutura recente pode mudar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Swing:
    idx: int          # posição no DataFrame renderizado
    tipo: str         # 'H' (swing high) | 'L' (swing low)
    preco: float
    data: str         # dd/mm


@dataclass
class Evento:
    idx: int          # candle em que o rompimento (por fechamento) aconteceu
    tipo: str         # 'BOS' | 'CHoCH'
    direcao: str      # 'alta' | 'baixa'
    nivel: float      # preço do swing rompido
    origem: int       # posição do swing que foi rompido (início da linha)
    data: str         # dd/mm do rompimento


@dataclass
class FVG:
    idx: int          # candle do meio (o deslocamento que abriu o gap)
    tipo: str         # 'alta' | 'baixa'
    topo: float       # limite superior da zona
    base: float       # limite inferior da zona (topo > base)
    mitigado: bool    # preço já voltou pra dentro do gap?
    data: str


@dataclass
class OrderBlock:
    idx: int          # candle do OB (último contrário antes do deslocamento)
    tipo: str         # 'compra' (demanda) | 'venda' (oferta/supply)
    topo: float
    base: float
    mitigado: bool    # preço já retornou à zona?
    data: str


@dataclass
class Liquidez:
    tipo: str         # 'BSL' (equal highs, acima) | 'SSL' (equal lows, abaixo)
    nivel: float
    x_ini: int
    x_fim: int
    varrido: bool     # preço já rompeu esse nível depois de formado?
    data: str


@dataclass
class SMC:
    ticker: str
    nome: str
    timeframe: str                 # rótulo legível ('Diário', 'Semanal')
    df: pd.DataFrame               # OHLC já fatiado p/ renderização
    swings: list[Swing] = field(default_factory=list)
    eventos: list[Evento] = field(default_factory=list)
    fvgs: list[FVG] = field(default_factory=list)
    obs: list[OrderBlock] = field(default_factory=list)
    liquidez: list[Liquidez] = field(default_factory=list)
    trend: str | None = None       # tendência estrutural corrente
    forca: int = 3                 # força do fractal usada
    provisorios: int = 0           # nº de candles finais ainda não confirmados


def detectar_swings(df: pd.DataFrame, forca: int = 3) -> tuple[list[int], list[int]]:
    """Fractais: swing high em i = máxima estritamente maior que as `forca` máximas
    de cada lado (idem para swing low com mínimas). Estrito (sem empate) p/ evitar
    marcar platôs. Devolve (posições de swing high, posições de swing low)."""
    highs = df["High"].values
    lows = df["Low"].values
    n = len(df)
    sh, sl = [], []
    for i in range(forca, n - forca):
        jh = highs[i - forca:i + forca + 1]
        jl = lows[i - forca:i + forca + 1]
        if highs[i] == jh.max() and (jh == highs[i]).sum() == 1:
            sh.append(i)
        if lows[i] == jl.min() and (jl == lows[i]).sum() == 1:
            sl.append(i)
    return sh, sl


def detectar_estrutura(df: pd.DataFrame, sh: list[int], sl: list[int]) -> tuple[list[Evento], str | None]:
    """Caminha os candles em ordem, guardando o último swing high (resistência) e
    último swing low (suporte) ainda não rompidos. Quando o FECHAMENTO rompe um deles:
      - a favor da tendência vigente → BOS (continuação);
      - contra a tendência vigente  → CHoCH (mudança de caráter).
    Fechamento (não pavio) para evitar sinal por sombra. O nível rompido é "consumido"
    e o motor espera o próximo swing daquele lado. Devolve (eventos, tendência final).
    """
    close = df["Close"].values
    highs = df["High"].values
    lows = df["Low"].values
    sh_price = {i: float(highs[i]) for i in sh}
    sl_price = {i: float(lows[i]) for i in sl}
    datas = [d.strftime("%d/%m") for d in df.index]

    eventos: list[Evento] = []
    trend: str | None = None
    ultimo_sh: tuple[int, float] | None = None
    ultimo_sl: tuple[int, float] | None = None

    for t in range(len(df)):
        if t in sh_price:
            ultimo_sh = (t, sh_price[t])
        if t in sl_price:
            ultimo_sl = (t, sl_price[t])

        if ultimo_sh is not None and t > ultimo_sh[0] and close[t] > ultimo_sh[1]:
            tipo = "CHoCH" if trend == "baixa" else "BOS"
            eventos.append(Evento(t, tipo, "alta", ultimo_sh[1], ultimo_sh[0], datas[t]))
            trend = "alta"
            ultimo_sh = None
        elif ultimo_sl is not None and t > ultimo_sl[0] and close[t] < ultimo_sl[1]:
            tipo = "CHoCH" if trend == "alta" else "BOS"
            eventos.append(Evento(t, tipo, "baixa", ultimo_sl[1], ultimo_sl[0], datas[t]))
            trend = "baixa"
            ultimo_sl = None

    return eventos, trend


def detectar_fvg(df: pd.DataFrame) -> list[FVG]:
    """Fair Value Gap = desequilíbrio de 3 candles. FVG de alta: a mínima do candle
    i+1 fica ACIMA da máxima do candle i-1 (gap não preenchido no meio). De baixa: a
    máxima de i+1 abaixo da mínima de i-1. Marca como mitigado se o preço voltou à zona."""
    h, l = df["High"].values, df["Low"].values
    datas = [d.strftime("%d/%m") for d in df.index]
    n = len(df)
    out: list[FVG] = []
    for i in range(1, n - 1):
        if l[i + 1] > h[i - 1]:
            out.append(FVG(i, "alta", float(l[i + 1]), float(h[i - 1]), False, datas[i]))
        elif h[i + 1] < l[i - 1]:
            out.append(FVG(i, "baixa", float(l[i - 1]), float(h[i + 1]), False, datas[i]))
    for f in out:
        seg_l, seg_h = l[f.idx + 2:], h[f.idx + 2:]
        if len(seg_l) == 0:
            continue
        f.mitigado = bool((seg_l <= f.topo).any()) if f.tipo == "alta" else bool((seg_h >= f.base).any())
    return out


def detectar_order_blocks(df: pd.DataFrame, eventos: list[Evento], look: int = 10) -> list[OrderBlock]:
    """OB Principal = último candle CONTRÁRIO antes do deslocamento que rompeu estrutura.
    Ancorado nos eventos (BOS/CHoCH): p/ um rompimento de alta, o último candle de baixa
    antes dele é o OB de compra (demanda); simétrico p/ baixa. Zona = RANGE do candle
    (máxima→mínima, pavios inclusos) — cobre toda a "impressão" do candle."""
    o, c = df["Open"].values, df["Close"].values
    h, l = df["High"].values, df["Low"].values
    datas = [d.strftime("%d/%m") for d in df.index]
    achados: dict[tuple[int, str], OrderBlock] = {}
    for e in eventos:
        alta = e.direcao == "alta"
        j = None
        for k in range(e.idx, max(-1, e.idx - look), -1):
            if (c[k] < o[k]) if alta else (c[k] > o[k]):   # candle contrário ao rompimento
                j = k
                break
        if j is None:
            continue
        tipo = "compra" if alta else "venda"
        achados.setdefault((j, tipo), OrderBlock(j, tipo, float(h[j]), float(l[j]), False, datas[j]))
    obs = sorted(achados.values(), key=lambda b: b.idx)
    for b in obs:
        seg_l, seg_h = l[b.idx + 1:], h[b.idx + 1:]
        if len(seg_l) == 0:
            continue
        b.mitigado = bool((seg_l <= b.topo).any()) if b.tipo == "compra" else bool((seg_h >= b.base).any())
    return obs


def _clusters(pts: list[tuple[int, float]], tol_rel: float, tipo: str,
              h, l, datas) -> list[Liquidez]:
    """Agrupa swings de preço parecido (dentro de tol_rel) em poças de liquidez."""
    if len(pts) < 2:
        return []
    maior = tipo == "BSL"
    ordenado = sorted(pts, key=lambda p: p[1])
    grupos, atual = [], [ordenado[0]]
    for p in ordenado[1:]:
        if abs(p[1] - atual[-1][1]) <= tol_rel * p[1]:
            atual.append(p)
        else:
            if len(atual) >= 2:
                grupos.append(atual)
            atual = [p]
    if len(atual) >= 2:
        grupos.append(atual)

    out: list[Liquidez] = []
    for g in grupos:
        idxs = [i for i, _ in g]
        precos = [pr for _, pr in g]
        nivel = max(precos) if maior else min(precos)
        x_fim = max(idxs)
        if maior:
            varrido = bool((h[x_fim + 1:] > nivel).any()) if x_fim + 1 < len(h) else False
        else:
            varrido = bool((l[x_fim + 1:] < nivel).any()) if x_fim + 1 < len(l) else False
        out.append(Liquidez(tipo, float(nivel), min(idxs), x_fim, varrido, datas[x_fim]))
    return out


def detectar_liquidez(df: pd.DataFrame, sh: list[int], sl: list[int],
                      tol_rel: float = 0.0025) -> list[Liquidez]:
    """Equal highs → liquidez de compra (BSL, acima); equal lows → de venda (SSL, abaixo)."""
    h, l = df["High"].values, df["Low"].values
    datas = [d.strftime("%d/%m") for d in df.index]
    bsl = _clusters([(i, float(h[i])) for i in sh], tol_rel, "BSL", h, l, datas)
    ssl = _clusters([(i, float(l[i])) for i in sl], tol_rel, "SSL", h, l, datas)
    return bsl + ssl


def analisar(ticker: str, nome: str, ohlc: pd.DataFrame | None,
             timeframe: str = "Diário", forca: int = 3, n_render: int = 120) -> SMC | None:
    """Roda o motor sobre o histórico completo e devolve um SMC já fatiado para os
    últimos `n_render` candles (índices em espaço de renderização)."""
    if ohlc is None or len(ohlc) < 2 * forca + 10:
        return None

    sh, sl = detectar_swings(ohlc, forca)
    eventos, trend = detectar_estrutura(ohlc, sh, sl)
    fvgs = detectar_fvg(ohlc)
    obs = detectar_order_blocks(ohlc, eventos)
    liquidez = detectar_liquidez(ohlc, sh, sl)

    ini = max(0, len(ohlc) - n_render)
    df_r = ohlc.iloc[ini:]
    highs = ohlc["High"].values
    lows = ohlc["Low"].values
    datas = [d.strftime("%d/%m") for d in ohlc.index]

    swings = (
        [Swing(i - ini, "H", float(highs[i]), datas[i]) for i in sh if i >= ini]
        + [Swing(i - ini, "L", float(lows[i]), datas[i]) for i in sl if i >= ini]
    )
    swings.sort(key=lambda s: s.idx)

    eventos_r = [
        Evento(e.idx - ini, e.tipo, e.direcao, e.nivel, max(0, e.origem - ini), e.data)
        for e in eventos if e.idx >= ini
    ]
    fvgs_r = [
        FVG(f.idx - ini, f.tipo, f.topo, f.base, f.mitigado, f.data)
        for f in fvgs if f.idx >= ini
    ]
    obs_r = [
        OrderBlock(b.idx - ini, b.tipo, b.topo, b.base, b.mitigado, b.data)
        for b in obs if b.idx >= ini
    ]
    liq_r = [
        Liquidez(q.tipo, q.nivel, max(0, q.x_ini - ini), q.x_fim - ini, q.varrido, q.data)
        for q in liquidez if q.x_fim >= ini
    ]

    return SMC(
        ticker=ticker, nome=nome, timeframe=timeframe, df=df_r,
        swings=swings, eventos=eventos_r, fvgs=fvgs_r, obs=obs_r, liquidez=liq_r,
        trend=trend, forca=forca, provisorios=forca,
    )
