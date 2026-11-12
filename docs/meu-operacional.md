# Meu operacional

Regras de como eu opero mini-índice (WIN) no day trade. O rr-quant existe para servir a este
documento: a leitura da manhã responde se vale operar e para que lado, o mapa de liquidez mostra
onde agir, e o backtest diz se cada regra se paga no histórico. Regra que não passar no backtest
sai daqui.

Em resumo: **poucos trades, risco fixo, alvo de pelo menos 3 vezes o risco, e só entrar quando
houver lugar, evento, volume e uma correção com cara de correção ao mesmo tempo.**

---

## 1. Risco (regras duras, valem antes de tudo)

| Regra | Valor |
|---|---|
| Risco por trade (**R**) | stop técnico de **no máximo 300 pontos** (alvo de 200 a 300) |
| Retorno mínimo | **alvo ≥ 3R**. Setup com RR abaixo de 3 não existe |
| Trades por dia | **no máximo 3** |
| Parada do dia | **depois de 2 stops, acabou o dia** |
| Contratos | **fixos**, decididos antes do pregão. Nunca aumentar a mão pra recuperar |
| Parcial | **nenhuma antes de 3R** |
| Saídas possíveis | **stop**, **0×0 técnico** (só quando a regra manda) ou **alvo**. Sem meio-termo |

**A conta no WIN** (R$ 0,20 por ponto por contrato):

| Stop | Perda por contrato | Alvo mínimo (3R) | Ganho por contrato |
|---|---|---|---|
| 200 pts | R$ 40 | 600 pts | R$ 120 |
| 300 pts | R$ 60 | 900 pts | R$ 180 |

- **Pior dia possível:** 2 stops de 300 pts = **600 pts × contratos**. Com 1 contrato, R$ 120.
- **Ponto de equilíbrio com 3:1:** 25% de acerto (1 alvo paga 3 stops).
- O stop vem da estrutura (abaixo do fundo que originou a entrada), não de um número escolhido.
  Se a estrutura pede mais de 300 pts, **não opera** ou desce para o tempo gráfico menor e espera
  um stop técnico que caiba.
- Depois de um stop, só volta a operar se o contexto continuar autorizando. O limite diário é um
  teto, não uma meta.

---

## 2. A leitura da manhã: vale operar? para que lado?

Feita antes da abertura do WIN (9h), com o dashboard.

1. **Agenda do dia.** Payroll, Copom, FOMC, CPI, IPCA e afins viram **aviso** no topo. Não proíbem
   o trade, mas indicam horário de volatilidade e pedem cuidado com ordem pendurada.
2. **Cadeia macro**, sempre na mesma ordem:

   ```
   petróleo → inflação → juros (DI) → ativos de risco e câmbio
   ```

   - **Juros (DI) primeiro.** Curva fechando favorece alta do índice; abrindo favorece queda.
   - **Dólar global (DXY)** separa o movimento do dólar no mundo do movimento só do real.
   - **EUA:** fechamento e futuros (o Ibovespa anda mais perto do Dow que do Nasdaq). **EWZ** é a
     ponte entre o fechamento americano e o pregão daqui.
   - **Commodities:** minério (Vale) e petróleo (Petrobras) pesam no índice.
   - **VIX acima de 20** = alerta de realização.
3. **Viés do dia:** compra, venda ou neutro. O macro **só filtra o viés** (por exemplo: com juros
   abrindo forte, não procurar compra). Se o filtro melhora o resultado é uma hipótese a testar
   no backtest, não uma certeza.

---

## 3. Mapa de liquidez

Liquidez são stops concentrados. O stop de quem está comprado é uma ordem de venda, e é esse
combustível que o preço vai buscar. **Se eu não sei onde está a liquidez, eu sou a liquidez.**

Marcar antes do pregão, em ordem de importância:

| Nível | O que é |
|---|---|
| **PDH / PDL** | máxima e mínima do dia anterior |
| **PWH / PWL** | máxima e mínima da semana anterior |
| **PMH / PML** | máxima e mínima do mês anterior |
| **EQH / EQL** | topos ou fundos nivelados (dois no mesmo preço = o dobro de stops) |
| **BSL / SSL** | liquidez acima dos topos / abaixo dos fundos relevantes |
| **POC / VAH / VAL** | preço mais negociado e limites da área de valor do dia anterior |
| **Laterais** | faixas de acumulação/distribuição; o fundo da lateral costuma coincidir com PDL/PWL/PML |

Esses níveis servem para duas coisas: **lugar de entrada** (depois de varridos) e **alvo** (antes
de varridos).

**Só existem dois tipos de trade:**
1. **Trade para capturar liquidez:** o preço está abaixo do PDH e eu compro para buscá-lo.
2. **Trade depois da captura:** o preço varre o PDH, volta, faz pullback, e eu vendo.

**Sem captura de liquidez, não tem entrada.**

---

## 4. Tempos gráficos

| Função | Tempo gráfico |
|---|---|
| Lugar e alvo (macro) | **60 min** e **15 min** |
| Gatilho e stop (micro) | **5 min**, e **2 min** no Profit (**3 min** no TradingView grátis) |

A assimetria do 3:1 vem daqui: **o alvo é do macro, o stop é do micro.** Stop pequeno com alvo
de swing.

Na zona do macro, há dois jeitos de entrar:
1. **Pegar no toque:** ordem limitada no order block. Só quando o contexto já está muito claro.
2. **Esperar o evento:** CHoCH no micro + pullback. **Só lugar não basta, precisa de evento.**

**Fluxo alinhado** = CHoCH no macro e no micro, na mesma direção.

---

## 5. Estrutura: BOS, CHoCH e indução

- **BOS:** quebra a favor da tendência (continuidade).
- **CHoCH:** rompe o fundo (ou topo) que originou o último BOS (reversão).
- **Indução (IDM):** antes do movimento de verdade, o preço "finge que vai" e pega os stops de quem
  entrou cedo. Quebra de estrutura sem contexto é só indução.
  - **Fake BOS:** o preço rompe o topo como se fosse continuar, quem comprou o rompimento é stopado
    na volta. Minha compra entra embaixo, depois disso.
  - **Fake CHoCH:** o preço perde o fundo como se fosse virar, quem vendeu a quebra é stopado. Minha
    compra entra depois disso.
  - **Regra:** antes de abrir posição, já precisa ter havido uma indução. Sem indução, quem está
    sendo induzido sou eu.

### CHoCH válido × CHoCH falso

| | Válido | Falso (armadilha) |
|---|---|---|
| Impulso que rompe | **5 pernas**, ou uma barra de força muito grande | **3 pernas** (ABC), com sobreposição, rompe só de pavio |
| O que rompe | o fundo/topo **que originou o BOS** | não rompe esse fundo/topo |
| Volume na quebra | **crescente** | **decrescente**: invalida, mesmo com 5 pernas |
| Pullback | **ABC** (zigzag, flat ou reacumulação) até o discount | pullback impulsivo, em 5 pernas sem A e B antes: não compra |
| O que fazer | entra no pullback | não opera o pullback (pode até operar contra) |

> **5 pernas no pullback × 5 subondas na perna C.** São coisas diferentes. Um pullback que desce
> em 5 pernas direto, sem repique, é impulso contra mim: não compro. Já a perna **C de uma flat**
> desce em 5 subondas por definição (a flat é 3-3-5), e é no fim dela que eu compro. O que manda é
> haver **A e B antes**.

---

## 6. Premium e discount

Fibonacci traçado no **impulso inteiro**.

