"""Camada macro — inflação e juros de EUA (FRED) e Brasil (BCB SGS).

Ambas as fontes são APIs públicas SEM CHAVE:
- FRED: CSV keyless em fred.stlouisfed.org/graph/fredgraph.csv?id=<serie>
- BCB SGS: JSON keyless em api.bcb.gov.br/dados/serie/bcdata.sgs.<cod>/dados

É o "porquê" macro por trás da cadeia petróleo→inflação→juros→ativos: fecha o
elo do juro (Selic/CDI/Treasury) e da inflação (CPI/IPCA), e calcula o juro real
brasileiro (Selic vs IPCA 12m), que a leitura pré-mercado usa implicitamente.
"""

from __future__ import annotations

import json
import urllib.request
import warnings
from dataclasses import dataclass, field

warnings.filterwarnings("ignore")

_TIMEOUT = 25


@dataclass
class Indicador:
    nome: str
    valor: float | None
    unidade: str
    data: str | None = None
    extra: str = ""  # ex.: "acum. 12m", "YoY"

    @property
    def ok(self) -> bool:
        return self.valor is not None


@dataclass
class Macro:
    eua: list[Indicador] = field(default_factory=list)
    brasil: list[Indicador] = field(default_factory=list)
    juro_real: float | None = None
    leitura: list[str] = field(default_factory=list)
    ok: bool = False


# ---------- FRED (EUA) ----------

def _fred(serie: str, cosd: str = "2023-01-01") -> list[tuple[str, float]]:
    """Devolve [(data_iso, valor)] de uma série FRED, ignorando faltantes ('.')."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={serie}&cosd={cosd}"
    raw = urllib.request.urlopen(url, timeout=_TIMEOUT).read().decode("utf-8")
    linhas = raw.strip().splitlines()[1:]  # pula cabeçalho
    saida: list[tuple[str, float]] = []
    for ln in linhas:
        try:
            data, val = ln.split(",")
            saida.append((data, float(val)))
        except (ValueError, IndexError):
            continue
    return saida


def _fred_nivel(serie: str, nome: str, unidade: str) -> Indicador:
    try:
        s = _fred(serie)
        if not s:
            return Indicador(nome, None, unidade)
        data, val = s[-1]
        return Indicador(nome, val, unidade, data)
    except Exception:
        return Indicador(nome, None, unidade)


def _fred_yoy(serie: str, nome: str) -> Indicador:
    """Variação anual (%) de uma série mensal de índice (CPI, PPI...)."""
    try:
        s = _fred(serie)
        if len(s) < 13:
            return Indicador(nome, None, "%", extra="acum. 12m")
        data, val = s[-1]
        _, val_12m = s[-13]
        yoy = (val / val_12m - 1) * 100
        return Indicador(nome, yoy, "%", data, "acum. 12m")
    except Exception:
        return Indicador(nome, None, "%", extra="acum. 12m")


# ---------- BCB SGS (Brasil) ----------

def _bcb(cod: int, n: int = 1) -> list[dict]:
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/{n}?formato=json"
    raw = urllib.request.urlopen(url, timeout=_TIMEOUT).read()
    return json.loads(raw)


def _bcb_nivel(cod: int, nome: str, unidade: str, extra: str = "") -> Indicador:
    try:
        dados = _bcb(cod, 1)
        if not dados:
            return Indicador(nome, None, unidade, extra=extra)
        d = dados[-1]
        # BCB usa data DD/MM/AAAA -> converte p/ ISO
        dia, mes, ano = d["data"].split("/")
        return Indicador(nome, float(d["valor"]), unidade, f"{ano}-{mes}-{dia}", extra)
    except Exception:
        return Indicador(nome, None, unidade, extra=extra)


# ---------- coleta + leitura ----------

def _val(lista: list[Indicador], nome: str) -> float | None:
    for i in lista:
        if i.nome == nome and i.ok:
            return i.valor
    return None


def coletar_macro() -> Macro:
    m = Macro()

    m.eua = [
        _fred_yoy("CPIAUCSL", "CPI (cheio)"),
        _fred_yoy("CPILFESL", "CPI núcleo"),
        _fred_yoy("PPIACO", "PPI"),
        _fred_nivel("UNRATE", "Desemprego", "%"),
        _fred_nivel("ICSA", "Jobless claims", "mil"),
        _fred_nivel("FEDFUNDS", "Fed funds", "% a.a."),
    ]
    # jobless claims: ICSA vem em unidades -> converte p/ milhares
    for i in m.eua:
        if i.nome == "Jobless claims" and i.ok:
            i.valor = round(i.valor / 1000)

    m.brasil = [
        _bcb_nivel(432, "Selic meta", "% a.a."),
        _bcb_nivel(4389, "CDI", "% a.a."),
        _bcb_nivel(13522, "IPCA", "%", "acum. 12m"),
        _bcb_nivel(433, "IPCA", "%", "mês"),
        _bcb_nivel(7478, "IPCA-15", "%", "mês"),
    ]

    m.ok = any(i.ok for i in m.eua) or any(i.ok for i in m.brasil)

    # juro real ex-post: (1+Selic)/(1+IPCA 12m) - 1
    selic = _val(m.brasil, "Selic meta")
    ipca12 = None
    for i in m.brasil:
        if i.nome == "IPCA" and i.extra == "acum. 12m" and i.ok:
            ipca12 = i.valor
    if selic is not None and ipca12 is not None:
        m.juro_real = ((1 + selic / 100) / (1 + ipca12 / 100) - 1) * 100

    # Leitura macro (fecha o elo inflação→juros da cadeia). Números em pt-BR (vírgula).
    def br(x: float, d: int = 2) -> str:
        return f"{x:.{d}f}".replace(".", ",")

    if ipca12 is not None:
        meta = "acima da meta (3% ±1,5)" if ipca12 > 4.5 else (
            "abaixo da meta" if ipca12 < 1.5 else "dentro da meta (3% ±1,5)")
        m.leitura.append(f"IPCA 12m em {br(ipca12)}% — {meta}.")
    if selic is not None and m.juro_real is not None:
        m.leitura.append(
            f"Selic meta {br(selic)}% a.a. → juro real ~{br(m.juro_real, 1)}%. "
            "Juro real alto atrai fluxo p/ renda fixa e pressiona a bolsa, mas sustenta o real."
        )
    cpi = _val(m.eua, "CPI (cheio)")
    ff = _val(m.eua, "Fed funds")
    if cpi is not None and ff is not None:
        m.leitura.append(
            f"Nos EUA, CPI {br(cpi, 1)}% com Fed funds {br(ff)}% — "
            + ("inflação ainda acima do conforto do Fed (2%), viés de juro alto por mais tempo."
               if cpi > 2.5 else "inflação convergindo, abre espaço p/ corte de juros.")
        )
    return m
