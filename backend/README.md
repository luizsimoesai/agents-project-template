# backend

Built with [Aegra](https://github.com/ibbybuilds/aegra) -- a self-hosted LangSmith Deployments alternative.

----

# Dia 23/03/2026


```bash
aegra init
📂 Where should I create the project? [.]: backend 

🌟 Choose a template:
  1. New Aegra Project — A simple chatbot with message memory.
  2. ReAct Agent — An agent with tools that reasons and acts step by step.

Enter your choice [1]: 2
You selected: ReAct Agent — An agent with tools that reasons and acts step by step.

📥 Creating project...
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/aegra.json
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/src/backend/graph.py
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/src/backend/tools.py
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/src/backend/__init__.py
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/pyproject.toml
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/README.md
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/src/backend/state.py
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/src/backend/prompts.py
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/src/backend/context.py
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/src/backend/utils.py
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/.env.example
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/.gitignore
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/docker-compose.yml
  CREATE  /Users/luizsimoes/projetos/agents-project-template/backend/Dockerfile

🎉 New project created at /Users/luizsimoes/projetos/agents-project-template/backend

Next steps:
  cd backend
  cp .env.example .env       # Configure your environment
  uv sync                    # Install dependencies
  uv run aegra dev           # Start developing!
```

Alterei o arquivo aegra.json, context.py e graph.py, 
já que renomei a pasta 'backend' criada automaticamente pelo aegra para 'agent'.

```json
{
  "name": "backend",
  "dependencies": [
    "./src"
  ],
  "graphs": {
    "agent": "./src/agent/graph.py:graph" #< ---- de 'backend' para 'agent'
  }
}
```

### Instalação de ferramentas de desenvolvimento

```bash
uv add --dev pytest pytest-cov taskipy ruff mypy
```

----

# Dia 24/03/2026

- instalei sqlalchemy, alembic, pydantic-settings e asyncpg
- Ordem da criação dos arquivos com Claude Code:
- models/user.py
- core/settings.py
- db/engine.py
- migrations/env.py

```bash
src/
├── core/
│   ├── __init__.py
│   └── settings.py   ← lê o .env, expõe settings.db_url
└── db/
    ├── __init__.py
    └── engine.py     ← engine async + AsyncSessionLocal
migrations/
└── env.py            ← atualizado para usar settings + metadata do User
```

## Como funciona a conexão com o banco

A configuração do banco de dados está dividida em três arquivos, cada um com uma responsabilidade clara:

```
.env
 └─► src/core/settings.py   (lê as variáveis e monta a URL)
       ├─► src/db/engine.py      (usa settings.db_url na aplicação)
       └─► migrations/env.py     (usa settings.db_url nas migrations)
```

### `src/core/settings.py`

Usa `pydantic-settings` para ler o `.env` automaticamente. Expõe uma propriedade `db_url` que monta a URL de conexão no formato `postgresql+asyncpg://...` a partir das variáveis `POSTGRES_*`. Se `DATABASE_URL` estiver definida no `.env`, ela tem prioridade.

### `src/db/engine.py`

Cria o `engine` assíncrono usando `asyncpg` (driver não-bloqueante, compatível com FastAPI/asyncio) e o `AsyncSessionLocal` para abrir sessões com o banco. Uso nos endpoints:

```python
async with AsyncSessionLocal() as session:
    result = await session.execute(...)
```

### `migrations/env.py`

Configura o Alembic para rodar as migrations. Dois detalhes importantes deste arquivo:

1. **`fileConfig` só roda na thread principal** — quando o Aegra executa as migrations no startup, ele usa `asyncio.to_thread()`. Chamar `fileConfig()` a partir de uma thread secundária causa deadlock no sistema de logging. A verificação `threading.current_thread() is threading.main_thread()` evita isso.

2. **`include_object`** — filtra o autogenerate para que o Alembic só gerencie as tabelas definidas nos nossos modelos. Sem isso, o Alembic detectaria as tabelas internas do Aegra (`checkpoints`, `runs`, `thread`, etc.) como "removidas" e geraria comandos `DROP TABLE` que quebrariam o servidor.

### Comandos de migration

```bash
# Criar um novo arquivo de migration a partir dos modelos
uv run alembic revision --autogenerate -m "descrição"

# Aplicar todas as migrations pendentes
uv run alembic upgrade head

# Voltar uma migration
uv run alembic downgrade -1
```

> O Aegra aplica as migrations automaticamente no startup (`uv run aegra dev`), então normalmente só é preciso rodar `alembic upgrade head` manualmente após criar um novo arquivo de migration.


# 27/03/2026

Implementação de CRUD de Usuários + Autenticação JWT seguindo o padrão de camadas do Aegra.

## O que foi construído

A ideia central foi adicionar uma camada completa de **autenticação e autorização** à API, usando JWT (JSON Web Tokens), e expor endpoints para **criar, listar, atualizar e deletar usuários** — tudo protegido por token.

A implementação seguiu um padrão de três camadas bem definidas:

```
Request HTTP
    └─► Router (src/api/routes/)       ← recebe e valida a requisição
          └─► Service (src/services/)  ← executa a lógica de negócio
                └─► ORM / Banco        ← persiste ou consulta os dados
```

---

## Novos arquivos criados

```
src/
├── schemas/
│   ├── user.py          ← UserCreate, UserRead, UserUpdate
│   └── auth.py          ← LoginRequest, TokenResponse, TokenPayload
├── services/
│   ├── user_service.py  ← CRUD de usuários + hash de senha
│   └── auth_service.py  ← login e rotação de refresh token
├── core/
│   └── security.py      ← criação/decodificação de JWT + get_current_user
└── api/
    └── routes/
        ├── auth.py       ← POST /auth/register, /login, /refresh | GET /auth/me
        └── users.py      ← CRUD completo em /users (todos protegidos por JWT)
```

---

## Schemas (`src/schemas/`)

Schemas são contratos de interface: definem exatamente o que a API **aceita** e o que ela **retorna**, usando Pydantic para validação automática.

- **`UserCreate`** — usado no body do cadastro. Recebe `name`, `email` e `password` em texto puro. A senha nunca é armazenada assim.
- **`UserRead`** — o que a API retorna ao cliente. Contém apenas `id`, `name`, `email` e `created_at`. O campo `password_hash` está deliberadamente ausente para não vazar dados sensíveis.
- **`UserUpdate`** — todos os campos são opcionais, implementando semântica de PATCH: o cliente só envia o que quer alterar.
- **`LoginRequest`** — email + senha para autenticar.
- **`TokenResponse`** — par de tokens (`access_token` + `refresh_token`) retornado após login ou refresh.

---

## Segurança JWT (`src/core/security.py`)

JWT (JSON Web Token) é um padrão para transmitir informações de forma segura entre cliente e servidor. Um token JWT é assinado com uma chave secreta, então o servidor consegue verificar que ele não foi adulterado.

Implementamos dois tipos de token:

| Tipo | Validade | Uso |
|------|----------|-----|
| **Access Token** | 30 minutos | Enviado em toda requisição para autenticar o usuário |
| **Refresh Token** | 7 dias | Usado apenas em `/auth/refresh` para obter um novo par de tokens |

A separação entre os dois evita que um refresh token seja usado para acessar endpoints protegidos — o campo `type` no payload do JWT é validado a cada decodificação.

A dependência `get_current_user` é a "porteira" da API: ela é injetada automaticamente pelo FastAPI em qualquer endpoint protegido, extrai o token do header `Authorization: Bearer <token>`, valida a assinatura e a expiração, e retorna o `UserRead` do usuário autenticado.

---

## Services (`src/services/`)

Os services contêm toda a lógica de negócio — sem lógica nos routers e sem camada de repositório separada (queries direto no service, como manda o padrão Aegra).

### `UserService`

- **`create_user`** — faz o hash da senha com bcrypt (custo 12) antes de persistir. Captura `IntegrityError` do banco e retorna 409 se o email já existir.
- **`get_user_by_email`** — retorna o ORM model completo (com `password_hash`). Uso **exclusivo** do `AuthService` para verificar a senha no login. Nunca exposto via router.
- **`update_user`** — usa `model_dump(exclude_none=True)` para aplicar apenas os campos enviados pelo cliente (PATCH semântico).

### `AuthService`

- **`login`** — busca o usuário pelo email e verifica a senha com `passlib`. A mensagem de erro é sempre genérica ("Invalid credentials"), tanto para email inexistente quanto para senha errada — isso impede que um atacante descubra quais emails estão cadastrados.
- **`refresh`** — valida o refresh token e emite um **novo par** de tokens (rotação). O token antigo é descartado automaticamente.

Os services são injetados via `Depends(get_user_service)` / `Depends(get_auth_service)`, seguindo o mesmo padrão do Aegra, com `get_session` importado de `aegra_api.core.orm`.

---

## Routers (`src/api/routes/`)

Os routers são finos: apenas orquestram os services e declaram os contratos HTTP (método, path, código de status, schema de resposta).

### `auth.py` — endpoints públicos (sem JWT)

| Método | Path | O que faz |
|--------|------|-----------|
| POST | `/api/v1/auth/register` | Cria uma conta nova |
| POST | `/api/v1/auth/login` | Autentica e retorna tokens |
| POST | `/api/v1/auth/refresh` | Troca o refresh token por um novo par |
| GET | `/api/v1/auth/me` | Retorna o perfil do usuário autenticado |

### `users.py` — endpoints protegidos (JWT obrigatório)

O router foi criado com `dependencies=[Depends(get_current_user)]`, o que aplica a proteção JWT a **todos** os endpoints de uma vez, sem repetir o `Depends` em cada função.

| Método | Path | O que faz |
|--------|------|-----------|
| POST | `/api/v1/users` | Cria um usuário |
| GET | `/api/v1/users` | Lista usuários — **admin only** (paginável via `skip` e `limit`) |
| GET | `/api/v1/users/{id}` | Busca um usuário pelo ID — **admin only** |
| PATCH | `/api/v1/users/{id}` | Atualiza parcialmente um usuário |
| DELETE | `/api/v1/users/{id}` | Remove um usuário — **admin only** (retorna 204) |

---

## Dependências instaladas

```bash
uv add "bcrypt" "python-jose[cryptography]" "python-multipart" "email-validator"
```

- **`bcrypt`** — hashing seguro de senhas com bcrypt (cost factor 12)
- **`python-jose[cryptography]`** — criação e validação de JWTs (HS256)
- **`python-multipart`** — necessário para o `OAuth2PasswordBearer` do FastAPI
- **`email-validator`** — habilita o tipo `EmailStr` do Pydantic

---

## Configuração necessária no `.env`

Adicionar a chave secreta JWT (mínimo 32 caracteres). Sem ela, todos os tokens gerados em produção ficam vulneráveis:

```bash
# Gerar uma chave segura:
openssl rand -hex 32

# Adicionar no .env:
JWT_SECRET_KEY=<chave-gerada-acima>
```


----

# 27/03/2026 — Parte 2

Adição da coluna `is_active` na tabela `users` e das rotas de ativação/desativação de usuários, restritas a administradores.

---

## O que foi feito

| Arquivo | Alteração |
|---------|-----------|
| `src/models/user.py` | Nova coluna `is_active` |
| `migrations/versions/b3e9f1a2c4d5_add_is_active_to_users.py` | Migration para adicionar a coluna |
| `src/schemas/user.py` | `UserRead` agora expõe `is_active` e `is_admin` |
| `src/core/security.py` | Nova dependência `get_current_admin` + bloqueio de usuário inativo |
| `src/services/user_service.py` | Novo método `set_user_active` |
| `src/services/auth_service.py` | Login bloqueado se `is_active=False` |
| `src/api/routes/users.py` | Novas rotas de ativação/desativação; DELETE restrito a admin |

---

## Passo a passo didático: como adicionar uma nova coluna

Este é o fluxo completo percorrido nesta alteração. Sempre que quiser adicionar um campo novo, repita estas etapas na mesma ordem.

### Passo 1 — Modelo ORM (`src/models/user.py`)

O modelo é o ponto de partida: ele representa a tabela no banco de dados como uma classe Python. Adicionar um campo aqui é o equivalente a declarar que a coluna existe no SQLAlchemy.

```python
is_active: Mapped[bool] = mapped_column(
    Boolean,
    default=True,           # valor padrão no Python
    server_default='true',  # valor padrão no banco (para INSERT sem o campo)
)
```

- **`default`** — usado pelo Python quando você cria um objeto `User()` sem passar o campo.
- **`server_default`** — enviado ao banco como `DEFAULT true` na DDL. Crucial para o próximo passo.

### Passo 2 — Migration Alembic

O modelo Python e o banco de dados são mundos separados. Para que o banco reflita a alteração, você precisa criar uma **migration**: um script SQL versionado que o Alembic executa.

```bash
# Gerar automaticamente a partir do diff entre o modelo e o banco:
uv run alembic revision --autogenerate -m "add is_active to users"

# Aplicar todas as migrations pendentes:
uv run alembic upgrade head

# Verificar em qual migration o banco está agora:
uv run alembic current
```

O arquivo gerado contém dois métodos:

```python
def upgrade() -> None:
    op.add_column('users', sa.Column('is_active', sa.Boolean(),
                                     nullable=False, server_default='true'))

def downgrade() -> None:
    op.drop_column('users', 'is_active')
```

- **`upgrade`** — aplicado quando você roda `alembic upgrade head`.
- **`downgrade`** — executado se precisar reverter com `alembic downgrade -1`.
- **`server_default='true'`** — garante que as linhas **já existentes** no banco recebam `true` automaticamente, sem precisar de um UPDATE manual.

### Passo 3 — Schema Pydantic (`src/schemas/user.py`)

Após existir no banco, o campo precisa aparecer nas respostas da API. Adicionamos `is_active` e `is_admin` ao `UserRead`:

```python
class UserRead(BaseModel):
    ...
    is_admin: bool
    is_active: bool
```

Esses campos também são necessários para que a dependência `get_current_admin` (próximo passo) possa ler o flag sem ir ao banco de novo.

### Passo 4 — Dependência de autorização (`src/core/security.py`)

Criamos `get_current_admin`, que **estende** `get_current_user` adicionando a verificação de admin:

```python
async def get_current_admin(
    current_user: UserRead = Depends(get_current_user),
) -> UserRead:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

O FastAPI resolve as dependências em cadeia: `get_current_admin` → `get_current_user` → token → banco. Se o usuário não for admin, retorna 403 antes de chegar no endpoint.

Aproveitamos também para bloquear usuários inativos em `get_current_user`:

```python
if not user.is_active:
    raise HTTPException(status_code=401, detail="Inactive user")
```

E no login (`AuthService`), impedimos que um usuário inativo obtenha novos tokens:

```python
if user is None or not valid or not user.is_active:
    raise HTTPException(status_code=401, detail="Invalid credentials")
```

### Passo 5 — Service (`src/services/user_service.py`)

Adicionamos o método `set_user_active` que ativa ou desativa um usuário:

```python
async def set_user_active(self, user_id, is_active: bool) -> UserRead:
    user = ...  # busca pelo ID, 404 se não existir
    user.is_active = is_active
    await self.session.commit()
    return UserRead.model_validate(user)
```

Um único método para os dois casos (ativar e desativar), controlado pelo parâmetro `is_active`.

### Passo 6 — Rotas (`src/api/routes/users.py`)

Novas rotas adicionadas ao router de usuários, cada uma com `dependencies=[Depends(get_current_admin)]`:

| Método | Path | Proteção | O que faz |
|--------|------|----------|-----------|
| GET | `/api/v1/users` | Admin | Lista todos os usuários |
| GET | `/api/v1/users/{id}` | Admin | Busca um usuário pelo ID |
| PATCH | `/api/v1/users/{id}/activate` | Admin | Define `is_active=True` |
| PATCH | `/api/v1/users/{id}/deactivate` | Admin | Define `is_active=False` |
| DELETE | `/api/v1/users/{id}` | Admin | Remove o usuário permanentemente |

Listagem e busca de usuários também requerem admin — qualquer usuário autenticado ter acesso à lista completa de contas seria uma exposição desnecessária de dados.

---

## Como testar as novas rotas

Para testar rotas de admin, você precisa de um usuário com `is_admin=True`. Como ainda não há endpoint para promover um usuário a admin, faça diretamente no banco:

```bash
# Conectar ao PostgreSQL
docker exec -it <container_postgres> psql -U backend -d backend

# Promover um usuário a admin pelo email
UPDATE users SET is_admin = true WHERE email = 'luiz@test.com';
```

Depois, faça login com esse usuário para obter um token de admin e teste:

```bash
# Desativar um usuário
curl -X PATCH http://localhost:2026/api/v1/users/<UUID>/deactivate \
  -H "Authorization: Bearer <TOKEN_ADMIN>"

# Ativar um usuário
curl -X PATCH http://localhost:2026/api/v1/users/<UUID>/activate \
  -H "Authorization: Bearer <TOKEN_ADMIN>"

# Deletar (apenas admin)
curl -X DELETE http://localhost:2026/api/v1/users/<UUID> \
  -H "Authorization: Bearer <TOKEN_ADMIN>"
```


----

# 27/03/2026 — Parte 5

Autenticação JWT unificada com o Aegra.

---

## O problema: dois servidores, dois sistemas de auth

O Aegra roda **dois servidores simultâneos**:

| Servidor | Porta | Endpoints |
|----------|-------|-----------|
| FastAPI customizado | 2026 | `/api/v1/…` (nosso código) |
| LangGraph interno | 2026 (mesmo) | `/threads/…`, `/runs/…`, `/assistants/…` (Aegra nativo) |

Até este ponto, nosso `/api/v1/…` exigia JWT. Mas os endpoints internos do Aegra (`/threads`, `/runs`, etc.) estavam **sem autenticação** — qualquer pessoa que soubesse a URL poderia criar threads, executar agentes e ler histórico diretamente.

A solução é registrar um **handler de autenticação** no `aegra.json`. O Aegra chama esse handler em cada requisição aos seus endpoints internos, usando o mesmo token JWT que já emitimos no login.

---

## Passo 1 — Handler de autenticação (`src/auth/jwt.py`)

Criamos o módulo `src/auth/jwt.py` com um handler decorado com `@auth.authenticate`:

```python
from langgraph_sdk import Auth
from jose import JWTError, jwt
from src.core.settings import settings

auth = Auth()

@auth.authenticate
async def authenticate(headers: dict) -> dict:
    token = headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not token:
        raise Auth.exceptions.HTTPException(status_code=401, ...)

    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[...])

    if payload.get("type") != "access":
        raise Auth.exceptions.HTTPException(status_code=401, ...)

    return {
        "identity": payload["sub"],   # user_id (UUID)
        "display_name": payload["sub"],
        "permissions": ["authenticated"],
    }
