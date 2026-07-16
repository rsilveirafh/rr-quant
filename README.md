# rr-quant

Projeto pessoal de trade **data-driven**: sair do "trade no feeling" e construir um
processo apoiado em dados reais, indicadores e métodos de leitura de mercado.

## Visão

Montar um **dashboard "quant"** que combine:

- **Varredura macro diária** dos mercados mundiais (a "revisão do mundo" — inspirada
  na leitura pré-mercado da Rebecca Parrião), reconstruída automaticamente via API,
  sem depender do vídeo.
- **Métodos discricionários** de análise técnica: Wyckoff, Elliott, Smart Money
  Concepts (SMC) — codificados como indicadores/sinais quando possível.
- **Camada de leitura/tese** extraída das transcrições dos criadores que o Ricardo
  acompanha, sobreposta aos números.

Meta pessoal do Ricardo (registrada em `memoria-pessoal/areas/financas/trade`):
> "Já notei que não sou um bom trader, que preciso de dados pra tomar decisões.
> Quero fazer isso com dados reais, indicadores, modelos de economia — um dashboard
> quant. Além de métodos baseados em Wyckoff, Elliott e Smart Money Concepts."

## Referências (vídeos-semente)

| # | Criador | Vídeo | O que interessa |
|---|---------|-------|-----------------|
| 1 | (ideia do dashboard quant) | `youtu.be/ZVMTeDBmSrI` | plantou a ideia do dashboard quant |
| 2 | **Rebecca Parrião** | `youtu.be/yNCA0h8OY-I` | revisão diária dos mercados mundiais → é a base do 1º dashboard |
| 3 | (método de análise) | `youtu.be/hsAH6wKj1PE` | método de análise de ações/índices/criptos |

## Frentes

1. **Dashboard "revisão do mundo"** — snapshot diário automático (índices mundiais,
   commodities, câmbio, juros/Treasuries, VIX, Ibov) com a mesma estrutura da leitura
   da Rebecca. → `docs/metodo-rebecca-parriao.md`
2. **Catálogo de conteúdo** — pipeline `URL do YouTube → transcrição → extração
   estruturada (tese macro, ativos, níveis, viés) → acervo pesquisável`.
3. **Dashboard quant / métodos** — Wyckoff/Elliott/SMC como indicadores + sinais.

## Dados (APIs gratuitas, não precisa tempo real)

| Dado | Fonte |
|------|-------|
| Índices mundiais, commodities, FX, ações US, VIX | `yfinance` (Yahoo Finance) |
| Ativos BR (Ibov, PETR4, VALE3) | `yfinance` (`.SA`, `^BVSP`) ou `brapi.dev` |
| Macro / Treasuries (inflação, yields) | FRED (Fed) + `yfinance ^TNX` |
| Selic / curva DI | API aberta do Banco Central (séries SGS) |

## Estrutura

```
rr-quant/
├── README.md                 este arquivo
├── CLAUDE.md                 contexto pro Claude Code trabalhar aqui
├── pyproject.toml            deps (yfinance, etc.)
├── data/
│   ├── transcricoes/         transcrições brutas dos vídeos (via markitdown)
│   └── raw/                  dumps de dados de mercado
├── docs/
│   └── metodo-rebecca-parriao.md   método destrinchado da leitura pré-mercado
└── src/rrquant/              código
```

## Status

🌱 Criado em 2026-07-16. Estrutura pronta; **6 dias de leitura pré-mercado da Rebecca
transcritos** e o método consolidado (união dos 6 dias, com frequências e tickers) em
`docs/metodo-rebecca-parriao.md`. Achados: ela **não cobre cripto**, o técnico dela começa
pela curva de **DI**, e a rotina abre por news+balanços+agenda. Código do primeiro
dashboard ainda não iniciado.
