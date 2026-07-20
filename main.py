import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from game_logic import evaluate_guess, is_win
from words import word_for_day, today_index
from pydantic import BaseModel

app = FastAPI()
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
            "keyboard_rows": KEYBOARD_ROWS
        }
    )

@app.get("/api/state")
def state():
    dias = {
        "day_index": today_index(), 
        "word_length": WORD_LENGTH, 
        "max_attempts": MAX_ATTEMPTS
    }
    return dias 

@app.post("/api/guess")
def guess(payload: GuessRequest, request: Request):
    dia_atual = today_index()
    if payload.day_index != dia_atual:
        raise HTTPException(status_code=409, detail="dia desatualizado, recarregue a página")

    if len(payload.guess) != WORD_LENGTH or not payload.guess.isalpha():
        raise HTTPException(status_code=422, detail="palpite inválido")

    session_key = f"attempts_{dia_atual}"
    tentativas_usadas = request.session.get(session_key, 0)

    if tentativas_usadas >= MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="número de tentativas excedido")

    tentativas_usadas += 1
    request.session[session_key] = tentativas_usadas

    resposta = word_for_day(dia_atual)
    avaliacao = evaluate_guess(payload.guess, resposta)
    ganhou = is_win(avaliacao)
    acabou = ganhou or tentativas_usadas >= MAX_ATTEMPTS
    resposta_revelada = resposta if acabou else None

    return {
        "evaluation": avaliacao,
        "is_win": ganhou,
        "is_game_over": acabou,
        "revealed_word": resposta_revelada,
        "attempt_number": tentativas_usadas,
    }