```

O handler:
1. Extrai o `Bearer <token>` do header `Authorization`
2. Decodifica com a **mesma chave secreta** usada pelo nosso FastAPI
3. Rejeita refresh tokens (só aceita `type="access"`)
4. Retorna um dict com `identity` — o Aegra usa esse valor para isolar recursos por usuário

O `Auth()` vem de `langgraph_sdk` (dependência já presente no Aegra). `Auth.exceptions.HTTPException` é o equivalente ao `HTTPException` do FastAPI, mas para o contexto do handler de auth do Aegra.

---

## Passo 2 — Registrar o handler no `aegra.json`

```json
{
  "auth": {
    "path": "./src/auth/jwt.py:auth",
    "disable_studio_auth": true
  }
}
```

- `path` aponta para o objeto `auth` no módulo que criamos.
- `disable_studio_auth: true` mantém o LangGraph Studio acessível sem token localmente. **Em produção, altere para `false`** — o Studio expõe execução direta de grafos e leitura de estado. Como `aegra.json` é JSON estático (sem interpolação de variáveis), essa alteração deve ser feita manualmente antes do deploy.

A partir deste ponto, **todos os endpoints nativos do Aegra** — `/threads`, `/runs`, `/assistants`, etc. — passam a exigir o mesmo JWT que nosso `/api/v1/auth/login` emite.

---

## Passo 3 — Configuração de CORS (`aegra.json`)

O Aegra gerencia CORS centralmente no `aegra.json` — não é necessário adicionar middleware no `main.py`. Sem essa configuração, o browser bloqueia 100% das requisições de um frontend (Next.js, React, etc.) para a API.

```json
{
  "http": {
    "app": "./src/main.py:app",
    "cors": {
      "allow_origins": ["http://localhost:3000"],
      "allow_credentials": true,
      "allow_methods": ["*"],
      "allow_headers": ["*"]
    }
  }
}
```

- `allow_origins` — lista os domínios autorizados. Em produção, substitua `http://localhost:3000` pela URL real do frontend.
- `allow_credentials: true` — obrigatório para que o browser envie o header `Authorization: Bearer <token>` em requisições cross-origin.
- `allow_methods` e `allow_headers: ["*"]` — permitem todos os métodos e headers, o que é adequado para desenvolvimento. Em produção, pode-se restringir a `["GET", "POST", "PATCH", "DELETE"]` e `["Authorization", "Content-Type"]`.

