"""Leitor do histórico local do Profit (Nelogica).

O Profit guarda as barras de cada ativo em arquivos binários dentro de
``%APPDATA%/Nelogica/Profit/database/assets/<ATIVO>/``, um por ano e tempo gráfico:

    WINFUT_F_0_1_5_1_1_0_2025.min      barras de 5 min de 2025 (registros de 128 bytes)
    WINFUT_F_0_2_1_1_1_0_2025.dayV1    barras diárias de 2025 (registros de 296 bytes)

Layout de cada registro (little-endian), decodificado em 2026-11-10:

    0   double  data/hora (TDateTime: dias desde 1899-12-30, horário de Brasília)
    16  double  abertura, máxima, mínima, fechamento
    48  double  volume financeiro (R$)
    56  int64   quantidade (contratos)
    64  int32   negócios
    72  double  volume financeiro de agressão compradora e vendedora
    88  int64   quantidade de agressão compradora e vendedora
    104 int32   negócios de agressão compradora e vendedora

O lado comprador foi identificado pela correlação do saldo de agressão com a direção do
candle (0,83 no WIN de 5 min). Os dados são do usuário do Profit e não são versionados.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import struct
from pathlib import Path

import pandas as pd

PASTA_PADRAO = Path(os.environ.get(
    "RRQUANT_PROFIT_DIR",
    Path.home() / "AppData/Roaming/Nelogica/Profit/database/assets",
))
_EPOCA = dt.datetime(1899, 12, 30)
_REGISTRO = {"min": 128, "dayV1": 296}
_CAMPOS = ["abertura", "maxima", "minima", "fechamento", "vol_fin", "contratos", "negocios",
           "agr_fin_compra", "agr_fin_venda", "agr_qtd_compra", "agr_qtd_venda"]


def _ler_arquivo(caminho: Path, tamanho: int) -> list[tuple]:
    dados = caminho.read_bytes()
    linhas = []
    for i in range(len(dados) // tamanho):
        r = i * tamanho
        (data,) = struct.unpack_from("<d", dados, r)
        o, h, l, c, vf = struct.unpack_from("<5d", dados, r + 16)
        (qtd,) = struct.unpack_from("<q", dados, r + 56)
        (neg,) = struct.unpack_from("<i", dados, r + 64)
        fa, fb = struct.unpack_from("<2d", dados, r + 72)
        qa, qb = struct.unpack_from("<2q", dados, r + 88)
        if c <= 0:
            continue
        linhas.append((_EPOCA + dt.timedelta(days=data), o, h, l, c, vf, qtd, neg, fa, fb, qa, qb))
    return linhas


def carregar(ativo: str = "WINFUT_F_0", minutos: int | None = 5,
             pasta: Path = PASTA_PADRAO) -> pd.DataFrame:
    """Barras do ativo no tempo gráfico pedido (``minutos=None`` = diário), em ordem."""
    if minutos is None:
        padrao, ext = re.compile(r"_2_1_1_1_0_\d{4}\.dayV1$"), "dayV1"
    else:
        padrao, ext = re.compile(rf"_1_{minutos}_1_1_0_\d{{4}}\.min$"), "min"
    arquivos = sorted(p for p in (pasta / ativo).iterdir() if padrao.search(p.name))
    if not arquivos:
        raise FileNotFoundError(f"sem barras de {minutos or 'diário'} para {ativo} em {pasta}")
    linhas = [ln for p in arquivos for ln in _ler_arquivo(p, _REGISTRO[ext])]
    df = pd.DataFrame(linhas, columns=["data", *_CAMPOS]).set_index("data")
    df.index = df.index.round("s")
    return df[~df.index.duplicated(keep="last")].sort_index()
