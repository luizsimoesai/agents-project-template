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

# 27/03/2026 — Parte 3

CRUD de Assistentes: endpoints para criar, listar, buscar, atualizar e deletar assistentes LangGraph, integrados à tabela `assistant` gerenciada pelo Aegra.

---

## O que é um "assistente" no contexto do Aegra?

Antes de entrar no código, é importante entender o conceito.

O Aegra usa o conceito de **assistente** para representar uma instância configurada de um grafo LangGraph. Pense assim:

- O **grafo** (`src/agent/graph.py`) é o "motor" — define a lógica do agente (o loop ReAct).
- O **assistente** é uma configuração salva desse motor para um usuário específico.

Cada assistente guarda três campos de configuração:

| Campo | O que é | Exemplo |
|-------|---------|---------|
| `config` | Configuração de baixo nível do LangGraph (ex: limites de recursão) | `{"recursion_limit": 10}` |
| `context` | Parâmetros lidos pelo `src/agent/context.py` em cada execução | `{"model": "anthropic/claude-sonnet-4-6", "system_prompt": "Você é..."}` |
| `metadata` | Dados livres para busca e filtro | `{"language": "pt-BR", "project": "suporte"}` |

Isso significa que cada usuário pode ter múltiplos assistentes apontando para o mesmo grafo, mas com comportamentos diferentes — um para suporte em português, outro com um prompt diferente para análise de dados, etc.

---

## Por que não criamos um modelo ORM nem uma migration?

A tabela `assistant` **pertence ao Aegra** — ela foi criada pelas migrations internas do framework quando você rodou `aegra dev` pela primeira vez. Mexer nela diretamente seria contornar a gestão do Aegra, o que quebraria o versionamento automático, o `CASCADE DELETE` e outras funcionalidades.

A solução foi **envolver** (`wrap`) o `AssistantService` que o próprio Aegra já oferece:

```
Nossa rota → Nosso AssistantService (wrapper) → AssistantService do Aegra → Banco
```

Esse padrão mantém o Aegra no controle da tabela e nos dá um ponto limpo para adaptar os schemas.

---

## Arquivos criados

```
src/
├── schemas/
│   └── assistant.py          ← AssistantCreate, AssistantRead, AssistantUpdate
├── services/
│   └── assistant_service.py  ← wrapper sobre o AssistantService do Aegra
└── api/
    └── routes/
        └── assistants.py     ← endpoints CRUD
```

`src/main.py` foi atualizado para registrar o novo router.

---

## Passo a passo: como foi construído

### Passo 1 — Entender o que o Aegra já oferece

Antes de escrever qualquer código, inspecionamos o `AssistantService` interno do Aegra (em `.venv/lib/python3.12/site-packages/aegra_api/`). Descobrimos:

- O construtor precisa de `AsyncSession` **e** `LangGraphService` (para validar o `graph_id`).
- O Aegra já expõe uma função `get_assistant_service` como dependência FastAPI — pronta para ser usada com `Depends()`.
- Todos os métodos recebem `user_identity: str` e filtram automaticamente os resultados pelo dono — ou seja, um usuário **nunca vê** os assistentes de outro.
- O campo `metadata` no Python é exposto com o alias `metadata_dict` (para não conflitar com atributos internos do Pydantic).

### Passo 2 — Schemas (`src/schemas/assistant.py`)

Criamos três schemas Pydantic que servem como "contrato" da nossa API — o que aceitamos e o que retornamos — independentemente do que o Aegra usa internamente.

**`AssistantCreate`** — body do POST:
```python
class AssistantCreate(BaseModel):
    name: str
    description: str | None = None
    graph_id: str = "agent"      # padrão: único grafo do projeto
    config: dict[str, Any] = {}
    context: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
```

**`AssistantRead`** — o que a API retorna. Note que `user_id` foi **omitido** propositalmente: o cliente já sabe quem é pelo token, e expor o `user_id` seria informação redundante e potencialmente sensível.

**`AssistantUpdate`** — todos os campos opcionais (PATCH semântico).

### Passo 3 — Service wrapper (`src/services/assistant_service.py`)

Este é o ponto central da implementação. O `AssistantService` não fala com o banco diretamente — ele delega para o Aegra e cuida da tradução de schemas.

