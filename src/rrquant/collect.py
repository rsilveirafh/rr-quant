"""Coleta de dados de mercado via yfinance e calculo da variacao do dia.

Usa threads=False p/ evitar o "database is locked" do cache de timezone do
yfinance em download concorrente. Variacao e calculada por ticker a partir
dos seus dois ultimos fechamentos validos (mercados fecham em dias diferentes
por feriado/fuso, entao nao da p/ assumir uma data comum).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yfinance as yf

from . import tickers as T

warnings.filterwarnings("ignore")

# O yfinance persiste o cache de fusos/cookies por padrão no perfil do usuário.
# Mantê-lo no projeto torna a execução portátil (inclusive em ambientes isolados).
_CACHE_YFINANCE = Path(__file__).resolve().parents[2] / "data" / "yfinance-cache"
_CACHE_YFINANCE.mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(_CACHE_YFINANCE)


@dataclass
class Cotacao:
    ticker: str
    nome: str
    ultimo: float | None
    anterior: float | None
    data: str | None  # data do ultimo fechamento (YYYY-MM-DD)

    @property
    def var_pct(self) -> float | None:
        if self.ultimo is None or self.anterior in (None, 0):
            return None
        return (self.ultimo / self.anterior - 1.0) * 100.0

    @property
    def ok(self) -> bool:
        return self.var_pct is not None


def _dois_ultimos(serie: pd.Series) -> tuple[float | None, float | None, str | None]:
    """Ultimos dois valores nao-nulos de uma serie de fechamento."""
    s = serie.dropna()
    if len(s) == 0:
        return None, None, None
    ultimo = float(s.iloc[-1])
    data = s.index[-1].strftime("%Y-%m-%d")
    anterior = float(s.iloc[-2]) if len(s) >= 2 else None
    return ultimo, anterior, data


def coletar(periodo: str = "7d") -> list[Cotacao]:
    """Baixa todos os tickers do catalogo e devolve as cotacoes com variacao."""
    simbolos = T.todos_os_tickers()
    nomes = T.mapa_nomes()

    df = yf.download(
        simbolos,
        period=periodo,
        interval="1d",
        progress=False,
        auto_adjust=True,
        threads=False,
    )
    fechamento = df["Close"] if "Close" in df.columns.get_level_values(0) else df

    cotacoes: list[Cotacao] = []
    for simbolo in simbolos:
        try:
            serie = fechamento[simbolo]
        except (KeyError, TypeError):
            serie = pd.Series(dtype="float64")
        ultimo, anterior, data = _dois_ultimos(serie)
        cotacoes.append(
            Cotacao(
                ticker=simbolo,
                nome=nomes.get(simbolo, simbolo),
                ultimo=ultimo,
                anterior=anterior,
                data=data,
            )
        )
    return cotacoes


def coletar_ohlc(ticker: str, periodo: str = "2y", intervalo: str = "1d") -> pd.DataFrame | None:
    """Baixa OHLC (Open/High/Low/Close) de UM ticker p/ análise SMC. Devolve DataFrame
    indexado por data ou None se não vier dado. Lida com o formato MultiIndex que o
    yfinance às vezes usa mesmo p/ um único símbolo."""
    df = yf.download(
        ticker, period=periodo, interval=intervalo,
        progress=False, auto_adjust=True, threads=False,
    )
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    cols = ["Open", "High", "Low", "Close"]
    if not all(c in df.columns for c in cols):
        return None
    out = df[cols].dropna()
    return out if len(out) else None


def resample_ohlc(df: pd.DataFrame | None, regra: str = "W") -> pd.DataFrame | None:
    """Reamostra OHLC diário p/ um timeframe maior (semanal por padrão). Abertura = 1º
    do período, máxima = maior, mínima = menor, fechamento = último. Permite a leitura
    HTF (semanal) a partir do mesmo pipeline diário, sem baixar fonte nova."""
    if df is None or df.empty:
        return None
    agg = df.resample(regra).agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    ).dropna()
    return agg if len(agg) else None


def por_bloco(cotacoes: list[Cotacao]) -> dict[str, list[Cotacao]]:
    """Reagrupa as cotacoes na estrutura de blocos do catalogo."""
    indice = {c.ticker: c for c in cotacoes}
    saida: dict[str, list[Cotacao]] = {}
    for bloco, itens in T.BLOCOS.items():
        saida[bloco] = [indice[t] for (t, _n) in itens if t in indice]
    return saida
