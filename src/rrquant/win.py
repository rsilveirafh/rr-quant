"""Dados do próprio WIN para o Plano do dia.

Três fontes, na ordem de preferência:

1. **Negócios da B3** (`b3negocios.py`): barras de 1 min montadas a partir do arquivo
   público de negócios de cada pregão e guardadas em `data/win/1min/`. Funciona no PC e
   no GitHub Actions, sem programa aberto nem login. Começa em 15/10/2026 (a B3 só guarda
   um mês); para semana e mês anteriores ao começo, completa com o diário da brapi.
2. **Profit local** (`profit.py`): barras de 2 min do WINFUT (série contínua do Profit),
   reamostradas para 15 min, 1h e diário. É a fonte completa, mas só existe no PC onde
   o Profit roda e só está em dia se o Profit tiver ficado aberto no último pregão.
3. **brapi.dev** (`/api/v2/futures`): diário do contrato vigente, sem token para WIN.
   Serve no GitHub Actions. Não tem intraday nem abertura (o campo `open` vem nulo).

Contrato vigente = o de maior volume no último pregão (é para lá que o mercado rola
antes do vencimento). Na brapi, a série é a do próprio contrato, sem emenda.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.request
from dataclasses import dataclass

import pandas as pd

from . import b3negocios, profit

BRAPI = "https://brapi.dev/api/v2/futures"
_AGG = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}


@dataclass
class DadosWin:
    rotulo: str                       # de onde veio, para a tela
    diario: pd.DataFrame              # OHLC diário (Open pode ser NaN na brapi)
    m15: pd.DataFrame | None = None   # intraday, só quando vem do Profit
    h1: pd.DataFrame | None = None


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "rr-quant"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def contrato_vigente() -> str | None:
    """Símbolo do WIN com maior volume no último pregão (ex.: 'WINZ26')."""
    cs = _get(f"{BRAPI}/term-structure?asset=WIN").get("contracts") or []
    cs = [c for c in cs if c.get("volume")]
    return max(cs, key=lambda c: c["volume"])["symbol"] if cs else None


def diario_brapi(simbolo: str, dias: int = 120) -> pd.DataFrame | None:
    inicio = (dt.date.today() - dt.timedelta(days=dias)).isoformat()
    hist = _get(f"{BRAPI}/historical?symbol={simbolo}&startDate={inicio}&sortOrder=asc").get(
        "future", {}).get("history") or []
    linhas = [(pd.Timestamp(h["date"], unit="s").normalize(), h.get("open"), h["high"], h["low"],
               h["close"]) for h in hist if h.get("high") and h.get("low") and h.get("close")]
    if not linhas:
        return None
    df = pd.DataFrame(linhas, columns=["data", "Open", "High", "Low", "Close"]).set_index("data")
    return df.astype(float).sort_index()


def _profit_ohlc(minutos: int = 2) -> pd.DataFrame | None:
    try:
        df = profit.carregar(minutos=minutos)
    except (FileNotFoundError, OSError):
        return None
    df.index = pd.to_datetime(df.index)
    return df.rename(columns={"abertura": "Open", "maxima": "High", "minima": "Low",
                              "fechamento": "Close"})[["Open", "High", "Low", "Close"]]


def _reamostrar(df: pd.DataFrame, regra: str) -> pd.DataFrame:
    return df.resample(regra).agg(_AGG).dropna()


def carregar(antes_de: dt.date) -> DadosWin | None:
    """Melhor fonte do WIN para o plano do pregão `antes_de` (só barras anteriores a ele).

    O Profit só é usado se tiver o último pregão completo, o mesmo que a brapi já tem;
    senão o intraday estaria velho e os níveis, errados."""
    simbolo, brapi = None, None
    try:
        simbolo = contrato_vigente()
        brapi = diario_brapi(simbolo) if simbolo else None
    except (OSError, ValueError, KeyError):
        pass
    ultimo = None
    if brapi is not None:
        d = brapi[brapi.index.date < antes_de]
        ultimo = d.index[-1].date() if len(d) else None

    b3 = b3negocios.carregar()
    if b3 is not None:
        b3 = b3[b3.index.date < antes_de].rename(columns={
            "abertura": "Open", "maxima": "High", "minima": "Low", "fechamento": "Close"})
        if len(b3):   # só o contrato vigente: emendar vencimentos cria degrau falso no gráfico
            b3 = b3[b3.contrato == b3.contrato.iloc[-1]]
        fim = b3.index[-1].date() if len(b3) else None
        if fim is not None and (ultimo is None or fim >= ultimo):
            diario = _reamostrar(b3[["Open", "High", "Low", "Close"]], "D")
            if brapi is not None:
                diario = diario.combine_first(brapi)
            return DadosWin(f"WIN dos negócios da B3 (barras de 1 min até {fim:%d/%m}, "
                            f"contrato {b3.contrato.iloc[-1]})", diario,
                            _reamostrar(b3, "15min"), _reamostrar(b3, "1h"))

    m2 = _profit_ohlc(2)
    if m2 is not None:
        m2 = m2[m2.index.date < antes_de]
        fim = m2.index[-1].date() if len(m2) else None
        if fim is not None and (ultimo is None or fim >= ultimo):
            return DadosWin(f"WIN do Profit (WINFUT, barras de 2 min até {fim:%d/%m})",
                            _reamostrar(m2, "D"), _reamostrar(m2, "15min"), _reamostrar(m2, "1h"))

    if brapi is not None:
        return DadosWin(f"WIN diário da brapi ({simbolo})", brapi)
    return None
