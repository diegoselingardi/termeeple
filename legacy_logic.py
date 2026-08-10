"""Regras do modo Legacy: palpite de qualquer tamanho, sem limite de tentativas
por contagem -- só por "meeples coins". Separado de game_logic.py de propósito:
as regras daqui (moedas, tolerância a tamanho diferente) valem só pra esse modo,
os outros três continuam usando evaluate_guess normalmente, sem essa tolerância."""

from game_logic import LetterStatus

MOEDAS_INICIAIS = 10
TAXA_POR_PALPITE = 1  # toda tentativa (certa ou errada) custa 1 moeda, além dos bônus/perdas abaixo


def avaliar_tamanho(tamanho_palpite: int, tamanho_resposta: int) -> tuple[str, int]:
    """Compara o tamanho do palpite com o da resposta e devolve (mensagem, delta_moedas)."""
    if tamanho_palpite < tamanho_resposta:
        return "Palpite tem menos letras que a palavra do dia", -1
    if tamanho_palpite > tamanho_resposta:
        return "Palpite tem mais letras que a palavra do dia", -1
    return "Palpite tem a mesma quantidade de letras que a palavra do dia", 1


def avaliar_letras(guess: str, answer: str) -> list[dict]:
    """Como evaluate_guess, mas tolerante a tamanhos diferentes -- só compara
    posições até o menor dos dois tamanhos; o que sobra do palpite além do
    tamanho da resposta conta sempre como ausente."""
    limite = min(len(guess), len(answer))
    resultado = [None] * len(guess)
    estoque = list(answer)

    for i in range(limite):
        if guess[i] == answer[i]:
            resultado[i] = {"letter": guess[i], "status": LetterStatus.CORRECT}
            estoque[i] = None

    for i in range(limite):
        if resultado[i] is not None:
            continue
        if guess[i] in estoque:
            resultado[i] = {"letter": guess[i], "status": LetterStatus.PRESENT}
            estoque[estoque.index(guess[i])] = None
        else:
            resultado[i] = {"letter": guess[i], "status": LetterStatus.ABSENT}

    for i in range(limite, len(guess)):
        resultado[i] = {"letter": guess[i], "status": LetterStatus.ABSENT}

    return resultado


def calcular_delta_moedas_letras(avaliacao: list[dict]) -> int:
    """+1 por letra certa, -1 por letra ausente, 0 por letra na posição errada."""
    delta = 0
    for item in avaliacao:
        if item["status"] == LetterStatus.CORRECT:
            delta += 1
        elif item["status"] == LetterStatus.ABSENT:
            delta -= 1
    return delta


def calcular_delta_moedas_letras_com_descobertas(
    avaliacao: list[dict], posicoes_ja_confirmadas: set[int]
) -> tuple[int, set[int]]:
    """Como calcular_delta_moedas_letras, mas só premia uma posição certa na primeira
    vez que ela é descoberta -- repetir uma letra já confirmada correta não rende
    moeda de novo (senão dava pra "farmar" moedas reusando uma letra já sabida).
    Letra ausente continua tirando moeda sempre, mesmo repetida -- só o lado
    positivo (posição certa) passa a valer uma vez só. Devolve (delta, posições
    recém-confirmadas nesse palpite, pra quem chamar atualizar o que já sabe)."""
    delta = 0
    novas_posicoes = set()
    for i, item in enumerate(avaliacao):
        if item["status"] == LetterStatus.CORRECT:
            if i not in posicoes_ja_confirmadas:
                delta += 1
                novas_posicoes.add(i)
        elif item["status"] == LetterStatus.ABSENT:
            delta -= 1
    return delta, novas_posicoes


def calcular_delta_moedas_tamanho_com_descoberta(
    delta_tamanho_bruto: int, tamanho_ja_descoberto: bool
) -> int:
    """Como o delta de avaliar_tamanho, mas só premia o tamanho certo na primeira
    vez que é descoberto -- acertar o tamanho de novo depois disso não rende moeda.
    Errar o tamanho continua tirando moeda sempre, mesmo repetindo o mesmo erro."""
    if delta_tamanho_bruto == 1 and tamanho_ja_descoberto:
        return 0
    return delta_tamanho_bruto
