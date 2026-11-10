"""Backtest do setup central de ``docs/meu-operacional.md`` no mini-índice.

Compra (a venda é o espelho, feita invertendo o sinal dos preços):

1. o preço varre uma liquidez abaixo (PDL, PWL, PML ou fundos nivelados);
2. faz CHoCH: fecha acima do último topo confirmado antes da mínima da varrida;
3. qualidade do CHoCH: 5 pernas ou barra de força, e volume maior que o da queda;
4. ordem limitada na retração de Fibonacci (61,8% por padrão) do impulso inteiro;
5. stop abaixo da mínima, risco de no máximo 300 pts, alvo na próxima liquidez acima
   (máxima do dia, PDH, PWH, PMH) a pelo menos 3R, ou alvo fixo de 3R;
6. regras do dia: no máximo 3 trades, parar depois de 2 stops, uma posição por vez.

Tudo é causal: um topo/fundo só existe depois de confirmado, a ordem só enxerga barras
fechadas, e quando stop e alvo cabem na mesma barra conta o stop. O resultado sai em R,
já descontado o custo (corretagem + escorregamento) em pontos.

Uso:
    python -m rrquant.setup_central              # micro de 2 min
    python -m rrquant.setup_central --minutos 5
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from . import profit


@dataclass(frozen=True)
class Regras:
    k_swing: int = 2           # força do fractal da estrutura (barras de cada lado)
    k_perna: int = 1           # força do fractal usado para contar pernas
    fib: float = 0.618         # retração da entrada
    folga_stop: float = 10     # pts abaixo da mínima
    risco_max: float = 300     # pts
    risco_min: float = 50      # pts (abaixo disso é ruído)
    rr_min: float = 3.0
    alvo: str = "liquidez"     # 'liquidez' | '3R'
    custo: float = 10          # pts por trade (ida e volta)
    atravessar: float = 0      # pts que o preço precisa passar da ordem para contar execução
    tol_eq: float = 20         # pts para considerar dois fundos nivelados
    validade_varrida: int = 240  # minutos para o CHoCH aparecer depois da varrida
    validade_ordem: int = 180    # minutos para a ordem ser executada depois do CHoCH
    exigir_pernas: bool = True
    exigir_volume: bool = True
    exigir_varrida: bool = True
    ultima_entrada: str = "17:30"
    max_trades: int = 3
    max_stops: int = 2


# --------------------------------------------------------------------------- níveis

def niveis_diarios(diario: pd.DataFrame) -> pd.DataFrame:
    """PDH/PDL, PWH/PWL, PMH/PML válidos para cada pregão (só dados anteriores a ele)."""
    d = diario[["maxima", "minima"]].copy()
    d.index = pd.to_datetime(d.index).normalize()
    out = pd.DataFrame(index=d.index)
    out["PDH"], out["PDL"] = d.maxima.shift(), d.minima.shift()
    for sigla, freq in (("W", "W-FRI"), ("M", "M")):
        per = d.index.to_period(freq)
        g = d.groupby(per).agg(h=("maxima", "max"), l=("minima", "min"))
        ant = g.shift()
        out[f"P{sigla}H"] = ant.h.reindex(per).to_numpy()
        out[f"P{sigla}L"] = ant.l.reindex(per).to_numpy()
    return out


def _espelhar(df: pd.DataFrame) -> pd.DataFrame:
    e = df.copy()
    e["abertura"], e["fechamento"] = -df.abertura, -df.fechamento
    e["maxima"], e["minima"] = -df.minima, -df.maxima
    return e


def _espelhar_niveis(n: pd.DataFrame) -> pd.DataFrame:
    e = pd.DataFrame(index=n.index)
    for a, b in (("PDH", "PDL"), ("PWH", "PWL"), ("PMH", "PML")):
        e[a], e[b] = -n[b], -n[a]
    return e


def _pivos(h: np.ndarray, l: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Topos/fundos fractais. O pivô em i só é conhecido na barra i + k."""
    n = len(h)
    ph, pl = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(k, n - k):
        if h[i] > h[i - k:i].max() and h[i] >= h[i + 1:i + k + 1].max():
            ph[i] = True
        if l[i] < l[i - k:i].min() and l[i] <= l[i + 1:i + k + 1].min():
            pl[i] = True
    return ph, pl


def _pernas(ph: np.ndarray, pl: np.ndarray, h, l, a: int, t: int) -> int:
    """Pernas do impulso que sai do fundo ``a`` e rompe em ``t`` (pivôs alternados)."""
    seq: list[list] = []
    for j in range(a + 1, t):          # pivô em j precisa da barra j+1 <= t
        for tipo, flag, p in (("H", ph[j], h[j]), ("L", pl[j], l[j])):
            if not flag:
                continue
            if seq and seq[-1][0] == tipo:
                if (tipo == "H") == (p > seq[-1][1]):
                    seq[-1][1] = p
            else:
                seq.append([tipo, p])
    while seq and seq[0][0] == "L":
        seq.pop(0)
    return len(seq) + 1


