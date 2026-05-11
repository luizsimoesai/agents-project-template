# agents-project-template

Template de agente LangGraph com backend FastAPI, autenticação JWT e frontend Next.js.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e Docker Compose
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Task](https://taskfile.dev/installation/)

---

## Passo a passo: do clone ao primeiro agente

### 1. Configurar o ambiente

```bash
cd backend
cp .env.example .env
```

Edite o `.env` e preencha pelo menos:

- `JWT_SECRET_KEY` — mínimo 32 caracteres (gere com `openssl rand -hex 32`)
- `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY` — chave do provedor de LLM

### 2. Instalar dependências

```bash
uv sync
```

### 3. Subir o banco de dados

```bash
docker compose up postgres -d
```

### 4. Rodar as migrations

```bash
uv run alembic upgrade head
```

### 5. Subir o servidor

```bash
task run
# Servidor: http://localhost:2026
# Docs (Swagger): http://localhost:2026/docs
```

---

## Criando o primeiro usuário admin

O endpoint `POST /api/v1/auth/register` é público, mas cria usuários comuns (`is_admin=false`). A promoção a admin é feita via SQL — isso é intencional por segurança.

### Registrar o usuário

```bash
curl -X POST http://localhost:2026/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Admin", "email": "admin@example.com", "password": "senha123!"}'
```

Ou use a interface em `http://localhost:2026/docs` → `POST /api/v1/auth/register`.

### Promover a admin via SQL

```bash
docker exec -it backend-postgres psql -U backend -d backend \
  -c "UPDATE users SET is_admin = true WHERE email = 'admin@example.com';"
```

### Fazer login e obter o JWT

```bash
curl -X POST http://localhost:2026/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "senha123!"}'
```

Resposta:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

---

## Criando um novo assistente (agente)

O Aegra expõe a [LangGraph API](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref/) na mesma porta. O grafo `agent` está registrado em `aegra.json`.

```bash
curl -X POST http://localhost:2026/assistants \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "graph_id": "agent",
    "name": "Meu Agente",
    "config": {
      "configurable": {
        "model": "anthropic/claude-sonnet-4-6",
        "system_prompt": "Você é um assistente útil."
      }
    }
  }'
```

Modelos disponíveis seguem o formato `"provider/model"`, ex:
- `"anthropic/claude-sonnet-4-6"`
- `"openai/gpt-4o-mini"`
- `"ollama/llama3.2"` (requer Ollama local)

---

## Resetar o banco de dados

```bash
docker compose down -v        # para e remove o volume
docker compose up postgres -d # recria o container
uv run alembic upgrade head   # reaplicar as migrations
```

---

## Stack do projeto

| Camada    | Tecnologia                        |
|-----------|-----------------------------------|
| Backend   | FastAPI + Aegra + LangGraph       |
| Agente    | LangGraph ReAct (tools + LLM)     |
| Banco     | PostgreSQL + SQLAlchemy + Alembic |
| Auth      | JWT (access + refresh tokens)     |
| Frontend  | Next.js                           |
