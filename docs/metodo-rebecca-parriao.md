# Método — Leitura Pré-Mercado (Rebecca Parrião)

Consolidado a partir de **6 dias** de transcrição em `data/transcricoes/`
(2026-05-20, 07-09, 07-10, 07-13, 07-14, 07-15).
Canal: **Rebecca Parrião / Trader** (`@rebeccaparriao`) — lives diárias seg–qui às 8h15
(BRT), foco em day trade de **dólar futuro** e **índice** (WIN/INFUT).

> ⚠️ **Nota de amostra**: o dia **07-10 foi atípico** (virou aula de inflação/IPCA), então
> ela pulou a varredura de mercados. Por isso a maioria dos ativos aparece em **5/6** dias
> (ausentes só no 07-10), não 6/6. Frequências abaixo refletem isso.

A leitura tem **estrutura fixa** — é o modelo de dados do dashboard.

## 1. Rotina real da leitura (ordem cronológica dos 6 dias)

1. **News / geopolítica** — hoje é o que ABRE a live (conflito Oriente Médio, estreito de
   Ormuz, tarifas do Trump sobre navios, etc.).
2. **Balanços / notícias corporativas** (bancos US, memórias/chips, PepsiCo…).
3. **Calendário macro do dia** — agenda de indicadores; na 2ª-feira ela varre a semana e
   põe "asterisco" no dia de maior volatilidade esperada.
4. **Cadeia causal** (o "racional" — abaixo).
5. **Varredura** Ásia/Oceania → Europa → EUA (fechamento de ontem + futuros).
6. **EWZ** — ponte do fechamento US pro doméstico.
7. **Commodities** — metálicas (ouro/prata/cobre/platina/paládio) → minério+Vale →
   petróleo+Petrobras.
8. **Renda fixa / liquidez global** — Treasuries US, curva DI.
9. **Moedas** — DXY → pares G7 → emergentes → real na CME.
10. **Técnico** na ordem **DI (juros) → índice futuro → dólar futuro**, projeção validada
    por fluxo/gatilho.

## 2. Cadeia de correlação (o racional-mestre — 6/6)

```
petróleo  →  inflação  →  curva de juros (Selic → DI)  →  ativos de risco + câmbio (USD/BRL)
```

- DI = "custo do dinheiro no tempo"; norteia índice futuro, ações, câmbio. **É por onde o
  técnico dela começa.**
- Regra prática: fechamento da curva de juros favorece alta do índice; abertura favorece
  queda.
- **DXY (euro ~50% da cesta)** usado pra separar movimento do dólar global vs. pares
  emergentes.
- Correlação de regra: **Ibov ≈ Dow Jones** ("não temos tech no índice").

## 3. Ativos / instrumentos (união dos 6 dias)

### Índices mundiais
| Ativo | Freq. | Ticker (yfinance) |
|---|---|---|
| Nikkei (Japão) | 5/6 | `^N225` |
| ASX (Austrália) | 5/6 | `^AXJO` |
| Shanghai | 5/6 | `000001.SS` |
| China A50 | 5/6 | (fut. `XIN9`) |
| Hang Seng (Hong Kong) | 5/6 | `^HSI` |
| Kospi (Coreia) | 5/6 | `^KS11` |
| Índia (Sensex) | 5/6 | `^BSESN` |
| Taiwan | 1/6 | `^TWII` |
| DAX (Alemanha) | 5/6 | `^GDAXI` |
| CAC (França) | 5/6 | `^FCHI` |
| FTSE (Reino Unido) | 5/6 | `^FTSE` |
| FTSE MIB (Itália) | 5/6 | `FTSEMIB.MI` |
| Ibex (Espanha) | 5/6 | `^IBEX` |
| SMI (Suíça) | 5/6 | `^SSMI` |
| Eurostoxx 50 | 5/6 | `^STOXX50E` |
| Dow Jones | 5/6 | `^DJI` |
| S&P 500 | 5/6 | `^GSPC` |
| Nasdaq | 5/6 | `^IXIC` |
| Small caps / Russell | 5/6 | `^RUT` |
| Ibovespa / índice futuro (INFUT/WIN) | 6/6 | `^BVSP` |
| EWZ (Ibov dolarizado, proxy NY) | 5/6 | `EWZ` |
| EWY (ETF Coreia em NY) | 1/6 | `EWY` |

