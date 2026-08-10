"""Arquivo de snapshots pré-abertura para o piloto de previsão do Ibovespa.

Cada execução registra as últimas cotações disponíveis e o horário real de coleta. A série
não é usada pelo modelo até haver observações suficientes; ela existe para formar uma base
histórica sem olhar informação posterior ao corte de 09:50 BRT.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf


FUSO_BAHIA = ZoneInfo("America/Bahia")
HORARIO_ALVO = (9, 50)

# Somente séries disponíveis no piloto gratuito. WIN/DOL/DI ficam para uma fonte B3
# intraday futura; não substituímos esses contratos por proxies sem identificá-los.
ATIVOS = {
    "asia_nikkei": "^N225",
    "asia_hang_seng": "^HSI",
    "asia_kospi": "^KS11",
    "europa_dax": "^GDAXI",
    "europa_eurostoxx": "^STOXX50E",
    "futuro_sp500": "ES=F",
    "futuro_nasdaq": "NQ=F",
    "ewz": "EWZ",
    "brent": "BZ=F",
    "cobre": "HG=F",
    "usd_brl": "BRL=X",
    "dxy": "DX-Y.NYB",
    "vix": "^VIX",
    "ibovespa": "^BVSP",
}

CAMPOS = ("coletado_em_brt", "qualidade_horario", "campo", "ticker", "preco", "barra_em")


def _qualidade_horario(agora: datetime) -> str:
    """Classifica a coleta; análises usarão apenas a janela 09:45–10:05 BRT."""
    minutos = agora.hour * 60 + agora.minute
    alvo = HORARIO_ALVO[0] * 60 + HORARIO_ALVO[1]
    return "no_alvo" if abs(minutos - alvo) <= 15 else "fora_da_janela"


def _ultima_barra(df: pd.DataFrame, ticker: str) -> tuple[float | None, str]:
    """Extrai último fechamento e timestamp do formato simples ou MultiIndex do yfinance."""
    if df is None or df.empty:
        return None, ""
    try:
        serie = df["Close"][ticker] if isinstance(df.columns, pd.MultiIndex) else df["Close"]
        serie = serie.dropna()
        if serie.empty:
            return None, ""
        return float(serie.iloc[-1]), str(serie.index[-1])
    except (KeyError, TypeError):
        return None, ""


def coletar_snapshot(agora: datetime | None = None) -> list[dict[str, str]]:
    """Coleta um lote de cotações de 1 minuto e devolve linhas prontas para CSV."""
    agora = agora or datetime.now(FUSO_BAHIA)
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=FUSO_BAHIA)
    else:
        agora = agora.astimezone(FUSO_BAHIA)

    tickers = list(ATIVOS.values())
    try:
        dados = yf.download(
            tickers, period="1d", interval="1m", prepost=True,
            progress=False, auto_adjust=True, threads=False,
        )
    except Exception:
        dados = pd.DataFrame()

    coletado = agora.isoformat(timespec="seconds")
    qualidade = _qualidade_horario(agora)
    linhas = []
    for campo, ticker in ATIVOS.items():
        preco, barra_em = _ultima_barra(dados, ticker)
        linhas.append({
            "coletado_em_brt": coletado,
            "qualidade_horario": qualidade,
            "campo": campo,
            "ticker": ticker,
            "preco": "" if preco is None else f"{preco:.10g}",
            "barra_em": barra_em,
        })
    return linhas


def gravar_snapshot(caminho: Path, linhas: list[dict[str, str]]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    novo = not caminho.exists()
    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS)
        if novo:
            escritor.writeheader()
        escritor.writerows(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Captura snapshot pré-abertura do piloto")
    parser.add_argument("--output", type=Path, default=Path("data/snapshots/pre_abertura.csv"))
    args = parser.parse_args(argv)
    linhas = coletar_snapshot()
    gravar_snapshot(args.output, linhas)
    validos = sum(bool(linha["preco"]) for linha in linhas)
    print(f"Snapshot: {validos}/{len(linhas)} cotações gravadas em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
