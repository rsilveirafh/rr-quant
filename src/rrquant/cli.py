"""Entrada: coleta os dados, gera o dashboard HTML e imprime um resumo no terminal.

Uso:
    python -m rrquant            # gera output/dashboard.html
    python -m rrquant --abrir    # gera e abre no navegador
"""

from __future__ import annotations

import argparse
import datetime as dt
import webbrowser
from pathlib import Path

from . import analyze, collect, macro as macro_mod, report, smc as smc_mod

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "output" / "dashboard.html"


def _resumo_terminal(blocos: dict[str, list[collect.Cotacao]]) -> None:
    for nome, cotacoes in blocos.items():
        print(f"\n  {nome}")
        for c in cotacoes:
            v = c.var_pct
            marca = "  --" if v is None else (f"{v:+6.2f}%")
            seta = "" if v is None or abs(v) < 0.01 else ("^" if v > 0 else "v")
            print(f"    {c.nome:<28} {marca} {seta}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rrquant", description="Varredura diaria de mercado")
    parser.add_argument("--abrir", action="store_true", help="abre o dashboard no navegador")
    parser.add_argument("--periodo", default="7d", help="periodo yfinance (default 7d)")
    parser.add_argument("--forca", type=int, default=4,
                        help="força do fractal p/ swings da aba SMC (default 4)")
    args = parser.parse_args(argv)

    print("Coletando dados de mercado (yfinance)...")
    cotacoes = collect.coletar(periodo=args.periodo)
    blocos = collect.por_bloco(cotacoes)

    print("Buscando macro (FRED / BCB)...")
    macro = macro_mod.coletar_macro()

    print("Analisando (regime, cadeia, commodities, probabilidades históricas)...")
    analise = analyze.analisar(cotacoes, macro=macro)

    print("SMC: estrutura do Ibovespa (diário + semanal)...")
    ohlc_ibov = collect.coletar_ohlc("^BVSP", periodo="2y", intervalo="1d")
    smc_ltf = smc_mod.analisar("^BVSP", "Ibovespa", ohlc_ibov,
                               timeframe="Diário", forca=args.forca)
    ohlc_sem = collect.resample_ohlc(ohlc_ibov, "W")
    smc_htf = smc_mod.analisar("^BVSP", "Ibovespa", ohlc_sem,
                               timeframe="Semanal", forca=2, n_render=60)
    dec = smc_mod.decisao(smc_htf, smc_ltf)

    datas = sorted({c.data for c in cotacoes if c.data})
    data_dados = datas[-1] if datas else None
    gerado_em = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    html = report.gerar_html(blocos, analise, gerado_em=gerado_em, data_dados=data_dados,
                             smc=smc_ltf, smc_htf=smc_htf, dec=dec)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(html, encoding="utf-8")

    print(f"\n  === LEITURA: {analise.regime_rotulo} ({analise.amplitude}) ===")
    for b in analise.regime_bullets:
        print(f"    - {b}")
    for p in analise.probs:
        print(f"    ~ {p.descricao}: {p.p_cond:.0f}% (base {p.base:.0f}%, {p.lift:+.0f}pp, n={p.n})")

    ok = sum(1 for c in cotacoes if c.ok)
    _resumo_terminal(blocos)
    print(f"\n  {ok}/{len(cotacoes)} ativos com dado. Ultimo fechamento ~ {data_dados}.")
    if smc_ltf:
        nb = sum(1 for e in smc_ltf.eventos if e.tipo == "BOS")
        nc = sum(1 for e in smc_ltf.eventos if e.tipo == "CHoCH")
        obf = sum(1 for b in smc_ltf.obs if not b.mitigado)
        fvo = sum(1 for f in smc_ltf.fvgs if not f.mitigado)
        htf_t = smc_htf.trend if smc_htf else "n/d"
        print(f"  SMC Ibovespa: semanal {htf_t or 'neutra'} / diario {smc_ltf.trend or 'neutra'} "
              f"| {len(smc_ltf.swings)} swings, {nb} BOS, {nc} CHoCH, "
              f"{obf}/{len(smc_ltf.obs)} OB frescos, {fvo}/{len(smc_ltf.fvgs)} FVG abertos.")
        if dec:
            flag = " [CONFLITO HTFxLTF]" if dec.conflito else ""
            print(f"  Decisao: {dec.acao}{flag} — controle: {dec.controle}.")
    else:
        print("  SMC Ibovespa: sem OHLC nesta execucao.")
    print(f"  Dashboard: {SAIDA}")

    if args.abrir:
        webbrowser.open(SAIDA.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
