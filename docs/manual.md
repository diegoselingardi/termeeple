# Manual do Termeeple — como o projeto funciona, explicado do zero

Esse documento existe pra você conseguir estudar, dar manutenção e expandir o Termeeple mesmo sabendo pouco Python ainda. Ele não substitui o [`README.md`](../README.md) (que é o resumo rápido) nem o [`docs/dependencias.md`](dependencias.md) (que explica cada biblioteca instalada) — é o terceiro documento, o mais didático dos três, focado em **por que** o código foi escrito do jeito que foi.

Vou usar analogias, mostrar trechos reais do seu código, e parar em pontos que costumam confundir quem está começando em Python. Não precisa ler tudo de uma vez — use o índice pra ir direto no que precisar.

## Índice

1. [Visão geral: o que o projeto faz](#1-visão-geral-o-que-o-projeto-faz)
2. [Mapa do projeto: quem fala com quem](#2-mapa-do-projeto-quem-fala-com-quem)
3. [O fluxo de uma partida, passo a passo](#3-o-fluxo-de-uma-partida-passo-a-passo)
4. [Tour pelos arquivos, função por função](#4-tour-pelos-arquivos-função-por-função)
5. [Conceitos de Python usados no projeto (explicados do zero)](#5-conceitos-de-python-usados-no-projeto-explicados-do-zero)
6. [SOLID aplicado ao Termeeple](#6-solid-aplicado-ao-termeeple)
7. [Boas práticas do projeto](#7-boas-práticas-do-projeto)
8. [Como estudar e expandir o projeto](#8-como-estudar-e-expandir-o-projeto)
9. [Glossário rápido](#9-glossário-rápido)

---

## 1. Visão geral: o que o projeto faz

O Termeeple é um clone do Wordle, em português, com tema de jogos de tabuleiro. Todo mundo que joga no mesmo dia recebe a mesma palavra (o nome de um jogo de tabuleiro), e tenta adivinhá-la em um número limitado de tentativas.

Tem três "modos" — pense neles como três jogos separados que só compartilham o motor por baixo:

| Modo | URL | Tamanho da palavra | Tentativas |
|---|---|---|---|
| Padrão | `/` | 5-6 letras | 6 |
| Difícil | `/dificil` | 7-10 letras | 7 |
| Composto | `/composto` | 5-10 letras, nomes que tinham espaço (ex.: "Blue Lagoon") | 8 |

O "motor por baixo" é sempre o mesmo: pegar a palavra do dia, comparar com o palpite do jogador, devolver quais letras estão certas/erradas/na posição errada, e lembrar quantas tentativas a pessoa já gastou hoje.

### As duas metades do projeto

Todo app web tem (pelo menos) duas metades, e é importante você enxergar essa separação porque ela aparece o tempo todo no código:

- **Backend** (roda no servidor, em Python): decide qual é a palavra do dia, valida palpites, guarda quantas tentativas cada pessoa já usou. Arquivos: `main.py`, `words.py`, `game_logic.py`.
- **Frontend** (roda no navegador de quem joga, em JavaScript): desenha o tabuleiro, captura o que a pessoa digita, manda pro backend, mostra o resultado. Arquivos: `templates/index.html`, `static/game.js`, `static/stats.js`, `static/sw.js`.

Uma regra de ouro do projeto, que você vai ver reforçada em vários lugares: **o backend nunca confia no frontend**. Se o backend perguntasse pro navegador "quantas tentativas você já usou?", qualquer pessoa poderia abrir o DevTools do navegador e mentir ("usei 0"), jogando pra sempre. Por isso o servidor guarda essa contagem ele mesmo, numa sessão (mais sobre isso na seção 5).

---

## 2. Mapa do projeto: quem fala com quem

```
                    ┌─────────────────────┐
                    │   Navegador (JS)     │
                    │  game.js, stats.js   │
                    └──────────┬───────────┘
                               │ fetch() — chamadas HTTP
                               ▼
                    ┌─────────────────────┐
                    │      main.py         │  ← rotas da API e da página
                    │  (FastAPI)           │
                    └──────────┬───────────┘
                               │ importa e chama
                     ┌─────────┴─────────┐
                     ▼                   ▼
              ┌────────────┐      ┌──────────────┐
              │  words.py   │      │ game_logic.py │
              │ (qual é a   │      │ (o palpite    │
              │  palavra    │      │  está certo?) │
              │  hoje?)     │      │               │
              └────────────┘      └──────────────┘
```

- `words.py` **não sabe nada** sobre HTTP, rotas ou o jogo em si — ele só sabe responder "qual palavra é a do dia X, nessa lista?". É puro cálculo de dados.
- `game_logic.py` **não sabe nada** sobre palavras do dia, sessões ou o site — ele só sabe comparar duas strings (o palpite e a resposta) e dizer letra por letra o que está certo.
- `main.py` é quem **junta tudo**: pergunta pro `words.py` qual é a palavra, pergunta pro `game_logic.py` se o palpite bateu, e decide o que responder pro navegador.

Essa separação (cada arquivo sabendo só da sua parte) é o primeiro conceito de boas práticas que vamos falar mais a fundo na seção 6 (SOLID) — o nome técnico é "responsabilidade única".

---

## 3. O fluxo de uma partida, passo a passo

Vamos seguir uma pessoa jogando o modo Padrão, do início ao fim.

### Passo 1 — a pessoa abre `termeeple.onrender.com`

O navegador faz uma requisição `GET /`. Em `main.py`, isso cai na função `pagina()` (dentro de `registrar_modo`, explicado na seção 4). Essa função:

1. Descobre qual é o dia de hoje (`today_index()`, em `words.py`).
2. Descobre qual é a palavra desse dia (`resolver_entrada_do_dia`).
3. Monta o teclado (esconde o Ç se a palavra não tiver essa letra).
4. Manda tudo isso pro template `index.html`, que gera o HTML final.

Repare: **o servidor sabe a palavra, mas nunca a manda pro navegador nesse HTML** — só o *tamanho* dela (`word_length`). Se a palavra certa estivesse escrita em algum lugar do HTML, qualquer pessoa poderia apertar `Ctrl+U` (ver código-fonte) e trapacear.

### Passo 2 — o JavaScript pergunta o estado do jogo

Assim que a página carrega, `game.js` roda essa linha:

```javascript
fetch(`/api${API_PREFIX}/state`)
```

Isso é uma segunda chamada, pro backend confirmar `day_index`, `word_length` e `max_attempts` — usado principalmente pra o JS saber se o `localStorage` do navegador (onde ele salva o progresso) ainda é válido pra hoje, ou se é um dia novo.

### Passo 3 — a pessoa digita um palpite e aperta Enter

`game.js` escuta os cliques no teclado na tela e as teclas do teclado físico. Quando a palavra está completa e a pessoa confirma, `submitGuess()` roda e manda:

```javascript
fetch(`/api${API_PREFIX}/guess`, {
    method: "POST",
    body: JSON.stringify({ guess: "TRUCO", day_index: 17 })
})
```

### Passo 4 — o backend valida e avalia o palpite

Essa requisição cai na função `guess()` dentro de `registrar_modo`, em `main.py`. Em ordem:

1. **A lista de palavras desse modo está vazia?** Se sim, erro 503 (serviço indisponível) — não tem palavra pra jogar.
2. **O `day_index` que o navegador mandou bate com o de hoje?** Se não (a pessoa deixou a aba aberta de ontem pra hoje, por exemplo), erro 409 — pede pra recarregar a página.
3. **Descobre a resposta certa** (`resolver_entrada_do_dia`).
4. **O palpite tem o tamanho certo e só letras?** Se não, erro 422.
5. **Quantas tentativas essa sessão já usou hoje, nesse modo?** Lê da sessão (cookie assinado), não confia em nada que veio do navegador.
6. **Já estourou o limite?** Se sim, erro 400.
7. **Soma mais uma tentativa e salva na sessão.**
8. **Chama `evaluate_guess()`** (em `game_logic.py`) pra saber, letra por letra, o que está certo/quase certo/errado.
9. **Verifica se ganhou** (`is_win()`).
10. **Monta a resposta em JSON** — inclusive `revealed_word` (a palavra certa, mas só se o jogo já acabou) e `ludopedia_link` (só se a pessoa ganhou).

### Passo 5 — o JavaScript pinta o tabuleiro

De volta em `game.js`, a resposta do passo 4 chega no `.then((data) => ...)`. Ele:

- Pinta cada letra da linha com a cor certa (`correct`/`present`/`absent`).
- Se o jogo acabou (`data.is_game_over`), mostra a palavra certa no banner (`showRevealBanner`), atualiza as estatísticas salvas no navegador (`recordResult`, em `stats.js`), e mostra o link da Ludopedia se ganhou.
- Salva o estado do tabuleiro no `localStorage`, pra se a pessoa recarregar a página, o jogo continue de onde parou.

### Diagrama resumido

```
Navegador                          Servidor (main.py)
    │                                     │
    │──── GET / ─────────────────────────▶│
    │                                     │ today_index() + resolver_entrada_do_dia()
    │◀─── HTML (sem a palavra!) ──────────│
    │                                     │
    │──── GET /api/state ─────────────────▶│
    │◀─── {day_index, word_length} ───────│
    │                                     │
    │  (pessoa digita "TRUCO" e confirma) │
    │                                     │
    │──── POST /api/guess {"guess": ...} ─▶│ conta tentativas na sessão
    │                                     │ evaluate_guess() em game_logic.py
    │◀─── {evaluation, is_win, ...} ───────│
```

---

## 4. Tour pelos arquivos, função por função

### `words.py` — "qual é a palavra de hoje?"

#### As três listas (`WORDS_PADRAO`, `WORDS_DIFICIL`, `WORDS_COMPOSTO`)

```python
WORDS_PADRAO: list[tuple[str, tuple[int, ...], str | None]] = [
    ("BINGO", (5,), None),
    ("GLOOM", (5,), "https://ludopedia.com.br/jogo/gloom"),
    ...
]
```

Cada item da lista é uma **tupla de 3 posições**: `(palavra, segmentos, link)`.
- `palavra`: a string que a pessoa precisa adivinhar, sempre maiúscula, sem espaço.
- `segmentos`: onde havia espaço no nome original. `"Blue Lagoon"` vira a palavra `"BLUELAGOON"` com segmentos `(4, 6)` — 4 letras, depois mais 6. Isso é só usado pra desenhar uma linha divisória visual no tabuleiro; o palpite continua sendo a palavra inteira, sem espaço.
- `link`: a URL da Ludopedia, se essa palavra veio de lá (`None` se for uma palavra genérica, tipo "BINGO").

#### `today_index()` — calculando "qual dia é hoje"

```python
def today_index():
    hoje_no_brasil = datetime.now(FUSO_BRASIL).date()
    data_atual = hoje_no_brasil - LAUNCH_DATE
    return data_atual.days
```

`LAUNCH_DATE` é o dia em que o jogo foi lançado (`date(2026, 7, 7)`). `today_index()` é simplesmente "quantos dias se passaram desde o lançamento". No dia do lançamento, é `0`. No dia seguinte, `1`. E assim por diante, pra sempre.

Por que calcular assim, em vez de guardar "qual é a palavra de hoje" num banco de dados? Porque **não precisa**: se todo mundo souber que dia é hoje (índice `17`, digamos) e todo mundo tiver a mesma lista de palavras, todo mundo cai automaticamente na mesma palavra — sem precisar de nenhum lugar pra "lembrar" isso. É elegante: zero estado pra gerenciar.

> **Por que `FUSO_BRASIL` e não só `date.today()`?** Esse foi exatamente o bug que corrigimos: o servidor roda num fuso horário diferente do Brasil (UTC), então sem especificar o fuso, a "meia-noite" do servidor não bate com a meia-noite de Brasília. `zoneinfo.ZoneInfo("America/Sao_Paulo")` resolve isso, forçando o cálculo a sempre considerar o horário de Brasília, não importa onde o servidor esteja fisicamente hospedado.

#### `entry_for_day()` — ciclando pela lista

```python
def entry_for_day(day_index, palavras):
    """Devolve (palavra, segmentos, link) do dia, ciclando pela lista."""
    return palavras[day_index % len(palavras)]
```

Aqui aparece o operador `%` (módulo — o resto de uma divisão). Se a lista tem 153 palavras e hoje é o dia `200`, `200 % 153 = 47` — ou seja, a palavra 47 da lista. Quando a lista acaba, ele **volta pro começo automaticamente**. É assim que, depois de usar todas as palavras, o ciclo recomeça sem precisar de nenhum código extra pra "resetar".

`word_for_day`, `segments_for_day` e `link_for_day` são só atalhos que chamam `entry_for_day` e pegam um pedaço específico da tupla (posição `[0]`, `[1]` ou `[2]`) — existem porque, historicamente, várias partes do código só precisavam de um pedaço da informação, e não fazia sentido forçar todo mundo a lidar com a tupla inteira.

#### `sponsored_entry_for_day()` — palavra patrocinada

```python
SPONSORED_WORDS: dict[date, tuple[str, tuple[int, ...], str | None]] = {
    # date(2026, 12, 1): ("EXEMPLO", (7,), "https://ludopedia.com.br/jogo/exemplo"),
}

def sponsored_entry_for_day(day_index):
    data_do_dia = LAUNCH_DATE + timedelta(days=day_index)
    return SPONSORED_WORDS.get(data_do_dia)
```

Isso é um "desvio" opcional: se uma data específica (uma parceria/patrocínio) estiver cadastrada nesse dicionário, o jogo usa essa palavra em vez de ciclar a lista normal, só nesse dia, só no modo Padrão. `.get()` num dicionário devolve `None` se a chave não existir — por isso não precisa de nenhum `if` verificando se a data está lá antes de perguntar.

#### `normalize_title()` e `_normalize_chars()` — transformando nome de jogo em palavra jogável

```python
def _normalize_chars(text: str) -> str:
    resultado = []
    for letra in text.upper():
        if letra == "Ç":
            resultado.append(letra)
            continue
        base = "".join(
            char for char in unicodedata.normalize("NFKD", letra) if not unicodedata.combining(char)
        )
        if base.isalpha():
            resultado.append(base.upper())
    return "".join(resultado)
```

Essa função pega um nome de jogo como `"Nemésis"` e devolve `"NEMESIS"` — maiúsculo, sem acento, sem pontuação. O truque está no `unicodedata.normalize("NFKD", ...)`: ele quebra uma letra acentuada em duas partes — a letra base (`E`) e o acento como um caractere "combinante" separado (```´```). Filtrando fora os caracteres combinantes (`unicodedata.combining(char)`), sobra só a letra base. O `Ç` é tratado à parte porque, diferente dos outros acentos, ele não "dissolve" em `C` + cedilha do mesmo jeito — ele é preservado como está.

`normalize_title()` usa isso pedaço por pedaço (`name.split()` — separa por espaço) pra também descobrir os "segmentos" (o tamanho de cada palavra original), que é o que vira a linha divisória visual no tabuleiro do modo Composto.

### `game_logic.py` — "o palpite está certo?"

Esse arquivo é pequeno de propósito: ele só sabe comparar duas strings, sem saber nada sobre o resto do jogo (nem sessão, nem HTTP, nem qual dia é hoje).

```python
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
```

Esse é o algoritmo clássico do Wordle, em **duas passadas**, e vale entender por quê — é o tipo de lógica que, se feita numa passada só, erra em palavras com letras repetidas.

- **Primeira passada:** marca tudo que está na posição certa (`CORRECT`) e "consome" essa letra do `estoque` (colocando `None` no lugar dela), pra ela não poder ser reaproveitada depois.
- **Segunda passada:** só olha o que sobrou (pulando o que já foi marcado `CORRECT`). Se a letra ainda existe em algum lugar do `estoque`, é `PRESENT` (existe, mas na posição errada) — e também é consumida do estoque, pra não ser contada duas vezes.

**Por que isso importa?** Imagine a resposta `"BANANA"` e o palpite `"AAAAAA"`. Sem esse cuidado de "consumir" cada letra da resposta uma única vez, o jogo marcaria as 6 letras `A` do palpite como certas/presentes — mas `"BANANA"` só tem 3 letras `A`. O `estoque` garante que cada letra da resposta só "empresta" seu status uma vez.

```python
def is_win(evalution):
    return all(item["status"] == LetterStatus.CORRECT for item in evalution)
```

`all(...)` devolve `True` só se **todos** os itens do que está dentro dos parênteses forem verdadeiros — nesse caso, só se toda letra do palpite for `CORRECT`.

### `main.py` — a cola entre tudo

#### `montar_teclado()`

```python
def montar_teclado(palavra):
    segunda_linha = list("ASDFGHJKL")
    if "Ç" in palavra:
        segunda_linha.append("Ç")
    segunda_linha.append("BACK")
    return [
        list("QWERTYUIOP"),
        segunda_linha,
        list("ZXCVBNM") + ["ENTER"],
    ]
```

`list("ASDFGHJKL")` transforma a string em uma lista de caracteres individuais: `['A', 'S', 'D', ...]`. O teclado só ganha a tecla `Ç` nos dias em que a palavra realmente precisa dela — assim ele fica mais limpo no resto do tempo.

#### `MODOS` — o dicionário de configuração central

```python
MODOS = {
    "padrao": {"prefixo": "", "palavras": WORDS_PADRAO, "max_attempts": 6, ...},
    "dificil": {"prefixo": "/dificil", "palavras": WORDS_DIFICIL, "max_attempts": 7, ...},
    "composto": {"prefixo": "/composto", "palavras": WORDS_COMPOSTO, "max_attempts": 8, ...},
}
```

Essa é a peça mais importante do arquivo pra entender a arquitetura toda: em vez de escrever a lógica de rotas **três vezes** (uma por modo), o projeto descreve cada modo como dados (um dicionário), e usa **uma função só** (`registrar_modo`) pra transformar cada entrada desse dicionário em rotas reais. Quer adicionar um quarto modo no futuro? Em teoria, é só adicionar uma entrada nova aqui (mais a lista de palavras em `words.py`) — sem tocar em `registrar_modo`.

#### `registrar_modo()` — a função que "fabrica" rotas

Essa é a função mais avançada do projeto, e vale ler com calma (voltamos a ela na seção 5, sobre *closures*). A ideia central:

```python
def registrar_modo(nome, config):
    prefixo = config["prefixo"]
    palavras = config["palavras"]
    # ...

    def pagina(request: Request):
        # usa `palavras`, `prefixo`, etc. de fora, sem receber como parâmetro
        ...

    def state():
        ...

    def guess(request: Request, payload: GuessRequest):
        ...

    app.get(prefixo or "/")(pagina)
    app.get(f"/api{prefixo}/state")(state)
    app.post(f"/api{prefixo}/guess")(guess)
```

`registrar_modo("padrao", MODOS["padrao"])` cria 3 funções novas (`pagina`, `state`, `guess`) que "lembram" pra sempre qual é a configuração do modo Padrão, e registra elas como rotas do FastAPI. Chamar `registrar_modo("dificil", MODOS["dificil"])` cria outras 3 funções, independentes, que lembram da configuração do Difícil. É por isso que, no final do arquivo:

```python
for _nome, _config in MODOS.items():
    registrar_modo(_nome, _config)
```

Esse `for` roda `registrar_modo` uma vez pra cada um dos 3 modos, criando as 9 rotas do projeto (3 modos × 3 rotas cada) a partir de **uma única implementação**.

#### `resolver_entrada_do_dia()`

```python
def resolver_entrada_do_dia(dia_atual, config):
    if config.get("patrocinavel"):
        patrocinada = sponsored_entry_for_day(dia_atual)
        if patrocinada is not None:
            return patrocinada
    return entry_for_day(dia_atual, config["palavras"])
```

Isso centraliza a regra "usa a palavra patrocinada se existir uma pra hoje E o modo permitir; senão, cicla a lista normal" — chamada tanto por `pagina()` quanto por `state()` e `guess()`, garantindo que os três nunca "discordem" sobre qual é a palavra do dia.

#### A sessão e o rate limit

```python
session_key = f"attempts_{nome}_{dia_atual}"
tentativas_usadas = request.session.get(session_key, 0)
```

`request.session` é fornecido pelo `SessionMiddleware` (configurado lá em cima com `secret_key`). Ele guarda dados num **cookie assinado** — o navegador guarda o cookie, mas não consegue alterá-lo sem invalidar a assinatura (porque não tem o `SECRET_KEY`). Isso é o que torna seguro confiar nesse número: mesmo que alguém edite o cookie manualmente tentando colocar `tentativas_usadas = 0`, o servidor detecta que a assinatura não bate e rejeita.

A chave inclui o **nome do modo** e o **dia** (`attempts_padrao_17`, `attempts_dificil_17`, ...) — assim, jogar no modo Difícil não consome as tentativas do Padrão, e tentativas de ontem não contam pra hoje.

```python
guess.__name__ = f"guess_{nome}"
guess = limiter.limit("20/minute")(guess)
```

Esse trecho existe por causa de um bug real que encontramos: a biblioteca `slowapi` (que faz o rate limiting) identifica cada rota internamente pelo **nome da função Python** (`func.__name__`). Como as 3 funções `guess` (uma por modo) originalmente se chamavam todas `"guess"`, o slowapi as tratava como *a mesma rota*, e cada requisição contava 3x pro limite. Renomear cada uma (`guess_padrao`, `guess_dificil`, `guess_composto`) resolve isso — é um detalhe de implementação de uma biblioteca externa que só descobrimos escrevendo um teste de regressão (veja a seção 7 sobre testes).

### `static/game.js` — o que roda no navegador

- Lê `word_length`, `max_attempts`, `modo` e `api_prefix` de atributos `data-*` no HTML (colocados lá pelo Jinja2/`main.py`) — assim o mesmo arquivo `.js` funciona pros 3 modos, sem precisar saber de antemão qual está ativo.
- `typeLetter()`/`doBackspace()`/`submitGuess()`: a lógica de digitar/apagar/confirmar.
- `saveBoardState()`/`restoreBoardState()`: salvam o tabuleiro inteiro no `localStorage` do navegador (não no servidor!), pra sobreviver a um recarregamento de página. Isso é só conveniência visual — a contagem de tentativas *de verdade* continua vindo do servidor.
- `shareOrCopy()`: usa a [Web Share API](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/share) do navegador (o menu nativo de compartilhar do celular/computador) quando disponível, e cai pra copiar o texto pro clipboard como alternativa.

### `static/stats.js` — estatísticas locais

Guarda jogos/vitórias/sequência/distribuição de tentativas no `localStorage`, por modo (`termeeple:stats:padrao`, `termeeple:stats:dificil`, ...). Repare que isso é **por navegador**, não por conta de usuário — o projeto não tem login, então as estatísticas ficam só naquele aparelho/navegador específico.

### `static/sw.js` — o service worker (PWA)

Um service worker é um "proxy" que roda no navegador entre o site e a rede, permitindo o app funcionar parcialmente offline e ser "instalável" como um app. A regra atual (depois da correção que fizemos): arquivos estáticos (`/static/*`, que não mudam de um dia pro outro) usam cache; a página e as chamadas de API sempre tentam a rede primeiro, porque mudam todo dia — cachear a página seria "congelar" a palavra do dia pra sempre no aparelho de quem já visitou o site uma vez.

### `templates/index.html` — o HTML gerado pelo Jinja2

Esse arquivo não é HTML puro — tem trechos de outra linguagem (Jinja2) misturados, que só existem no template, nunca chegam ao navegador do jeito que estão escritos aqui:

```html
<div id="board" data-word-length="{{ word_length }}" ...>
  {% for linha in range(max_attempts) %}
    <div class="board-row"> ... </div>
  {% endfor %}
</div>
```

`{{ word_length }}` é substituído pelo valor real (por exemplo, `6`) antes de mandar o HTML pro navegador. `{% for %}...{% endfor %}` repete o bloco de dentro uma vez por tentativa disponível — é assim que o tabuleiro tem o número certo de linhas pra cada modo, sem precisar de HTML escrito à mão pra cada tamanho possível.

---

## 5. Conceitos de Python usados no projeto (explicados do zero)

### Módulos e `import`

Cada arquivo `.py` é um "módulo". `from words import today_index` significa "vá no arquivo `words.py` e traga só a função `today_index` de lá pra eu poder usar aqui". Isso é o que permite dividir o projeto em pedaços pequenos e organizados, em vez de um arquivo gigante com tudo dentro.

### Tuplas vs. listas

```python
("BINGO", (5,), None)      # tupla — tamanho fixo, não muda depois de criada
["A", "S", "D", "F"]       # lista — pode crescer, encolher, mudar
```

O projeto usa **tupla** pra cada entrada de palavra porque essa informação nunca muda depois de definida (uma palavra sempre tem o mesmo tamanho de segmento). Usa **lista** pro teclado, porque o código precisa `.append()` a tecla `Ç` condicionalmente. Repare o detalhe: `(5,)` (com vírgula) é uma tupla de um item só; `(5)` sem vírgula seria só o número `5` entre parênteses — a vírgula é obrigatória pra Python entender que é uma tupla.

### Type hints (`list[tuple[str, tuple[int, ...], str | None]]`)

```python
WORDS_PADRAO: list[tuple[str, tuple[int, ...], str | None]] = [...]
```

Isso é uma **anotação de tipo** — um "aviso" pra quem lê o código (e pra ferramentas como editores e o `ruff`) sobre o formato esperado dos dados. Lendo de fora pra dentro:
- `list[...]` → é uma lista de...
- `tuple[str, tuple[int, ...], str | None]` → ...tuplas de 3 posições: uma `string`, depois uma tupla de números inteiros (`tuple[int, ...]` — o `...` significa "quantos inteiros forem, não tem tamanho fixo"), depois uma `string` **ou** `None` (`str | None` — o `|` significa "ou um, ou outro").

Importante: isso é só documentação pro leitor humano e pras ferramentas — o Python **não impede** você de colocar um valor de outro tipo ali (ele não vai travar em tempo de execução se você errar). Mas ajuda demais a entender o formato só de olhar a declaração, sem precisar ler o resto do arquivo.

### f-strings

```python
session_key = f"attempts_{nome}_{dia_atual}"
```

O `f` antes das aspas transforma a string numa "f-string" — qualquer coisa entre `{}` vira código Python de verdade, calculado e inserido ali. Se `nome = "padrao"` e `dia_atual = 17`, o resultado é a string `"attempts_padrao_17"`. É a forma moderna de "montar" texto misturando com variáveis (a alternativa antiga seria `"attempts_" + nome + "_" + str(dia_atual)`, bem mais verbosa).

### List comprehension

```python
"outros_modos": [
    (m, c["titulo"], c["prefixo"] or "/") for m, c in MODOS.items() if m != nome
],
```

Isso é uma forma compacta de escrever um `for` que constrói uma lista nova. É equivalente a:

```python
outros_modos = []
for m, c in MODOS.items():
    if m != nome:
        outros_modos.append((m, c["titulo"], c["prefixo"] or "/"))
```

`MODOS.items()` devolve pares `(chave, valor)` do dicionário — aqui, `m` é o nome do modo (`"padrao"`, `"dificil"`, ...) e `c` é a configuração dele. O `if m != nome` no final filtra fora o modo atual (não faz sentido mostrar um link "pra você mesmo"). `c["prefixo"] or "/"` usa o `or` como um atalho: se `c["prefixo"]` for uma string vazia (`""`, que é "falsa" em Python), usa `"/"` no lugar.

### `Enum`

```python
from enum import Enum

class LetterStatus(str, Enum):
    CORRECT = "correct"
    PRESENT = "present"
    ABSENT = "absent"
```

Um `Enum` é uma forma de dizer "essas são as únicas opções válidas pra essa coisa" — em vez de espalhar a string `"correct"` digitada à mão em vários lugares do código (e correr o risco de um dia digitar `"correto"` por engano em algum lugar), você usa `LetterStatus.CORRECT` sempre, e o Python garante que só existem essas 3 opções. Herdar de `str` também (`class LetterStatus(str, Enum)`) faz esse valor se comportar como uma string normal quando precisa (por exemplo, ao virar JSON na resposta da API).

### Funções que devolvem funções, e *closures*

Esse é provavelmente o conceito mais avançado do projeto, então vamos com calma. Uma *closure* é uma função definida **dentro** de outra função, que "lembra" das variáveis de fora dela mesmo depois que a função de fora já terminou de rodar.

```python
def registrar_modo(nome, config):
    palavras = config["palavras"]        # variável "de fora"

    def guess(request, payload):
        # essa função usa `palavras` e `nome`, mesmo sem recebê-los como parâmetro
        ... palavras ...
        ... nome ...

    return guess
```

Quando `registrar_modo("dificil", MODOS["dificil"])` roda, ele cria uma função `guess` que ficou "grudada" pra sempre no `palavras` e `nome` daquela chamada específica (a lista `WORDS_DIFICIL` e a string `"dificil"`). Quando `registrar_modo("padrao", ...)` roda de novo, é uma *nova* função `guess`, grudada nos valores do modo Padrão — as duas não se confundem, mesmo tendo o mesmo nome de variável (`palavras`) escrito no código-fonte.

É esse mecanismo que permite o projeto ter uma única implementação de `guess` no código, mas 3 comportamentos diferentes rodando em produção (um por modo) — sem `if modo == "padrao": ... elif modo == "dificil": ...` espalhado por todo canto.

### Decorators (`@`)

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

Um decorator "embrulha" uma função, adicionando comportamento sem você precisar mexer no corpo dela. `@app.get("/health")` diz pro FastAPI: "quando chegar uma requisição `GET /health`, chame essa função aqui e devolva o que ela retornar". No projeto, a maioria das rotas é registrada de outro jeito (`app.get(prefixo)(pagina)`, dentro de `registrar_modo`) porque o caminho da rota (`prefixo`) só é conhecido em tempo de execução, dentro do `for` — decorators (`@algo`) só funcionam com valores fixos, escritos diretamente no código.

### Exceptions (`try`/`except`, `HTTPException`)

```python
raise HTTPException(status_code=422, detail="palpite inválido")
```

`raise` interrompe a execução da função imediatamente e "levanta" um erro. O FastAPI sabe capturar `HTTPException` especificamente e transformar isso numa resposta HTTP de verdade (nesse caso, `422 Unprocessable Entity`, com aquele texto no corpo da resposta) — o navegador recebe isso como qualquer outra resposta de erro de uma API.

### Sessões e cookies assinados

```python
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "dev-insecure-key-troque-em-producao"),
)
```

Um *middleware* é um código que roda **em toda requisição**, antes (e depois) da função da rota específica. O `SessionMiddleware` lê/escreve um cookie especial no navegador da pessoa, que carrega os dados de `request.session` de forma **assinada criptograficamente** com o `SECRET_KEY`. "Assinado" quer dizer: o conteúdo é visível (não é secreto), mas vem com uma "prova" matemática de que ninguém alterou ele depois — se alguém editar o cookie manualmente, a assinatura não bate mais, e o servidor descarta a sessão inteira (tratando como se fosse uma pessoa nova, com 0 tentativas usadas — nunca aceitando um valor adulterado).

### `zoneinfo` e fusos horários

```python
from zoneinfo import ZoneInfo
FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")
datetime.now(FUSO_BRASIL)
```

Computadores costumam guardar hora internamente em UTC (o "horário de Greenwich", sem fuso). `ZoneInfo("America/Sao_Paulo")` é uma referência pra "traduzir" esse horário pra como ele aparece no relógio de Brasília, já considerando automaticamente qualquer regra de horário de verão que já existiu no Brasil no passado (mesmo não estando mais em vigor hoje). Sem passar um fuso explícito, `datetime.now()`/`date.today()` usam o fuso **do próprio computador/servidor** — que no caso do Render é UTC, não o horário de Brasília, e foi exatamente isso que causou o bug da palavra trocando 3h mais cedo.

---

## 6. SOLID aplicado ao Termeeple

SOLID é um conjunto de 5 princípios de design de código, criados originalmente pensando em programação orientada a objetos (classes). O Termeeple é majoritariamente **funcional/procedural** (funções soltas, poucas classes) — então nem todos os 5 se aplicam da mesma forma. Vou ser honesto sobre isso em vez de forçar a barra: entender *onde* um princípio se aplica bem (e onde simplesmente não é o formato certo pra ele) é mais útil do que decorar a sigla.

### **S** — Single Responsibility (Responsabilidade Única)

> Cada módulo/função deveria ter um, e só um, motivo pra mudar.

Esse é o princípio que mais aparece no projeto, de forma bem clara:
- `game_logic.py` muda só se a **regra do jogo** mudar (por exemplo, se você decidisse dar uma dica extra).
- `words.py` muda só se a forma de **escolher/gerar palavras** mudar.
- `main.py` muda só se **como as requisições HTTP são tratadas** mudar.

Se amanhã você quiser trocar a regra de avaliação (por exemplo, um modo "hard" do Wordle, onde reusar uma letra marcada como presente é obrigatório), você mexe só em `game_logic.py` — nada em `words.py` ou nas rotas precisa mudar. Isso é o princípio funcionando na prática.

### **O** — Open/Closed (Aberto pra extensão, fechado pra modificação)

> Deveria ser possível estender o comportamento sem alterar o código já existente.

O exemplo mais claro é o dicionário `MODOS` + a função `registrar_modo()`. Adicionar um modo novo (hipoteticamente, um "Modo Turbo") é, em teoria, **adicionar uma entrada no dicionário** — sem precisar tocar na lógica de `registrar_modo`, `pagina`, `state` ou `guess`. O comportamento "se estende" através de configuração, não de alterar o motor existente.

### **L** — Liskov Substitution

> Um "filho" deveria poder substituir o "pai" sem quebrar nada.

Esse princípio é sobre herança de classes — e o projeto praticamente não usa herança (só o `LetterStatus(str, Enum)`, que é um caso especial e não conta muito aqui). Sinceramente: **não force esse princípio num projeto que não usa classes/herança pra representar variações de comportamento**. Ele existe, é importante em outros contextos, mas tentar "encaixar" ele aqui seria complexidade desnecessária.

### **I** — Interface Segregation

> Não force um código a depender de coisas que ele não usa.

Dá pra ver uma versão informal disso em `words.py`: em vez de uma função gigante que devolve *tudo* sobre o dia, existem `word_for_day`, `segments_for_day`, `link_for_day` separadas — cada parte do código que só precisa do tamanho da palavra (por exemplo) pode chamar só `segments_for_day`, sem ser obrigada a lidar com o link da Ludopedia também. (Só que, no fundo, hoje todas essas três chamam `entry_for_day()`, que devolve a tupla inteira mesmo — então essa segregação é mais uma conveniência de leitura do que uma economia real de trabalho. Vale saber que existe esse meio-termo.)

### **D** — Dependency Inversion

> Dependa de abstrações, não de detalhes concretos.

`registrar_modo(nome, config)` recebe um `config` (um dicionário genérico) em vez de, por exemplo, receber `WORDS_PADRAO` e `6` e `"Termeeple"` como parâmetros soltos e específicos. Isso significa que `registrar_modo` não sabe (nem precisa saber) que existem exatamente 3 modos, ou quais são seus nomes — ele só sabe processar "qualquer coisa no formato de configuração de modo". Isso é uma forma simples (sem interfaces/classes abstratas, que seriam o jeito "livro-texto" de fazer isso) de aplicar a ideia central do princípio: o código genérico não deveria conhecer os detalhes específicos de cada caso de uso.

### Resumo honesto

Num projeto do tamanho do Termeeple (um app pequeno, funcional, sem múltiplas equipes mexendo nele), aplicar SOLID à risca com classes e interfaces seria over-engineering — complexidade que não se paga. O que vale a pena levar dessa seção: **S** e **O** aparecem de forma genuína e útil no código atual; **L** simplesmente não se aplica (não tem herança pra "violar"); **I** e **D** aparecem em versões mais informais, adaptadas ao estilo funcional do projeto. Isso é normal e correto — os princípios são ferramentas pra pensar, não uma checklist obrigatória.

---

## 7. Boas práticas do projeto

### Segurança: nunca confiar no cliente

Já foi mencionado, mas merece destaque como princípio geral: toda vez que o servidor precisa de um número que importa pra segurança/economia do jogo (quantas tentativas já foram usadas), ele guarda **do lado dele** (na sessão assinada), nunca aceitando esse número vindo do navegador. Um exemplo prático de "nunca confie no cliente" ao ler o código: o `payload.day_index` que vem do navegador só é usado pra **detectar** se o cliente está com uma página desatualizada (comparando com `today_index()` calculado no servidor) — nunca é usado como a verdade sobre qual dia é hoje.

### Testes automatizados (pytest)

O projeto tem `test_api.py`, `test_words.py`, `test_game_logic.py`. A ideia de um teste automatizado é simples: em vez de você abrir o navegador manualmente toda vez pra conferir se algo ainda funciona depois de uma mudança, escreve-se código que faz essa verificação sozinho, em menos de 1 segundo, toda vez que rodar `pytest`.

```python
def test_rate_limit_e_isolado_por_modo(client_dois_modos):
    ...
    assert ultima_resposta_padrao.status_code == 429
    ...
    assert resposta_dificil.status_code != 429
```

`assert` é a palavra-chave central de um teste: "isso **precisa** ser verdade; se não for, o teste falha e me avisa". Um bom teste de regressão (como esse) é escrito **depois** de encontrar um bug de verdade — ele existe especificamente pra garantir que aquele bug específico nunca volte a acontecer silenciosamente.

### Lint e formatação automática (ruff)

```bash
ruff check .    # procura erros/padrões arriscados
ruff format .   # arruma a formatação (espaçamento, aspas, etc.) sozinho
```

Isso existe pra você não precisar decorar/discutir estilo de código (tabs vs. espaços, aspas simples vs. duplas) — a ferramenta decide e aplica sozinha, de forma consistente em todo o projeto.

### CI (Integração Contínua)

O arquivo `.github/workflows/ci.yml` faz o GitHub rodar `pytest` e `ruff` automaticamente toda vez que você sobe código (push) ou abre um Pull Request — mesmo se você esquecer de rodar na sua máquina antes. É uma rede de segurança extra.

### Git: branches pequenas e Pull Requests, mesmo sozinho

O projeto segue o fluxo "branch nova pra cada mudança, depois PR pra `main`" mesmo sendo você a única pessoa desenvolvendo. As vantagens continuam valendo sozinho: cada mudança fica isolada e revisável separadamente, o histórico do `git log` conta uma história clara ("aqui corrigi X", "aqui adicionei Y"), e é fácil reverter *só* uma mudança específica sem afetar as outras, se precisar.

### DRY (Don't Repeat Yourself)

A consolidação de `word_for_day`/`segments_for_day`/`link_for_day` em `entry_for_day()` (seção 4) é um exemplo direto: as três faziam exatamente a mesma conta (`palavras[day_index % len(palavras)]`) e só mudavam qual posição da tupla devolviam no final. Reduzir isso a uma implementação central significa que, se um dia a lógica de "qual é o índice certo" mudar, você corrige em **um lugar só**, e todo o resto automaticamente se beneficia.

### YAGNI (You Aren't Gonna Need It)

O princípio oposto ao "programar pensando em todo futuro possível": construir só o que é necessário **agora**, sem antecipar funcionalidades hipotéticas. Um exemplo no projeto: `SPONSORED_WORDS` é só um dicionário simples, chaveado por data exata — não existe (ainda) um sistema de "campanhas com data de início/fim", múltiplos patrocinadores simultâneos, ou painel de administração. Se um dia isso virar necessidade real, aí sim vale complicar; até lá, a versão simples resolve o problema de hoje sem carregar peso morto.

---

## 8. Como estudar e expandir o projeto

Algumas sugestões de exercícios, da mais simples pra mais avançada, pra você praticar mexendo no próprio projeto:

1. **Leia os testes antes do código.** `test_game_logic.py` é o menor e mais direto — dá pra entender o que `evaluate_guess` deveria fazer só lendo os `assert`s, antes mesmo de olhar a implementação.
2. **Rode `pytest -v`** (o `-v` mostra o nome de cada teste individualmente) e tente prever, antes de rodar, quais vão passar.
3. **Experimente quebrar algo de propósito** numa branch separada (por exemplo, comente a linha `estoque[i] = None` em `evaluate_guess`) e rode os testes — veja qual teste passa a falhar, e por quê. É uma das formas mais rápidas de entender *por que* uma linha existe.
4. **Adicione um print() temporário** dentro de `resolver_entrada_do_dia` mostrando `dia_atual` e o que foi devolvido, rode o servidor local (`uvicorn main:app --reload`) e acompanhe no terminal enquanto navega no site.
5. **Tente adicionar um modo novo** (mesmo que só como exercício, numa branch que você depois descarta): uma entrada em `MODOS`, uma lista nova (mesmo vazia) em `words.py`. Isso testa se você realmente entendeu como `registrar_modo` funciona.
6. Quando sentir mais confiança, encare as funções mais dependentes de bibliotecas externas (`SessionMiddleware`, `slowapi.Limiter`) lendo a documentação oficial delas em paralelo — o `docs/dependencias.md` já te dá o ponto de partida de qual biblioteca faz o quê.

---

## 9. Glossário rápido

| Termo | O que significa |
|---|---|
| **Rota** | Uma combinação de método HTTP (GET/POST) + caminho (`/api/guess`) que o servidor sabe responder. |
| **Middleware** | Código que roda em toda requisição, antes/depois da rota específica (ex.: `SessionMiddleware`). |
| **Sessão** | Dados guardados entre requisições da mesma pessoa, via cookie assinado. |
| **Cookie assinado** | Dado visível no navegador, mas com uma "prova" criptográfica de que não foi alterado. |
| **Rate limiting** | Limitar quantas requisições uma mesma origem pode fazer num intervalo de tempo (`slowapi`). |
| **Closure** | Função interna que "lembra" das variáveis da função externa mesmo depois dela terminar. |
| **Decorator** | `@algo` acima de uma função — embrulha/modifica o comportamento dela. |
| **Type hint** | Anotação (`: str`, `-> list[int]`) documentando o tipo esperado, sem forçar isso em tempo de execução. |
| **Enum** | Conjunto fechado de valores válidos nomeados (`LetterStatus.CORRECT`). |
| **Service worker** | Script que roda "entre" o navegador e a rede, permitindo cache/funcionamento offline/PWA. |
| **PWA** | *Progressive Web App* — site que pode ser "instalado" e se comportar como um app nativo. |
| **UTC** | Horário universal, sem fuso — a maioria dos servidores usa isso internamente. |
| **Lint** | Análise automática do código procurando erros/padrões arriscados, sem executar o programa. |
| **CI** | *Continuous Integration* — rodar testes/checagens automaticamente a cada mudança no repositório. |
| **DRY** | *Don't Repeat Yourself* — evitar duplicar a mesma lógica em vários lugares. |
| **YAGNI** | *You Aren't Gonna Need It* — não construir agora o que só *pode* ser necessário no futuro. |
