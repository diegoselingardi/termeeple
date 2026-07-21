"""Busca candidatos a palavra do dia na API da Ludopedia (jogos base, 2020-2024, nome de 5-10
letras depois de normalizado). Não escreve em words.py -- só imprime uma lista pra você revisar
e colar manualmente as entradas que quiser em WORDS.

Uso:
    export LUDOPEDIA_ACCESS_TOKEN=seu_token
    # Windows PowerShell: $env:LUDOPEDIA_ACCESS_TOKEN="seu_token"
    python scripts/fetch_ludopedia_words.py
"""

import os
import sys
import time
from pathlib import Path

import requests

API_BASE = "https://ludopedia.com.br/api/v1"
ANO_MIN = 2020
ANO_MAX = 2024
TAM_MIN = 5
TAM_MAX = 10
TP_JOGO = "b"  # só jogos base, sem expansão
ROWS_POR_PAGINA = 100
PAUSA_ENTRE_CHAMADAS = 0.2  # segundos -- API está em ALPHA, sem limite de taxa documentado


def cabecalho(token):
    return {"Authorization": f"Bearer {token}"}


def listar_jogos(token):
    """Pagina GET /jogos e devolve todo (id_jogo, nm_jogo) do catálogo."""
    jogos = []
    pagina = 1
    while True:
        resposta = requests.get(
            f"{API_BASE}/jogos",
            headers=cabecalho(token),
            params={"tp_jogo": TP_JOGO, "page": pagina, "rows": ROWS_POR_PAGINA},
        )
        resposta.raise_for_status()
        corpo = resposta.json()
        pagina_jogos = corpo.get("jogos", [])
        if not pagina_jogos:
            break
        jogos.extend(pagina_jogos)
        if len(jogos) >= corpo.get("total", 0):
            break
        pagina += 1
        time.sleep(PAUSA_ENTRE_CHAMADAS)
    return jogos


def ano_do_jogo(token, id_jogo):
    """Busca o detalhe do jogo e devolve o ano nacional (preferido) ou o de publicação."""
    resposta = requests.get(f"{API_BASE}/jogos/{id_jogo}", headers=cabecalho(token))
    resposta.raise_for_status()
    detalhe = resposta.json()
    return detalhe.get("ano_nacional") or detalhe.get("ano_publicacao")


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from words import WORDS, normalize_title

    token = os.environ.get("LUDOPEDIA_ACCESS_TOKEN")
    if not token:
        print(
            "Defina LUDOPEDIA_ACCESS_TOKEN no ambiente antes de rodar este script.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Baixando lista de jogos da Ludopedia...", file=sys.stderr)
    jogos = listar_jogos(token)
    print(f"{len(jogos)} jogos base encontrados no catálogo.", file=sys.stderr)

    ja_usadas = {palavra for palavra, _ in WORDS}
    candidatos_por_tamanho = {}
    for jogo in jogos:
        palavra, segmentos = normalize_title(jogo["nm_jogo"])
        if not (TAM_MIN <= len(palavra) <= TAM_MAX):
            continue
        if palavra in ja_usadas:
            continue
        # dedup: mantém o primeiro jogo encontrado pra cada palavra normalizada
        candidatos_por_tamanho.setdefault(palavra, (jogo, segmentos))

    print(
        f"{len(candidatos_por_tamanho)} candidatos após filtrar tamanho e duplicatas.",
        file=sys.stderr,
    )
    print(
        f"Consultando ano de lançamento de cada candidato (pausa de {PAUSA_ENTRE_CHAMADAS}s)...",
        file=sys.stderr,
    )

    encontrados = []
    for palavra, (jogo, segmentos) in candidatos_por_tamanho.items():
        ano = ano_do_jogo(token, jogo["id_jogo"])
        time.sleep(PAUSA_ENTRE_CHAMADAS)
        if ano is not None and ANO_MIN <= ano <= ANO_MAX:
            encontrados.append((ano, jogo["nm_jogo"], palavra, segmentos))

    encontrados.sort()
    print(f"\n{len(encontrados)} jogos de {ANO_MIN}-{ANO_MAX} com {TAM_MIN}-{TAM_MAX} letras:\n")
    for ano, nome_original, palavra, segmentos in encontrados:
        print(f'{ano}  {nome_original!r:40}  -> ("{palavra}", {segmentos!r}),')


if __name__ == "__main__":
    main()
