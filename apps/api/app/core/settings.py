from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "CreatorRetain API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/creatorretain"
    )

    # ------------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------------
    APP_URL: str = "http://localhost:3000"

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------
    INVITATION_TTL_DAYS: int = 30

    EMAIL_BACKEND: str = "console"
    EMAIL_FROM_NAME: str = "CreatorRetain"
    EMAIL_FROM_ADDRESS: str = "invites@example.com"

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = False

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()