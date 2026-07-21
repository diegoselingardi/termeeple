from datetime import date

WORDS: list[str] = [
    "TURNO",
    "DADOS",
    "REGRA",
    "CARTA",
    "TORRE",
    "BINGO",
    "XEQUE",
    "FICHA",
    "RONDA",
    "MOEDA",
    "SORTE",
    "DUELO",
    "PEÇAS",
    "GRUPO",
    "TIMES",
    "DAMAS",
    "TROCA",
    "ALVOS",
    "TRUCO",
    "MESAS",
    "PONTO",
    "LADOS",
]

LAUNCH_DATE = date(2026, 7, 7)


def today_index():
    data_atual = date.today() - LAUNCH_DATE
    return data_atual.days


def word_for_day(day_index):
    palavra_index = day_index % len(WORDS)
    return WORDS[palavra_index]
