# Frontend Design Spec — Chat App com Aegra + LangGraph

**Data:** 2026-03-28
**Stack:** Next.js 15 (App Router) · Tailwind CSS · shadcn/ui · TanStack Query · @langchain/langgraph-sdk

---

## 1. Contexto

Frontend completo de uma aplicação web de chat com assistentes IA. Conecta-se a um backend existente (FastAPI + LangGraph via Aegra) expondo autenticação JWT, CRUD de assistentes, gerenciamento de conversas e streaming de mensagens via SSE.

O backend corre num único servidor Aegra que expõe simultaneamente:
- Endpoints customizados FastAPI: `POST /api/v1/auth/*`, `/api/v1/users/*`, `/api/v1/assistants/*`, `/api/v1/threads/*`
- Endpoints nativos LangGraph (protocolo Agent): `POST /threads/{id}/runs/stream`, etc.

O auth handler do Aegra (`src/auth/jwt.py:auth`) aplica-se a **todos** os endpoints, incluindo os nativos LangGraph.

---

## 2. Stack Técnica

| Pacote | Uso |
|---|---|
| `next` (App Router) | Framework, roteamento, middleware |
| `tailwindcss` | Estilização utilitária |
| `shadcn/ui` | Componentes base (Button, Dialog, Sheet, Toast, Table, etc.) |
| `@tanstack/react-query` | Cache e gestão de estado servidor para CRUD |
| `@langchain/langgraph-sdk` | `useStream` para chat streaming |
| `zustand` | Estado global mínimo de auth (access token + user) |
| `next-themes` | Dark/light mode via classe `dark` no `<html>` |
| `sonner` | Toasts de feedback |
| `zod` | Validação de formulários |
| `react-hook-form` | Gestão de formulários |

---

## 3. Identidade Visual

- **Cor de destaque:** `#136ddd` — usada em títulos, labels de role no chat, botões primários, ícones ativos na sidebar
- **Fonte mono:** `font-mono` em labels de role (`assistant` / `você`), campos `model`/`system_prompt`, IDs de assistente/thread
- **Bordas:** sutis (`border border-border`), sem sombras excessivas, `rounded-md` máximo
- **Temas:** dark/light com `next-themes`; CSS variables do shadcn/ui compatíveis nativamente

---

## 4. Arquitetura de Pastas

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── signup/page.tsx
│   ├── (app)/
│   │   ├── layout.tsx            ← AppLayout: sidebar dupla + proteção JWT
│   │   ├── assistants/
│   │   │   ├── page.tsx          ← lista de assistentes no painel contextual
│   │   │   └── [id]/
│   │   │       ├── page.tsx      ← edição do assistente
│   │   │       └── threads/
│   │   │           ├── page.tsx          ← lista de conversas
│   │   │           └── [threadId]/
│   │   │               └── page.tsx      ← interface de chat
│   │   ├── profile/page.tsx      ← perfil do usuário logado
│   │   └── admin/page.tsx        ← lista de usuários (admin only)
│   ├── middleware.ts              ← redireciona não-autenticados para /login
│   └── layout.tsx                ← root layout com ThemeProvider
├── components/
│   ├── layout/
│   │   ├── AppSidebar.tsx        ← barra de ícones esquerda
│   │   └── ContextPanel.tsx      ← segundo painel (assistentes / conversas / admin)
│   ├── assistants/
│   │   ├── AssistantCard.tsx
│   │   └── AssistantForm.tsx     ← Sheet modal para criar/editar
│   ├── threads/
│   │   └── ThreadItem.tsx
│   ├── chat/
│   │   ├── ChatView.tsx          ← orquestra histórico + streaming
│   │   ├── ChatMessage.tsx       ← uma mensagem estilo terminal
│   │   └── ChatInput.tsx         ← textarea + envio + stop
│   ├── admin/
│   │   └── AdminUserTable.tsx
│   └── ui/                       ← componentes shadcn/ui gerados
├── lib/
│   ├── api/
│   │   ├── client.ts             ← apiClient: fetch + Bearer + refresh automático
│   │   ├── auth.ts               ← funções: login, signup, refresh, me
│   │   ├── assistants.ts
│   │   ├── threads.ts
│   │   └── users.ts
│   ├── hooks/
│   │   ├── useAssistants.ts
│   │   ├── useThreads.ts
│   │   ├── useUsers.ts
│   │   └── useProfile.ts
│   └── store/
│       └── auth.ts               ← Zustand: { accessToken, user, setAuth, clearAuth }
└── .env.local
    NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 5. Navegação — Sidebar Dupla