```python
from aegra_api.services.assistant_service import (
    AssistantService as AegraService,
    get_assistant_service as get_aegra_service,
)

class AssistantService:
    def __init__(self, _svc: AegraService) -> None:
        self._svc = _svc
```

O padrão de **composição** (guardar o serviço do Aegra como `self._svc`) é preferível a herança aqui porque não queremos expor todos os métodos internos do Aegra — só os que fazem sentido para a nossa API.

**Conversão de resposta** — o único ponto não trivial é o campo `metadata`:

```python
def _to_read(a: AegraAssistant) -> AssistantRead:
    return AssistantRead(
        ...
        metadata=a.metadata_dict,  # alias do Aegra para evitar conflito com Pydantic
        ...
    )
```

**Factory de dependência** — seguindo o padrão do projeto:

```python
def get_assistant_service(
    _svc: AegraService = Depends(get_aegra_service),
) -> AssistantService:
    return AssistantService(_svc)
```

O FastAPI resolve `get_aegra_service` automaticamente (que por sua vez resolve `get_session` e `get_langgraph_service`). Nossa factory só precisa envolver o resultado.

### Passo 4 — Router (`src/api/routes/assistants.py`)

O padrão é idêntico ao `users.py`: proteção JWT no router inteiro e `current_user` injetado em cada handler para extrair o `user_id`.

```python
router = APIRouter(
    prefix="/assistants",
    tags=["assistants"],
    dependencies=[Depends(get_current_user)],  # JWT em todos os endpoints
)
```

A diferença do `users.py` é que aqui o `assistant_id` no path é `str` (não `uuid.UUID`), porque o Aegra armazena os IDs como `TEXT` no banco:

```python
@router.get("/{assistant_id}", response_model=AssistantRead)
async def get_assistant(
    assistant_id: str,   # ← str, não uuid.UUID
    ...
```

### Passo 5 — Registrar o router (`src/main.py`)

```python
from src.api.routes.assistants import router as assistants_router

app.include_router(assistants_router, prefix="/api/v1")
# → Endpoints ficam em /api/v1/assistants/...
```

---

## Endpoints disponíveis

| Método | Path | Status | O que faz |
|--------|------|--------|-----------|
| POST | `/api/v1/assistants` | 201 | Cria um assistente |
| GET | `/api/v1/assistants` | 200 | Lista os assistentes do usuário |
| GET | `/api/v1/assistants/{id}` | 200 | Busca um assistente pelo ID |
| PATCH | `/api/v1/assistants/{id}` | 200 | Atualiza parcialmente (Aegra incrementa a versão) |
| DELETE | `/api/v1/assistants/{id}` | 204 | Remove o assistente e todos os seus runs/versões |

Todos os endpoints exigem autenticação JWT. Cada usuário só vê e gerencia os seus próprios assistentes.

---

## Como testar

```bash
# 1. Criar um assistente simples
curl -X POST http://localhost:2026/api/v1/assistants \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Meu Assistente"}'

# 2. Criar com contexto customizado (muda o comportamento do agente)
curl -X POST http://localhost:2026/api/v1/assistants \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Assistente PT",
    "context": {
      "system_prompt": "Você é um assistente prestativo que responde sempre em português.",
      "model": "anthropic/claude-sonnet-4-6"
    }
  }'

# 3. Listar assistentes
curl http://localhost:2026/api/v1/assistants \
  -H "Authorization: Bearer <TOKEN>"

# 4. Atualizar (Aegra incrementa version automaticamente)
curl -X PATCH http://localhost:2026/api/v1/assistants/<ASSISTANT_ID> \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"description": "Assistente para conversas em português"}'

# 5. Deletar (remove o assistente, seus runs e suas versões)
curl -X DELETE http://localhost:2026/api/v1/assistants/<ASSISTANT_ID> \
  -H "Authorization: Bearer <TOKEN>"
```


----

# 27/03/2026 — Parte 4

Chat com Assistentes: threads de conversa e execução do grafo LangGraph com memória persistente.

---

## O que é uma Thread?

Antes de entrar no código, é fundamental entender o modelo de conversas do LangGraph.

Uma **thread** é uma sessão de conversa. Pense nela como um "fio" que conecta todas as mensagens trocadas com o agente:

```
Thread
 ├─ Mensagem 1: "Olá!"          → AI: "Olá! Como posso ajudar?"
 ├─ Mensagem 2: "Quanto é 2+2?" → AI: "4."
 └─ Mensagem 3: "E o dobro?"    → AI: "8."   ← agente lembra do contexto anterior
```