- **Compra só no discount:** retração de pelo menos 50%, de preferência **61,8% a 79%**.
- **Venda só no premium:** acima de 50% do movimento de baixa.
- Correção rasa (38,2% a 50%) só vale em **flat** ou **reacumulação**.
- Vale depois de CHoCH e depois de BOS.

---

## 6.1. Qualidade da correção (a parte que mais separa trade de stop)

**Impulso tem que ter cara de impulso, correção tem que ter cara de correção.** Lugar, gatilho e
discount certos não salvam uma correção ruim.

- **Chegada em linha reta** (o preço volta até a zona sem repique, rápido, com barras grandes):
  **não pego no toque.** Espero CHoCH no micro e pullback.
- **Chegada com relutância** (canal ou cunha descendente, "deriva", barras se sobrepondo): mostra
  que quem empurrava está fraco. Conta a favor.

### Flat (3-3-5)

A onda **A** é um ABC contra o movimento, a **B** é um ABC a favor e a **C** desce em **5
subondas** até o order block. É no fim da C que eu compro.

| Tipo | Topo da B × topo de origem | Fundo da C × fundo da A | Opero? |
|---|---|---|---|
| **Regular** | nivela (vira EQH: liquidez dupla de alvo) | rompe | sim |
| **Irregular** | rompe (fake BOS) | rompe (fake CHoCH) | **sim, a melhor**: induz os dois lados |
| **Interrompida** | rompe | não chega, para num OB | às vezes (rara) |
| **Clássica** | nivela | nivela | **nunca**: liquidez em cima e embaixo |

- **Flat × zigzag:** o zigzag (ABC simples) deixa só um topo como alvo. A flat deixa dois topos
  ou uma dupla indução. Zigzag só quando o movimento anterior foi muito forte.
- Se as 5 subondas da C saírem feias (sobrepostas, sem ritmo), **cancelo a ordem**.

### Canal, bandeira e cunha de continuação: regra dos 5 toques

Só pego no toque (ou no CHoCH) com **pelo menos 5 toques** somados nas bordas do canal. Com 4, o
preço tende a fazer mais um toque embaixo e a compra antecipada vira stop. Cada toque em cima
acumula liquidez; cada toque embaixo é uma captura.

---

## 7. Volume: esforço × resultado

Volume é esforço, preço é resultado.

- Para comprar o pullback de um CHoCH de alta, o volume **tinha que subir na quebra**.
- Barra bonita sem volume não é entrada.
- Exceção: **clímax** (pico de volume no fim de uma tendência) marca exaustão, não força.
- **Absorção sem agressão** não é gatilho. **Absorção seguida de agressão** é.

---

## 8. Laterais (acumulação e distribuição)

Ciclo: acumulação → alta → reacumulação → alta → distribuição → baixa → redistribuição → baixa.

- A lateral é a **causa**, a tendência é o **efeito**. Entrar na saída da lateral é estar no
  começo do movimento, por isso não faz sentido realizar a 1:1.
- **Melhor trade numa lateral:** o preço varre os últimos fundos (**spring**, com aumento de
  volume), faz CHoCH para cima e pullback. Alternativa: pullback depois que o preço sai da faixa.
- **Erro clássico:** vender o rompimento do fundo da lateral. Quase sempre é o spring.

**Fases do Wyckoff** (servem para acumulação, reacumulação, distribuição e redistribuição):

| Fase | Função |
|---|---|
| A | parar a tendência anterior |
| B | manipular os extremos (varre em cima e embaixo) |
| C | captura total de liquidez (spring na acumulação, UTAD na distribuição) |
| D e E | expansão e o pullback que eu opero |

- **Acumulação** e **distribuição** revertem a tendência. **Reacumulação** e **redistribuição**
  continuam.
- Nem toda lateral é flat. Uma lateral longa com fases é Wyckoff; a flat é uma correção de 3 ondas.
- O contexto decide o lado: com macro de alta, fase D e liquidez acima (PDH, PWH), um pullback
  em 5 subondas é compra, não venda.

