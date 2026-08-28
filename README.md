# rr-quant

Dashboard quant pessoal. Monta, antes de cada pregão, um retrato objetivo do mercado a partir de dados públicos, e me diz não só o número, mas por que ele importa.

Construí para uso próprio, porque decidir por leitura de gráfico e sensação não estava funcionando para mim. A ideia é simples: se a decisão vai ser discricionária de qualquer jeito, que pelo menos parta de um panorama montado sempre da mesma forma, sem eu escolher o que olhar no dia.

Roda com dados de fechamento, sem tempo real e sem chave de API paga.

## O que ele faz

**Snapshot de 46 ativos.** Índices mundiais, commodities, câmbio, juros e Treasuries, VIX e VXN, e ações brasileiras. Coleta via `yfinance` e monta um HTML por bloco com a variação do dia.

**Camada de leitura.** Interpreta os números em vez de só listá-los:

- Regime do dia, entre risk-on, risk-off e misto, por volatilidade, amplitude das bolsas e comportamento dos ativos de proteção.
- Cadeia de correlação, com a leitura de cada elo: petróleo para Petrobras, metais para Vale, juro global para apetite a risco, DXY para real e emergentes.
- Probabilidades condicionais históricas sobre dois anos, do tipo "quando Ásia, Europa e S&P sobem, o Ibovespa subiu em X% dos dias", sempre com a taxa-base ao lado para o número não enganar.
- Read-through de commodities em três estados, alta, lado e queda, porque "por que o Brent está parado" também é informação.

**Camada macro.** Inflação e juros por API pública sem chave: FRED para CPI, núcleo, PPI, desemprego e Fed funds, e o SGS do Banco Central para Selic, CDI, IPCA e IPCA-15. Calcula o juro real e fecha o elo entre inflação e juros da cadeia de correlação.

**Placar do Ibovespa.** Estimativa da probabilidade de o índice fechar em alta no próximo pregão, por regressão logística sobre as variáveis que antecedem a abertura: Ásia e Europa do dia, fechamento da véspera em Nova York e DXY, todas defasadas para não usar informação que ainda não existia no momento da decisão.

A acurácia reportada é fora da amostra, com corte cronológico, e hoje fica perto de 54%. O ganho sobre a taxa-base é pequeno. O número aparece com essa ressalva no próprio dashboard.

**Histórico walk-forward.** Reconstrói dia a dia a probabilidade que o placar teria dado, cada dia previsto por um modelo treinado só com o passado. É o primeiro backtest de verdade do projeto, e existe porque a primeira versão do placar marcava 55% de acerto e caiu para 48,5% quando respeitei o relógio dos dados. Prefiro descobrir isso eu mesmo.

**Acessibilidade.** Toda variação é redundante, com cor, seta e sinal, nunca só cor. Há um botão que troca para uma paleta segura para daltonismo, com Okabe-Ito, e a escolha fica salva no navegador.

## Como rodar

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e .
.venv/Scripts/python -m rrquant            # gera output/dashboard.html
.venv/Scripts/python -m rrquant --abrir    # gera e abre no navegador
```

## Estrutura

```
rr-quant/
├── src/rrquant/
│   ├── tickers.py     catálogo de ativos por bloco
│   ├── collect.py     coleta e variação via yfinance
│   ├── analyze.py     regime, correlações, probabilidades, placar
│   ├── macro.py       FRED e BCB SGS
│   ├── porques.py     base conceitual do "por que isso importa"
│   ├── charts.py      gráficos SVG inline
│   ├── report.py      montagem do HTML
│   └── cli.py         entrada
├── docs/              método e notas
└── output/            dashboard gerado
```

Os gráficos são SVG e CSS inline, sem dependência de biblioteca, para o dashboard abrir offline.

## Fontes de dados

| Dado | Fonte |
|---|---|
| Índices mundiais, commodities, FX, ações, VIX | yfinance |
| Ativos brasileiros | yfinance com sufixo `.SA` |
| Macro e Treasuries dos EUA | FRED |
| Selic, CDI, IPCA | API de séries SGS do Banco Central |

## Escolhas técnicas

Usei regressão logística escrita direto em numpy em vez de `scikit-learn` ou `statsmodels`, porque no Python 3.14 essas bibliotecas nem sempre têm wheel disponível e eu não queria uma dependência pesada por um modelo de cinco variáveis. Migrar vale a pena quando eu quiser os diagnósticos que elas trazem prontos.

## Próximos passos

- Migrar o placar para `statsmodels` ou `scikit-learn`, pelos diagnósticos.
- Curva de DI da B3 e CME FedWatch.
- Variação overnight.
- Backtest completo, com retorno e não só taxa de acerto.
- Reorganizar o front-end, que cresceu sem plano.

## Aviso

Ferramenta pessoal de estudo. Nada aqui é recomendação de investimento. As estatísticas descrevem co-movimento histórico, não previsão, e o próprio dashboard rotula assim.
