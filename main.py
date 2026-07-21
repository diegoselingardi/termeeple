import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from game_logic import evaluate_guess, is_win
from words import today_index, word_for_day

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

MAX_ATTEMPTS = 6
WORD_LENGTH = 5
KEYBOARD_ROWS = [
    list("QWERTYUIOP"),
    list("ASDFGHJKLÇ"),
    ["ENTER"] + list("ZXCVBNM") + ["BACK"],
]


class GuessRequest(BaseModel):
    guess: str
    day_index: int


@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "day_index": today_index(),
            "word_length": WORD_LENGTH,
            "max_attempts": MAX_ATTEMPTS,
            "keyboard_rows": KEYBOARD_ROWS,
        },
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/state")
def state():
    dias = {"day_index": today_index(), "word_length": WORD_LENGTH, "max_attempts": MAX_ATTEMPTS}
    return dias


@app.post("/api/guess")
@limiter.limit("20/minute")
def guess(request: Request, payload: GuessRequest):
    dia_atual = today_index()
    if payload.day_index != dia_atual:
        logger.warning(
            "day_index desatualizado recebido (cliente=%s, atual=%s)",
            payload.day_index,
            dia_atual
        )
        raise HTTPException(status_code=409, detail="dia desatualizado, recarregue a página")

    if len(payload.guess) != WORD_LENGTH or not payload.guess.isalpha():
        logger.warning("palpite inválido recebido: %r", payload.guess)
        raise HTTPException(status_code=422, detail="palpite inválido")

    session_key = f"attempts_{dia_atual}"
    tentativas_usadas = request.session.get(session_key, 0)

    if tentativas_usadas >= MAX_ATTEMPTS:
        logger.warning("tentativa além do limite bloqueada (dia=%s)", dia_atual)
        raise HTTPException(status_code=400, detail="número de tentativas excedido")

    tentativas_usadas += 1
    request.session[session_key] = tentativas_usadas

    resposta = word_for_day(dia_atual)
    avaliacao = evaluate_guess(payload.guess, resposta)
    ganhou = is_win(avaliacao)
    acabou = ganhou or tentativas_usadas >= MAX_ATTEMPTS
    resposta_revelada = resposta if acabou else None

    logger.info(
        "palpite processado (dia=%s, tentativa=%s/%s, vitoria=%s, fim_de_jogo=%s)",
        dia_atual,
        tentativas_usadas,
        MAX_ATTEMPTS,
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
