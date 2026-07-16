# rr-quant — contexto pro Claude Code

Projeto pessoal de trade data-driven do Ricardo. Visão geral e roadmap no `README.md`.

## O que é

Dashboard "quant" que reconstrói a **varredura macro diária de mercados** (inspirada
na leitura pré-mercado da Rebecca Parrião) com dados reais de API, e por cima aplica
métodos de análise técnica (Wyckoff, Elliott, Smart Money Concepts).

## Convenções

- **Idioma**: português (código em inglês; comentários/docs em pt-BR).
- **Python**: 3.14. Ambiente virtual em `.venv`. Deps no `pyproject.toml`.
- **Dados de mercado**: preferir APIs gratuitas sem tempo real (yfinance, FRED, BCB SGS,
  brapi). Dados EOD/atrasados são suficientes.
- **Transcrições**: extraídas com `markitdown "<url>" -o arquivo.md` (usa
  `youtube-transcript-api`). Nunca capturar stdout — grava direto no arquivo pra não
  corromper acentos. Ficam em `data/transcricoes/` no padrão
  `YYYY-MM-DD_criador_titulo.md`.

## Método da Rebecca (a estrutura que vira o dashboard)

Ver `docs/metodo-rebecca-parriao.md`. Resumo da espinha dorsal da leitura diária:
cadeia de correlação `petróleo → inflação → juros (Selic/DI) → ativos de risco + câmbio`,
varredura Ásia/Europa/US, commodities, moedas, renda fixa, ações-evento, e execução
via Elliott + suporte/resistência + fluxo/absorção (SMC) + VIX>20 como alerta.

## Estado

Só documentação + transcrição de exemplo por enquanto. Sem código ainda. Próximo passo
provável: POC do snapshot diário de mercados via yfinance.
