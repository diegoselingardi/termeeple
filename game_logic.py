from enum import Enum

class LetterStatus(str, Enum):
    CORRECT = "correct"
    PRESENT = "present"
    ABSENT = "absent"
        
def evaluate_guess(guess: str, answer: str) -> list[dict]:
    resultado = [None] * len(guess)
    estoque = list(answer)

    for i, letra in enumerate(guess):
        if letra == answer[i]:
            resultado[i] = {"letter": letra, "status": LetterStatus.CORRECT}
            estoque[i] = None

    for i, letra in enumerate(guess):
            if resultado[i] is not None: 
                continue
            if letra in estoque:
                resultado[i] = {"letter": letra, "status": LetterStatus.PRESENT}
                posicao = estoque.index(letra)
                estoque[posicao] = None
            else:
                resultado[i] = {"letter": letra, "status": LetterStatus.ABSENT}

    return resultado

def is_win(evalution):
     return all(item["status"] == LetterStatus.CORRECT for item in evalution)