### Commodities
| Ativo | Freq. | Ticker |
|---|---|---|
| Petróleo Brent | 6/6 | `BZ=F` |
| Petróleo WTI | 5/6 | `CL=F` |
| Ouro | 5/6 | `GC=F` |
| Prata | 5/6 | `SI=F` |
| Cobre | 5/6 | `HG=F` |
| Platina | 5/6 | `PL=F` |
| Paládio | 5/6 | `PA=F` |
| Minério de ferro (porto de Dalian) | 5/6 | (Dalian; proxy `TIO=F`/via Vale) |
| Café (contrato C, NY) | 1/6 | `KC=F` |
| Cacau | 1/6 | `CC=F` |
| Gás natural | 1/6 | `NG=F` |

### Moedas / câmbio
| Par | Freq. | Ticker |
|---|---|---|
| USD/BRL (real, futuro CME/Chicago) | 6/6 | `BRL=X` |
| **DXY (dólar index)** | 4/6 | `DX-Y.NYB` |
| USD/EUR | 5/6 | `EURUSD=X` |
| USD/GBP (libra) | 5/6 | `GBPUSD=X` |
| USD/JPY (iene) | 5/6 | `JPY=X` |
| USD/CHF (franco suíço) | 5/6 | `CHF=X` |
| USD/ZAR (rand) | 5/6 | `ZAR=X` |
| USD/MXN (peso mexicano) | 5/6 | `MXN=X` |
| USD/AUD (dólar australiano) | 4/6 | `AUDUSD=X` |
| Lira turca | 1/6 | `TRY=X` |

### Renda fixa / juros
| Item | Freq. | Fonte |
|---|---|---|
| Treasuries US (2/10/30 anos; 30y >5% recorrente) | 5/6 | `^FVX` `^TNX` `^TYX` |
| Curva DI Brasil (ponta curta/média/longa) | 6/6 | BCB / B3 |
| Selic / expectativa Copom | ~4/6 | BCB SGS 432 |
| CDI (o DI "representa o CDI") | 1/6 | BCB |
| PU / leilão de títulos do Tesouro | 2/6 | Tesouro / Anbima |

### Ações individuais
| Ação | Freq. | Ticker |
|---|---|---|
| Petrobras (+ ADR PBR) | 5/6 | `PETR4.SA` / `PBR` |
| Vale (+ ADR) | 5/6 | `VALE3.SA` / `VALE` |
| Nvidia | 1/6 | `NVDA` |
| PepsiCo | 1/6 | `PEP` |
| Micron | 1/6 | `MU` |
| Samsung | 1/6 | `005930.KS` |
| SanDisk | 1/6 | `SNDK` |
| JPMorgan | 2/6 | `JPM` |
| Goldman Sachs | 2/6 | `GS` |
| Bank of America | 2/6 | `BAC` |
| ASML | 1/6 | `ASML` |
| Meta / Alphabet (contexto Capex) | 1/6 | `META` / `GOOGL` |
| Totvs (tech BR) | 1/6 | `TOTS3.SA` |

### Volatilidade
| Item | Freq. | Ticker |
|---|---|---|
| VIX (>20 = alerta de realização) | recorrente | `^VIX` |
| VXN (volatilidade da Nasdaq, à parte do VIX) | 2/6 | `^VXN` |

### ❌ Não cobre
- **Cripto = 0/6.** Ela não toca em criptomoedas. Não modelar como frente de dados sem
  evidência em amostra maior.
- **PTAX e payroll não apareceram** em nenhum dos 6 dias — não prometer cobertura.

## 4. Conceitos / métodos técnicos (união)

**Conceito-mestre**: *"de quanto custava → quanto passou a custar"* (spread aberto) +
**inflexão** — vocabulário dela em 6/6. Três regiões de valor: **máxima** (resistência),
**mínima** (suporte), **inflexão** (preço de decisão).

- **Elliott** — ondas A/B/C, 4ª/5ª onda, amplitude replicada.
- **"Frequência"** — estrutura de mercado (topos/fundos descendentes = baixa; ganhar máxima
  "descaracteriza" a queda). Equivale a market structure / BOS de SMC.
