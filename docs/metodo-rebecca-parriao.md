# Método — Leitura Pré-Mercado (Rebecca Parrião)

Destrinchado a partir da transcrição de `data/transcricoes/2026-05-20_rebecca-parriao_leitura-pre-mercado.md`.
Canal: lives diárias seg–qui às 8h15 (BRT), foco em day trade de **dólar futuro** e índice.

A leitura dela tem **estrutura fixa** — é isso que vira o modelo de dados do dashboard.

## 1. Cadeia de correlação (o "porquê" — o racional dela)

Ela raciocina sempre nessa ordem causal:

```
petróleo  →  inflação  →  curva de juros (Selic → DI)  →  ativos de risco + câmbio (USD/BRL)
```

- Guerra/Oriente Médio → petróleo caro por mais tempo → inflação prolongada.
- Inflação desancorada → BC precisa de juros altos pra defender a moeda.
- Curva de juros (DI) = "custo do dinheiro no tempo" → norteia índice futuro, ações,
  câmbio.
- **Regra prática dela**: fechamento da curva de juros ("juros caindo") favorece alta
  do índice; abertura da curva favorece queda.

## 2. Varredura de mercados (overnight → pré-abertura)

Ordem em que ela passa os olhos, com os ativos citados:

| Bloco | Ativos citados na live |
|-------|------------------------|
| **Ásia/Oceania** | Nikkei (Japão), ASX (Austrália), Shanghai, China A50, Hong Kong, Coreia do Sul, Índia |
| **Europa** | DAX (Alemanha), CAC (França), FTSE (Reino Unido), FTSE MIB (Itália), Ibex (Espanha), SMI (Suíça), Eurostoxx 50 |
| **EUA (fech. ontem + futuros)** | Dow Jones, S&P 500, Nasdaq, small caps (Russell) |
| **Commodities** | ouro, prata, cobre, platina, paládio, petróleo Brent, WTI, minério de ferro (porto de Dalian), café/cacau (contrato C, NY) |
| **Moedas** | USD vs EUR / GBP / JPY / CHF; emergentes: rand (ZAR), peso (MXN); **BRL** (real, futuro na CME/Chicago) |
| **Renda fixa** | Treasuries US (2/10/30 anos — 30y a 5%+ acendeu alerta), curva DI Brasil |
| **Ações / eventos** | Petrobras (exportadoras de petróleo pesam), Vale (maior peso no Ibov), balanço da Nvidia, fluxo cambial, ata do FOMC |

## 3. Técnico e execução (a "leitura fina")

- **Elliott** — conta ondas A/B/C; projeta 4ª/5ª onda; "amplitude replicada".
- **"Frequência"** (linguagem própria dela p/ estrutura de mercado) — sequência
  máxima→mínima→inflexão; topos abaixo de topos + fundos abaixo de fundos = tendência
  de baixa; ganhar máxima anterior "descaracteriza" a queda. (É basicamente
  market structure / BOS de SMC.)
- **Fluxo / absorção** (Smart Money Concepts) — "absorção sem agressão vendedora não
  dá gatilho"; regiões líquidas; captura de liquidez.
- **Suporte/resistência e polaridade** — teste de polaridade após rompimento.
- **VIX > 20** = alerta de possível realização (volatilidade implícita do S&P elevada).
- **Gestão de risco** — realização parcial + compra de proteção (puts) antes de eventos
  (ex.: balanço da Nvidia).

## 4. Como isso vira dashboard

O que é **automatizável por API** (frentes 1 e 3 do projeto):

- Blocos 2 (varredura) e a maior parte do 1 (juros/inflação) → snapshot diário via
  yfinance + FRED + BCB. Cada linha da tabela acima vira um ticker.
- VIX, Treasuries, curva DI → séries numéricas diretas.
- Estrutura de mercado / "frequência" / ondas → derivável de OHLC (swing highs/lows),
  é a ponte pro dashboard quant (frente 3).

O que **só sai da transcrição** (frente 2 — camada de tese):

- A *leitura* dela (viés do dia, "eu estaria vendendo aqui"), níveis específicos que
  ela desenha no gráfico, e o encadeamento narrativo macro.

## Tickers de referência (rascunho p/ yfinance)

```
Índices:  ^N225 ^AXJO 000001.SS ^HSI ^KS11 ^BSESN ^GDAXI ^FCHI ^FTSE ^GSPC ^IXIC ^DJI ^RUT ^BVSP
Commod.:  GC=F SI=F HG=F PL=F PA=F BZ=F CL=F
Câmbio:   BRL=X EURUSD=X GBPUSD=X JPY=X CHF=X ZAR=X MXN=X
Risco/RF: ^VIX ^TNX (10y) ^TYX (30y)
Ações:    PETR4.SA VALE3.SA NVDA
```
*(validar cada símbolo na 1ª implementação — alguns variam.)*
