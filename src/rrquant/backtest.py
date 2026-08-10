"""Backtest histórico sem vazamento: fechamento t -> próximo pregão do Ibovespa.

Este é o atalho honesto enquanto o piloto de snapshots 09:50 BRT ainda acumula dados.
Ele não tenta reconstruir a pré-abertura: cada previsão usa exclusivamente fechamentos que
já existiam no fim do pregão t e prevê a direção do próximo pregão brasileiro.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from .analyze import _fit_logit, _sigmoide


TICKERS = {
    "ibov": "^BVSP",
    "nikkei": "^N225",
    "hang_seng": "^HSI",
    "kospi": "^KS11",
    "dax": "^GDAXI",
    "eurostoxx": "^STOXX50E",
    "sp500": "^GSPC",
    "ewz": "EWZ",
    "dxy": "DX-Y.NYB",
    "usd_brl": "BRL=X",
    "brent": "BZ=F",
    "cobre": "HG=F",
    "vix": "^VIX",
}


def baixar_fechamentos(periodo: str = "10y") -> pd.DataFrame:
    """Baixa preços de fechamento diários e normaliza o retorno do yfinance."""
    bruto = yf.download(list(TICKERS.values()), period=periodo, interval="1d",
                        progress=False, auto_adjust=True, threads=False)
    fech = bruto["Close"] if isinstance(bruto.columns, pd.MultiIndex) else bruto
    fech = fech.rename(columns={ticker: nome for nome, ticker in TICKERS.items()})
    return fech.sort_index()


def montar_dataset(fechamentos: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Monta fatores conhecidos no fechamento e o alvo do próximo pregão.

    Feriado externo recebe retorno zero, pois não houve informação nova naquele mercado.
    O alvo é deslocado em -1: jamais aparece entre os preditores do mesmo registro.
    """
    if "ibov" not in fechamentos:
        raise ValueError("Histórico do Ibovespa indisponível.")
    precos = fechamentos.reindex(columns=list(TICKERS)).copy()
    retornos = precos.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    indice = precos["ibov"].dropna().index
    if indice.empty:
        raise ValueError("Histórico diário do Ibovespa não foi retornado pela fonte.")
    retornos = retornos.reindex(indice).fillna(0.0)
    ibov = retornos["ibov"]

    dados = pd.DataFrame(index=indice)
    dados["asia"] = retornos[["nikkei", "hang_seng", "kospi"]].mean(axis=1)
    dados["europa"] = retornos[["dax", "eurostoxx"]].mean(axis=1)
    for nome in ("sp500", "ewz", "dxy", "usd_brl", "brent", "cobre", "vix"):
        dados[nome] = retornos[nome]
    dados["ibov_retorno_1d"] = ibov
    dados["ibov_momentum_5d"] = ibov.rolling(5).sum()
    dados["ibov_momentum_20d"] = ibov.rolling(20).sum()
    dados["ibov_vol_5d"] = ibov.rolling(5).std()
    dados["ibov_vol_20d"] = ibov.rolling(20).std()
    dados["y"] = (ibov.shift(-1) > 0).astype(float)
    dados.loc[dados.index[-1], "y"] = np.nan
    dados = dados.dropna()
    fatores = [c for c in dados if c != "y"]
    return dados, fatores


def walk_forward(dados: pd.DataFrame, fatores: list[str], min_treino: int = 252,
                 janela_treino: int = 1260) -> pd.DataFrame:
    """Treina só no passado e prevê uma linha por vez, até o último dado disponível."""
    if len(dados) <= min_treino:
        raise ValueError("Histórico insuficiente para o treino mínimo.")
    X = dados[fatores].to_numpy(dtype=float)
    y = dados["y"].to_numpy(dtype=float)
    linhas = []
    for i in range(min_treino, len(dados)):
        inicio = max(0, i - janela_treino)
        X_treino, y_treino = X[inicio:i], y[inicio:i]
        media, desvio = X_treino.mean(axis=0), X_treino.std(axis=0)
        desvio[desvio == 0] = 1.0
        pesos, intercepto = _fit_logit((X_treino - media) / desvio, y_treino)
        prob = float(_sigmoide(((X[i] - media) / desvio) @ pesos + intercepto))
        real = bool(y[i])
        linhas.append({
            "data_sinal": dados.index[i].date().isoformat(),
            "prob_alta_proximo_pregao": round(prob, 6),
            "real_alta_proximo_pregao": int(real),
            "acertou": int((prob >= 0.5) == real),
            "confianca": "alta" if prob >= 0.60 or prob <= 0.40 else "neutra",
        })
    return pd.DataFrame(linhas)


def resumo(resultado: pd.DataFrame) -> str:
    acuracia = resultado["acertou"].mean() * 100
    brier = ((resultado["prob_alta_proximo_pregao"] - resultado["real_alta_proximo_pregao"]) ** 2).mean()
    confiantes = resultado[resultado["confianca"] == "alta"]
    cobertura = len(confiantes) / len(resultado) * 100
    acc_conf = confiantes["acertou"].mean() * 100 if len(confiantes) else float("nan")
    return (f"{len(resultado)} previsões | acurácia {acuracia:.1f}% | Brier {brier:.4f} | "
            f"confiança alta: {len(confiantes)} ({cobertura:.1f}%), acurácia {acc_conf:.1f}%")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backtest fechamento -> próximo pregão")
    parser.add_argument("--periodo", default="10y")
    parser.add_argument("--min-treino", type=int, default=252)
    parser.add_argument("--janela-treino", type=int, default=1260)
    parser.add_argument("--output", type=Path,
                        default=Path("data/backtests/fechamento_proximo_pregao.csv"))
    args = parser.parse_args(argv)
    dados, fatores = montar_dataset(baixar_fechamentos(args.periodo))
    resultado = walk_forward(dados, fatores, args.min_treino, args.janela_treino)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(args.output, index=False)
    print(resumo(resultado))
    print(f"Fatores ({len(fatores)}): {', '.join(fatores)}")
    print(f"Resultado: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