- **Fluxo / absorção** — distingue **absorção sem agressão** (não dá gatilho) de
  **absorção seguida de agressão** (gatilho). **Exaustão de volume** como gatilho.
- **Volume Profile / Volume at Price** — ~10 faixas, período = D-1.
- **Fibonacci** — 31.8 / 50 / 61.8 pra zonas de ajuste (1/6).
- **VIX > 20** = alerta de realização; **gama negativo → short squeeze / zerada direcional**.
- **Contraparte + liquidez × volatilidade** — base do gatilho.
- **Gestão** — risco de entrada (parcial + puts) **e** de posição (carrego / fazer médio);
  chamada de margem acelera os 15 min finais.
- **Acumulação / distribuição** (linguagem tipo Wyckoff).
- **Fluxo por corretora** — quem compra/vende (Ideal, UBS, XP, BTG, Genial, Santander,
  Necton, Ágora).
- **Leitura de contexto** — rotação setorial (defensivo × crescimento); concentração de
  índice como risco (Kospi ~40% em 2 ativos); múltiplos/Capex/valuation; fuga p/ segurança
  (ouro + franco suíço + treasuries); concorrência de fluxo emergente
  (México/Colômbia/Argentina/Austrália rivais do BR).

## 5. Indicadores macro / eventos (união)

**EUA (→ FRED)**: CPI (núcleo/cheio) · PPI · jobless claims (toda quinta) · retail sales ·
expectativa Michigan · Philly Fed · housing/hipotecas · ata do FOMC · balanço do Fed ·
vendas mensais de memória/chips.

**Brasil (→ BCB / IBGE)**: IPCA / IPCA-15 (por grupo) · Boletim Focus · IBC-Br · setor de
serviços (~70% do PIB) · varejo · Selic/Copom · fluxo cambial.

**Global / calendário externo**: China (PIB, produção industrial, desemprego, balança
comercial, novos empréstimos) · PIB zona do euro · PIB UK · decisões de juros (Copom, FOMC
29-jul, Canadá, Indonésia) · balança comercial Japão · inflação México/Colômbia.

**Derivativos de juros (drivers diários)**:
- **CME FedWatch / fed funds futures** (`ZQ=F`) — probabilidades implícitas de decisão de
  juros ("onde estão colocando dinheiro"), o "gráfico de pontos".
- **COT report** (CME) — posições vendidas líquidas.

**Petróleo/energia**: estoque de petróleo US (EIA) · monitoramento marítimo do estreito de
Ormuz (rastreio de navios ao vivo — input qualitativo).

**Corporativo**: balanços (with foco em after-market, ex. Nvidia).

## 6. Fronteira: automatizável vs. tese

- **Automatizável por API** (frentes 1 e 3): blocos 3, 5, 8, 9 da rotina + os indicadores
  numéricos (CPI, IPCA, DI, FedWatch, COT). Cada linha das tabelas acima = um ticker/série.
- **Só sai da transcrição** (frente 2 — camada de tese): news/geopolítica (Ormuz, tarifas),
  monitoramento marítimo, o viés do dia ("eu estaria vendendo aqui"), níveis específicos que
  ela desenha, e o encadeamento narrativo.

## 7. Tickers de referência (rascunho p/ yfinance — validar na 1ª implementação)

```
Índices:  ^N225 ^AXJO 000001.SS ^HSI ^KS11 ^BSESN ^TWII ^GDAXI ^FCHI ^FTSE FTSEMIB.MI ^IBEX ^SSMI ^STOXX50E ^GSPC ^IXIC ^DJI ^RUT ^BVSP EWZ EWY
Commod.:  GC=F SI=F HG=F PL=F PA=F BZ=F CL=F NG=F KC=F CC=F
Câmbio:   BRL=X DX-Y.NYB EURUSD=X GBPUSD=X JPY=X CHF=X ZAR=X MXN=X AUDUSD=X TRY=X
Risco/RF: ^VIX ^VXN ^FVX ^TNX ^TYX ZQ=F
Ações:    PETR4.SA PBR VALE3.SA VALE NVDA PEP MU 005930.KS SNDK JPM GS BAC ASML META GOOGL TOTS3.SA
```
