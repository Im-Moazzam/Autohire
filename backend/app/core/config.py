from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "local"
    secret_key: str = "change-me"

    # Fail loudly: nothing works safely without these.
    token_encryption_key: str
    database_url: str
    redis_url: str

    frontend_url: str = "http://localhost:5173"
    public_apply_base_url: str = "http://localhost:5173/apply"
    vite_api_url: str = "http://localhost:8000/api/v1"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    # Passed explicitly to fastembed's TextEmbedding(cache_dir=...) rather than
    # relying on its own env-var name (which has changed across versions) —
    # a wrong env var gives a silent per-container re-download, not an error.
    embedding_cache_dir: str = "/models"

    # Reserved: no cloud analyzer exists yet (TS-07 may add an optional
    # OpenAI embedder) — not dead, just not read by anything today.
    openai_api_key: str = ""

    smtp_host: str = "mailhog"
    smtp_port: int = 1025

    max_resume_mb: int = 5

    # Where LocalResumeStore writes resume folders (APP_ENV=local). Defaults to
    # the docker-compose mount; not every process runs in that container (CI,
    # a host .venv), so this must be overridable rather than hardcoded.
    local_storage_root: str = "/storage"

    # IANA name. Single app-wide zone, not per-recruiter (US-24) — every TIME
    # column on scheduling_preferences is wall-clock in this zone. Written onto
    # each row at insert time rather than read live, so changing this later
    # doesn't silently reinterpret already-saved availability windows.
    scheduling_timezone: str = "Asia/Karachi"


settings = Settings()
