from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load variables from a .env file in the working directory.
    # extra="ignore" means unknown env vars won't raise errors.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database connection ---
    # Option 1: provide a full connection string (takes priority when set).
    # Must use the asyncpg driver: postgresql+asyncpg://user:pass@localhost:5432/mydb
    database_url: str | None = None

    # Option 2: individual fields (used when DATABASE_URL is not set).
    # These match the variable names in .env.example.
    postgres_user: str = "backend"
    postgres_password: str = "backend_secret"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "backend"

    # --- JWT / Auth ---
    jwt_secret_key: str = "change-me-to-a-very-long-secret-key-at-least-32-chars!!"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- SQLAlchemy behaviour ---
    # When db_echo_log is True, every SQL statement is printed to stdout.
    # Useful for debugging queries; keep False in production.
    db_echo_log: bool = False

    # pool_size: number of persistent connections kept open.
    # max_overflow: extra connections allowed above pool_size under heavy load.
    sqlalchemy_pool_size: int = 2
    sqlalchemy_max_overflow: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def db_url(self) -> str:
        """Async URL used by the application (asyncpg driver).

        asyncpg is a non-blocking PostgreSQL driver that works natively with
        Python asyncio and FastAPI. Used by src/db/engine.py at runtime.
        """
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Single shared instance — import this everywhere instead of instantiating
# Settings() again, so the .env file is only read once.
settings = Settings()
