# Termeeple

Um clone do Wordle com tema de jogos de tabuleiro, em português. Uma palavra nova por dia, todo mundo joga a mesma — em cada um dos três modos independentes (Padrão, Difícil, Composto).

🔗 Jogue em: [termeeple.onrender.com](https://termeeple.onrender.com)

## Stack

- **Backend:** Python + [FastAPI](https://fastapi.tiangolo.com/), templates com Jinja2
- **Frontend:** HTML/CSS/JavaScript puro (sem framework), PWA com service worker
- **Sessão:** cookie assinado (`starlette.middleware.sessions`) — o servidor controla as tentativas do dia, o cliente nunca é confiável pra isso
- **Rate limiting:** [slowapi](https://github.com/laurentS/slowapi)
- **Testes:** pytest + `fastapi.testclient`
- **Lint/formatação:** [ruff](https://docs.astral.sh/ruff/)
- **CI:** GitHub Actions (lint + testes a cada push/PR)
- **Deploy:** [Render](https://render.com/) (free tier)

## Como funciona

- Cada dia tem um índice (`day_index`) calculado a partir de uma data de lançamento fixa, no fuso de Brasília.
- Quatro modos de jogo independentes, cada um com sua própria lista de palavras, sessão e estatísticas (não se misturam):
  - **Padrão** (`/`) — palavras de 5-6 letras, 6 tentativas.
  - **Difícil** (`/dificil`) — palavras de 7-10 letras, 7 tentativas.
  - **Composto** (`/composto`) — nomes de jogos com espaço (ex.: "Blue Lagoon" → `BLUELAGOON`), 8 tentativas.
  - **Legacy** (`/legacy`) — palavra de qualquer tamanho (desconhecido pro jogador), sem limite de tentativas por contagem: você aposta "meeples coins" (começa com 5) a cada palpite, que custa -1 de taxa. Acertar o tamanho ou uma posição rende +1, mas só na primeira vez que aquilo é descoberto (repetir informação já sabida não rende de novo); errar o tamanho ou ter uma letra ausente custa -1 sempre; letra certa em posição errada não muda nada. O jogo acaba ao acertar (revela a palavra) ou ao zerar as moedas (nunca revela). Reaproveita as palavras já curadas dos outros três modos (`words.WORDS_LEGACY`).
- A palavra de cada modo vem de uma lista fixa (`words.py`), ciclando pelo índice. Parte é curada a partir de nomes de jogos da [Ludopedia](https://ludopedia.com.br/), via `scripts/fetch_ludopedia_words.py` (rodado manualmente, de vez em quando) — quando a palavra vem de lá, acertar mostra um link pra ficha do jogo.
- É possível reservar uma palavra pra uma data específica (`SPONSORED_WORDS` em `words.py`, só no modo Padrão) — usado pra patrocínio pontual, sem nenhuma indicação visual na interface.
- O servidor guarda quantas tentativas cada sessão já usou hoje, o `attempt_number` nunca é aceito do cliente, só o servidor sabe a contagem real.

## Rodando localmente

\`\`\`bash
git clone https://github.com/diegoselingardi/termeeple.git
cd termeeple

python -m venv .venv
.venv\Scripts\Activate.ps1   # Linux/Mac: source .venv/bin/activate

pip install -r requirements-dev.txt
copy .env.example .env       # depois edite com uma SECRET_KEY real

uvicorn main:app --reload
\`\`\`

O app sobe em `http://localhost:8000`.

### Variáveis de ambiente

Veja `.env.example`. A única obrigatória em produção:

| Variável     | Descrição                                                                 |
| ------------ | -------------------------------------------------------------------------- |
| `SECRET_KEY` | Assina o cookie de sessão. Gere com `python -c "import secrets; print(secrets.token_hex(32))"` |

## Testes e lint

\`\`\`bash
pytest
ruff check .
ruff format .
\`\`\`

O CI roda essas três checagens automaticamente em todo push/PR pra `main`.

## Estrutura do projeto

\`\`\`
main.py              # rotas da API e da página
game_logic.py         # regra de avaliação do palpite dos 3 modos padrão (puro, sem I/O)
legacy_logic.py         # regras do modo Legacy: moedas, tolerância a tamanho diferente
words.py                 # lista de palavras e cálculo do dia
static/                 # CSS, JS do jogo, service worker, ícones
templates/               # HTML (Jinja2)
test_*.py                 # testes automatizados
scripts/manual_check.py    # script manual pra testar a API local (fora do pytest)
scripts/fetch_ludopedia_words.py  # busca candidatos a palavra do dia na API da Ludopedia
\`\`\`

## Documentação adicional

- [`docs/manual.md`](docs/manual.md) — manual didático explicando o funcionamento do jogo, o fluxo completo, conceitos de Python usados no projeto, SOLID e boas práticas (pensado pra quem está aprendendo Python).
- [`docs/dependencias.md`](docs/dependencias.md) — o que cada dependência do `requirements.txt`/`requirements-dev.txt` faz.

## Créditos

Paleta de cores baseada na identidade visual do [Canal do Tio Di](https://www.youtube.com/@canaldotiodi).

## Fluxo de contribuição

Mudanças passam por branch + pull request antes de ir pra `main`, mesmo em desenvolvimento solo — ajuda a manter histórico de revisão e facilita reverter algo pontual:

\`\`\`bash
git checkout -b minha-mudanca
# ... commits ...
git push origin minha-mudanca
# abrir PR no GitHub, conferir o checklist do template, dar merge
\`\`\`