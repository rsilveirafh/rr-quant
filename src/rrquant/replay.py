"""Replay de um pregão do WIN, de cima para baixo (diário → 4h → 60 → 15 → 5 → 2 min).

Gera uma página HTML que passa o dia barra a barra (2 min). Em cada momento ela mostra só o
que já era conhecido: candles fechados, topos e fundos já confirmados, BOS/CHoCH já
fechados e o estado do setup central (o mesmo motor do backtest). É o ensaio da tela ao vivo.

Uso:
    python -m rrquant.replay                 # último pregão salvo
    python -m rrquant.replay 2026-10-15 --abrir
    python -m rrquant.replay --listar        # pregões em que o setup operou
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd

from . import profit, setup_central as sc

SAIDA = Path.cwd() / "output" / "replay"
ORIGEM = pd.Timestamp("2000-01-03 09:00")          # âncora dos tempos gráficos
PAINEIS = [("Diário", None, 120), ("4h", 240, 15), ("60 min", 60, 5),
           ("15 min", 15, 3), ("5 min", 5, 2), ("2 min", 2, 1)]
ESPELHO = {"PDL": "PDH", "PWL": "PWH", "PML": "PMH", "EQL": "EQH",
           "PDH": "PDL", "PWH": "PWL", "PMH": "PML", "nenhum": "nenhum"}


def _ts(x: pd.Timestamp) -> int:
    """Horário de Brasília tratado como UTC, para o eixo do gráfico mostrar a hora local."""
    return int(pd.Timestamp(x).value // 10**9)


def _reamostrar(df: pd.DataFrame, minutos: int) -> pd.DataFrame:
    g = df.resample(f"{minutos}min", origin=ORIGEM)
    out = pd.DataFrame({"abertura": g.abertura.first(), "maxima": g.maxima.max(),
                        "minima": g.minima.min(), "fechamento": g.fechamento.last(),
                        "contratos": g.contratos.sum()})
    return out.dropna()


def _estrutura(df: pd.DataFrame, k: int, fim: pd.Series) -> tuple[list, list, list]:
    """Topos/fundos, BOS/CHoCH por fechamento e zonas (OB/FVG), cada um com o instante em que
    ficou conhecido (``c``) e, nas zonas, o instante em que deixou de valer (``f``)."""
    o, h, l, c = (df[x].to_numpy() for x in ("abertura", "maxima", "minima", "fechamento"))
    ph, pl = sc._pivos(h, l, k)
    t = df.index
    swings = [{"t": _ts(t[i]), "p": float(h[i] if ph[i] else l[i]), "tipo": "H" if ph[i] else "L",
               "c": _ts(fim.iloc[i + k])}
              for i in range(len(df)) if (ph[i] or pl[i]) and i + k < len(df)]
    eventos, zonas, tendencia = [], [], None
    topo = fundo = None                       # (índice, preço, rompido?)
    for i in range(len(df)):
        j = i - k
        if j >= 0 and ph[j]:
            topo = [j, h[j], False]
        if j >= 0 and pl[j]:
            fundo = [j, l[j], False]
        for ref, sobe in ((topo, True), (fundo, False)):
            if ref is None or ref[2]:
                continue
            if (c[i] > ref[1]) if sobe else (c[i] < ref[1]):
                ref[2] = True
                d = "alta" if sobe else "baixa"
                tipo = "BOS" if tendencia in (None, d) else "CHoCH"
                tendencia = d
                eventos.append({"t": _ts(t[i]), "c": _ts(fim.iloc[i]), "tipo": tipo, "dir": d,
                                "nivel": float(ref[1]), "t0": _ts(t[ref[0]])})
                # order block: último candle contrário no extremo de onde saiu o impulso
                seg = slice(ref[0], i + 1)
                m = ref[0] + int(np.argmin(l[seg]) if sobe else np.argmax(h[seg]))
                ob = next((j for j in range(m, max(m - 10, -1), -1)
                           if (c[j] < o[j] if sobe else c[j] > o[j])), None)
                if ob is not None:
                    zonas.append(_zona("OB", d, h[ob], l[ob], ob, i, df, fim))
    n = len(df)
    for i in range(2, n):                     # FVG: buraco entre a barra i-2 e a barra i
        if l[i] - h[i - 2] >= 10:
            zonas.append(_zona("FVG", "alta", l[i], h[i - 2], i - 1, i, df, fim))
        if l[i - 2] - h[i] >= 10:
            zonas.append(_zona("FVG", "baixa", l[i - 2], h[i], i - 1, i, df, fim))
    return swings, eventos, zonas


def _zona(tipo: str, d: str, topo: float, base: float, i0: int, i_conh: int,
          df: pd.DataFrame, fim: pd.Series) -> dict:
    """OB some quando um fechamento atravessa a zona; FVG some quando o buraco é preenchido."""
    l, h, c = df.minima.to_numpy(), df.maxima.to_numpy(), df.fechamento.to_numpy()
    depois = np.arange(i_conh + 1, len(df))
    if tipo == "OB":
        fora = (c[depois] < base) if d == "alta" else (c[depois] > topo)
    else:
        fora = (l[depois] <= base) if d == "alta" else (h[depois] >= topo)
    j = depois[fora][0] if fora.any() else None
    return {"tipo": tipo, "dir": d, "topo": float(topo), "base": float(base),
            "t": _ts(df.index[i0]), "c": _ts(fim.iloc[i_conh]),
            "f": None if j is None else _ts(fim.iloc[j])}


def _barras_json(df: pd.DataFrame) -> list:
    return [[_ts(i), float(r.abertura), float(r.maxima), float(r.minima), float(r.fechamento),
             float(r.contratos)] for i, r in df.iterrows()]


def _estado(est: dict, lo: np.ndarray, sinal: int, nome) -> dict:
    """Estado do motor numa barra, em preços reais (a venda roda espelhada)."""
    p = lambda x: None if x is None or not np.isfinite(x) else 5 * round(float(sinal * x) / 5)  # noqa: E731
    v, o, pos, rep = est["varrida"], est["ordem"], est["posicao"], est["reprovado"]
    liq = [[nome(k), p(x)] for k, x in est["abaixo"].items()]
    liq += [[nome("EQL"), p(x)] for x in sorted(set(est["eql"]), reverse=True)[:3]]
    s = {"liquidez": sorted(liq, key=lambda z: -sinal * z[1]),             # mais próxima primeiro
         "alvos": sorted(([nome(k), p(x)] for k, x in est["acima"].items()), key=lambda z: sinal * z[1])}
    if v is not None:
        s["varrida"] = {"nivel": "+".join(nome(x) for x in v["nivel"].split("+")),
                        "fundo": p(lo[v["fundo"]]), "ref": p(v.get("ref"))}
    if o is not None and "entrada" in o:
        risco = o["entrada"] - o["stop"]
        rr = (o["alvo"] - o["entrada"]) / risco if np.isfinite(o["alvo"]) and risco > 0 else None
        s["ordem"] = {"entrada": p(o["entrada"]), "stop": p(o["stop"]), "alvo": p(o["alvo"]),
                      "risco": round(float(risco)), "rr": None if rr is None else round(float(rr), 2),
                      "ativa": bool(o["ativa"]), "pernas": o["info"]["pernas"],
                      "forca": o["info"]["forca"], "vol": o["info"]["vol_ratio"],
                      "nivel": "+".join(nome(x) for x in o["info"]["nivel"].split("+"))}
    if pos is not None:
        s["posicao"] = {"entrada": p(pos["entrada"]), "stop": p(pos["stop"]), "alvo": p(pos["alvo"]),
                        "risco": round(float(pos["risco"])), "t": _ts(pos["t_entrada"]),
                        "rr": round(float((pos["alvo"] - pos["entrada"]) / pos["risco"]), 2),
                        "pernas": pos["pernas"], "forca": pos["forca"], "vol": pos["vol_ratio"],
                        "nivel": "+".join(nome(x) for x in pos["nivel"].split("+"))}
    if rep is not None:
        s["reprovado"] = {**rep, "t": _ts(rep["t"]), "nivel": "+".join(nome(x) for x in rep["nivel"].split("+"))}
    return s


def montar(dia: pd.Timestamp, df2: pd.DataFrame, diario: pd.DataFrame, r: sc.Regras) -> dict:
    dias = df2.index.normalize().unique()
    pos = dias.get_loc(dia)
    ini = dias[max(0, pos - 20)]
    base = df2[(df2.index >= ini) & (df2.index < dia + pd.Timedelta(days=1))]
    hoje = base[base.index.normalize() == dia]
    niv = sc.niveis_diarios(diario)

    # ---- motor do setup, registrando o estado de cada barra do dia
    estados = {"compra": {}, "venda": {}}
    cands = []
    for lado, d, nv, sinal in (("compra", base, niv, 1),
                               ("venda", sc._espelhar(base), sc._espelhar_niveis(niv), -1)):
        lo = d.minima.to_numpy()
        nome = (lambda k: k) if lado == "compra" else (lambda k: ESPELHO.get(k, k))
        tempos = d.index

        def espiao(t, est, lado=lado, lo=lo, sinal=sinal, nome=nome, tempos=tempos):
            if tempos[t].normalize() == dia:
                estados[lado][_ts(tempos[t])] = _estado(est, lo, sinal, nome)
        c = sc._candidatos_compra(d, nv, r, lado, espiao=espiao)
        if lado == "venda":
            for x in c:
                for k in ("entrada", "stop", "alvo", "saida"):
                    x[k] = -x[k]
        cands += c
    aceitos = sc._regras_do_dia(cands, r)
    trades = [] if aceitos.empty else [
        {"lado": x.lado, "t": _ts(x.t_entrada), "ts": _ts(x.t_saida), "entrada": round(x.entrada),
         "saida": round(x.saida), "stop": round(x.stop), "alvo": round(x.alvo), "R": round(x.R, 2),
         "nivel": x.nivel}
        for x in aceitos.itertuples() if x.t_entrada.normalize() == dia]

    # ---- painéis
    paineis = []
    for titulo, minutos, n_dias in PAINEIS:
        if minutos is None:
            hist = diario[pd.to_datetime(diario.index).normalize() < dia].tail(120)
            hist.index = pd.to_datetime(hist.index).normalize()
            fim = pd.Series(hist.index + pd.Timedelta(hours=18, minutes=30), index=hist.index)
            sw, ev, zn = _estrutura(hist, 2, fim)
        else:
            tf = _reamostrar(base, minutos) if minutos != 2 else base
            antes = tf.index.normalize() < dia
            dias_hist = tf.index.normalize()[antes].unique()[-n_dias:]
            tf = tf[tf.index.normalize() >= (dias_hist[0] if len(dias_hist) else dia)]
            fim = pd.Series(tf.index + pd.Timedelta(minutes=minutos), index=tf.index)
            sw, ev, zn = _estrutura(tf, 2 if minutos >= 15 else 3, fim)
            hist = tf[tf.index.normalize() < dia]
        paineis.append({"titulo": titulo, "min": minutos or 1440, "hist": _barras_json(hist),
                        "swings": sw, "eventos": ev, "zonas": zn})

    n = niv.loc[dia] if dia in niv.index else None
    niveis = [] if n is None else [[k, round(float(n[k]))] for k in n.index if pd.notna(n[k])]
    return {"dia": f"{dia:%Y-%m-%d}", "origem": _ts(ORIGEM), "barras": _barras_json(hoje),
            "paineis": paineis, "niveis": niveis, "estados": estados, "trades": trades,
            "regras": {"risco_max": r.risco_max, "rr_min": r.rr_min, "fib": r.fib, "folga": r.folga_stop,
                       "max_trades": r.max_trades, "max_stops": r.max_stops}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rrquant.replay")
    ap.add_argument("dia", nargs="?")
    ap.add_argument("--abrir", action="store_true")
    ap.add_argument("--listar", action="store_true", help="lista os pregões em que o setup operou")
    a = ap.parse_args(argv)
    df2, diario, r = profit.carregar(minutos=2), profit.carregar(minutos=None), sc.Regras()
    if a.listar:
        t = sc.rodar(df2, diario, r)
        g = t.groupby(t.t_entrada.dt.date).R.agg(trades="size", R="sum").round(2)
        print(g.to_string())
        return 0
    dias = df2.index.normalize().unique()
    dia = pd.Timestamp(a.dia) if a.dia else dias[-1]
    if dia not in dias:
        raise SystemExit(f"{dia:%Y-%m-%d} não está no histórico de 2 min "
                         f"({dias[0]:%Y-%m-%d} a {dias[-1]:%Y-%m-%d})")
    dados = montar(dia, df2, diario, r)
    modelo = (Path(__file__).parent / "replay.html").read_text(encoding="utf-8")
    SAIDA.mkdir(parents=True, exist_ok=True)
    arq = SAIDA / f"{dados['dia']}.html"
    arq.write_text(modelo.replace("/*DADOS*/null", json.dumps(dados, separators=(",", ":"))),
                   encoding="utf-8")
    print(f"replay salvo em {arq} ({len(dados['trades'])} trade(s) no dia)")
    if a.abrir:
        webbrowser.open(arq.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
