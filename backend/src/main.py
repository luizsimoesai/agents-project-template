from fastapi import FastAPI

from src.api.routes.auth import router as auth_router
from src.api.routes.models import router as models_router
from src.api.routes.users import router as users_router

app = FastAPI()


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "FastAPI is running!"}


# All auth endpoints live under /api/v1/auth (no JWT required).
app.include_router(auth_router, prefix="/api/v1")

# All user CRUD endpoints live under /api/v1/users (JWT required on all routes).
app.include_router(users_router, prefix="/api/v1")

# All model catalog endpoints live under /api/v1/models.
app.include_router(models_router, prefix="/api/v1")
