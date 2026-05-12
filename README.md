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
cd backend

uv venv
uv sync

uv run aegra dev # ou task run
```


```bash
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

## Registar um novo tipo de agente

O template usa uma convenção de dois ficheiros para expor novos grafos ao utilizador final:

**1. Registar o grafo no backend** (`backend/aegra.json`):

```json
{
  "graphs": {
    "agent":      "./src/agent/graph.py:graph",
    "deep_agent": "./src/agent/deepagents/graph.py:graph",
    "meu_agente": "./src/agent/meu_agente/graph.py:graph"
  }
}
```

**2. Adicionar a descrição no frontend** (`frontend/lib/graph-types.ts`):

```ts
export const GRAPH_TYPES: GraphType[] = [
  // ... entradas existentes ...
  {
    graph_id: "meu_agente",
    label: "Nome Amigável",
    description: "Uma frase explicando o que este agente faz.",
  },
]
```

O select de criação de assistentes usa este array — ao adicionar uma entrada aqui, a opção aparece imediatamente para o utilizador final. Se um assistente existente tiver um `graph_id` não listado, o badge na lista mostra o `graph_id` cru como fallback.

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
