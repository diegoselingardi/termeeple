import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from game_logic import LetterStatus, evaluate_guess, is_win
from legacy_logic import (
    MOEDAS_INICIAIS,
    TAXA_POR_PALPITE,
    avaliar_letras,
    avaliar_tamanho,
    calcular_delta_moedas_letras_com_descobertas,
    calcular_delta_moedas_tamanho_com_descoberta,
)
from words import (
    WORDS_COMPOSTO,
    WORDS_DIFICIL,
    WORDS_LEGACY,
    WORDS_PADRAO,
    entry_for_day,
    segment_boundaries,
    sponsored_entry_for_day,
    today_index,
)

logger = logging.getLogger("termeeple")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# SECRET_KEY precisa vir de variável de ambiente em produção (ex.: configurar no Render).
# O valor abaixo é só um fallback pra rodar localmente sem configurar nada.
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "dev-insecure-key-troque-em-producao"),
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/sw.js")
def service_worker():
    """Serve o service worker a partir da raiz -- registrar um SW controla, por
    padrão, só o diretório onde o arquivo está; servido de /static/sw.js ele só
    controlaria pedidos sob /static/, nunca as páginas do jogo em si."""
    return FileResponse("static/sw.js", media_type="application/javascript")


def montar_teclado(palavra):
    """Teclado padrão QWERTY, igual o Termo: BACK no fim da 2ª linha, ENTER no fim
    da 3ª. O Ç só aparece nos dias em que a palavra realmente tem essa letra, pra
    não poluir o teclado à toa."""
    segunda_linha = list("ASDFGHJKL")
    if "Ç" in palavra:
        segunda_linha.append("Ç")
    segunda_linha.append("BACK")
    return [
        list("QWERTYUIOP"),
        segunda_linha,
        list("ZXCVBNM") + ["ENTER"],
    ]


def montar_teclado_legacy():
    """Teclado do modo Legacy -- sempre mostra o Ç, diferente dos outros modos.
    Lá, decidir mostrar o Ç com base na palavra do dia não vaza nada (o tamanho
    já aparece no tabuleiro); aqui a palavra é secreta, então esconder ou não o Ç
    condicionalmente entregaria de graça se ela tem ou não essa letra."""
    return [
        list("QWERTYUIOP"),
        list("ASDFGHJKL") + ["Ç", "BACK"],
        list("ZXCVBNM") + ["ENTER"],
    ]


# Três modos independentes -- cada um cicla só pela sua própria lista de palavras,
# com sua própria sessão de tentativas e (no front-end) suas próprias estatísticas.
# Padrão mantém as URLs originais (prefixo vazio), pra não quebrar nada em produção.
MODOS = {
    "padrao": {
        "prefixo": "",
        "palavras": WORDS_PADRAO,
        "max_attempts": 6,
        "titulo": "Termeeple",
        "descricao": "Uma versão baseada em Wordle para quem joga tabuleiro",
        "patrocinavel": True,
    },
    "dificil": {
        "prefixo": "/dificil",
        "palavras": WORDS_DIFICIL,
        "max_attempts": 7,
        "titulo": "Termeeple modo difícil",
        "descricao": "Modo Difícil — nomes de 7 a 10 letras",
    },
    "composto": {
        "prefixo": "/composto",
        "palavras": WORDS_COMPOSTO,
        "max_attempts": 8,
        "titulo": "Termeeple modo composto",
        "descricao": "Modo Composto — nomes de jogos com espaço, de 5 a 10 letras",
    },
}


class GuessRequest(BaseModel):
    guess: str
    day_index: int


# Usado só pra montar os links de "outros modos" na tela de configurações.
# Inclui o Legacy, que tem rotas próprias (não passa por registrar_modo) por ter
# uma mecânica bem diferente dos outros três -- sem tabuleiro de tamanho fixo,
# sem limite de tentativas por contagem, com aposta de moedas em vez disso.
NAVEGACAO_MODOS = {
    **{nome: {"titulo": c["titulo"], "prefixo": c["prefixo"]} for nome, c in MODOS.items()},
    "legacy": {"titulo": "Termeeple Legacy", "prefixo": "/legacy"},
}


def resolver_entrada_do_dia(dia_atual, config):
    """Devolve (palavra, segmentos, link) do dia -- usa a palavra patrocinada da data
    de hoje quando o modo permite (config["patrocinavel"]) e existe uma pra hoje;
    senão cicla normalmente pela lista de palavras do modo."""
    if config.get("patrocinavel"):
        patrocinada = sponsored_entry_for_day(dia_atual)
        if patrocinada is not None:
            return patrocinada
    return entry_for_day(dia_atual, config["palavras"])


