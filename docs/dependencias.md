# Dependências do Termeeple — o que cada uma faz

Esse documento explica cada pacote que aparece no `requirements.txt` (produção) e no `requirements-dev.txt` (desenvolvimento), baseado no estado atual do seu repositório.

Duas colunas importantes pra entender:
- **Direto** = você (ou o código do projeto) usa esse pacote diretamente, com um `import`.
- **Transitivo** = você nunca importa ele; ele foi instalado sozinho porque um pacote direto precisa dele por baixo dos panos.

Não decorar tudo é normal — os transitivos você só precisa saber que existem, não como usar.

---

## `requirements.txt` — o que roda em produção

### O núcleo do app

| Pacote | Tipo | Pra que serve |
|---|---|---|
| **fastapi** | Direto | O framework web em si. Define suas rotas (`@app.get`, `@app.post`) e organiza toda a API. |
| **uvicorn** | Direto | O servidor que efetivamente executa o FastAPI. É o que roda quando você digita `uvicorn main:app`. FastAPI sozinho não "escuta" nenhuma porta — o uvicorn é quem faz isso. |
| **starlette** | Transitivo (mas importante) | O framework por baixo do FastAPI — literalmente, o FastAPI é construído em cima dele. É de onde vêm o `Request`, o `SessionMiddleware` (cookies assinados) e o `TestClient` que você usa nos testes. Você importa ele diretamente algumas vezes (`from starlette.middleware.sessions import SessionMiddleware`), mas a maior parte do tempo é o FastAPI usando ele por trás. |

### Templates e páginas

| Pacote | Tipo | Pra que serve |
|---|---|---|
| **Jinja2** | Direto | O motor de templates que renderiza o `templates/index.html` (é o que permite `{{ day_index }}` virar um valor real no HTML). |
| **MarkupSafe** | Transitivo | Dependência do Jinja2. Escapa automaticamente qualquer HTML perigoso nos templates, evitando ataques de XSS sem você precisar pensar nisso. |

### Validação de dados

| Pacote | Tipo | Pra que serve |
|---|---|---|
| **pydantic** | Direto | Valida e converte os dados que chegam na API. É o motivo de `class GuessRequest(BaseModel)` funcionar — se alguém mandar um JSON fora do formato esperado, o pydantic rejeita automaticamente, antes mesmo da sua função `guess()` rodar. |
| **pydantic_core** | Transitivo | O motor de validação por trás do pydantic (escrito em Rust, por performance). Você nunca importa ele direto. |
| **annotated-types** / **annotated-doc** | Transitivo | Ajudam o pydantic a entender anotações de tipo mais ricas do Python (o `Annotated[...]`). Suporte interno, sem uso direto seu. |
| **typing_extensions** / **typing-inspection** | Transitivo | Trazem recursos novos de "type hints" do Python pra funcionar em versões mais antigas da linguagem. Usados internamente por pydantic/fastapi. |

### Sessão, segurança e limite de requisições

| Pacote | Tipo | Pra que serve |
|---|---|---|
| **itsdangerous** | Direto (indireto) | Assina os cookies de sessão. É a peça que garante que ninguém consegue forjar o número de tentativas no cookie sem saber o `SECRET_KEY` — o coração da correção de segurança que fizemos. |
| **slowapi** | Direto | Implementa o rate limiting — o `@limiter.limit("20/minute")` na rota `/api/guess`. |

### Suporte de baixo nível (rede e terminal)

| Pacote | Tipo | Pra que serve |
|---|---|---|
| **anyio** | Transitivo | Biblioteca de concorrência assíncrona que o Starlette usa por baixo pra rodar código `async`/`sync` junto, sem você precisar gerenciar isso na mão. |
| **h11** | Transitivo | Implementa o protocolo HTTP/1.1 em baixo nível; usado pelo uvicorn pra falar HTTP de verdade com o navegador. |
| **click** | Transitivo | Biblioteca de linha de comando; o uvicorn usa pra processar os argumentos quando você roda `uvicorn main:app --reload`. |
| **colorama** | Transitivo | Faz as cores do terminal (os `INFO` verdes do uvicorn) funcionarem corretamente no Windows/PowerShell. |
| **idna** | Transitivo | Lida com nomes de domínio internacionalizados — dependência de baixo nível de bibliotecas de rede. |

---

## `requirements-dev.txt` — só pra desenvolvimento

A primeira linha, `-r requirements.txt`, não é um pacote — é uma instrução: "instale tudo do arquivo de produção também". É por isso que basta um `pip install -r requirements-dev.txt` pra ter o ambiente completo.

### Testes

| Pacote | Tipo | Pra que serve |
|---|---|---|
| **pytest** | Direto | O framework de testes. Roda tudo que está em `test_*.py` quando você digita `pytest`. |
| **httpx2** | Direto (indireto) | O `starlette.testclient.TestClient`, que seus testes de API usam pra simular requisições sem precisar de um servidor de verdade rodando, depende dele por baixo dos panos. |
| **pluggy** | Transitivo | Sistema de plugins do pytest — é o que permite estender o pytest com funcionalidades extras. Você não usa direto. |
| **iniconfig** | Transitivo | O pytest usa pra ler configurações em arquivos `.ini`/`pyproject.toml`. |
| **Pygments** | Transitivo | Colore a saída de erro do pytest no terminal (os trechos de código destacados quando um teste falha). |

### Lint e formatação

| Pacote | Tipo | Pra que serve |
|---|---|---|
| **ruff** | Direto | Faz duas coisas: `ruff check` (lint — encontra bugs, imports desorganizados) e `ruff format` (formatação automática de estilo). |

### Script manual (`scripts/manual_check.py`)

| Pacote | Tipo | Pra que serve |
|---|---|---|
| **requests** | Direto | Biblioteca clássica pra fazer chamadas HTTP em Python. Usada só pelo `scripts/manual_check.py`, pra testar a API manualmente sem precisar do navegador. |
| **certifi** | Transitivo | Fornece a lista de certificados HTTPS confiáveis que o `requests` usa pra validar conexões seguras. |
| **charset-normalizer** | Transitivo | Detecta automaticamente a codificação de texto (UTF-8, Latin-1, etc.) das respostas HTTP que o `requests` recebe. |
| **urllib3** | Transitivo | O motor de conexão HTTP de baixo nível por trás do `requests`. |

---

## Uma observação extra, fora do que você pediu

Enquanto eu conferia o conteúdo pra montar esse documento, reparei que seu `requirements.txt` está salvo em **UTF-16** (em vez do UTF-8 padrão) — isso é bem comum quando o PowerShell redireciona a saída de um comando com `>` (o `pip freeze > requirements.txt` do item 2). Não está causando problema nenhum hoje (o `pip install` e o CI leem ele numa boa), mas é um formato incomum pra esse tipo de arquivo, e algumas ferramentas mais rígidas podem estranhar no futuro. Se quiser, é só abrir o arquivo no VS Code, olhar no canto inferior direito (aparece a codificação atual), e usar "Save with Encoding" → UTF-8. Não é urgente, só deixo registrado.
