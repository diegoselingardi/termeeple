"""Testes da API (main.py)."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

import main
import words
from words import WORDS_PADRAO

DIA_FIXO = 0
PALAVRA_DO_DIA = WORDS_PADRAO[DIA_FIXO][0]  # "TURNO"
MAX_ATTEMPTS_PADRAO = main.MODOS["padrao"]["max_attempts"]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "today_index", lambda: DIA_FIXO)
    main.limiter.reset()  # reseta contadores de limite de taxa entre testes
    return TestClient(main.app)


def test_state_retorna_o_dia_fixado(client):
    resposta = client.get("/api/state")
    assert resposta.status_code == 200
    assert resposta.json()["day_index"] == DIA_FIXO


def test_guess_com_day_index_desatualizado_e_rejeitado(client):
    resposta = client.post("/api/guess", json={"guess": "DADOS", "day_index": DIA_FIXO + 1})
    assert resposta.status_code == 409


def test_guess_com_tamanho_invalido_e_rejeitado(client):
    resposta = client.post("/api/guess", json={"guess": "AB", "day_index": DIA_FIXO})
    assert resposta.status_code == 422


def test_guess_com_caracteres_invalidos_e_rejeitado(client):
    resposta = client.post("/api/guess", json={"guess": "12345", "day_index": DIA_FIXO})
    assert resposta.status_code == 422


def test_acertar_a_palavra_termina_o_jogo_e_revela(client):
    resposta = client.post("/api/guess", json={"guess": PALAVRA_DO_DIA, "day_index": DIA_FIXO})
    corpo = resposta.json()
    assert corpo["is_win"] is True
    assert corpo["is_game_over"] is True
    assert corpo["revealed_word"] == PALAVRA_DO_DIA
    # palavras genéricas (WORDS_PADRAO) não correspondem a um jogo real -- sem link
    assert corpo["ludopedia_link"] is None


def test_esgotar_tentativas_termina_o_jogo_e_revela(client):
    for _ in range(MAX_ATTEMPTS_PADRAO):
        resposta = client.post("/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO})

    corpo = resposta.json()
    assert corpo["is_game_over"] is True
    assert corpo["revealed_word"] == PALAVRA_DO_DIA
    assert corpo["attempt_number"] == MAX_ATTEMPTS_PADRAO


def test_tentativa_alem_do_limite_e_bloqueada(client):
    for _ in range(MAX_ATTEMPTS_PADRAO):
        client.post("/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO})

    resposta_extra = client.post("/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO})
    assert resposta_extra.status_code == 400


def test_cliente_nao_consegue_forjar_numero_de_tentativa(client):
    """Regressão do bug de segurança original: o servidor precisa ignorar
    qualquer campo attempt_number vindo do cliente e contar sozinho, via sessão."""
    resposta = client.post(
        "/api/guess",
        json={"guess": "MOEDA", "day_index": DIA_FIXO, "attempt_number": 6},
    )
    corpo = resposta.json()
    # mesmo mandando attempt_number: 6, o servidor trata como a 1a tentativa real
    assert corpo["attempt_number"] == 1
    assert corpo["is_game_over"] is False
    assert corpo["revealed_word"] is None


def test_sessoes_diferentes_nao_compartilham_tentativas(monkeypatch):
    monkeypatch.setattr(main, "today_index", lambda: DIA_FIXO)
    main.limiter.reset()  # reseta contadores de limite de taxa entre testes
    cliente_a = TestClient(main.app)
    cliente_b = TestClient(main.app)

    for _ in range(MAX_ATTEMPTS_PADRAO):
        cliente_a.post("/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO})

    # cliente_a já esgotou; cliente_b, com cookies próprios, deve começar do zero
    resposta_b = cliente_b.post("/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO})
    assert resposta_b.status_code == 200
    assert resposta_b.json()["attempt_number"] == 1


def test_rate_limit_bloqueia_excesso_de_requisicoes(client):
    limite = 20
    for _ in range(limite):
        client.post("/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO})

    resposta_extra = client.post("/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO})
    assert resposta_extra.status_code == 429


PALAVRA_LONGA = "BLUELAGOON"  # 10 letras, não faz parte de WORDS_PADRAO -- só pra testar tamanho
SEGMENTOS_PALAVRA_LONGA = (4, 6)  # "BLUE" + "LAGOON"


@pytest.fixture
def client_palavra_longa(monkeypatch):
    monkeypatch.setattr(main, "today_index", lambda: DIA_FIXO)
    monkeypatch.setattr(main, "word_for_day", lambda dia, palavras: PALAVRA_LONGA)
    monkeypatch.setattr(main, "segments_for_day", lambda dia, palavras: SEGMENTOS_PALAVRA_LONGA)
    main.limiter.reset()
    return TestClient(main.app)


def test_state_reflete_tamanho_da_palavra_do_dia(client_palavra_longa):
    resposta = client_palavra_longa.get("/api/state")
    assert resposta.json()["word_length"] == len(PALAVRA_LONGA)


def test_pagina_inicial_reflete_tamanho_da_palavra_do_dia(client_palavra_longa):
    resposta = client_palavra_longa.get("/")
    assert f'data-word-length="{len(PALAVRA_LONGA)}"' in resposta.text


def test_guess_do_tamanho_da_palavra_longa_e_aceito(client_palavra_longa):
    resposta = client_palavra_longa.post(
        "/api/guess", json={"guess": PALAVRA_LONGA, "day_index": DIA_FIXO}
    )
    assert resposta.status_code == 200
    assert resposta.json()["is_win"] is True


def test_guess_de_5_letras_e_rejeitado_quando_palavra_do_dia_tem_10(client_palavra_longa):
    resposta = client_palavra_longa.post(
        "/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO}
    )
    assert resposta.status_code == 422


def test_pagina_inicial_marca_quebra_visual_no_limite_do_segmento(client_palavra_longa):
    resposta = client_palavra_longa.get("/")
    assert 'id="tile-0-4"' in resposta.text
    assert 'class="tile tile--group-start" id="tile-0-4"' in resposta.text
    assert 'class="tile tile--group-start" id="tile-0-3"' not in resposta.text


# ---- Modos (Difícil/Composto): rotas próprias, sessão isolada da do Padrão ----

LINK_TESTE_DIFICIL = "https://ludopedia.com.br/jogo/testando"
PALAVRA_TESTE_DIFICIL = ("TESTANDO", (8,), LINK_TESTE_DIFICIL)  # 8 letras, só pro teste


@pytest.fixture
def client_dois_modos(monkeypatch):
    monkeypatch.setattr(main, "today_index", lambda: DIA_FIXO)
    main.limiter.reset()
    main.MODOS["dificil"]["palavras"].append(PALAVRA_TESTE_DIFICIL)
    try:
        yield TestClient(main.app)
    finally:
        main.MODOS["dificil"]["palavras"].remove(PALAVRA_TESTE_DIFICIL)


def test_modo_dificil_state_reflete_sua_propria_palavra(client_dois_modos):
    resposta = client_dois_modos.get("/api/dificil/state")
    assert resposta.status_code == 200
    assert resposta.json()["word_length"] == len(PALAVRA_TESTE_DIFICIL[0])


def test_tentativas_nao_vazam_entre_modos(client_dois_modos):
    for _ in range(MAX_ATTEMPTS_PADRAO):
        client_dois_modos.post("/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO})

    # esgotou as tentativas do Padrão; Difícil, mesmo dia e mesma sessão, começa do zero
    resposta_dificil = client_dois_modos.post(
        "/api/dificil/guess", json={"guess": PALAVRA_TESTE_DIFICIL[0], "day_index": DIA_FIXO}
    )
    assert resposta_dificil.status_code == 200
    assert resposta_dificil.json()["attempt_number"] == 1


def test_ludopedia_link_aparece_so_quando_acerta(client_dois_modos):
    resposta_errada = client_dois_modos.post(
        "/api/dificil/guess", json={"guess": "PERDENDO", "day_index": DIA_FIXO}
    )
    assert resposta_errada.json()["ludopedia_link"] is None

    resposta_certa = client_dois_modos.post(
        "/api/dificil/guess", json={"guess": PALAVRA_TESTE_DIFICIL[0], "day_index": DIA_FIXO}
    )
    assert resposta_certa.json()["is_win"] is True
    assert resposta_certa.json()["ludopedia_link"] == LINK_TESTE_DIFICIL


def test_patrocinio_sobrescreve_padrao_mas_nao_vaza_pro_dificil(client_dois_modos, monkeypatch):
    data_hoje = words.LAUNCH_DATE + timedelta(days=DIA_FIXO)
    entrada_patrocinada = ("PATROCINADA", (11,), "https://ludopedia.com.br/jogo/patrocinada")
    monkeypatch.setitem(words.SPONSORED_WORDS, data_hoje, entrada_patrocinada)

    # Padrão passa a jogar a palavra patrocinada, não mais a da lista normal (WORDS_PADRAO)
    resposta_padrao = client_dois_modos.post(
        "/api/guess", json={"guess": "PATROCINADA", "day_index": DIA_FIXO}
    )
    assert resposta_padrao.status_code == 200
    assert resposta_padrao.json()["is_win"] is True

    # Difícil não é patrocinável -- continua com sua própria palavra normalmente
    resposta_dificil = client_dois_modos.post(
        "/api/dificil/guess", json={"guess": PALAVRA_TESTE_DIFICIL[0], "day_index": DIA_FIXO}
    )
    assert resposta_dificil.status_code == 200
    assert resposta_dificil.json()["is_win"] is True


def test_modo_sem_palavras_cadastradas_mostra_aviso_na_pagina():
    cliente = TestClient(main.app)
    resposta = cliente.get("/composto")
    assert resposta.status_code == 200
    assert "ainda não tem palavras cadastradas" in resposta.text


def test_modo_sem_palavras_cadastradas_bloqueia_api():
    cliente = TestClient(main.app)
    assert cliente.get("/api/composto/state").status_code == 503
    resposta = cliente.post("/api/composto/guess", json={"guess": "TESTE", "day_index": 0})
    assert resposta.status_code == 503