---

## 9. Ondas (marcação manual)

O impulso tem **5 ondas** (1, 3 e 5 andam; 2 e 4 corrigem) e a correção tem **3** (A, B, C).

| Onda | O que acontece |
|---|---|
| 1 | sai da lateral e ninguém acredita |
| 2 | o medo volta |
| 3 | todo mundo vê; nunca é a mais curta |
| 4 | respiro e realização; lateral com topos nivelados costuma ser aqui |
| 5 | euforia; quem compra aqui compra esticado |

Correções que eu opero: **zigzag** (B faz topo menor), **flat** (B nivela ou rompe de leve o topo)
e **reacumulação**. A contagem também serve para **não** operar: mostra onde o trade seria stop.
Essa parte eu marco à mão; o rr-quant só aproxima (contagem de pernas).

---

## 10. O setup central (checklist)

Compra (a venda é o espelho):

| # | Confluência | Obrigatória? |
|---|---|---|
| 1 | **Captura de liquidez** antes: PDL, PWL, PML, EQL ou fundo de lateral varrido | sim |
| 2 | **CHoCH válido** no micro (5 pernas, rompe o fundo de origem) | sim |
| 3 | **Volume crescente** na quebra | sim |
| 4 | **Pullback corretivo** (ABC, flat ou reacumulação), nunca em linha reta | sim |
| 4a | **Indução** antes da entrada (fake BOS ou fake CHoCH) | sim |
| 4b | Correção do tipo **flat irregular ou regular** | soma |
| 5 | **Discount**: retração de 61,8% a 79% | sim |
| 6 | **Order block ou FVG** na zona da retração (o gatilho) | sim |
| 7 | POC ou área de valor na mesma zona | soma |
| 8 | Fluxo alinhado (CHoCH também no macro) | soma |
| 9 | Viés da manhã a favor | soma |
| — | **Alvo** na próxima liquidez do macro (PDH, PWH, BSL) a **≥ 3R** | sim |

- **Um único fator contra invalida.** Não importa quantas confluências somem.
- Os pesos das confluências que "somam" serão calibrados no backtest, não contados à mão.

---

## 11. Quando não operar

- Já foram 2 stops no dia, ou já foram 3 trades.
- Não houve captura de liquidez.
- O alvo até a próxima liquidez do macro não chega a 3R.
- O stop técnico passa de 300 pontos.
- O volume não confirma a quebra.
- Notícia forte nos próximos minutos (o aviso da agenda).
- Fora da janela que eu consigo acompanhar com atenção total (cerca de 1 hora).
- O preço chegou à zona em linha reta e ainda não houve CHoCH no micro.
- A correção é uma **flat clássica** (liquidez dos dois lados).
- Canal de continuação com menos de 5 toques.

---

## 12. O que o backtest precisa responder

Nenhuma regra acima foi testada ainda. O rr-quant vai medir, com custos:

1. **O setup central tem expectativa positiva em R?** Quantas ocorrências, taxa de acerto,
   expectativa por trade, pior sequência de perdas.
2. **Ele é melhor que entradas aleatórias** com o mesmo stop e alvo?
3. **Cada confluência ajuda?** Tirar uma de cada vez e ver o que muda (volume na quebra, discount,
   captura de liquidez, contagem de pernas).
4. **O filtro macro da manhã melhora o resultado** ou só reduz o número de trades?
5. **O alvo de 3R é alcançável no WIN** com stop de 200 a 300 pontos, dentro do horário que eu
   opero?
6. **O tipo de correção muda o resultado?** Flat irregular, flat regular, zigzag e chegada em
   linha reta, comparados em R por trade. (A aula afirma que a flat irregular é a melhor; é a
   hipótese a derrubar ou confirmar.)

Primeiro com dados do Ibovespa em 60 min (para montar o motor), depois com a série do WIN
exportada do Profit (para valer de verdade).
