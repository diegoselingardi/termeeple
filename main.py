import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from game_logic import evaluate_guess, is_win
from words import (
    WORDS_COMPOSTO,
    WORDS_DIFICIL,
    WORDS_PADRAO,
    segment_boundaries,
    segments_for_day,
    today_index,
    word_for_day,
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

KEYBOARD_ROWS = [
    list("QWERTYUIOP"),
    list("ASDFGHJKLÇ"),
    ["BACK"] + list("ZXCVBNM") + ["ENTER"],
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
    },
    "dificil": {
        "prefixo": "/dificil",
        "palavras": WORDS_DIFICIL,
        "max_attempts": 7,
        "titulo": "Termeeple — Difícil",
        "descricao": "Modo Difícil — nomes de 7 a 10 letras",
    },
    "composto": {
        "prefixo": "/composto",
        "palavras": WORDS_COMPOSTO,
        "max_attempts": 8,
        "titulo": "Termeeple — Composto",
        "descricao": "Modo Composto — nomes de jogos com espaço, de 5 a 10 letras",
    },
}


class GuessRequest(BaseModel):
    guess: str
    day_index: int


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
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "day_index": dia_atual,
                "word_length": len(word_for_day(dia_atual, palavras)),
                "max_attempts": max_attempts,
                "keyboard_rows": KEYBOARD_ROWS,
                "segment_boundaries": segment_boundaries(segments_for_day(dia_atual, palavras)),
                "modo": nome,
                "titulo": titulo,
                "descricao": descricao,
                "outros_modos": [
                    (m, c["titulo"], c["prefixo"] or "/") for m, c in MODOS.items() if m != nome
                ],
            },
        )

    def state():
        if not palavras:
            raise HTTPException(status_code=503, detail="modo sem palavras cadastradas")
        dia_atual = today_index()
        return {
            "day_index": dia_atual,
            "word_length": len(word_for_day(dia_atual, palavras)),
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

        resposta = word_for_day(dia_atual, palavras)

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


@app.get("/health")
def health():
    return {"status": "ok"}