## Resumo das mudanças

| Arquivo | O que mudou |
|---------|-------------|
| `src/auth/jwt.py` | Novo — handler `@auth.authenticate` que valida nossos JWTs |
| `aegra.json` | Seção `"auth"` com o handler JWT + seção `"http.cors"` para o frontend |

----

# 28/03/2026 — Refatoração interna

Revisão de qualidade, reuso e eficiência dos serviços implementados nos dias anteriores. Sem mudanças na API pública.

## O que foi feito

### `src/services/user_service.py` — extração de `_fetch_user`

Os métodos `get_user`, `update_user`, `set_user_active` e `delete_user` repetiam o mesmo bloco de busca + 404 quatro vezes:

```python
result = await self.session.execute(select(User).where(User.id == user_id))
user = result.scalar_one_or_none()
if user is None:
    raise HTTPException(status_code=404, detail="User not found")
```

Extraímos um helper privado `_fetch_user` que centraliza a lógica — qualquer alteração na mensagem de erro ou no status code agora exige um único edit.

----

# Dia 28/03/2026

## Suíte de testes

Criada suíte completa de testes unitários e de integração em `backend/tests/`.

### Estrutura

```
backend/tests/
├── conftest.py              # fixtures compartilhadas
├── test_security.py         # create_access_token, decode_token, get_current_user, get_current_admin
├── test_user_service.py     # UserService — todos os métodos
├── test_auth_service.py     # AuthService — login e refresh
├── test_auth_handler.py     # src.auth.jwt.authenticate (handler do Aegra)
└── test_routes_auth.py      # rotas /api/v1/auth/* (integração com httpx)
```

