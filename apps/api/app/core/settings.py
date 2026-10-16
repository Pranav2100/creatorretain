from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "CreatorRetain API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Lets an owner move their own workspace between plans. The
    # stand-in for billing: switch off once a payment provider owns
    # the plan column.
    ALLOW_SELF_SERVE_PLAN_CHANGE: bool = True

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

    # Where this API answers. Used to build URLs for files it
    # serves itself, so it only matters while storage is local.
    API_URL: str = "http://127.0.0.1:8000"

    # Browser origins allowed to call the API, comma separated
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    # ------------------------------------------------------------------
    # File storage
    # ------------------------------------------------------------------
    # local    - this machine's own disk, for development
    # supabase - a Supabase Storage bucket
    STORAGE_BACKEND: str = "local"

    LOCAL_MEDIA_ROOT: str = "var/media"

    # Project URL, e.g. https://abcdefgh.supabase.co
    SUPABASE_URL: str | None = None

    # The service role key, not the anon key. It bypasses row level
    # security, so it stays on the server and never reaches a
    # browser.
    SUPABASE_SECRET_KEY: str | None = None
    
    SUPABASE_STORAGE_BUCKET: str = "public-media"

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