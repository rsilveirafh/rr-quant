"""Coleta de dados de mercado via yfinance e calculo da variacao do dia.

Usa threads=False p/ evitar o "database is locked" do cache de timezone do
yfinance em download concorrente. Variacao e calculada por ticker a partir
dos seus dois ultimos fechamentos validos (mercados fecham em dias diferentes
por feriado/fuso, entao nao da p/ assumir uma data comum).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from . import tickers as T

warnings.filterwarnings("ignore")


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


def por_bloco(cotacoes: list[Cotacao]) -> dict[str, list[Cotacao]]:
    """Reagrupa as cotacoes na estrutura de blocos do catalogo."""
    indice = {c.ticker: c for c in cotacoes}
    saida: dict[str, list[Cotacao]] = {}
    for bloco, itens in T.BLOCOS.items():
        saida[bloco] = [indice[t] for (t, _n) in itens if t in indice]
    return saida