### Como rodar

```bash
# Todos os testes com cobertura
cd backend
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# Um arquivo específico
uv run pytest tests/test_user_service.py -v
```

### Cobertura atual

| Módulo | Cobertura |
|--------|-----------|
| `src/core/security.py` | 100% |
| `src/api/routes/auth.py` | 100% |
| `src/services/user_service.py` | 98% |
| `src/services/auth_service.py` | 97% |
| `src/auth/jwt.py` | 95% |

### Decisões de design

- **Serviços testados com mocks puros** — `AsyncMock(spec=AsyncSession)` e `AsyncMock(spec=LangGraphService)`, sem banco de dados real.
- **Rotas testadas com `httpx.AsyncClient`** e `app.dependency_overrides` — sem subir infraestrutura.
- **bcrypt com `rounds=4`** no conftest para que os testes de senha rodem em milissegundos (produção usa `rounds=12`).
- **`session.refresh.side_effect`** popula `created_at`/`updated_at` nos objetos ORM durante os testes, já que esses campos só têm `server_default` (o banco os preenche em produção).


----

# 06/04/2026 — Atualização Aegra v0.9.2

Atualização da dependência `aegra-cli` de `>=0.8.3` para `>=0.9.2` e correção do `Dockerfile`.

---

## O que mudou no Aegra

