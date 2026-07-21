from words import WORDS, normalize_title, segment_boundaries, segments_for_day, word_for_day


def test_dia_zero_retorna_primeira_palavra():
    assert word_for_day(0) == WORDS[0][0]


def test_ciclo_volta_ao_comeco():
    assert word_for_day(len(WORDS)) == word_for_day(0)


def test_todas_as_palavras_tem_entre_5_e_10_letras():
    assert all(5 <= len(palavra) <= 10 for palavra, _ in WORDS)


def test_segmentos_somam_o_tamanho_da_palavra():
    assert all(sum(segmentos) == len(palavra) for palavra, segmentos in WORDS)


def test_segments_for_day_bate_com_word_for_day():
    assert sum(segments_for_day(0)) == len(word_for_day(0))


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