# --------------------------------------------------------------------------- compra

def _candidatos_compra(df: pd.DataFrame, niveis: pd.DataFrame, r: Regras, lado: str,
                       funil: dict | None = None) -> list[dict]:
    funil = {} if funil is None else funil
    conta = lambda k: funil.__setitem__(k, funil.get(k, 0) + 1)  # noqa: E731
    o, h, l, c = (df[x].to_numpy() for x in ("abertura", "maxima", "minima", "fechamento"))
    vol = df.contratos.to_numpy(float)
    agr = (df.agr_qtd_compra - df.agr_qtd_venda).to_numpy(float)
    if lado == "venda":
        agr = -agr
    tempo = df.index
    dia = tempo.normalize()
    hhmm = tempo.strftime("%H:%M")
    ph, pl = _pivos(h, l, r.k_swing)
    ph1, pl1 = _pivos(h, l, r.k_perna)
    amp = h - l
    atr = pd.Series(amp).rolling(20, min_periods=5).mean().to_numpy()
    n = len(df)
    trades: list[dict] = []
    barra = max(int(pd.Series(tempo).diff().dt.total_seconds().median() // 60), 1)
    val_varrida, val_ordem = r.validade_varrida // barra, r.validade_ordem // barra

    novo_dia = np.r_[True, dia[1:] != dia[:-1]]
    ultimo_do_dia = np.r_[dia[1:] != dia[:-1], True]

    est = None            # estado do dia
    for t in range(n):
        if novo_dia[t]:
            nv = niveis.loc[dia[t]] if dia[t] in niveis.index else None
            est = {
                "abaixo": {} if nv is None else {k: nv[k] for k in ("PDL", "PWL", "PML") if pd.notna(nv[k])},
                "acima": {} if nv is None else {k: nv[k] for k in ("PDH", "PWH", "PMH") if pd.notna(nv[k])},
                "eql": [], "fundos": [], "max_dia": -np.inf,
                "varrida": None, "ordem": None, "posicao": None,
            }
        # ---- posição aberta: gestão
        pos = est["posicao"]
        if pos is not None:
            saida = None
            if o[t] <= pos["stop"]:
                saida = o[t]
            elif l[t] <= pos["stop"]:
                saida = pos["stop"]
            elif h[t] >= pos["alvo"]:
                saida = max(o[t], pos["alvo"])
            elif ultimo_do_dia[t]:
                saida = c[t]
            if saida is not None:
                pos["saida"], pos["t_saida"] = saida, tempo[t]
                pos["R"] = (saida - pos["entrada"] - r.custo) / pos["risco"]
                trades.append(pos)
                est["posicao"] = None
        # ---- ordem pendurada: execução (com o topo/alvo da barra anterior)
        ordem = est["ordem"]
        if ordem is not None and est["posicao"] is None and ordem["ativa"] and hhmm[t] <= r.ultima_entrada:
            if l[t] <= ordem["entrada"] - r.atravessar:
                ent = min(o[t], ordem["entrada"])
                pos = {**ordem["info"], "lado": lado, "t_entrada": tempo[t], "entrada": ent,
                       "stop": ordem["stop"], "alvo": ordem["alvo"], "risco": ent - ordem["stop"]}
                est["ordem"] = None
                conta("5 executada")
                if l[t] <= pos["stop"]:              # stop na própria barra de entrada
                    saida = min(o[t], pos["stop"]) if o[t] <= pos["stop"] else pos["stop"]
                    pos.update(saida=saida, t_saida=tempo[t],
                               R=(saida - ent - r.custo) / pos["risco"])
                    trades.append(pos)
                elif ultimo_do_dia[t]:
                    pos.update(saida=c[t], t_saida=tempo[t], R=(c[t] - ent - r.custo) / pos["risco"])
                    trades.append(pos)
                else:
                    est["posicao"] = pos
        # ---- liquidez acima já tomada no dia deixa de ser alvo
        est["max_dia"] = max(est["max_dia"], h[t])
        est["acima"] = {k: v for k, v in est["acima"].items() if v > est["max_dia"]}
        # ---- fundos confirmados e fundos nivelados (EQL)
        j = t - r.k_swing
        if j >= 0 and pl[j] and dia[j] == dia[t]:
            for f in est["fundos"]:
                if abs(f - l[j]) <= r.tol_eq:
                    est["eql"].append(min(f, l[j]))
            est["fundos"].append(l[j])
        # ---- varrida de liquidez abaixo
        if est["ordem"] is None and est["posicao"] is None:
            varridos = [k for k, v in est["abaixo"].items() if l[t] < v]
            eq_varridos = [v for v in est["eql"] if l[t] < v]
            if eq_varridos:
                varridos.append("EQL")
            for k in varridos:
                est["abaixo"].pop(k, None)
            est["eql"] = [v for v in est["eql"] if l[t] >= v]
            est["fundos"] = [v for v in est["fundos"] if l[t] >= v]
            v = est["varrida"]
            if varridos:
                conta("1 varridas")
                est["varrida"] = {"nivel": "+".join(varridos), "t0": t, "fundo": t}
            elif v is not None and l[t] < l[v["fundo"]]:
                v["fundo"] = t
            elif not r.exigir_varrida and v is None:
                est["varrida"] = {"nivel": "nenhum", "t0": t, "fundo": t}
            v = est["varrida"]
            if v is not None and l[t] < l[v["fundo"]]:
                v["fundo"] = t
            if v is not None and t - v["t0"] > val_varrida:
                est["varrida"] = None
            elif v is not None and t > v["fundo"]:
                # CHoCH: fecha acima do último topo confirmado antes do fundo
                f = v["fundo"]
                topos = [i for i in range(max(0, f - 120), f) if ph[i] and i + r.k_swing <= t]
                if topos and c[t] > h[topos[-1]] and (c[t - 1] <= h[topos[-1]]):
                    ref = topos[-1]
                    conta("2 CHoCH")
                    pernas = _pernas(ph1, pl1, h, l, f, t)
                    forca = bool(np.any((amp[f + 1:t + 1] >= 2 * atr[f + 1:t + 1]) &
                                        (c[f + 1:t + 1] > o[f + 1:t + 1])))
                    vol_ratio = vol[f + 1:t + 1].mean() / max(vol[ref:f + 1].mean(), 1)
                    ok = ((not r.exigir_pernas or pernas >= 5 or forca) and
                          (not r.exigir_volume or vol_ratio > 1))
                    if not (pernas >= 5 or forca):
                        conta("x pernas reprovou")
                    if not vol_ratio > 1:
                        conta("x volume reprovou")
                    if ok:
                        conta("3 CHoCH aprovado")
                        est["ordem"] = {"t0": t, "fundo": l[f], "topo": h[f:t + 1].max(), "ativa": False,
                                        "info": {"nivel": v["nivel"], "t_choch": tempo[t], "pernas": pernas,
                                                 "forca": forca, "vol_ratio": round(vol_ratio, 2),
                                                 "delta_agr": agr[f + 1:t + 1].sum()}}
                    est["varrida"] = None
        # ---- atualiza a ordem para a próxima barra (topo, entrada, stop, alvo)
        ordem = est["ordem"]
        if ordem is not None and est["posicao"] is None:
            if t > ordem["t0"]:
                ordem["topo"] = max(ordem["topo"], h[t])
            topo, fundo = ordem["topo"], ordem["fundo"]
            entrada = topo - r.fib * (topo - fundo)
            stop = fundo - r.folga_stop
            risco = entrada - stop
            if r.alvo == "3R":
                alvo = entrada + r.rr_min * risco
            else:
                acima = sorted(v for v in [*est["acima"].values()] if v > topo)
                alvo = acima[0] if acima else np.inf
            ordem.update(entrada=entrada, stop=stop, alvo=alvo,
                         ativa=(r.risco_min <= risco <= r.risco_max and
                                np.isfinite(alvo) and alvo - entrada >= r.rr_min * risco))
            if not ordem.get("contou"):
                motivo = ("risco>max" if risco > r.risco_max else "risco<min" if risco < r.risco_min
                          else "sem alvo" if not np.isfinite(alvo) else "RR<3" if not ordem["ativa"] else None)
                if motivo:
                    ordem.setdefault("motivos", set()).add(motivo)
                else:
                    ordem["contou"] = True
                    conta("4 ordem ativa")
            if t - ordem["t0"] > val_ordem or ultimo_do_dia[t]:
                if not ordem.get("contou"):
                    for m in ordem.get("motivos", ()):
                        conta(f"x ordem nunca ativa: {m}")
                est["ordem"] = None
    return trades


# --------------------------------------------------------------------------- dia

def _regras_do_dia(cands: list[dict], r: Regras) -> pd.DataFrame:
    if not cands:
        return pd.DataFrame()
    cands = sorted(cands, key=lambda x: x["t_entrada"])
    aceitos, livre, por_dia = [], None, {}
    for x in cands:
        d = x["t_entrada"].normalize()
        n, stops = por_dia.get(d, (0, 0))
        if n >= r.max_trades or stops >= r.max_stops:
            continue
        if livre is not None and x["t_entrada"] < livre:
            continue
        aceitos.append(x)
        livre = x["t_saida"]
        por_dia[d] = (n + 1, stops + (x["R"] < 0))
    return pd.DataFrame(aceitos)


def rodar(df: pd.DataFrame, diario: pd.DataFrame, r: Regras = Regras(),
          funil: dict | None = None) -> pd.DataFrame:
    niv = niveis_diarios(diario)
    compra = _candidatos_compra(df, niv, r, "compra", funil)
    venda = _candidatos_compra(_espelhar(df), _espelhar_niveis(niv), r, "venda", funil)
    for x in venda:
        for k in ("entrada", "stop", "alvo", "saida"):
            x[k] = -x[k]
    return _regras_do_dia(compra + venda, r)


def aleatorio(df: pd.DataFrame, trades: pd.DataFrame, r: Regras, n_sim: int = 300,
              semente: int = 7) -> np.ndarray:
    """Mesmo número de trades, mesmos dias e riscos, mas hora e direção sorteadas, alvo 3R."""
    rng = np.random.default_rng(semente)
    o, h, l, c = (df[x].to_numpy() for x in ("abertura", "maxima", "minima", "fechamento"))
    dia = df.index.normalize()
    pos_dia = pd.Series(np.arange(len(df))).groupby(dia).agg(["min", "max"])
    hhmm = df.index.strftime("%H:%M").to_numpy()
    medias = []
    for _ in range(n_sim):
        rs = []
        for _, tr in trades.iterrows():
            a, b = pos_dia.loc[tr.t_entrada.normalize()]
            ok = np.arange(a, b + 1)[hhmm[a:b + 1] <= r.ultima_entrada]
            i = rng.choice(ok)
            s = rng.choice([1, -1])
            ent, risco = o[i], tr.risco
            stop, alvo = ent - s * risco, ent + s * r.rr_min * risco
            res = None
            for k in range(i, b + 1):
                lo, hi = (l[k], h[k]) if s == 1 else (-h[k], -l[k])
                if lo <= s * stop:
                    res = -risco
                    break
                if hi >= s * alvo and k > i:
                    res = r.rr_min * risco
                    break
            if res is None:
                res = s * (c[b] - ent)
            rs.append((res - r.custo) / risco)
        medias.append(np.mean(rs))
    return np.array(medias)


# --------------------------------------------------------------------------- relatório

def resumo(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"trades": 0}
    R = t.R.to_numpy()
    eq = np.cumsum(R)
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    seq, pior = 0, 0
    for x in R:
        seq = seq + 1 if x < 0 else 0
        pior = max(pior, seq)
    meses = max((t.t_entrada.max() - t.t_entrada.min()).days / 30.4, 1)
    return {"trades": len(t), "por_mes": round(len(t) / meses, 1),
            "acerto_%": round(100 * (R > 0).mean(), 1),
            "alvos_%": round(100 * (R >= 2.5).mean(), 1),
            "media_R": round(R.mean(), 3), "total_R": round(R.sum(), 1),
            "max_dd_R": round(dd, 1), "pior_seq": pior,
            "risco_medio": round(t.risco.mean())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rrquant.setup_central")
    ap.add_argument("--minutos", type=int, default=2)
    ap.add_argument("--sim", type=int, default=200)
    a = ap.parse_args(argv)
    df = profit.carregar(minutos=a.minutos)
    diario = profit.carregar(minutos=None)
    base = Regras()
    print(f"WIN {a.minutos} min: {df.index[0]:%Y-%m-%d} a {df.index[-1]:%Y-%m-%d}, "
          f"{df.index.normalize().nunique()} pregões\n")
    variantes = {
        "regras completas (alvo na liquidez)": base,
        "alvo fixo de 3R": replace(base, alvo="3R"),
        "sem exigir varrida": replace(base, exigir_varrida=False),
        "sem filtro de pernas": replace(base, exigir_pernas=False),
        "sem filtro de volume": replace(base, exigir_volume=False),
        "entrada em 50%": replace(base, fib=0.5),
        "entrada em 79%": replace(base, fib=0.79),
    }
    linhas = {}
    for nome, r in variantes.items():
        t = rodar(df, diario, r)
        linhas[nome] = resumo(t)
        if nome.startswith("regras completas"):
            principal = t
    print(pd.DataFrame(linhas).T.to_string(), "\n")
    if not principal.empty:
        sims = aleatorio(df, principal, base, n_sim=a.sim)
        print(f"Entradas aleatórias (mesmos dias e riscos, {a.sim} sorteios): média "
              f"{sims.mean():+.3f} R; o setup ({principal.R.mean():+.3f} R) supera "
              f"{100 * (sims < principal.R.mean()).mean():.0f}% dos sorteios\n")
        p = principal.assign(ano=principal.t_entrada.dt.year,
                             hora=principal.t_entrada.dt.hour)
        for col in ("lado", "nivel", "hora", "ano"):
            print(p.groupby(col).R.agg(trades="size", media_R="mean", total_R="sum")
                  .round(2).to_string(), "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