### Coluna de ícones (esquerda, 52px)

Ícones na ordem:
1. Logo (topo)
2. **Assistentes** (`LayoutList`) — acende em `#136ddd` quando ativo
3. **Perfil** (`User`)
4. **Tema** (`Sun` / `Moon` — `ThemeToggle`)
5. **Admin** (`ShieldCheck`) — **visível somente se `user.is_admin === true`**, acende em `#136ddd` quando ativo
6. **Logout** (`LogOut`) — no rodapé

### Painel contextual (segunda coluna, ~220px)

Muda conforme ícone selecionado:
- **Assistentes**: lista de assistentes do usuário + botão "Novo assistente"
- **Assistente selecionado**: lista de conversas daquele assistente + botão "Nova conversa"
- **Admin**: lista de usuários com campo de busca e filtro de status

### Área principal

Chat, formulário de assistente ou perfil conforme rota.

---

## 6. Módulos

### 6.1 Autenticação

**Rotas públicas:** `/login`, `/signup`

**Endpoints:**
- `POST /api/v1/auth/login` → `{ access_token, refresh_token }`
- `POST /api/v1/auth/register` → cria conta e redireciona para login
- `POST /api/v1/auth/refresh` → novo par de tokens
- `GET /api/v1/auth/me` → dados do usuário autenticado

**Fluxo:**
1. Login → salva `access_token` no Zustand (memória) + cookie `access_token` (não-httpOnly, para o middleware) e `refresh_token` em `localStorage`
2. `apiClient` injeta `Authorization: Bearer <access_token>` (lido do Zustand) em toda requisição
3. Resposta 401 → tenta refresh; se OK repete a request original com novo token; se falhar → `clearAuth()` + redirect `/login`
4. Logout → `clearAuth()` + remove cookie + limpa `localStorage` + redirect `/login`
5. `middleware.ts` lê o cookie `access_token` (acessível no Edge); redireciona para `/login` se ausente. Validação completa do JWT ocorre no servidor Aegra — o middleware apenas verifica presença do cookie.

**Campos de formulário:**
- Login: email, senha
- Signup: nome, email, senha (mínimo 8 caracteres)

### 6.2 Perfil do Usuário

**Rota:** `/profile`

**Endpoints:**
- `GET /api/v1/auth/me` → exibe dados atuais
- `PATCH /api/v1/users/{id}` → atualiza nome e/ou email

Campos editáveis: nome, email. Senha não é alterável via esta tela (o backend não expõe campo de troca de senha no `UserUpdate`).

### 6.3 Assistentes

**Rota:** `/assistants` + `/assistants/{id}`

**Endpoints:**
- `GET /api/v1/assistants` → lista (escopo do usuário autenticado)
- `POST /api/v1/assistants` → criar
- `PATCH /api/v1/assistants/{id}` → editar
- `DELETE /api/v1/assistants/{id}` → apagar

**Formulário (Sheet lateral):**
- `name` — obrigatório
- `description` — opcional
- `context.model` — campo texto com placeholder `anthropic/claude-sonnet-4-6` (fonte mono)
- `context.system_prompt` — textarea com placeholder de instruções (fonte mono)

`graph_id` é sempre `"agent"` (fixo, não exposto ao usuário).

Ação de apagar requer confirmação via `AlertDialog`.

### 6.4 Conversas (Chat)

**Rotas:** `/assistants/{id}/threads` + `/assistants/{id}/threads/{threadId}`

**Endpoints:**
- `GET /api/v1/threads` → lista (filtrada no cliente por `assistant_id`)
- `POST /api/v1/threads` → criar (body: `{ assistant_id, thread_name }`)
- `DELETE /api/v1/threads/{id}` → apagar
- `GET /api/v1/threads/{id}/history` → histórico de mensagens ao abrir conversa

**Streaming — `useStream`:**

```ts
import { useStream } from "@langchain/langgraph-sdk/react"

const { messages, submit, isStreaming, stop } = useStream({
  apiUrl: process.env.NEXT_PUBLIC_API_URL,
  assistantId: thread.assistant_id,   // Aegra assistant_id
  threadId: thread.thread_id,
  defaultHeaders: {
    Authorization: `Bearer ${accessToken}`,  // do Zustand store
  },
  messagesKey: "messages",
})
```

