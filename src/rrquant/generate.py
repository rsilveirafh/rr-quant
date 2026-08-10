"""Gera o dashboard em memoria para o CLI e para a funcao da Vercel."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from . import analyze, collect, macro as macro_mod, report, smc as smc_mod


@dataclass
class DashboardGerado:
    html: str
    market_date: str | None
    generated_at: str


def gerar_dashboard(periodo: str = "7d", forca: int = 4) -> DashboardGerado:
    """Coleta os dados e monta o HTML, sem gravar arquivos locais."""
    cotacoes = collect.coletar(periodo=periodo)
    blocos = collect.por_bloco(cotacoes)
    macro = macro_mod.coletar_macro()
    analise = analyze.analisar(cotacoes, macro=macro)

    ohlc_ibov = collect.coletar_ohlc("^BVSP", periodo="2y", intervalo="1d")
    smc_ltf = smc_mod.analisar("^BVSP", "Ibovespa", ohlc_ibov,
                               timeframe="Diario", forca=forca)
    ohlc_sem = collect.resample_ohlc(ohlc_ibov, "W")
    smc_htf = smc_mod.analisar("^BVSP", "Ibovespa", ohlc_sem,
                               timeframe="Semanal", forca=2, n_render=60)
    ohlc_15m = collect.coletar_ohlc("^BVSP", periodo="60d", intervalo="15m")
    smc_15m = smc_mod.analisar("^BVSP", "Ibovespa", ohlc_15m,
                               timeframe="15 min", forca=4, n_render=160)
    smc_1h = smc_mod.analisar("^BVSP", "Ibovespa", collect.resample_ohlc(ohlc_15m, "1h"),
                              timeframe="1 hora", forca=3, n_render=120)
    smc_4h = smc_mod.analisar("^BVSP", "Ibovespa", collect.resample_ohlc(ohlc_15m, "4h"),
                              timeframe="4 horas", forca=2, n_render=80)
    dec = smc_mod.decisao(smc_htf, smc_ltf)

    datas = sorted({c.data for c in cotacoes if c.data})
    market_date = datas[-1] if datas else None
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = report.gerar_html(blocos, analise, gerado_em=generated_at,
                             data_dados=market_date, smc=smc_ltf,
                             smc_htf=smc_htf, smc_4h=smc_4h, smc_1h=smc_1h,
                             smc_15m=smc_15m, dec=dec)
    return DashboardGerado(html=html, market_date=market_date, generated_at=generated_at)
