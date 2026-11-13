"""Coletor dos negócios do WIN publicados pela B3, guardados como barras de 1 minuto.

A B3 publica, para cada contrato e cada pregão, um zip com todos os negócios do dia
(preço, quantidade, horário em milissegundos, corretoras):

    https://arquivos.b3.com.br/rapinegocios/tickercsv/<CONTRATO>/<AAAA-MM-DD>

Não achei documentação oficial desse endereço; ele aparece em tutoriais de terceiros e foi
testado em 2026-11-12. A B3 mantém só cerca de um mês de arquivos, então o rr-quant guarda
as barras em `data/win/1min/<AAAA-MM>.csv` e vai juntando o próprio histórico. O arquivo
não traz o lado agressor; para isso continua valendo o Profit.

Contrato do dia: o WIN vence na quarta-feira mais próxima do dia 15 dos meses pares, e a
série usa o vencimento mais próximo até o dia do vencimento, inclusive. É a mesma regra de
série contínua do Profit, sem ajuste de preço na troca.

Uso: `python -m rrquant.b3negocios` baixa os pregões que faltam no último mês.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

URL = "https://arquivos.b3.com.br/rapinegocios/tickercsv/{contrato}/{dia}"
PASTA = Path(__file__).resolve().parents[2] / "data" / "win" / "1min"
LETRAS = {2: "G", 4: "J", 6: "M", 8: "Q", 10: "V", 12: "Z"}
COLUNAS = ["contrato", "abertura", "maxima", "minima", "fechamento", "contratos", "negocios"]


# ---------------------------------------------------------------- contrato do dia

def vencimento(ano: int, mes: int) -> dt.date:
    """Quarta-feira mais próxima do dia 15 (regra do contrato de Ibovespa da B3).
    Feriado no dia não é tratado: a B3 adia para o pregão seguinte."""
    quinze = dt.date(ano, mes, 15)
    delta = (2 - quinze.weekday()) % 7          # 2 = quarta
    if delta > 3:
        delta -= 7
    return quinze + dt.timedelta(days=delta)


def contrato_do_dia(dia: dt.date) -> str:
    ano, mes = dia.year, dia.month
    for _ in range(3):
        if mes % 2:
            mes += 1
        if mes > 12:
            ano, mes = ano + 1, 2
        if dia <= vencimento(ano, mes):
            return f"WIN{LETRAS[mes]}{ano % 100:02d}"
        mes += 1
    raise ValueError(dia)


# ---------------------------------------------------------------- download e barras

def baixar(contrato: str, dia: dt.date) -> bytes | None:
    """Zip do dia, ou None se a B3 não tiver (fim de semana, feriado, fora da janela)."""
    req = urllib.request.Request(URL.format(contrato=contrato, dia=dia.isoformat()),
                                 headers={"User-Agent": "Mozilla/5.0 (rr-quant)"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            dados = r.read()
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return None
        raise
    return dados if dados[:2] == b"PK" else None


def barras_1min(zip_bytes: bytes, contrato: str, bloco: int = 500_000) -> pd.DataFrame | None:
    """Negócios do zip agregados em barras de 1 minuto (rótulo = início do minuto).

    Um pregão do WIN tem uns 6 milhões de negócios (400 MB de texto). A leitura é em blocos:
    cada bloco vira barras de 1 min e os blocos se juntam no fim, então a memória fica em
    torno de 100 MB em vez de alguns GB. O arquivo vem em ordem de negócio (cronológica)."""
    partes = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        nomes = [n for n in z.namelist() if n.lower().endswith((".txt", ".csv"))]
        if not nomes:
            return None
        with z.open(nomes[0]) as f:
            leitor = pd.read_csv(f, sep=";", decimal=",", chunksize=bloco,
                                 dtype={"HoraFechamento": str, "DataNegocio": str,
                                        "CodigoInstrumento": str},
                                 usecols=["CodigoInstrumento", "AcaoAtualizacao", "PrecoNegocio",
                                          "QuantidadeNegociada", "HoraFechamento", "DataNegocio"])
            for df in leitor:
                df = df[(df.CodigoInstrumento == contrato) & (df.AcaoAtualizacao == 0)]
                if df.empty:
                    continue
                chave = df.DataNegocio + " " + df.HoraFechamento.str.zfill(9).str[:4]
                g = df.groupby(chave, sort=True)
                partes.append(pd.DataFrame({
                    "abertura": g.PrecoNegocio.first(), "maxima": g.PrecoNegocio.max(),
                    "minima": g.PrecoNegocio.min(), "fechamento": g.PrecoNegocio.last(),
                    "contratos": g.QuantidadeNegociada.sum(), "negocios": g.size(),
                }))
    if not partes:
        return None
    g = pd.concat(partes).groupby(level=0, sort=True)   # minuto que cruza dois blocos
    out = pd.DataFrame({
        "contrato": contrato,
        "abertura": g.abertura.first(), "maxima": g.maxima.max(), "minima": g.minima.min(),
        "fechamento": g.fechamento.last(),
        "contratos": g.contratos.sum().astype(int), "negocios": g.negocios.sum().astype(int),
    })
    out.index = pd.to_datetime(out.index, format="%Y-%m-%d %H%M")
    out.index.name = "data_hora"
    return out


# ---------------------------------------------------------------- armazenamento

def carregar(pasta: Path = PASTA) -> pd.DataFrame | None:
    """Todas as barras guardadas, em ordem."""
    arquivos = sorted(pasta.glob("*.csv")) if pasta.exists() else []
    if not arquivos:
        return None
    df = pd.concat(pd.read_csv(a, index_col="data_hora", parse_dates=["data_hora"]) for a in arquivos)
    return df[~df.index.duplicated(keep="last")].sort_index()


def dias_guardados() -> set[dt.date]:
    df = carregar()
    return set() if df is None else set(df.index.date)


def gravar(barras: pd.DataFrame) -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    for mes, parte in barras.groupby(barras.index.to_period("M")):
        alvo = PASTA / f"{mes}.csv"
        if alvo.exists():
            velho = pd.read_csv(alvo, index_col="data_hora", parse_dates=["data_hora"])
            parte = pd.concat([velho[~velho.index.isin(parte.index)], parte]).sort_index()
        parte[COLUNAS].to_csv(alvo, float_format="%.0f")


def coletar(dias: int = 35, hoje: dt.date | None = None) -> list[tuple[dt.date, str, int]]:
    """Baixa os dias úteis da janela que ainda não estão guardados. Devolve o que entrou."""
    # O dia corrente só entra depois do fechamento (horário de Brasília): durante o pregão a
    # B3 já serve o arquivo parcial, e um dia gravado pela metade nunca mais seria baixado.
    if hoje is None:
        agora = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3)))
        hoje = agora.date() if agora.hour >= 20 else agora.date() - dt.timedelta(days=1)
    feitos = dias_guardados()
    novos = []
    for k in range(dias, -1, -1):
        dia = hoje - dt.timedelta(days=k)
        if dia.weekday() >= 5 or dia in feitos:
            continue
        contrato = contrato_do_dia(dia)
        z = baixar(contrato, dia)
        b = barras_1min(z, contrato) if z else None
        if b is None or b.empty:
            continue
        gravar(b)
        novos.append((dia, contrato, len(b)))
        print(f"  {dia} {contrato}: {len(b)} barras, {int(b.contratos.sum()):,} contratos".replace(",", "."))
    return novos


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rrquant.b3negocios", description=__doc__.splitlines()[0])
    ap.add_argument("--dias", type=int, default=35, help="janela para trás, em dias corridos")
    args = ap.parse_args(argv)
    novos = coletar(args.dias)
    print(f"{len(novos)} pregões novos em {PASTA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
