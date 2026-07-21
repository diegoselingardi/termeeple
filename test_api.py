"""Testes da API (main.py)."""

import pytest
from fastapi.testclient import TestClient

import main
from words import WORDS

DIA_FIXO = 0
PALAVRA_DO_DIA = WORDS[DIA_FIXO]  # "TURNO"

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

def test_esgotar_tentativas_termina_o_jogo_e_revela(client):
    for _ in range(main.MAX_ATTEMPTS):
        resposta = client.post("/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO})

    corpo = resposta.json()
    assert corpo["is_game_over"] is True
    assert corpo["revealed_word"] == PALAVRA_DO_DIA
    assert corpo["attempt_number"] == main.MAX_ATTEMPTS

def test_tentativa_alem_do_limite_e_bloqueada(client):
    for _ in range(main.MAX_ATTEMPTS):
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

    for _ in range(main.MAX_ATTEMPTS):
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