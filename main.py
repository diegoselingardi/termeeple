from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from game_logic import evaluate_guess, is_win
from words import word_for_day, today_index
from pydantic import BaseModel

app = FastAPI()
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
    attempt_number: int

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
def guess(payload: GuessRequest):
    resposta = word_for_day(payload.day_index)
    avaliacao = evaluate_guess(payload.guess, resposta)
    ganhou = is_win(avaliacao)
    acabou = ganhou or payload.attempt_number >= MAX_ATTEMPTS
    resposta_revelada = resposta if acabou else None
    return {"evaluation": avaliacao, "is_win": ganhou, "is_game_over": acabou, "revealed_word": resposta_revelada}