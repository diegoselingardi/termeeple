# Termeeple

Um clone do Wordle com tema de jogos de tabuleiro, em português. Uma palavra nova por dia, todo mundo joga a mesma.

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

- Cada dia tem um índice (`day_index`) calculado a partir de uma data de lançamento fixa.
- A palavra do dia vem de uma lista fixa (`words.py`), ciclando pelo índice.
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
game_logic.py         # regra de avaliação do palpite (puro, sem I/O)
words.py               # lista de palavras e cálculo do dia
static/                 # CSS, JS do jogo, service worker, ícones
templates/               # HTML (Jinja2)
test_*.py                 # testes automatizados
scripts/manual_check.py    # script manual pra testar a API local (fora do pytest)
\`\`\`

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