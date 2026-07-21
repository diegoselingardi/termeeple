import unicodedata
from datetime import date

# Cada entrada é (palavra_normalizada, tamanhos_dos_segmentos_originais).
# Os segmentos marcam onde havia espaço no nome original
# (ex.: "Blue Lagoon" -> ("BLUELAGOON", (4, 6))), usados só pra desenhar
# uma quebra visual no tabuleiro -- o palpite continua sendo só as letras.
WORDS: list[tuple[str, tuple[int, ...]]] = [
    ("TURNO", (5,)),
    ("DADOS", (5,)),
    ("REGRA", (5,)),
    ("CARTA", (5,)),
    ("TORRE", (5,)),
    ("BINGO", (5,)),
    ("XEQUE", (5,)),
    ("FICHA", (5,)),
    ("RONDA", (5,)),
    ("MOEDA", (5,)),
    ("SORTE", (5,)),
    ("DUELO", (5,)),
    ("PEÇAS", (5,)),
    ("GRUPO", (5,)),
    ("TIMES", (5,)),
    ("DAMAS", (5,)),
    ("TROCA", (5,)),
    ("ALVOS", (5,)),
    ("TRUCO", (5,)),
    ("MESAS", (5,)),
    ("PONTO", (5,)),
    ("LADOS", (5,)),
]

LAUNCH_DATE = date(2026, 7, 7)


def today_index():
    data_atual = date.today() - LAUNCH_DATE
    return data_atual.days


def word_for_day(day_index):
    palavra_index = day_index % len(WORDS)
    return WORDS[palavra_index][0]


def segments_for_day(day_index):
    palavra_index = day_index % len(WORDS)
    return WORDS[palavra_index][1]


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