O histórico **não fica na tabela `thread`** — ele fica no **checkpointer** do LangGraph, que armazena snapshots do estado do grafo no PostgreSQL. A tabela `thread` é apenas um registro de metadados (quem criou, qual assistente, status).

Cada thread está vinculada a um assistente. Isso significa que as configurações do assistente (`model`, `system_prompt`, etc.) são aplicadas em todas as mensagens dessa conversa.

---

## Arquivos criados

```
src/
├── schemas/
│   └── thread.py         ← ThreadCreate, ThreadRead, ChatRequest, ChatResponse, MessageRead
├── services/
│   └── thread_service.py ← CRUD de threads + execução do grafo + leitura de histórico
└── api/
    └── routes/
        └── threads.py    ← endpoints de threads e chat
```

`src/main.py` foi atualizado para registrar o novo router.

---

## Passo a passo: como foi construído

### Passo 1 — Entender a tabela `thread` do Aegra

A tabela `thread` no banco tem esta estrutura:

| Coluna | Tipo | Notas |
|--------|------|-------|
| `thread_id` | TEXT PK | UUID gerado pela nossa aplicação |
| `status` | TEXT | `idle \| busy \| interrupted \| error` |
| `metadata_json` | JSONB | Dados livres — guardamos `assistant_id`, `thread_name` aqui |
| `user_id` | TEXT | Dono da thread |
| `created_at` | TIMESTAMP | Auto |
| `updated_at` | TIMESTAMP | Auto |

O `assistant_id` não tem uma coluna dedicada — o Aegra guarda dados adicionais em `metadata_json`. Por isso, quando lemos uma thread, extraímos o `assistant_id` de `metadata_json.get("assistant_id")`.

### Passo 2 — Schemas (`src/schemas/thread.py`)

Cinco schemas definem o contrato da API:

- **`ThreadCreate`** — body do POST para criar uma thread. Requer apenas `assistant_id`.
- **`ThreadRead`** — resposta da API. Extrai `assistant_id` e `thread_name` do `metadata_json` para simplificar o acesso do cliente.
- **`ChatRequest`** — body do POST `/chat`. Apenas a mensagem em texto puro.
- **`ChatResponse`** — resposta do agente com `thread_id` e `message`.
- **`MessageRead`** — uma entrada no histórico, com `role` ("human" ou "ai") e `content`.

### Passo 3 — Service (`src/services/thread_service.py`)

Este é o arquivo mais importante. O `ThreadService` tem **duas dependências**, não uma:

```python
class ThreadService:
    def __init__(self, session: AsyncSession, langgraph_service: LangGraphService):
        self.session = session
        self._lg = langgraph_service
```

- **`session`** — para CRUD direto na tabela `thread` (mesmo padrão do `UserService`)
- **`langgraph_service`** — para executar o grafo e ler o histórico do checkpointer

**Por que duas dependências?** Porque as responsabilidades são diferentes:
- Criar/listar/deletar uma thread → banco de dados via SQLAlchemy
- Conversar / ler histórico → LangGraph via checkpointer

---

**Criação de thread:**

```python
thread = AegraThread(
    thread_id=str(uuid.uuid4()),   # geramos o UUID aqui (não tem server_default)
    status="idle",
    metadata_json={
        "assistant_id": data.assistant_id,
        "graph_id": "agent",
        "owner": user_id,
        "thread_name": data.thread_name,
    },
    user_id=user_id,
)
```

Geramos o `thread_id` manualmente porque a tabela do Aegra não tem `server_default` para esse campo (diferente da tabela `users` que usa `uuid_generate_v4()`).

---

**Execução do chat:**

Este é o coração da implementação. O método `chat()` faz:

```python
# 1. Montar o config do LangGraph
config = {"configurable": {"thread_id": thread_id}}

# 2. Chamar o grafo passando o contexto do assistente via kwarg context=
result = await graph.ainvoke(
    {"messages": [HumanMessage(content=message)]},
    config,
    context=assistant.context or {},   # model, system_prompt do assistente
)

# 2. Obter uma instância do grafo com o checkpointer injetado
async with self._lg.get_graph("agent", config=config, access_context="threads.create_run") as graph:

    # 3. Invocar o grafo com a mensagem do usuário
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        config,
    )

# 4. Extrair a última mensagem (resposta do agente)
last = result["messages"][-1]
```

