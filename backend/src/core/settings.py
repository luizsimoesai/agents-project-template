from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    postgres_user: str = "backend"
    postgres_password: str = "backend_secret"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "backend"

    jwt_secret_key: str = "change-me-to-a-very-long-secret-key-at-least-32-chars!!"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # When True, every SQL statement is printed to stdout. Keep False in production.
    db_echo_log: bool = False
    sqlalchemy_pool_size: int = 2
    sqlalchemy_max_overflow: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