A v0.9.0 foi a principal mudança. Em resumo:

**Workers com escala horizontal** — Em produção (`aegra up`), o Aegra agora executa os grafos em processos separados ("workers") que consomem tarefas de uma fila Redis. Isso permite rodar várias instâncias em paralelo. Em desenvolvimento (`aegra dev`), o comportamento é exatamente o mesmo de antes — sem Redis, sem configuração extra.

**Heartbeat nos endpoints de espera** — Os endpoints `/runs/wait` e `/runs/join` agora enviam `\n` periódicos enquanto o agente processa, evitando que proxies (nginx, AWS ALB) encerrem a conexão por timeout. O resultado final continua sendo JSON normal — parsers padrão ignoram os `\n` automaticamente.

**Variáveis de configuração novas** (todas opcionais, só necessárias se ativar Redis):

| Variável | Padrão | O que faz |
|----------|--------|-----------|
| `REDIS_BROKER_ENABLED` | `false` | Ativa workers Redis em produção |
| `WORKER_COUNT` | `3` | Número de workers por instância |
| `N_JOBS_PER_WORKER` | `10` | Tarefas simultâneas por worker |
| `BG_JOB_TIMEOUT_SECS` | `3600` | Tempo máximo de execução (segundos) |

---

## O que foi alterado neste projeto