def registrar_modo(nome, config):
    prefixo = config["prefixo"]
    palavras = config["palavras"]
    max_attempts = config["max_attempts"]
    titulo = config["titulo"]
    descricao = config["descricao"]

    def pagina(request: Request):
        if not palavras:
            return HTMLResponse(
                f"<h1>{titulo}</h1><p>Esse modo ainda não tem palavras cadastradas.</p>"
            )
        dia_atual = today_index()
        palavra, segmentos, _link = resolver_entrada_do_dia(dia_atual, config)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "day_index": dia_atual,
                "word_length": len(palavra),
                "max_attempts": max_attempts,
                "keyboard_rows": montar_teclado(palavra),
                "segment_boundaries": segment_boundaries(segmentos),
                "modo": nome,
                "titulo": titulo,
                "descricao": descricao,
                "outros_modos": [
                    (m, info["titulo"], info["prefixo"] or "/")
                    for m, info in NAVEGACAO_MODOS.items()
                    if m != nome
                ],
            },
        )

    def state():
        if not palavras:
            raise HTTPException(status_code=503, detail="modo sem palavras cadastradas")
        dia_atual = today_index()
        palavra, _segmentos, _link = resolver_entrada_do_dia(dia_atual, config)
        return {
            "day_index": dia_atual,
            "word_length": len(palavra),
            "max_attempts": max_attempts,
        }

    def guess(request: Request, payload: GuessRequest):
        if not palavras:
            raise HTTPException(status_code=503, detail="modo sem palavras cadastradas")

        dia_atual = today_index()
        if payload.day_index != dia_atual:
            logger.warning(
                "day_index desatualizado recebido (modo=%s, cliente=%s, atual=%s)",
                nome,
                payload.day_index,
                dia_atual,
            )
            raise HTTPException(status_code=409, detail="dia desatualizado, recarregue a página")

        resposta, _segmentos, link_ganhou = resolver_entrada_do_dia(dia_atual, config)

        if len(payload.guess) != len(resposta) or not payload.guess.isalpha():
            logger.warning("palpite inválido recebido (modo=%s): %r", nome, payload.guess)
            raise HTTPException(status_code=422, detail="palpite inválido")

        session_key = f"attempts_{nome}_{dia_atual}"
        tentativas_usadas = request.session.get(session_key, 0)

        if tentativas_usadas >= max_attempts:
            logger.warning("tentativa além do limite bloqueada (modo=%s, dia=%s)", nome, dia_atual)
            raise HTTPException(status_code=400, detail="número de tentativas excedido")

        tentativas_usadas += 1
        request.session[session_key] = tentativas_usadas

        avaliacao = evaluate_guess(payload.guess, resposta)
        ganhou = is_win(avaliacao)
        acabou = ganhou or tentativas_usadas >= max_attempts
        resposta_revelada = resposta if acabou else None
        link_ludopedia = link_ganhou if ganhou else None

        logger.info(
            "palpite processado (modo=%s, dia=%s, tentativa=%s/%s, vitoria=%s, fim_de_jogo=%s)",
            nome,
            dia_atual,
            tentativas_usadas,
            max_attempts,
            ganhou,
            acabou,
        )

        return {
            "evaluation": avaliacao,
            "is_win": ganhou,
            "is_game_over": acabou,
            "revealed_word": resposta_revelada,
            "attempt_number": tentativas_usadas,
            "ludopedia_link": link_ludopedia,
        }

    # Nomes únicos por modo -- o slowapi identifica cada rota limitada por
    # "{func.__module__}.{func.__name__}"; sem isso, as 3 funções "guess" (uma por
    # modo, mas todas com o mesmo __name__) colidiriam no mesmo registro interno,
    # e cada requisição contaria 3x pro limite de taxa (bug real encontrado em teste).
    pagina.__name__ = f"pagina_{nome}"
    state.__name__ = f"state_{nome}"
    guess.__name__ = f"guess_{nome}"
    guess = limiter.limit("20/minute")(guess)

    app.get(prefixo or "/")(pagina)
    app.get(f"/api{prefixo}/state")(state)
    app.post(f"/api{prefixo}/guess")(guess)


for _nome, _config in MODOS.items():
    registrar_modo(_nome, _config)


def resolver_entrada_legacy(dia_atual):
    """(Palavra, link) do dia do modo Legacy -- não tem patrocínio (isso é exclusivo
    do Padrão) nem segmentos (não há tabuleiro pra desenhar a quebra visual)."""
    palavra, _segmentos, link = entry_for_day(dia_atual, WORDS_LEGACY)
    return palavra, link


@app.get("/legacy")
def legacy_pagina(request: Request):
    dia_atual = today_index()
    return templates.TemplateResponse(
        request,
        "legacy.html",
        {
            "day_index": dia_atual,
            "moedas_iniciais": MOEDAS_INICIAIS,
            "keyboard_rows": montar_teclado_legacy(),
            "titulo": "Termeeple Legacy",
            "outros_modos": [
                (m, info["titulo"], info["prefixo"] or "/")
                for m, info in NAVEGACAO_MODOS.items()
                if m != "legacy"
            ],
        },
    )


