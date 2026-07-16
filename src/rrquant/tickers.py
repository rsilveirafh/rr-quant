"""Catalogo de tickers da varredura diaria.

Organizado na mesma ordem em que a Rebecca Parriao passa os mercados
(ver ../../docs/metodo-rebecca-parriao.md). Cada bloco e uma lista de
(ticker_yfinance, nome_de_exibicao). So os ativos recorrentes (freq >= 4/6)
entram no snapshot padrao; os ocasionais ficam comentados p/ ligar depois.
"""

# Blocos na ordem da varredura. dict preserva ordem de insercao (py3.7+).
BLOCOS: dict[str, list[tuple[str, str]]] = {
    "Asia / Oceania": [
        ("^N225", "Nikkei (Japao)"),
        ("^AXJO", "ASX (Australia)"),
        ("000001.SS", "Shanghai"),
        ("^HSI", "Hang Seng (HK)"),
        ("^KS11", "Kospi (Coreia)"),
        ("^BSESN", "Sensex (India)"),
    ],
    "Europa": [
        ("^GDAXI", "DAX (Alemanha)"),
        ("^FCHI", "CAC (Franca)"),
        ("^FTSE", "FTSE (Reino Unido)"),
        ("FTSEMIB.MI", "FTSE MIB (Italia)"),
        ("^IBEX", "Ibex (Espanha)"),
        ("^SSMI", "SMI (Suica)"),
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
        ("BZ=F", "Petroleo Brent"),
        ("CL=F", "Petroleo WTI"),
        ("GC=F", "Ouro"),
        ("SI=F", "Prata"),
        ("HG=F", "Cobre"),
        ("PL=F", "Platina"),
        ("PA=F", "Paladio"),
        # ("NG=F", "Gas natural"),   # 1/6
        # ("KC=F", "Cafe (contrato C)"),  # 1/6
    ],
    "Cambio": [
        ("BRL=X", "USD/BRL (real)"),
        ("DX-Y.NYB", "DXY (dolar index)"),
        ("EURUSD=X", "EUR/USD"),
        ("GBPUSD=X", "GBP/USD (libra)"),
        ("JPY=X", "USD/JPY (iene)"),
        ("CHF=X", "USD/CHF (franco)"),
        ("ZAR=X", "USD/ZAR (rand)"),
        ("MXN=X", "USD/MXN (peso)"),
        ("AUDUSD=X", "AUD/USD (dolar aus.)"),
    ],
    "Renda fixa / Volatilidade": [
        ("^FVX", "Treasury 5 anos"),
        ("^TNX", "Treasury 10 anos"),
        ("^TYX", "Treasury 30 anos"),
        ("^VIX", "VIX (vol. S&P)"),
        ("^VXN", "VXN (vol. Nasdaq)"),
    ],
    "Acoes / eventos": [
        ("PETR4.SA", "Petrobras"),
        ("VALE3.SA", "Vale"),
        ("NVDA", "Nvidia"),
        ("JPM", "JPMorgan"),
        ("GS", "Goldman Sachs"),
        ("BAC", "Bank of America"),
    ],
}

# Ativos onde "alta e ruim" (juros/volatilidade/USD-BRL): a variacao positiva
# nao e necessariamente boa. So afeta rotulo de contexto, nao a cor.
INVERSOS = {"^FVX", "^TNX", "^TYX", "^VIX", "^VXN", "BRL=X"}


def todos_os_tickers() -> list[str]:
    return [t for bloco in BLOCOS.values() for (t, _nome) in bloco]


def mapa_nomes() -> dict[str, str]:
    return {t: nome for bloco in BLOCOS.values() for (t, nome) in bloco}
