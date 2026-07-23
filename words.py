import unicodedata
from datetime import date

# Cada entrada é (palavra_normalizada, tamanhos_dos_segmentos_originais, link_da_ludopedia).
# Os segmentos marcam onde havia espaço no nome original
# (ex.: "Blue Lagoon" -> ("BLUELAGOON", (4, 6), link)), usados só pra desenhar
# uma quebra visual no tabuleiro -- o palpite continua sendo só as letras.
# O link é None nas palavras genéricas (não correspondem a um jogo real da Ludopedia)
# e só é preenchido nas palavras importadas via scripts/fetch_ludopedia_words.py --
# mostrado ao jogador quando ele acerta.
#
# Três listas independentes, uma por modo de jogo (Padrão/Difícil/Composto) -- cada
# modo cicla só pela sua própria lista, sem misturar palavras entre modos.
WORDS_PADRAO: list[tuple[str, tuple[int, ...], str | None]] = [
    ("TURNO", (5,), None),
    ("DADOS", (5,), None),
    ("REGRA", (5,), None),
    ("CARTA", (5,), None),
    ("TORRE", (5,), None),
    ("BINGO", (5,), None),
    ("XEQUE", (5,), None),
    ("FICHA", (5,), None),
    ("RONDA", (5,), None),
    ("MOEDA", (5,), None),
    ("SORTE", (5,), None),
    ("DUELO", (5,), None),
    ("PEÇAS", (5,), None),
    ("GRUPO", (5,), None),
    ("TIMES", (5,), None),
    ("DAMAS", (5,), None),
    ("TROCA", (5,), None),
    ("ALVOS", (5,), None),
    ("TRUCO", (5,), None),
    ("MESAS", (5,), None),
    ("PONTO", (5,), None),
    ("LADOS", (5,), None),
]

# 7-10 letras, sem espaço -- ainda sem curadoria (aguardando import da Ludopedia).
WORDS_DIFICIL: list[tuple[str, tuple[int, ...], str | None]] = []

# 5-10 letras, só nomes que tinham espaço originalmente -- ainda sem curadoria.
WORDS_COMPOSTO: list[tuple[str, tuple[int, ...], str | None]] = []

LAUNCH_DATE = date(2026, 7, 7)


def today_index():
    data_atual = date.today() - LAUNCH_DATE
    return data_atual.days


def word_for_day(day_index, palavras):
    palavra_index = day_index % len(palavras)
    return palavras[palavra_index][0]


def segments_for_day(day_index, palavras):
    palavra_index = day_index % len(palavras)
    return palavras[palavra_index][1]


def link_for_day(day_index, palavras):
    palavra_index = day_index % len(palavras)
    return palavras[palavra_index][2]


def segment_boundaries(segments):
    """Índices de coluna (0-based) onde começa um novo segmento, exceto o primeiro."""
    limites = set()
    posicao = 0
    for tamanho in segments[:-1]:
        posicao += tamanho
        limites.add(posicao)
    return limites


def _normalize_chars(text: str) -> str:
    resultado = []
    for letra in text.upper():
        if letra == "Ç":
            resultado.append(letra)
            continue
        base = "".join(
            char for char in unicodedata.normalize("NFKD", letra) if not unicodedata.combining(char)
        )
        if base.isalpha():
            resultado.append(base.upper())
    return "".join(resultado)


def normalize_title(name: str) -> tuple[str, tuple[int, ...]]:
    """Converte um nome de jogo em (palavra_valida_pro_tabuleiro, tamanhos_dos_segmentos).
    Maiúsculas, sem espaço/pontuação/número, mantendo Ç (não é dobrável em C). Cada palavra
    separada por espaço no nome original vira um segmento -- usado só pra exibição."""
    segmentos = []
    partes = []
    for pedaco in name.split():
        normalizado = _normalize_chars(pedaco)
        if normalizado:
            partes.append(normalizado)
            segmentos.append(len(normalizado))
    return "".join(partes), tuple(segmentos)