@app.get("/api/legacy/state")
def legacy_state(request: Request):
    dia_atual = today_index()
    moedas = request.session.get(f"legacy_moedas_{dia_atual}", MOEDAS_INICIAIS)
    venceu = request.session.get(f"legacy_venceu_{dia_atual}", False)
    palavra, link = resolver_entrada_legacy(dia_atual)
    return {
        "day_index": dia_atual,
        "coins": moedas,
        "is_win": venceu,
        # só revela a palavra por vitória -- perder por falta de moedas nunca revela
        "is_game_over": venceu or moedas <= 0,
        "revealed_word": palavra if venceu else None,
        "ludopedia_link": link if venceu else None,
    }


@app.post("/api/legacy/guess")
@limiter.limit("20/minute")
def legacy_guess(request: Request, payload: GuessRequest):
    dia_atual = today_index()
    if payload.day_index != dia_atual:
        logger.warning(
            "day_index desatualizado recebido (modo=legacy, cliente=%s, atual=%s)",
            payload.day_index,
            dia_atual,
        )
        raise HTTPException(status_code=409, detail="dia desatualizado, recarregue a página")

    moedas_key = f"legacy_moedas_{dia_atual}"
    venceu_key = f"legacy_venceu_{dia_atual}"
    tamanho_descoberto_key = f"legacy_tamanho_descoberto_{dia_atual}"
    posicoes_confirmadas_key = f"legacy_posicoes_confirmadas_{dia_atual}"
    moedas = request.session.get(moedas_key, MOEDAS_INICIAIS)
    venceu = request.session.get(venceu_key, False)

    if venceu or moedas <= 0:
        raise HTTPException(status_code=400, detail="jogo já terminou hoje")

    palpite = payload.guess.strip().upper()
    if not palpite or not palpite.isalpha() or len(palpite) > 10:
        logger.warning("palpite inválido recebido (modo=legacy): %r", payload.guess)
        raise HTTPException(status_code=422, detail="palpite inválido")

    resposta, link = resolver_entrada_legacy(dia_atual)

    if palpite == resposta:
        request.session[venceu_key] = True
        logger.info("palpite processado (modo=legacy, dia=%s, vitoria=True)", dia_atual)
        return {
            "is_win": True,
            "is_game_over": True,
            "coins": moedas,
            "size_message": None,
            # tudo certo, é o palpite vencedor -- devolve pro front-end poder
            # desenhar essa tentativa também no histórico, toda verde
            "evaluation": [{"letter": letra, "status": LetterStatus.CORRECT} for letra in resposta],
            "revealed_word": resposta,
            "ludopedia_link": link,
        }

    # Bônus de tamanho e de posição certa só valem na primeira vez que são
    # descobertos -- senão dava pra "farmar" moedas reusando uma letra ou um
    # tamanho já sabidos. Letra ausente e tamanho errado continuam custando
    # moeda sempre, e cada palpite enviado ainda paga a taxa de aposta.
    mensagem_tamanho, delta_tamanho_bruto = avaliar_tamanho(len(palpite), len(resposta))
    tamanho_ja_descoberto = request.session.get(tamanho_descoberto_key, False)
    delta_tamanho = calcular_delta_moedas_tamanho_com_descoberta(
        delta_tamanho_bruto, tamanho_ja_descoberto
    )
    if delta_tamanho_bruto == 1:
        request.session[tamanho_descoberto_key] = True

    avaliacao = avaliar_letras(palpite, resposta)
    posicoes_confirmadas = set(request.session.get(posicoes_confirmadas_key, []))
    delta_letras, novas_posicoes = calcular_delta_moedas_letras_com_descobertas(
        avaliacao, posicoes_confirmadas
    )
    if novas_posicoes:
        request.session[posicoes_confirmadas_key] = sorted(posicoes_confirmadas | novas_posicoes)

    moedas = max(0, moedas - TAXA_POR_PALPITE + delta_tamanho + delta_letras)
    acabou = moedas <= 0
    request.session[moedas_key] = moedas

    logger.info(
        "palpite processado (modo=legacy, dia=%s, moedas=%s, fim_de_jogo=%s)",
        dia_atual,
        moedas,
        acabou,
    )

    return {
        "is_win": False,
        "is_game_over": acabou,
        "coins": moedas,
        "size_message": mensagem_tamanho,
        "evaluation": avaliacao,
        # nunca revela por derrota -- só resolver_entrada_legacy() no caso de vitória sabe a palavra
        "revealed_word": None,
        "ludopedia_link": None,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
