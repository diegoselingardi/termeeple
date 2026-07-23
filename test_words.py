from words import (
    WORDS_COMPOSTO,
    WORDS_DIFICIL,
    WORDS_PADRAO,
    normalize_title,
    segment_boundaries,
    segments_for_day,
    word_for_day,
)


def test_dia_zero_retorna_primeira_palavra():
    assert word_for_day(0, WORDS_PADRAO) == WORDS_PADRAO[0][0]


def test_ciclo_volta_ao_comeco():
    assert word_for_day(len(WORDS_PADRAO), WORDS_PADRAO) == word_for_day(0, WORDS_PADRAO)


def test_palavras_padrao_tem_5_ou_6_letras():
    assert all(5 <= len(palavra) <= 6 for palavra, _ in WORDS_PADRAO)


def test_palavras_dificil_tem_7_a_10_letras():
    assert all(7 <= len(palavra) <= 10 for palavra, _ in WORDS_DIFICIL)


def test_palavras_composto_tem_mais_de_um_segmento():
    assert all(len(segmentos) > 1 for _, segmentos in WORDS_COMPOSTO)


def test_segmentos_somam_o_tamanho_da_palavra():
    todas = (*WORDS_PADRAO, *WORDS_DIFICIL, *WORDS_COMPOSTO)
    assert all(sum(segmentos) == len(palavra) for palavra, segmentos in todas)


def test_segments_for_day_bate_com_word_for_day():
    assert sum(segments_for_day(0, WORDS_PADRAO)) == len(word_for_day(0, WORDS_PADRAO))


def test_normalize_title_remove_espaco_e_deixa_maiusculo():
    assert normalize_title("Blue Lagoon") == ("BLUELAGOON", (4, 6))


def test_normalize_title_mantem_ce_cedilha():
    assert normalize_title("Peças") == ("PEÇAS", (5,))


def test_normalize_title_remove_outros_acentos():
    assert normalize_title("Àrea Éxtra Órbita") == ("AREAEXTRAORBITA", (4, 5, 6))


def test_normalize_title_remove_numeros_e_pontuacao():
    assert normalize_title("7 Wonders: Duel!") == ("WONDERSDUEL", (7, 4))


def test_segment_boundaries_marca_inicio_de_cada_segmento_exceto_o_primeiro():
    assert segment_boundaries((4, 6)) == {4}
    assert segment_boundaries((5,)) == set()
    assert segment_boundaries((3, 3, 4)) == {3, 6}