**Por que `async with`?** O `get_graph()` é um context manager assíncrono — ao entrar no bloco, o Aegra injeta o checkpointer PostgreSQL no grafo. Isso garante que cada requisição receba uma instância isolada do grafo com acesso à persistência.

**Por que `thread_id` no configurable?** O checkpointer do LangGraph usa o `thread_id` como chave para identificar qual histórico de conversa deve ser carregado. Sem ele, o agente não teria memória entre chamadas.

**Por que `context=assistant.context`?** O grafo define `context_schema=Context` e recebe o contexto de runtime via o mecanismo `Runtime[T]` do LangGraph. Esse mecanismo é alimentado pelo kwarg `context=` do `ainvoke`/`astream` — não pelo `configurable`. Espalhar os campos de contexto diretamente em `configurable` não popula o `Runtime[T]` e os valores seriam ignorados pelo nó `call_model`.

---

**Leitura do histórico:**

```python
async with self._lg.get_graph("agent", access_context="threads.read") as graph:
    state = await graph.aget_state(config)

messages = state.values.get("messages", [])
```

`aget_state()` lê o último checkpoint da thread — que contém o estado completo do grafo, incluindo todos os mensagens acumuladas. O `access_context="threads.read"` informa ao Aegra que estamos apenas lendo, não executando o grafo.

### Passo 4 — Router (`src/api/routes/threads.py`)

O endpoint `/chat` é o mais interessante porque precisa de **duas dependências de serviço**:

```python
@router.post("/{thread_id}/chat")
async def chat(
    thread_id: str,
    body: ChatRequest,
    current_user: UserRead = Depends(get_current_user),
    thread_service: ThreadService = Depends(get_thread_service),
    assistant_service: AssistantService = Depends(get_assistant_service),  # ← reutilizado!
):
    thread = await thread_service.get_thread(thread_id, str(current_user.id))
    assistant = await assistant_service.get(thread.assistant_id, str(current_user.id))
    return await thread_service.chat(thread_id, body.message, assistant, str(current_user.id))
```

O router busca o assistente vinculado à thread antes de chamar o service. Isso é intencional — o router orquestra a busca das dependências, e o service executa a lógica. A separação mantém o `ThreadService` agnóstico ao `AssistantService`.

### Passo 5 — Registrar o router (`src/main.py`)

```python
from src.api.routes.threads import router as threads_router
app.include_router(threads_router, prefix="/api/v1")
# → Endpoints ficam em /api/v1/threads/...
```

---

## Endpoints disponíveis

| Método | Path | Status | O que faz |
|--------|------|--------|-----------|
| POST | `/api/v1/threads` | 201 | Cria uma thread vinculada a um assistente |
| GET | `/api/v1/threads` | 200 | Lista as threads do usuário |
| GET | `/api/v1/threads/{id}` | 200 | Busca uma thread pelo ID |
| DELETE | `/api/v1/threads/{id}` | 204 | Remove a thread e todo o histórico |
| POST | `/api/v1/threads/{id}/chat` | 200 | Envia uma mensagem e aguarda a resposta (bloqueante) |
| POST | `/api/v1/threads/{id}/chat/stream` | 200 | Envia uma mensagem e recebe tokens em streaming (SSE) |
| GET | `/api/v1/threads/{id}/history` | 200 | Retorna o histórico completo da conversa |

---

## Como testar

```bash
# 1. Criar um assistente com prompt personalizado
curl -X POST http://localhost:2026/api/v1/assistants \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Assistente PT",
    "context": {"system_prompt": "Você é um assistente que responde em português."}
  }'

# 2. Criar uma thread vinculada ao assistente
curl -X POST http://localhost:2026/api/v1/threads \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"assistant_id": "<ASSISTANT_ID>", "thread_name": "Conversa 1"}'

# 3. Enviar uma mensagem (bloqueante — aguarda a resposta completa)
curl -X POST http://localhost:2026/api/v1/threads/<THREAD_ID>/chat \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá! Quanto é 2 + 2?"}'

# 4. Continuar a conversa (o agente lembra do contexto)
curl -X POST http://localhost:2026/api/v1/threads/<THREAD_ID>/chat \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"message": "E o dobro desse resultado?"}'

# 5. Ver o histórico completo da conversa
curl http://localhost:2026/api/v1/threads/<THREAD_ID>/history \
  -H "Authorization: Bearer <TOKEN>"

# 6. Deletar a thread (remove a thread e os runs via CASCADE)
# Nota: o histórico de mensagens (checkpoints LangGraph) permanece no banco —
# esse é o comportamento documentado do Aegra: checkpoints são mantidos separadamente.
curl -X DELETE http://localhost:2026/api/v1/threads/<THREAD_ID> \
  -H "Authorization: Bearer <TOKEN>"
```

