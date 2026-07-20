from game_logic import evaluate_guess, is_win, LetterStatus

def test_is_win():
    resultado = evaluate_guess("REGRA", "REGRA")
    assert is_win(resultado) is True

    resultado = evaluate_guess("XEGRA", "REGRA")
    assert is_win(resultado) is False

def test_letra_repetida_no_palpite_uma_so_na_resposta():
    resultado = evaluate_guess("XEGRA", "REGRA")
    letras_a = [item for item in resultado if item["letter"] == "A"]
    sinalizados = [item for item in letras_a if item["status"] != LetterStatus.ABSENT]
    assert len(sinalizados) == 1, "REGRA só tem 1 'A' -- só um dos dois A's do palpite pode virar present/correct"