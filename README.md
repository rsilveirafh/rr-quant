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

## Como rodar (frente 1 — snapshot diário)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e .   # ou: pip install yfinance pandas
.venv/Scripts/python -m rrquant            # gera output/dashboard.html
.venv/Scripts/python -m rrquant --abrir    # gera e abre no navegador
```

Código em `src/rrquant/`: `tickers.py` (catálogo por bloco), `collect.py` (fetch +
variação via yfinance), `report.py` (HTML), `cli.py` (entrada).

## Status

🌱 Criado em 2026-07-16.
- ✅ **6 dias de leitura pré-mercado transcritos** + método consolidado em
  `docs/metodo-rebecca-parriao.md` (achados: **não cobre cripto**, técnico começa pela
  curva de **DI**, rotina abre por news+balanços+agenda).
- ✅ **Frente 1 — snapshot diário**: coleta 46 ativos (índices mundiais, commodities,
  câmbio, juros, VIX/VXN, ações) via yfinance e gera dashboard HTML por bloco com variação
  do dia. Roda com dados EOD.
- ✅ **Camada de leitura (`analyze.py`)** — interpreta os números e mostra o *porquê*:
  - **Regime do dia** (risk-on / risk-off / misto) por volatilidade + amplitude das bolsas
    + ativos de proteção.
  - **Cadeia de correlação** (petróleo→Petrobras, metais→Vale, juros global→risco,
    DXY→real/emergentes) com leitura de cada elo.
  - **Probabilidades condicionais históricas** (2 anos): ex. "quando a Ásia/Europa/S&P/EWZ
    sobe, o Ibov sobe em X% dos dias" com taxa-base e lift.
  - **Correlações-chave** (Ibov×Dow/S&P/EWZ/Nikkei/DXY, Petrobras×Brent, Vale×Cobre).
  - Estatísticas rotuladas como **co-movimento histórico, não previsão**.
- ⏳ Próximo: macro via FRED/BCB + CME FedWatch; variação overnight (futuros); frente 2
  (extração das transcrições).