---

# 27/03/2026 — Parte 5

Streaming de respostas (SSE) e autenticação JWT unificada com o Aegra.

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

### Atenção: SSE com autenticação não funciona com `EventSource`

O `EventSource` nativo do browser não suporta headers customizados — ele não consegue enviar o `Authorization: Bearer`. Para consumir o endpoint de streaming autenticado, o frontend deve usar `fetch()` com `ReadableStream`:

```typescript
// ✅ Correto — fetch suporta headers customizados
const res = await fetch(`/api/v1/threads/${threadId}/chat/stream`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ message }),
});

const reader = res.body!.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = decoder.decode(value);
  // parsear eventos SSE: linhas "event: ..." e "data: ..."
}

// ❌ Errado para endpoints autenticados
const es = new EventSource(`/api/v1/threads/${threadId}/chat/stream`);
// não há como passar o token JWT
```

---

## Passo 3 — Endpoint de streaming (`src/api/routes/threads.py`)

O streaming usa o mesmo `StreamingResponse` do FastAPI, envolvendo o gerador assíncrono `stream_chat()` que já estava implementado no `ThreadService`.

```python
from fastapi.responses import StreamingResponse

@router.post("/{thread_id}/chat/stream")
async def stream_chat(thread_id, body, current_user, thread_service, assistant_service):
    thread = await thread_service.get_thread(thread_id, str(current_user.id))
    assistant = await assistant_service.get(thread.assistant_id, str(current_user.id))
    return StreamingResponse(
        thread_service.stream_chat(thread_id, body.message, assistant, user_id=str(current_user.id)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

Os headers `Cache-Control: no-cache` e `X-Accel-Buffering: no` são essenciais para que proxies (nginx, Cloudflare) não tentem armazenar o stream em buffer antes de enviá-lo ao cliente.

---

## Como funciona o streaming internamente

O método `stream_chat()` no `ThreadService` usa `graph.astream()` com `stream_mode=["messages"]`. O LangGraph emite tuplas `(mode, chunk)` onde o chunk pode ser:

- `BaseMessageChunk` — um fragmento de token (ex: `"Ol"`, `"á"`, `" mundo"`)
- `BaseMessage` — uma mensagem completa (ex: `ToolMessage` após executar uma ferramenta)

Cada chunk é formatado como um evento SSE pelo `format_sse_message()` do Aegra:

```
event: metadata
data: {"run_id": "...", "attempt": 1}

event: messages/metadata
data: {"<msg_id>": {"metadata": {...}}}

event: messages/partial
data: [{"type": "AIMessageChunk", "content": "Ol", ...}]

event: messages/partial
data: [{"type": "AIMessageChunk", "content": "á!", ...}]

event: messages/complete
data: [{"type": "AIMessage", "content": "Olá!", ...}]

event: end
data: {"status": "success"}
```

Este é exatamente o mesmo protocolo que o Aegra usa nos seus endpoints nativos, o que significa que clientes que já consomem o streaming do Aegra funcionarão com nosso endpoint sem alterações.

---

## Como testar o streaming

```bash
# Streaming com curl (exibe os eventos SSE no terminal)
curl -N -X POST http://localhost:2026/api/v1/threads/<THREAD_ID>/chat/stream \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Conte uma história curta."}'
```

A flag `-N` desativa o buffer do curl, mostrando cada evento SSE assim que chega.

Exemplo de saída esperada:
```
event: metadata
data: {"run_id": "abc123", "attempt": 1}

event: messages/metadata
data: {"msg_001": {"metadata": {"langgraph_node": "call_model"}}}

event: messages/partial
data: [{"type": "AIMessageChunk", "content": "Era"}]

event: messages/partial
data: [{"type": "AIMessageChunk", "content": " uma vez"}]

...

event: messages/complete
data: [{"type": "AIMessage", "content": "Era uma vez..."}]

