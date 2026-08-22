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

    openai_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index: str = "autohire"

    smtp_host: str = "mailhog"
    smtp_port: int = 1025

    max_resume_mb: int = 5
    allowed_resume_types: str = (
        "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    # Where LocalResumeStore writes resume folders (APP_ENV=local). Defaults to
    # the docker-compose mount; not every process runs in that container (CI,
    # a host .venv), so this must be overridable rather than hardcoded.
    local_storage_root: str = "/storage"


settings = Settings()