| Arquivo | Alteração |
|---------|-----------|
| `pyproject.toml` | `aegra-cli>=0.8.3` → `>=0.9.2` |
| `Dockerfile` | Adicionado `COPY src/ ./src/` no stage final — corrige falha de deploy em cloud |

O `COPY src/` estava ausente do stage final do `Dockerfile`, o que fazia o deploy em cloud falhar silenciosamente (em desenvolvimento o `docker-compose` mascarava o problema com um volume mount). Esse bug foi corrigido no template oficial do Aegra na v0.9.0.

### atualização em `.env.example`
```bash
# --- Aegra Workers (Redis) ---
# Ative apenas em produção (aegra up). Em desenvolvimento (aegra dev) não é necessário.
REDIS_BROKER_ENABLED=false
# REDIS_URL=redis://localhost:6379
# WORKER_COUNT=3              # workers por instância
# N_JOBS_PER_WORKER=10        # tarefas simultâneas por worker
# BG_JOB_TIMEOUT_SECS=3600   # tempo máximo de execução por run (segundos)
```

----

# 06/04/2026 — Correção: tabelas internas do Aegra não eram criadas em banco novo

## O problema

Ao subir o banco do zero (`docker compose down -v && uv run aegra dev`), o servidor falhava com:

```
UndefinedTableError: relation "assistant" does not exist
```

As tabelas internas do Aegra (`assistant`, `thread`, `runs`, etc.) nunca eram criadas.

## Por que acontece

O Aegra tem seu próprio sistema de migrations Alembic, com scripts bundled no pacote instalado. Ao iniciar, ele chama `find_alembic_ini()` para localizar qual `alembic.ini` usar — e essa função verifica o diretório de trabalho **primeiro**:

```python
# aegra_api/core/migrations.py
def find_alembic_ini() -> Path:
    cwd_ini = Path("alembic.ini")
    if cwd_ini.exists():
        return cwd_ini.resolve()   # <-- encontra o nosso alembic.ini aqui
    # ... bundled fallback nunca alcançado
```

Como o projeto tem seu próprio `alembic.ini` na raiz do `backend/`, o Aegra nunca chega ao fallback com os seus scripts internos. Resultado: as migrations do Aegra (que criam `assistant`, `thread`, `runs`, etc.) nunca rodam em banco novo.

**Nota:** Isso não está documentado nem reportado como bug no repositório do Aegra. O template `aegra init` não cria `alembic.ini` — o Aegra foi projetado para projetos sem Alembic próprio. A adição do Alembic ao projeto (para gerenciar tabelas customizadas como `users`) é o que cria o conflito. A descoberta veio da leitura direta do código-fonte instalado em `.venv`.

## A solução

Em vez de rodar as migrations do Aegra (o que causaria conflitos na tabela `alembic_version`), usamos `SQLAlchemy.create_all(checkfirst=True)` para criar as tabelas do Aegra diretamente a partir dos seus modelos ORM.

A função `_ensure_aegra_tables()` foi adicionada ao início de `migrations/env.py` e é chamada automaticamente a cada execução do Alembic:

