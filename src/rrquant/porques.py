"""Base de conhecimento — o "porquê" de cada informação.

Texto CONCEITUAL (mecanismo de causa→efeito), não dado numérico. Explica a
importância de cada indicador/ativo/bloco pra leitura de mercado. É o material
que, mais à frente, embasa o teste de "como será o dia seguinte": deixa
explícito o encadeamento que um modelo preditivo tentaria capturar.
"""

# --- Por que cada BLOCO importa e em que ordem ler ---
BLOCO: dict[str, str] = {
    "Ásia / Oceania":
        "Primeiras bolsas a fechar no dia (fuso). Dão o humor inicial e antecipam a "
        "abertura de Europa e Brasil. Muito puxadas por China e commodities.",
    "Europa":
        "Fecham durante a nossa manhã. Refinam o humor global pouco antes da abertura de "
        "Nova York e do Ibovespa.",
    "EUA":
        "Maior mercado do mundo — dita o apetite a risco global. O fechamento de ontem + os "
        "futuros de hoje pautam a abertura do Ibov, que anda quase junto do Dow/S&P.",
    "Brasil":
        "O Ibovespa é o alvo da leitura. O EWZ (Ibov em dólar, negociado em NY) é a prévia "
        "dolarizada de como o estrangeiro está vendo o Brasil.",
    "Commodities":
        "O Brasil é exportador de commodities: petróleo (Petrobras) e minério/metais (Vale) "
        "são o maior peso do índice e movem a balança comercial e o real.",
    "Câmbio":
        "O dólar é o termômetro de risco dos emergentes. DXY forte (dólar forte no mundo) "
        "suga fluxo do Brasil; real fraco realimenta inflação e juros.",
    "Renda fixa / Volatilidade":
        "Os juros (Treasuries) definem o custo global do dinheiro; VIX/VXN medem o medo. "
        "VIX acima de 20 acende alerta de realização nas bolsas.",
    "Ações / eventos":
        "Ações-chave e eventos (balanços) que movem os índices: Petrobras e Vale no Brasil; "
        "bancos e techs (Nvidia) nos EUA.",
}

# --- Por que cada INDICADOR MACRO importa (keyed por nome do Indicador) ---
MACRO: dict[str, str] = {
    "CPI (cheio)":
        "Inflação ao consumidor dos EUA — o dado que mais move os mercados no mundo. Define "
        "o ritmo de juros do Fed, que por sua vez move dólar, Treasuries e apetite a risco.",
    "CPI núcleo":
        "CPI sem alimentos e energia (voláteis). O Fed olha mais o núcleo porque é a inflação "
        "'estrutural' — a que a política de juros de fato consegue combater.",
    "PPI":
        "Inflação ao produtor (preços na porta da fábrica). Antecede o CPI: pressão no PPI "
        "hoje tende a virar inflação ao consumidor amanhã.",
    "Desemprego":
        "O Fed tem mandato duplo (inflação + emprego). Desemprego baixo dá folga p/ manter "
        "juro alto; se dispara, força o Fed a cortar.",
    "Jobless claims":
        "Pedidos semanais de seguro-desemprego — termômetro de alta frequência do mercado de "
        "trabalho. Subindo = economia esfriando.",
    "Fed funds":
        "Juro básico dos EUA: o custo do dinheiro no mundo e o piso do retorno 'sem risco' "
        "global. Juro alto lá suga capital dos emergentes (Brasil incluso).",
    "Selic meta":
        "Taxa básica de juros do Brasil (Copom). Ancora toda a curva de juros (DI). Juro alto "
        "atrai capital e segura o real, mas encarece o crédito e desvia fluxo da bolsa p/ a "
        "renda fixa — é o principal fator da leitura de índice e dólar.",
    "CDI":
        "Juro do interbancário, colado na Selic. É o custo de oportunidade de todo "
        "investimento no país — o famoso 'bater o CDI'.",
    "IPCA":
        "Inflação oficial do Brasil. Comparada à meta (3% ±1,5) dita se o Banco Central sobe "
        "ou corta a Selic. É o gatilho da política de juros.",
    "IPCA-15":
        "Prévia do IPCA (coletada por volta do meio do mês). Antecipa a tendência de preços "
        "antes do índice cheio.",
}

# --- Por que cada COMMODITY importa + leitura de 3 estados (alta / de lado / queda) ---
COMMODITY: dict[str, dict[str, str]] = {
    "BZ=F": {
        "titulo": "Petróleo (Brent)",
        "importancia":
            "Preço internacional do petróleo. Move a inflação global (combustível, frete) e "
            "é o principal driver da Petrobras e de todo o setor de energia.",
        "alta": "Em alta: pressiona a inflação e favorece Petrobras e petrolíferas; se for "
                "choque de oferta (OPEP+ ou geopolítica), pode assustar os juros.",
        "lado": "De lado: oferta (OPEP+) e demanda equilibradas, sem choque geopolítico novo "
                "— inflação de energia neutra e sem gatilho fresco p/ Petrobras.",
        "queda": "Em queda: alivia a inflação (bom p/ juros), mas pesa nas petrolíferas.",
    },
    "HG=F": {
        "titulo": "Cobre (Dr. Copper)",
        "importancia":
            "Metal industrial presente em tudo (construção, eletrônicos, energia). Apelidado "
            "'Dr. Copper' porque a demanda por ele antecipa o crescimento econômico global.",
        "alta": "Em alta: sinaliza expectativa de crescimento — favorável a mineração (Vale) "
                "e a ativos de emergentes.",
        "lado": "De lado: demanda global sem sinal claro de aceleração nem de freada.",
        "queda": "Em queda: sugere desaceleração da demanda mundial — vento contra Vale e "
                 "commodities.",
    },
    "GC=F": {
        "titulo": "Ouro",
        "importancia":
            "Reserva de valor e refúgio clássico. Não paga juro, então brilha quando há medo, "
            "inflação alta ou juro real baixo (o custo de oportunidade de segurá-lo cai).",
        "alta": "Em alta: busca por proteção / hedge — costuma indicar aversão a risco no "
                "mercado.",
        "lado": "De lado: sem estresse novo e sem alívio — investidor nem corre p/ proteção "
                "nem a abandona.",
        "queda": "Em queda: apetite a risco maior, ou dólar/juro real subindo e tirando o "
                 "brilho do metal.",
    },
    "SI=F": {
        "titulo": "Prata",
        "importancia":
            "Metade refúgio (como o ouro), metade industrial (painel solar, eletrônicos). "
            "Costuma amplificar os movimentos do ouro.",
        "alta": "Em alta: refúgio + demanda industrial firme puxando junto.",
        "lado": "De lado: sem catalisador nem no lado refúgio nem no industrial.",
        "queda": "Em queda: enfraquece os dois lados (proteção e indústria) ao mesmo tempo.",
    },
    "PLPA": {
        "titulo": "Platina / Paládio",
        "importancia":
            "Usados em catalisadores de veículos. Funcionam como proxy da indústria "
            "automotiva e do ciclo industrial.",
        "alta": "Em alta: demanda industrial/automotiva firme.",
        "lado": "De lado: indústria em ritmo estável, sem novidade.",
        "queda": "Em queda: sinal de indústria e setor automotivo mais fracos.",
    },
}


def estado(v: float, limiar: float = 0.2) -> str:
    """Classifica a variação em 'alta' / 'lado' / 'queda'."""
    if abs(v) < limiar:
        return "lado"
    return "alta" if v > 0 else "queda"
