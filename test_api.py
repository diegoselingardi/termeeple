"""Testes da API (main.py)."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

import main
import words
from words import WORDS_PADRAO

DIA_FIXO = 0
PALAVRA_DO_DIA = WORDS_PADRAO[DIA_FIXO][0]
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
    monkeypatch.setattr(
        main, "entry_for_day", lambda dia, palavras: (PALAVRA_LONGA, SEGMENTOS_PALAVRA_LONGA, None)
    )
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
    """Isola o modo Difícil com uma lista de 1 palavra só, pra a palavra do dia ser
    sempre previsível independente de quantas palavras reais já foram curadas."""
    monkeypatch.setattr(main, "today_index", lambda: DIA_FIXO)
    main.limiter.reset()
    palavras_dificil = main.MODOS["dificil"]["palavras"]
    originais = list(palavras_dificil)
    palavras_dificil.clear()
    palavras_dificil.append(PALAVRA_TESTE_DIFICIL)
    try:
        yield TestClient(main.app)
    finally:
        palavras_dificil.clear()
        palavras_dificil.extend(originais)


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


def test_rate_limit_e_isolado_por_modo(client_dois_modos):
    """Regressão: as 3 rotas de guess (uma por modo) colidiam no mesmo registro
    interno do slowapi porque tinham o mesmo __name__, fazendo cada requisição
    contar 3x pro limite -- esgotar o rate limit do Padrão não pode bloquear
    o Difícil, que tem seu próprio contador."""
    ultima_resposta_padrao = None
    for _ in range(21):
        ultima_resposta_padrao = client_dois_modos.post(
            "/api/guess", json={"guess": "MOEDA", "day_index": DIA_FIXO}
        )
    assert ultima_resposta_padrao.status_code == 429

    resposta_dificil = client_dois_modos.post(
        "/api/dificil/guess", json={"guess": PALAVRA_TESTE_DIFICIL[0], "day_index": DIA_FIXO}
    )
    assert resposta_dificil.status_code != 429


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


@pytest.fixture
def composto_temporariamente_vazio():
    """Esvazia o modo Composto só durante o teste, pra simular o estado antes de
    qualquer curadoria -- restaura os dados reais depois, mesmo se o teste falhar."""
    palavras_composto = main.MODOS["composto"]["palavras"]
    originais = list(palavras_composto)
    palavras_composto.clear()
    try:
        yield
    finally:
        palavras_composto.extend(originais)


def test_modo_sem_palavras_cadastradas_mostra_aviso_na_pagina(composto_temporariamente_vazio):
    cliente = TestClient(main.app)
    resposta = cliente.get("/composto")
    assert resposta.status_code == 200
    assert "ainda não tem palavras cadastradas" in resposta.text


def test_modo_sem_palavras_cadastradas_bloqueia_api(composto_temporariamente_vazio):
    cliente = TestClient(main.app)
    assert cliente.get("/api/composto/state").status_code == 503
    resposta = cliente.post("/api/composto/guess", json={"guess": "TESTE", "day_index": 0})
    assert resposta.status_code == 503


def test_teclado_nao_mostra_ce_cedilha_quando_palavra_nao_tem():
    teclas = [tecla for linha in main.montar_teclado("BINGO") for tecla in linha]
    assert "Ç" not in teclas


def test_teclado_mostra_ce_cedilha_quando_palavra_tem():
    teclas = [tecla for linha in main.montar_teclado("LENÇOIS") for tecla in linha]
    assert "Ç" in teclas


# ---- Modo Legacy: palpite de qualquer tamanho, sem tentativas fixas, moedas ----

LINK_TESTE_LEGACY = "https://ludopedia.com.br/jogo/tuscany"
PALAVRA_TESTE_LEGACY = "TUSCANY"  # 7 letras, só pro teste (mesmo exemplo usado ao desenhar o modo)


@pytest.fixture
def client_legacy(monkeypatch):
    monkeypatch.setattr(main, "today_index", lambda: DIA_FIXO)
    monkeypatch.setattr(
        main,
        "entry_for_day",
        lambda dia, palavras: (PALAVRA_TESTE_LEGACY, (7,), LINK_TESTE_LEGACY),
    )
    main.limiter.reset()
    return TestClient(main.app)


def test_legacy_state_inicial(client_legacy):
    resposta = client_legacy.get("/api/legacy/state")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["coins"] == main.MOEDAS_INICIAIS
    assert corpo["is_win"] is False
    assert corpo["is_game_over"] is False
    assert corpo["revealed_word"] is None
    assert corpo["ludopedia_link"] is None


def test_legacy_guess_correto_vence_e_revela_palavra_e_link(client_legacy):
    resposta = client_legacy.post(
        "/api/legacy/guess", json={"guess": PALAVRA_TESTE_LEGACY, "day_index": DIA_FIXO}
    )
    corpo = resposta.json()
    assert corpo["is_win"] is True
    assert corpo["is_game_over"] is True
    assert corpo["revealed_word"] == PALAVRA_TESTE_LEGACY
    assert corpo["ludopedia_link"] == LINK_TESTE_LEGACY
    # o palpite vencedor também vem com a avaliação (tudo "correct"), pro
    # front-end poder desenhar essa tentativa no histórico, toda verde
    assert [item["letter"] for item in corpo["evaluation"]] == list(PALAVRA_TESTE_LEGACY)
    assert all(item["status"] == "correct" for item in corpo["evaluation"])


def test_legacy_moedas_somam_tamanho_certo_mais_letras_certas(client_legacy):
    # "TUSCANO" tem o mesmo tamanho de "TUSCANY", descoberto pela 1a vez (+1), e
    # acerta as 6 primeiras posições pela 1a vez (+6); só erra a última -- "O" não
    # sobra em nenhum outro lugar da resposta depois de consumidas as 6 letras
    # certas (-1). Menos a taxa de 1 moeda por palpite (-1). Total: +6.
    resposta = client_legacy.post(
        "/api/legacy/guess", json={"guess": "TUSCANO", "day_index": DIA_FIXO}
    )
    corpo = resposta.json()
    assert corpo["is_win"] is False
    assert corpo["is_game_over"] is False
    assert corpo["coins"] == main.MOEDAS_INICIAIS + 5
    assert corpo["size_message"] == "Palpite tem a mesma quantidade de letras que a palavra do dia"


def test_legacy_repetir_posicao_ja_confirmada_nao_rende_bonus_de_novo(client_legacy):
    # "TAAAAAA": acerta as posições 0 (T) e 4 (A) pela 1a vez (+2), tamanho certo
    # pela 1a vez (+1), as outras 5 posições ficam ausentes (-5), menos a taxa
    # (-1) -- delta líquido -3.
    primeira = client_legacy.post(
        "/api/legacy/guess", json={"guess": "TAAAAAA", "day_index": DIA_FIXO}
    )
    assert primeira.json()["coins"] == main.MOEDAS_INICIAIS - 3

    # repetir o mesmo palpite: tamanho e as duas posições já são conhecidos, não
    # rendem bônus de novo -- só as 5 letras ausentes (-5, sem desconto) e a taxa
    # (-1) contam, zerando as moedas.
    segunda = client_legacy.post(
        "/api/legacy/guess", json={"guess": "TAAAAAA", "day_index": DIA_FIXO}
    )
    assert segunda.json()["coins"] == 0
    assert segunda.json()["is_game_over"] is True


def test_legacy_repetir_o_mesmo_palpite_sem_letra_certa_so_cobra_a_taxa_na_segunda_vez(
    client_legacy,
):
    # "USCANYT" é um rearranjo de TUSCANY sem nenhuma letra na posição certa (só
    # "presente", sem penalidade) -- a 1a vez descobre o tamanho (+1), cancelando
    # a taxa (-1): saldo não muda. A 2a vez repete a mesma informação (tamanho já
    # sabido, nenhuma posição nova) e só paga a taxa (-1).
    primeira = client_legacy.post(
        "/api/legacy/guess", json={"guess": "USCANYT", "day_index": DIA_FIXO}
    )
    assert primeira.json()["coins"] == main.MOEDAS_INICIAIS

    segunda = client_legacy.post(
        "/api/legacy/guess", json={"guess": "USCANYT", "day_index": DIA_FIXO}
    )
    assert segunda.json()["coins"] == main.MOEDAS_INICIAIS - 1


def test_legacy_guess_menor_mostra_mensagem_de_tamanho(client_legacy):
    resposta = client_legacy.post("/api/legacy/guess", json={"guess": "CAO", "day_index": DIA_FIXO})
    assert resposta.json()["size_message"] == "Palpite tem menos letras que a palavra do dia"


def test_legacy_guess_maior_mostra_mensagem_de_tamanho(client_legacy):
    resposta = client_legacy.post(
        "/api/legacy/guess", json={"guess": "TUSCANYZZZ", "day_index": DIA_FIXO}
    )
    assert resposta.json()["size_message"] == "Palpite tem mais letras que a palavra do dia"


def test_legacy_derrota_por_falta_de_moedas_nunca_revela_a_palavra(client_legacy):
    # "ZZZZZZZ": tamanho certo (+1) mas nenhuma letra existe em TUSCANY (-7) --
    # de 2 moedas iniciais, isso zera (clamp) e termina o jogo sem revelar nada.
    resposta = client_legacy.post(
        "/api/legacy/guess", json={"guess": "ZZZZZZZ", "day_index": DIA_FIXO}
    )
    corpo = resposta.json()
    assert corpo["coins"] == 0
    assert corpo["is_game_over"] is True
    assert corpo["is_win"] is False
    assert corpo["revealed_word"] is None
    assert corpo["ludopedia_link"] is None


def test_legacy_guess_apos_fim_de_jogo_e_bloqueado(client_legacy):
    client_legacy.post("/api/legacy/guess", json={"guess": "ZZZZZZZ", "day_index": DIA_FIXO})
    resposta = client_legacy.post(
        "/api/legacy/guess", json={"guess": PALAVRA_TESTE_LEGACY, "day_index": DIA_FIXO}
    )
    assert resposta.status_code == 400


def test_legacy_day_index_desatualizado_e_rejeitado(client_legacy):
    resposta = client_legacy.post(
        "/api/legacy/guess", json={"guess": "CAO", "day_index": DIA_FIXO + 1}
    )
    assert resposta.status_code == 409


def test_legacy_palpite_com_caracteres_invalidos_e_rejeitado(client_legacy):
    resposta = client_legacy.post(
        "/api/legacy/guess", json={"guess": "CA3O", "day_index": DIA_FIXO}
    )
    assert resposta.status_code == 422


def test_legacy_palpite_maior_que_10_letras_e_rejeitado(client_legacy):
    resposta = client_legacy.post(
        "/api/legacy/guess", json={"guess": "A" * 11, "day_index": DIA_FIXO}
    )
    assert resposta.status_code == 422


def test_legacy_rate_limit_bloqueia_excesso_de_requisicoes(client_legacy):
    for _ in range(20):
        client_legacy.post("/api/legacy/guess", json={"guess": "CAO", "day_index": DIA_FIXO})

    resposta_extra = client_legacy.post(
        "/api/legacy/guess", json={"guess": "CAO", "day_index": DIA_FIXO}
    )
    assert resposta_extra.status_code == 429


def test_legacy_aparece_na_navegacao_dos_outros_modos(client_legacy):
    resposta = client_legacy.get("/")
    assert "Termeeple Legacy" in resposta.text


def test_pagina_legacy_lista_os_outros_modos(client_legacy):
    resposta = client_legacy.get("/legacy")
    assert resposta.status_code == 200
    assert "Termeeple modo difícil" in resposta.text
    assert "Termeeple modo composto" in resposta.text
