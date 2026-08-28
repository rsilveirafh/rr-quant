"""Catálogo de tickers da varredura diária.

Organizado na mesma ordem em que a leitura pré-mercado passa os mercados
(ver ../../docs/metodo-leitura-pre-mercado.md). Cada bloco é uma lista de
(ticker_yfinance, nome_de_exibição). Só os ativos recorrentes entram no
snapshot padrão; os ocasionais ficam comentados p/ ligar depois.
"""

# Blocos na ordem da varredura. dict preserva ordem de inserção (py3.7+).
BLOCOS: dict[str, list[tuple[str, str]]] = {
    "Ásia / Oceania": [
        ("^N225", "Nikkei (Japão)"),
        ("^AXJO", "ASX (Austrália)"),
        ("000001.SS", "Shanghai"),
        ("^HSI", "Hang Seng (HK)"),
        ("^KS11", "Kospi (Coreia)"),
        ("^BSESN", "Sensex (Índia)"),
    ],
    "Europa": [
        ("^GDAXI", "DAX (Alemanha)"),
        ("^FCHI", "CAC (França)"),
        ("^FTSE", "FTSE (Reino Unido)"),
        ("FTSEMIB.MI", "FTSE MIB (Itália)"),
        ("^IBEX", "Ibex (Espanha)"),
        ("^SSMI", "SMI (Suíça)"),
        ("^STOXX50E", "Eurostoxx 50"),
    ],
    "EUA": [
        ("^DJI", "Dow Jones"),
        ("^GSPC", "S&P 500"),
        ("^IXIC", "Nasdaq"),
        ("^RUT", "Russell 2000 (small caps)"),
    ],
    "Brasil": [
        ("^BVSP", "Ibovespa"),
        ("EWZ", "EWZ (Ibov dolarizado, NY)"),
    ],
    "Commodities": [
        ("BZ=F", "Petróleo Brent"),
        ("CL=F", "Petróleo WTI"),
        ("GC=F", "Ouro"),
        ("SI=F", "Prata"),
        ("HG=F", "Cobre"),
        ("PL=F", "Platina"),
        ("PA=F", "Paládio"),
        # ("NG=F", "Gás natural"),        # 1/6
        # ("KC=F", "Café (contrato C)"),  # 1/6
    ],
    "Câmbio": [
        ("BRL=X", "USD/BRL (real)"),
        ("DX-Y.NYB", "DXY (dólar index)"),
        ("EURUSD=X", "EUR/USD"),
        ("GBPUSD=X", "GBP/USD (libra)"),
        ("JPY=X", "USD/JPY (iene)"),
        ("CHF=X", "USD/CHF (franco)"),
        ("ZAR=X", "USD/ZAR (rand)"),
        ("MXN=X", "USD/MXN (peso)"),
        ("AUDUSD=X", "AUD/USD (dólar aus.)"),
    ],
    "Renda fixa / Volatilidade": [
        ("^FVX", "Treasury 5 anos"),
        ("^TNX", "Treasury 10 anos"),
        ("^TYX", "Treasury 30 anos"),
        ("^VIX", "VIX (vol. S&P)"),
        ("^VXN", "VXN (vol. Nasdaq)"),
    ],
    "Ações / eventos": [
        ("PETR4.SA", "Petrobras"),
        ("VALE3.SA", "Vale"),
        ("NVDA", "Nvidia"),
        ("JPM", "JPMorgan"),
        ("GS", "Goldman Sachs"),
        ("BAC", "Bank of America"),
    ],
}

# Ativos onde "alta é ruim" p/ risco (juros/volatilidade/USD-BRL): variação
# positiva costuma indicar aversão a risco. Afeta só o rótulo de contexto.
INVERSOS = {"^FVX", "^TNX", "^TYX", "^VIX", "^VXN", "BRL=X"}

# Blocos de renda variável (bolsas) — usados no cálculo de regime/amplitude.
BLOCOS_BOLSA = ["Ásia / Oceania", "Europa", "EUA", "Brasil"]


def todos_os_tickers() -> list[str]:
    return [t for bloco in BLOCOS.values() for (t, _nome) in bloco]


def mapa_nomes() -> dict[str, str]:
    return {t: nome for bloco in BLOCOS.values() for (t, nome) in bloco}
