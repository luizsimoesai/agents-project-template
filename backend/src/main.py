from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.api.routes.auth import router as auth_router
from src.api.routes.models import router as models_router
from src.api.routes.users import router as users_router
from src.core.rate_limit import limiter

app = FastAPI()
# Register the shared limiter so @limiter.limit(...) decorators on routes
# resolve, and install slowapi's middleware + 429 handler.
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(_request: object, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "FastAPI is running!"}


# All auth endpoints live under /api/v1/auth (no JWT required).
app.include_router(auth_router, prefix="/api/v1")

# All user CRUD endpoints live under /api/v1/users (JWT required on all routes).
app.include_router(users_router, prefix="/api/v1")

# All model catalog endpoints live under /api/v1/models.
app.include_router(models_router, prefix="/api/v1")
