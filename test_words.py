from words import word_for_day, WORDS

def test_dia_zero_retorna_primeira_palavra():
    assert word_for_day(0) == WORDS[0]

def test_ciclo_volta_ao_comeco():
    assert word_for_day(len(WORDS)) == word_for_day(0)