```python
def _ensure_aegra_tables() -> None:
    from aegra_api.core.orm import Base as _AegraBase
    from aegra_api.settings import settings as _aegra_settings
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _create() -> None:
        _engine = create_async_engine(_aegra_settings.db.database_url)
        async with _engine.begin() as _conn:
            # uuid-ossp é necessário porque o modelo assistant usa
            # uuid_generate_v4() como server_default
            await _conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await _conn.run_sync(_AegraBase.metadata.create_all, checkfirst=True)
        await _engine.dispose()

    asyncio.run(_create())
```

**Por que `create_all` e não as migrations do Aegra?**

Rodar as migrations do Aegra (com `alembic upgrade head`) gravaria a revisão final do Aegra na tabela `alembic_version`. Na próxima vez que o Alembic rodasse para as migrations do projeto, ele encontraria uma revisão desconhecida na tabela e falharia com `CommandError: Can't locate revision`.

`create_all(checkfirst=True)` cria as tabelas sem tocar na `alembic_version`, então as duas bases de migrations coexistem sem conflito.

**Por que o `uuid-ossp`?**

O PostgreSQL 18 não habilita a extensão `uuid-ossp` por padrão. O modelo ORM do Aegra para a tabela `assistant` usa `public.uuid_generate_v4()::text` como `server_default` — função que só existe com essa extensão. Habilitamos a extensão antes do `create_all` para que a criação da tabela funcione. `IF NOT EXISTS` torna a operação idempotente.

## Limitação conhecida

`create_all(checkfirst=True)` só cria tabelas que ainda não existem. Se uma atualização futura do Aegra **adicionar colunas** a tabelas já existentes, o `create_all` não as adicionará. Nesse caso, é necessário:

- Em desenvolvimento: `docker compose down -v` e subir novamente
- Em produção: aguardar o Aegra corrigir o bug em `find_alembic_ini()` ou aplicar `ALTER TABLE` manualmente

----

# 10/04/2026 — Integração do BudgetMiddleware

Migração do agente de `StateGraph` manual para `create_agent` com adição do middleware customizado `langchain-budget-middleware` para rastreamento de tokens e custo por thread.

---

## Motivação

O agente original era construído manualmente com `StateGraph`, o que não permitia o uso de middlewares da API `create_agent` do LangChain. A migração foi necessária para integrar o `BudgetMiddleware`, que rastreia uso de tokens e custo em tempo real e emite eventos SSE consumidos pelo frontend.

---

## O que foi alterado

| Arquivo | Alteração |
|---------|-----------|
| `src/agent/graph.py` | Migração de `StateGraph` para `create_agent` + `@dynamic_prompt` + `BudgetMiddleware` |

---

## `src/agent/graph.py` — migração para `create_agent`

### Antes

O agente era um `StateGraph` com um nó `call_model` que invocava o modelo manualmente:

```python
async def call_model(state: State, runtime: Runtime[Context]) -> dict:
    model = load_chat_model(runtime.context.model).bind_tools(TOOLS)
    system_message = SystemMessage(
        content=runtime.context.system_prompt.format(
            system_time=datetime.now(tz=UTC).isoformat()
        )
    )
    response = await model.ainvoke([system_message, *state.messages])
    return {"messages": [response]}

graph = (
    StateGraph(State, input_schema=InputState, context_schema=Context)
    .add_node("agent", call_model)
    .add_node("tools", ToolNode(TOOLS))
    ...
    .compile(name="agent")
)
```

### Depois

O loop ReAct é gerado pelo `create_agent`. O system prompt e o budget passam a ser injetados via middleware:

```python
@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    return request.runtime.context.system_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )

graph = create_agent(
    model=_model,
    tools=TOOLS,
    context_schema=Context,
    middleware=[
        dynamic_system_prompt,
        BudgetMiddleware(
            emit_updates=True,
            scope="thread",
            token_limit=5_000,
            cost_limit=0.001,
            pricing=_pricing,
            warn_at=0.8,
            on_limit="end",
        ),
    ],
    name="agent",
)
```

### `@dynamic_prompt`

O decorator `@dynamic_prompt` da API de middlewares do LangChain substitui o system prompt antes de cada chamada ao modelo. Ele recebe um `ModelRequest` que expõe `request.runtime.context` — o mesmo `Context` dataclass do agente — e retorna uma `str` que vira o novo `SystemMessage`. Isso preserva o comportamento original de ler `runtime.context.system_prompt` e formatar com `{system_time}`.

### `BudgetMiddleware`

Instalado via `uv add --editable /Users/luizsimoes/projetos/budget-middleware` (pacote local em desenvolvimento). Configuração utilizada:

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `emit_updates` | `True` | Emite evento `budget_update` no stream após cada chamada |
| `scope` | `"thread"` | Acumula tokens ao longo de toda a thread |
| `token_limit` | `5_000` | Para o agente ao atingir 5k tokens |
| `cost_limit` | `0.001` | Para ao atingir $0,001 por thread |
| `pricing` | `TokenPricing(0.0008, 0.0024)` | Estimativa para modelo 120B OSS ($0,80/$2,40 por 1M tokens) |
| `warn_at` | `0.8` | Emite aviso ao atingir 80% do limite |
| `on_limit` | `"end"` | Encerra graciosamente (sem lançar exceção) |

