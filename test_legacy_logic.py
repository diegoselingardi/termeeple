from game_logic import LetterStatus
from legacy_logic import (
    avaliar_letras,
    avaliar_tamanho,
    calcular_delta_moedas_letras,
    calcular_delta_moedas_letras_com_descobertas,
    calcular_delta_moedas_tamanho_com_descoberta,
)


def test_avaliar_tamanho_palpite_menor():
    mensagem, delta = avaliar_tamanho(3, 6)
    assert mensagem == "Palpite tem menos letras que a palavra do dia"
    assert delta == -1


def test_avaliar_tamanho_palpite_maior():
    mensagem, delta = avaliar_tamanho(8, 6)
    assert mensagem == "Palpite tem mais letras que a palavra do dia"
    assert delta == -1


def test_avaliar_tamanho_palpite_igual():
    mensagem, delta = avaliar_tamanho(6, 6)
    assert mensagem == "Palpite tem a mesma quantidade de letras que a palavra do dia"
    assert delta == 1


def test_avaliar_letras_mesmo_tamanho_funciona_como_evaluate_guess():
    resultado = avaliar_letras("XEGRA", "REGRA")
    letras_a = [item for item in resultado if item["letter"] == "A"]
    sinalizados = [item for item in letras_a if item["status"] != LetterStatus.ABSENT]
    assert len(sinalizados) == 1, (
        "REGRA só tem 1 'A' -- só um dos dois A's pode virar present/correct"
    )


def test_avaliar_letras_palpite_mais_curto_so_avalia_ate_o_proprio_tamanho():
    resultado = avaliar_letras("CAO", "COYOTE")
    assert len(resultado) == 3
    assert resultado[0] == {"letter": "C", "status": LetterStatus.CORRECT}
    assert resultado[1]["status"] == LetterStatus.ABSENT  # 'A' não existe em COYOTE
    assert resultado[2]["status"] == LetterStatus.PRESENT  # 'O' existe, posição errada


def test_avaliar_letras_palpite_mais_longo_sobra_sempre_ausente():
    # "COYOTES" tem 7 letras, a resposta "COYOTE" só tem 6 -- mesmo o "S" não
    # existindo em COYOTE, o ponto importante é que a letra extra (índice 6,
    # além do tamanho da resposta) é sempre marcada ausente, sem checar presença.
    resultado = avaliar_letras("COYOTES", "COYOTE")
    assert len(resultado) == 7
    assert all(item["status"] == LetterStatus.CORRECT for item in resultado[:6])
    assert resultado[6] == {"letter": "S", "status": LetterStatus.ABSENT}


def test_avaliar_letras_letra_extra_nao_e_contada_como_presente_mesmo_existindo_na_resposta():
    # "COYOTEC" -- o "C" extra no fim (índice 6) existe em COYOTE, mas como está
    # além do tamanho da resposta, tem que ser ausente, não presente.
    resultado = avaliar_letras("COYOTEC", "COYOTE")
    assert resultado[6] == {"letter": "C", "status": LetterStatus.ABSENT}


def test_calcular_delta_moedas_letras():
    avaliacao = [
        {"letter": "C", "status": LetterStatus.CORRECT},
        {"letter": "A", "status": LetterStatus.ABSENT},
        {"letter": "O", "status": LetterStatus.PRESENT},
    ]
    assert calcular_delta_moedas_letras(avaliacao) == 0  # +1 -1 +0


def test_calcular_delta_moedas_letras_com_descobertas_primeira_vez_rende_bonus():
    avaliacao = [
        {"letter": "C", "status": LetterStatus.CORRECT},
        {"letter": "A", "status": LetterStatus.ABSENT},
    ]
    delta, novas = calcular_delta_moedas_letras_com_descobertas(avaliacao, set())
    assert delta == 0  # +1 (posição 0 nova) -1 (ausente)
    assert novas == {0}


def test_calcular_delta_moedas_letras_com_descobertas_posicao_repetida_nao_rende():
    avaliacao = [
        {"letter": "C", "status": LetterStatus.CORRECT},
        {"letter": "A", "status": LetterStatus.ABSENT},
    ]
    # posição 0 já estava confirmada antes -- não rende bônus de novo, só a
    # penalidade da letra ausente continua valendo
    delta, novas = calcular_delta_moedas_letras_com_descobertas(avaliacao, {0})
    assert delta == -1
    assert novas == set()


def test_calcular_delta_moedas_tamanho_com_descoberta_primeira_vez_rende_bonus():
    assert calcular_delta_moedas_tamanho_com_descoberta(1, tamanho_ja_descoberto=False) == 1


def test_calcular_delta_moedas_tamanho_com_descoberta_repetido_nao_rende():
    assert calcular_delta_moedas_tamanho_com_descoberta(1, tamanho_ja_descoberto=True) == 0


def test_calcular_delta_moedas_tamanho_com_descoberta_errado_continua_penalizando():
    # tamanho errado nunca tem bônus pra "deduplicar" -- continua custando sempre,
    # independente de já ter sido tentado antes
    assert calcular_delta_moedas_tamanho_com_descoberta(-1, tamanho_ja_descoberto=True) == -1
