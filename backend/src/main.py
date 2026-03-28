# custom_routes.py
from fastapi import FastAPI

from src.api.routes.assistants import router as assistants_router
from src.api.routes.auth import router as auth_router
from src.api.routes.threads import router as threads_router
from src.api.routes.users import router as users_router

app = FastAPI()


# This works — overrides the default root
@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "FastAPI is running!"}


# All auth endpoints live under /api/v1/auth (no JWT required).
app.include_router(auth_router, prefix="/api/v1")

# All user CRUD endpoints live under /api/v1/users (JWT required on all routes).
app.include_router(users_router, prefix="/api/v1")

# Assistant CRUD endpoints live under /api/v1/assistants (JWT required on all routes).
# Wraps Aegra's AssistantService — no migration needed, the table is owned by Aegra.
app.include_router(assistants_router, prefix="/api/v1")

# Thread and chat endpoints live under /api/v1/threads (JWT required on all routes).
# Threads are conversation sessions; chat execution uses LangGraphService directly.
app.include_router(threads_router, prefix="/api/v1")