### Eventos `budget_update`

A cada chamada ao modelo, o middleware emite um evento customizado no stream SSE:

```json
{
  "type": "budget_update",
  "tokens_input": 312,
  "tokens_output": 87,
  "tokens_total": 399,
  "token_limit": 5000,
  "token_percent": 0.0798,
  "cost_usd": 0.000458,
  "cost_limit": 0.001,
  "cost_percent": 0.458,
  "context_window_tokens": 399,
  "context_window_size": null,
  "warning_triggered": false,
  "limit_reached": false
}
```

O frontend consome esses eventos via `onCustomEvent` no `useStream` e exibe o componente `BudgetWidget` no canto superior direito do chat.

---

## Correção no `langchain-budget-middleware`

Durante os testes, identificou-se um comportamento indesejado: quando o limite era atingido **durante** uma chamada ao modelo, a resposta gerada era descartada e substituída pela mensagem de limite — o texto sumia da tela.

**Causa:** em `_process_call`, ao detectar que o acumulado ultrapassou o limite após a resposta, o middleware chamava `_handle_limit`, que descartava o `response` real e retornava uma mensagem artificial.

**Correção aplicada no pacote `budget-middleware`:**

`state.py` — novo campo para persistir o estado de limite na thread:
```python
budget_limit_reached: NotRequired[bool]
```

`middleware.py` — pré-check passa a ler a flag do state:
```python
already_reached = bool(state.get("budget_limit_reached") or False)
if already_reached or self._is_limit_reached(tokens_input, tokens_output):
    return self._handle_limit(...)
```

`middleware.py` — `_process_call` deixa a resposta atual passar e grava a flag para bloquear a próxima chamada:
```python
if limit_reached:
    state_update["budget_limit_reached"] = True
    return ExtendedModelResponse(
        model_response=response,   # resposta preservada
        command=Command(update=state_update),
    )
```

**Resultado:** a resposta que cruza o limite é exibida por completo. Somente na próxima mensagem o agente retorna a mensagem de limite.


----

# 12/05/2026 — Comportamentos internos do Aegra

## Assistente padrão (`_ensure_default_assistants`)

No startup, o Aegra cria automaticamente um assistente para cada grafo registrado em `aegra.json`. O assistente é criado com `user_id="system"` e `metadata.created_by="system"`, usando um UUID determinístico gerado via `uuid5(NAMESPACE, graph_id)` — o mesmo ID é sempre gerado para o mesmo nome de grafo, então reiniciar o servidor não duplica registros.

**Por que existe:** o assistente padrão permite usar o grafo diretamente via API sem criar um assistente primeiro — útil em deployments simples sem gerenciamento de usuários.

**Neste projeto:** cada usuário cria seus próprios assistentes. O assistente `system` nunca aparece no frontend porque `fetchAssistants()` em `frontend/lib/api/assistants.ts` filtra qualquer assistente com `metadata.created_by === "system"`. Não há motivo para remover esse comportamento — o filtro já é a solução correta.

---

## Checkpoints órfãos após deleção de threads

Ao deletar uma thread (`DELETE /threads/{thread_id}`), o Aegra remove o registro da tabela `threads` e cancela runs ativos — mas **não limpa os dados de checkpoint** (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`). Isso está documentado no próprio docstring do endpoint:

> *"Checkpoint history stored in the graph backend is not affected."*

Em produção com volume de conversas, essas tabelas crescem indefinidamente.

**Status:** bug conhecido, registrado na issue [#288](https://github.com/aegra/aegra/issues/288) do repositório oficial. O PR [#355](https://github.com/aegra/aegra/pulls/355) adiciona `scripts/checkpoint_cleanup.py`, um script de limpeza batchado com `--dry-run`, advisory lock do Postgres e proteção contra threads ativas. Testado em produção com ~3.8M de linhas / 224 GB.

**O que fazer:** aguardar o merge do PR #355 e atualizar o pacote com:

```bash
cd backend
uv sync
```

O constraint `aegra-cli>=0.9.2` em `pyproject.toml` é aberto para cima, então `uv sync` pegará a nova versão automaticamente quando publicada no PyPI. Antes de atualizar, verificar o changelog para breaking changes.

**Dados já acumulados:** o script `checkpoint_cleanup.py` limpa dados existentes — não é apenas preventivo. Usar `--dry-run` primeiro para estimar o impacto antes de executar.

**Por que não usar trigger de banco:** o próprio time do Aegra avaliou e rejeitou essa abordagem na issue #288, pois mistura ownership entre as tabelas do Aegra e as do LangGraph. A solução oficial é application-level (`adelete_thread()` no código do Aegra), o que virá com o PR #355.