O hook chama `POST /threads/{id}/runs/stream` no servidor Aegra diretamente (endpoint nativo LangGraph), que já tem auth JWT aplicada.

**Visual das mensagens (estilo terminal):**
```
assistant  ←  label mono em #136ddd
Olá! Como posso ajudar você hoje?
─────────────────────────────────
você       ←  label mono em cor neutra
Me ajude com uma tarefa complexa
─────────────────────────────────
assistant
Claro! Vou analisar...█  ←  cursor piscando durante streaming
```

`ChatInput`: textarea multilinha, Enter envia, Shift+Enter nova linha, botão Stop visível durante streaming.

### 6.5 Painel Administrativo

**Rota:** `/admin` — acessível apenas se `user.is_admin === true`

**Endpoints:**
- `GET /api/v1/users?skip=0&limit=100` → lista todos os usuários
- `PATCH /api/v1/users/{id}/activate` → ativar usuário
- `PATCH /api/v1/users/{id}/deactivate` → desativar usuário
- `DELETE /api/v1/users/{id}` → apagar usuário

**Funcionalidades:**
- Tabela com colunas: nome, email, status (ativo/inativo), data de criação, ações
- Busca por nome (filtro client-side)
- Filtro por status: Todos / Ativos / Inativos
- Ações por linha: ativar/desativar, apagar (com `AlertDialog`)

`AdminGuard`: se `!user.is_admin`, renderiza página 403 em vez do conteúdo.

---

## 7. Estado Global (Zustand)

```ts
interface AuthStore {
  accessToken: string | null
  user: UserRead | null        // { id, name, email, is_admin, is_active, created_at }
  setAuth: (token: string, user: UserRead) => void  // também grava cookie access_token
  clearAuth: () => void                              // também remove cookie e localStorage
}
```

Todo estado de servidor (listas, detalhes) fica no TanStack Query, não no Zustand.

---

## 8. API Client

```ts
// lib/api/client.ts
async function apiClient(path, options) {
  const { accessToken } = useAuthStore.getState()
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options.headers,
    },
  })
  if (res.status === 401) {
    // tenta refresh
    const refreshed = await tryRefresh()
    if (refreshed) return apiClient(path, options)  // repete com novo token
    clearAuth(); redirect("/login")
  }
  return res
}
```

---

## 9. Tratamento de Erros

| Cenário | Comportamento |
|---|---|
| 401 token expirado | Refresh automático transparente |
| 401 após refresh falhar | `clearAuth()` + redirect `/login` + toast "Sessão expirada" |
| 403 não-admin em `/admin` | Página 403 com botão voltar |
| 422 validação | Toast com mensagem do campo inválido extraída do body |
| 500 | Toast genérico "Erro no servidor, tente novamente" |
| Stream interrompido | Toast "Conexão perdida" + botão reenviar visível no `ChatInput` |
| Ação destrutiva | `AlertDialog` de confirmação antes de DELETE |

---

## 10. Responsividade

- Sidebar dupla colapsa em mobile: ícones viram menu bottom bar; painel contextual vira drawer
- Área de chat ocupa 100% da tela em mobile
- Tabela admin usa scroll horizontal em telas pequenas

---

## 11. Endpoints Backend Mapeados

| Método | Path | Uso |
|---|---|---|
| POST | `/api/v1/auth/register` | Signup |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/refresh` | Refresh token |
| GET | `/api/v1/auth/me` | Usuário atual |
| PATCH | `/api/v1/users/{id}` | Editar perfil |
| GET | `/api/v1/users` | Lista usuários (admin) |
| PATCH | `/api/v1/users/{id}/activate` | Ativar usuário (admin) |
| PATCH | `/api/v1/users/{id}/deactivate` | Desativar usuário (admin) |
| DELETE | `/api/v1/users/{id}` | Apagar usuário (admin) |
| GET | `/api/v1/assistants` | Lista assistentes |
| POST | `/api/v1/assistants` | Criar assistente |
| PATCH | `/api/v1/assistants/{id}` | Editar assistente |
| DELETE | `/api/v1/assistants/{id}` | Apagar assistente |
| GET | `/api/v1/threads` | Lista conversas |
| POST | `/api/v1/threads` | Criar conversa |
| DELETE | `/api/v1/threads/{id}` | Apagar conversa |
| GET | `/api/v1/threads/{id}/history` | Histórico de mensagens |
| POST | `/threads/{id}/runs/stream` | Chat streaming (Aegra nativo, via `useStream`) |
