"""Tela ao vivo do WIN: o replay alimentado pelo RTD do Profit.

O Profit só grava o histórico em disco quando carrega um gráfico, então o preço ao vivo vem do
servidor RTD dele (``RTDTrading.RtdServer``), lido por uma instância oculta do Excel. As barras
de 2 min do dia são montadas a partir do último preço e da quantidade acumulada; o histórico
anterior vem dos arquivos do Profit. A cada barra fechada o motor do setup roda de novo, e a
página (http://localhost:8765) se atualiza sozinha.

Uso (com o Profit aberto, de preferência antes das 9h):
    python -m rrquant.aovivo
"""

from __future__ import annotations

import argparse
import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd

from . import profit, replay, setup_central as sc

CAMPOS = ["ULT", "HOR", "DAT", "QTT"]
MINUTOS = 2


class LeitorRTD(threading.Thread):
    """Lê o RTD do Profit pelo Excel e monta barras de 2 min."""

    def __init__(self, ativo: str):
        super().__init__(daemon=True)
        self.ativo = ativo
        self.barras: dict[pd.Timestamp, list] = {}   # início → [o, h, l, c, contratos]
        self.ultimo: dict = {}
        self.trava = threading.Lock()
        self.erro: str | None = None
        self.parar = threading.Event()

    def run(self) -> None:
        import pythoncom
        import win32com.client as w
        pythoncom.CoInitialize()
        xl = None
        try:
            xl = w.DispatchEx("Excel.Application")
            xl.Visible = False
            xl.DisplayAlerts = False
            wb = xl.Workbooks.Add()
            sh = wb.Worksheets(1)
            for j, c in enumerate(CAMPOS):
                sh.Cells(1, j + 1).Formula = f'=RTD("rtdtrading.rtdserver",,"{self.ativo}","{c}")'
            faixa = sh.Range(sh.Cells(1, 1), sh.Cells(1, len(CAMPOS)))
            qtt_ant = None
            while not self.parar.is_set():
                pythoncom.PumpWaitingMessages()
                ult, hor, dat, qtt = faixa.Value[0]
                if isinstance(ult, float) and isinstance(hor, str) and ":" in hor and ult > 0:
                    t = pd.Timestamp(pd.to_datetime(f"{dat} {hor}", dayfirst=True))
                    dq = 0 if qtt_ant is None or qtt is None else max(qtt - qtt_ant, 0)
                    qtt_ant = qtt
                    b0 = replay.ORIGEM + ((t - replay.ORIGEM) // pd.Timedelta(minutes=MINUTOS)) * pd.Timedelta(minutes=MINUTOS)
                    with self.trava:
                        b = self.barras.get(b0)
                        if b is None:
                            self.barras[b0] = [ult, ult, ult, ult, dq]
                        else:
                            b[1], b[2], b[3], b[4] = max(b[1], ult), min(b[2], ult), ult, b[4] + dq
                        self.ultimo = {"ult": ult, "hor": hor, "t": t}
                time.sleep(0.25)
        except Exception as e:  # noqa: BLE001 - mostrado na página
            self.erro = f"RTD: {e}"
        finally:
            if xl is not None:
                try:
                    xl.DisplayAlerts = False
                    for wb in list(xl.Workbooks):
                        wb.Close(False)
                    xl.Quit()
                except Exception:  # noqa: BLE001
                    pass
            pythoncom.CoUninitialize()

    def fechadas(self, agora: pd.Timestamp) -> pd.DataFrame:
        """Barras de 2 min já fechadas, no formato do leitor do Profit."""
        with self.trava:
            itens = [(t, *b) for t, b in self.barras.items()
                     if t + pd.Timedelta(minutes=MINUTOS) <= agora]
        df = pd.DataFrame(itens, columns=["data", "abertura", "maxima", "minima", "fechamento", "contratos"])
        df = df.set_index("data").sort_index()
        for c in ("vol_fin", "negocios", "agr_fin_compra", "agr_fin_venda", "agr_qtd_compra", "agr_qtd_venda"):
            df[c] = 0.0
        return df

    def formando(self) -> list | None:
        with self.trava:
            if not self.barras:
                return None
            t = max(self.barras)
            return [replay._ts(t), *[float(x) for x in self.barras[t]]]


class Painel:
    """Junta histórico + barras ao vivo e recalcula o replay a cada barra fechada."""

    def __init__(self, leitor: LeitorRTD, r: sc.Regras):
        self.leitor, self.r = leitor, r
        self.hist2 = profit.carregar(minutos=MINUTOS)
        self.diario = profit.carregar(minutos=None)
        self.dados: dict | None = None
        self.versao = 0
        self.n_fechadas = -1
        self.trava = threading.Lock()

    def atualizar(self) -> None:
        ult = self.leitor.ultimo.get("t")
        agora = ult if ult is not None else pd.Timestamp.now()
        vivo = self.leitor.fechadas(agora)
        if len(vivo) == self.n_fechadas and self.dados is not None:
            return
        dia = agora.normalize()
        hist = self.hist2
        if len(vivo):
            hist = hist[hist.index < vivo.index[0]]           # o ao vivo substitui o arquivo
            hist = pd.concat([hist, vivo[hist.columns.intersection(vivo.columns)]]).sort_index()
        if dia not in hist.index.normalize():
            return
        diario = self.diario
        if dia not in pd.to_datetime(diario.index).normalize():
            hoje = hist[hist.index.normalize() == dia]
            diario = pd.concat([diario, pd.DataFrame(
                {"abertura": hoje.abertura.iloc[0], "maxima": hoje.maxima.max(),
                 "minima": hoje.minima.min(), "fechamento": hoje.fechamento.iloc[-1]}, index=[dia])])
        dados = replay.montar(dia, hist, diario, self.r)
        dados["aovivo"] = True
        with self.trava:
            self.dados, self.n_fechadas = dados, len(vivo)
            self.versao += 1


def servir(painel: Painel, porta: int) -> ThreadingHTTPServer:
    arq_modelo = Path(replay.__file__).parent / "replay.html"

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silencioso
            pass

        def _enviar(self, corpo: str, tipo: str) -> None:
            b = corpo.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", f"{tipo}; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):  # noqa: N802
            with painel.trava:
                dados, versao = painel.dados, painel.versao
            if self.path.startswith("/tick"):
                u = painel.leitor.ultimo
                self._enviar(json.dumps({"versao": versao, "ult": u.get("ult"), "hor": u.get("hor"),
                                         "barra": painel.leitor.formando(), "erro": painel.leitor.erro}),
                             "application/json")
            elif self.path.startswith("/dados"):
                self._enviar(json.dumps(dados, separators=(",", ":")), "application/json")
            elif dados is None:
                self._enviar("<meta http-equiv=refresh content=3><body style='background:#0f1216;color:#d6dde6;"
                             "font:16px system-ui;padding:40px'>Esperando a primeira barra de 2 min fechar "
                             f"pelo RTD do Profit... {painel.leitor.erro or ''}</body>", "text/html")
            else:
                modelo = arq_modelo.read_text(encoding="utf-8")
                self._enviar(modelo.replace("/*DADOS*/null", json.dumps(dados, separators=(",", ":"))),
                             "text/html")

    srv = ThreadingHTTPServer(("127.0.0.1", porta), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rrquant.aovivo")
    ap.add_argument("--ativo", default="WINFUT_F_0")
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument("--sem-navegador", action="store_true")
    a = ap.parse_args(argv)
    leitor = LeitorRTD(a.ativo)
    leitor.start()
    painel = Painel(leitor, sc.Regras())
    servir(painel, a.porta)
    url = f"http://localhost:{a.porta}"
    print(f"tela ao vivo em {url} (Ctrl+C para sair)")
    if not a.sem_navegador:
        webbrowser.open(url)
    try:
        while True:
            try:
                painel.atualizar()
            except Exception as e:  # noqa: BLE001
                print("erro ao atualizar:", e)
            if leitor.erro:
                print(leitor.erro)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        leitor.parar.set()
        leitor.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
