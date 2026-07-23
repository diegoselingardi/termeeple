"""Busca candidatos a palavra do dia na API da Ludopedia (jogos base, 2020-2024, nome de 5-10
letras depois de normalizado). Não escreve em words.py -- só imprime uma lista pra você revisar
e colar manualmente as entradas que quiser em WORDS.

Uso:
    export LUDOPEDIA_ACCESS_TOKEN=seu_token
    # Windows PowerShell: $env:LUDOPEDIA_ACCESS_TOKEN="seu_token"
    python scripts/fetch_ludopedia_words.py

Progresso fica em cache (scripts/.ludopedia_cache.json) -- se o script for interrompido
(ex.: rate limit) rodar de novo continua de onde parou, sem baixar tudo outra vez. Pra
forçar uma busca do zero (ex.: catálogo mudou), apague esse arquivo.
"""

import json
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
PAUSA_ENTRE_CHAMADAS = 1.0  # segundos entre chamadas -- API está em ALPHA, sem limite documentado
ESPERA_MAXIMA_RETRY = 120  # teto do backoff quando a API responde 429
CACHE_PATH = Path(__file__).resolve().parent / ".ludopedia_cache.json"

# Espera "atual" persiste entre chamadas -- se ficar tomando 429, ela vai escalando de
# verdade em vez de reiniciar do zero a cada palpite/jogo novo (o bug que causava o loop
# de 429 constante). Relaxa aos poucos (metade) só quando uma chamada dá certo.
_estado_backoff = {"espera": PAUSA_ENTRE_CHAMADAS}


def carregar_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {"jogos": None, "anos": {}}


def salvar_cache(cache):
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def cabecalho(token):
    return {"Authorization": f"Bearer {token}"}


def get_com_retry(url, headers=None, params=None):
    """GET com retry/backoff pra 429 (Too Many Requests) -- a API não documenta o limite
    de taxa, então respeita o Retry-After se vier (e for numérico), ou dobra a espera."""
    while True:
        resposta = requests.get(url, headers=headers, params=params)
        if resposta.status_code == 429:
            retry_after = resposta.headers.get("Retry-After")
            try:
                proxima_espera = float(retry_after) if retry_after is not None else None
            except ValueError:
                proxima_espera = None
            if proxima_espera is None:
                proxima_espera = _estado_backoff["espera"] * 2
            espera = min(proxima_espera, ESPERA_MAXIMA_RETRY)
            _estado_backoff["espera"] = espera
            print(f"429 (rate limit), aguardando {espera:.0f}s...", file=sys.stderr)
            time.sleep(espera)
            continue
        resposta.raise_for_status()
        time.sleep(_estado_backoff["espera"])
        _estado_backoff["espera"] = max(PAUSA_ENTRE_CHAMADAS, _estado_backoff["espera"] / 2)
        return resposta


def listar_jogos(token):
    """Pagina GET /jogos e devolve todo (id_jogo, nm_jogo) do catálogo."""
    jogos = []
    pagina = 1
    while True:
        resposta = get_com_retry(
            f"{API_BASE}/jogos",
            headers=cabecalho(token),
            params={"tp_jogo": TP_JOGO, "page": pagina, "rows": ROWS_POR_PAGINA},
        )
        corpo = resposta.json()
        pagina_jogos = corpo.get("jogos", [])
        if not pagina_jogos:
            break
        jogos.extend(pagina_jogos)
        print(f"  página {pagina}: {len(jogos)}/{corpo.get('total', 0)} jogos", file=sys.stderr)
        if len(jogos) >= corpo.get("total", 0):
            break
        pagina += 1
    return jogos


def ano_do_jogo(token, id_jogo):
    """Busca o detalhe do jogo e devolve o ano nacional (preferido) ou o de publicação."""
    resposta = get_com_retry(f"{API_BASE}/jogos/{id_jogo}", headers=cabecalho(token))
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

    cache = carregar_cache()

    if cache["jogos"] is not None:
        jogos = cache["jogos"]
        print(f"Usando lista em cache: {len(jogos)} jogos.", file=sys.stderr)
    else:
        print("Baixando lista de jogos da Ludopedia...", file=sys.stderr)
        jogos = listar_jogos(token)
        cache["jogos"] = jogos
        salvar_cache(cache)
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
    print("Consultando ano de lançamento de cada candidato...", file=sys.stderr)

    encontrados = []
    total_candidatos = len(candidatos_por_tamanho)
    for indice, (palavra, (jogo, segmentos)) in enumerate(candidatos_por_tamanho.items(), start=1):
        id_jogo_str = str(jogo["id_jogo"])
        if id_jogo_str in cache["anos"]:
            ano = cache["anos"][id_jogo_str]
        else:
            ano = ano_do_jogo(token, jogo["id_jogo"])
            cache["anos"][id_jogo_str] = ano
            salvar_cache(cache)
        if indice % 20 == 0 or indice == total_candidatos:
            print(f"  {indice}/{total_candidatos} candidatos consultados", file=sys.stderr)
        if ano is not None and ANO_MIN <= ano <= ANO_MAX:
            encontrados.append((ano, jogo["nm_jogo"], palavra, segmentos))

    encontrados.sort()
    print(f"\n{len(encontrados)} jogos de {ANO_MIN}-{ANO_MAX} com {TAM_MIN}-{TAM_MAX} letras:\n")
    for ano, nome_original, palavra, segmentos in encontrados:
        print(f'{ano}  {nome_original!r:40}  -> ("{palavra}", {segmentos!r}),')


if __name__ == "__main__":
    main()
