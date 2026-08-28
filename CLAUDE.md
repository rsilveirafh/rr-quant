# rr-quant — contexto pro Claude Code

Dashboard quant pessoal. Visão geral, o que faz e roadmap no `README.md`.

## O que é

Reconstrói uma varredura macro diária de mercados a partir de APIs públicas e, por cima
dos números, monta uma camada de leitura: regime do dia, cadeia de correlação,
probabilidades condicionais e um placar do Ibovespa por regressão logística.

## Convenções

- **Idioma**: português. Código em inglês, comentários e docs em pt-BR.
- **Python**: 3.14. Ambiente virtual em `.venv`, dependências no `pyproject.toml`.
- **Dados de mercado**: só API pública e gratuita, sem chave paga e sem tempo real
  (yfinance, FRED, BCB SGS, brapi). Dado de fechamento é suficiente.
- **Sem conteúdo de terceiros no repositório.** Transcrição, texto ou material de
  criador não entra em `data/` nem em `docs/`. O que vale é a estrutura destilada em
  `docs/metodo-leitura-pre-mercado.md`.
- **Nada de look-ahead.** Toda variável usada para prever o pregão seguinte precisa
  estar defasada para o instante da decisão. Validação sempre fora da amostra, com
  corte cronológico.
- **Estatística é descrição, não previsão.** Todo número exibido leva a taxa-base ao
  lado e o rótulo correspondente.

## Estrutura do método

`docs/metodo-leitura-pre-mercado.md` traz a espinha dorsal que vira modelo de dados:
cadeia de correlação `petróleo → inflação → juros (Selic/DI) → ativos de risco e câmbio`,
varredura Ásia, Europa e Estados Unidos, commodities, moedas, renda fixa e ações-evento.

## Estado

Frente do snapshot diário em produção: 46 ativos, camada de leitura, camada macro,
placar do Ibovespa e histórico walk-forward. Próximos passos no `README.md`.

O front-end cresceu sem plano e é a próxima reorganização prevista.
