from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_MIN_JWT_SECRET_LEN = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    postgres_user: str = "backend"
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "backend"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    @field_validator("jwt_secret_key")
    @classmethod
    def _validate_jwt_secret(cls, v: str) -> str:
        if len(v) < _MIN_JWT_SECRET_LEN:
            raise ValueError(
                f"JWT_SECRET_KEY must be at least {_MIN_JWT_SECRET_LEN} characters. "
                "Generate one with: openssl rand -hex 32"
            )
        return v

    # When True, every SQL statement is printed to stdout. Keep False in production.
    db_echo_log: bool = False
    sqlalchemy_pool_size: int = 2
    sqlalchemy_max_overflow: int = 0

    # Set False in tests (or if rate limiting is enforced upstream by a CDN/proxy).
    rate_limit_enabled: bool = True

    # Auth cookie flags. Set COOKIE_SECURE=false for HTTP dev; production must
    # leave this True so cookies are not transmitted over plain HTTP.
    cookie_secure: bool = True

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
