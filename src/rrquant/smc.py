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
class SMC:
    ticker: str
    nome: str
    timeframe: str                 # rótulo legível ('Diário', 'Semanal')
    df: pd.DataFrame               # OHLC já fatiado p/ renderização
    swings: list[Swing] = field(default_factory=list)
    eventos: list[Evento] = field(default_factory=list)
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


def analisar(ticker: str, nome: str, ohlc: pd.DataFrame | None,
             timeframe: str = "Diário", forca: int = 3, n_render: int = 120) -> SMC | None:
    """Roda o motor sobre o histórico completo e devolve um SMC já fatiado para os
    últimos `n_render` candles (índices em espaço de renderização)."""
    if ohlc is None or len(ohlc) < 2 * forca + 10:
        return None

    sh, sl = detectar_swings(ohlc, forca)
    eventos, trend = detectar_estrutura(ohlc, sh, sl)

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

    return SMC(
        ticker=ticker, nome=nome, timeframe=timeframe, df=df_r,
        swings=swings, eventos=eventos_r, trend=trend,
        forca=forca, provisorios=forca,
    )