event: end
data: {"status": "success"}
```

---

## Resumo das mudanças

| Arquivo | O que mudou |
|---------|-------------|
| `src/auth/jwt.py` | Novo — handler `@auth.authenticate` que valida nossos JWTs |
| `aegra.json` | Seção `"auth"` com o handler JWT + seção `"http.cors"` para o frontend |
| `src/api/routes/threads.py` | Novo endpoint `POST /{id}/chat/stream` com `StreamingResponse` |


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

Esse padrão já existia no `ThreadService` como `_fetch`. Extraímos um helper privado `_fetch_user` que centraliza a lógica — qualquer alteração na mensagem de erro ou no status code agora exige um único edit.

### `src/services/thread_service.py` — constante e helper

Dois problemas corrigidos:

1. **Magic string `"agent"`** — aparecia em dois lugares (`create_thread` e `get_history`). Agora há uma constante de módulo:

   ```python
   _DEFAULT_GRAPH_ID = "agent"
   ```

2. **Extração de conteúdo duplicada** — a linha `content = msg.content if isinstance(msg.content, str) else str(msg.content)` repetia em `chat` e `get_history`. Extraído como:

   ```python
   def _extract_content(msg: object) -> str:
       content = getattr(msg, "content", "")
       return content if isinstance(content, str) else str(content)
   ```

### `src/services/thread_service.py` — remoção de query redundante em `chat` e `stream_chat`

Os métodos `chat` e `stream_chat` chamavam `_fetch` internamente para verificar ownership da thread. Porém, o route handler que chama esses métodos já havia feito essa verificação via `get_thread` logo antes. Resultado: **duas queries idênticas** contra a tabela `thread` em toda requisição de chat.

A verificação foi removida dos métodos internos e a responsabilidade de verificar ownership permanece no route handler (que já faz isso). O parâmetro `user_id` foi removido de `chat` e `stream_chat` já que não era mais usado:

```python
# antes
return await thread_service.chat(thread_id, body.message, assistant, user_id=str(current_user.id))

# depois
return await thread_service.chat(thread_id, body.message, assistant)
```

### `src/schemas/thread.py` — `status` tipado com `Literal`

O campo `status` de `ThreadRead` era `str`, com os valores válidos documentados apenas em um comentário. Substituído por:

```python
status: Literal["idle", "busy", "interrupted", "error"]
```

Isso fornece validação automática pelo Pydantic, documentação no schema OpenAPI e checagem de tipo estático.

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
├── test_thread_service.py   # ThreadService — CRUD, chat, stream_chat, get_history
├── test_auth_handler.py     # src.auth.jwt.authenticate (handler do Aegra)
├── test_routes_auth.py      # rotas /api/v1/auth/* (integração com httpx)
└── test_routes_threads.py   # rotas /api/v1/threads/* (integração com httpx)
```

### Como rodar

```bash
# Todos os testes com cobertura
cd backend
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# Um arquivo específico
uv run pytest tests/test_user_service.py -v

# Um teste específico
uv run pytest tests/test_thread_service.py::test_chat_passes_correct_config_and_context -v
```

### Cobertura atual

| Módulo | Cobertura |
|--------|-----------|
| `src/core/security.py` | 100% |
| `src/api/routes/auth.py` | 100% |
| `src/api/routes/threads.py` | 100% |
| `src/services/user_service.py` | 98% |
| `src/services/auth_service.py` | 97% |
| `src/services/thread_service.py` | 97% |
| `src/auth/jwt.py` | 95% |

**79 testes, todos passando em ~0.6s.**

### Decisões de design

- **Serviços testados com mocks puros** — `AsyncMock(spec=AsyncSession)` e `AsyncMock(spec=LangGraphService)`, sem banco de dados real.
- **Rotas testadas com `httpx.AsyncClient`** e `app.dependency_overrides` — sem subir infraestrutura.
- **bcrypt com `rounds=4`** no conftest para que os testes de senha rodem em milissegundos (produção usa `rounds=12`).
- **`session.refresh.side_effect`** popula `created_at`/`updated_at` nos objetos ORM durante os testes, já que esses campos só têm `server_default` (o banco os preenche em produção).
- **`stream_chat`** testado com async generators reais (`async def fake_astream`) em vez de `AsyncMock`, para respeitar o protocolo de iteração assíncrona.

