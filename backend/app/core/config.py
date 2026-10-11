from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Deployment concern only (e.g. _COOKIE_SECURE) — TS-07 split adapter
    # selection into the four settings below. Do not branch adapter code on
    # this; it no longer means "which backend does the app talk to."
    app_env: str = "local"
    secret_key: str = "change-me"

    resume_store: str = "local"  # local | drive
    mailer: str = "local"  # local | gmail
    calendar_store: str = "local"  # local | google
    embedder: str = "fastembed"  # fastembed | openai (openai not implemented)
    analyzer: str = "local"  # local | llm

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

    # ANALYZER=llm talks OpenAI-compatible Chat Completions, which Gemini, Grok,
    # Groq, OpenRouter and Ollama all speak — so the provider is a base_url, not
    # a vendor SDK, and switching is three lines of .env with no code change.
    # Only free tiers are in scope for this project; see .env.example.
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""
    # Hybrid ranking weight (ADR-006): final = (1-w)*cosine + w*llm.
    # 0.0 reproduces US-18's pure-cosine ordering exactly — the escape hatch if
    # the model proves unreliable, and asserted by a test.
    llm_score_weight: float = 0.3
    # Free tiers are token-limited and resume_parser imposes no ceiling, so the
    # resume is truncated before it reaches a prompt.
    llm_max_resume_chars: int = 6000

    smtp_host: str = "mailhog"
    smtp_port: int = 1025

    max_resume_mb: int = 5

    # Single hardcoded admin identity (TS-14) — no separate password, no
    # is_admin DB column. Still requires a real Google-authenticated session;
    # this just gates which authenticated recruiter may reach /admin/*.
    admin_email: str = ""

    # Where LocalResumeStore writes resume folders (RESUME_STORE=local).
    # Defaults to the docker-compose mount; not every process runs in that
    # container (CI, a host .venv), so this must be overridable rather than
    # hardcoded.
    local_storage_root: str = "/storage"

    # IANA name. Single app-wide zone, not per-recruiter (US-24) — every TIME
    # column on scheduling_preferences is wall-clock in this zone. Written onto
    # each row at insert time rather than read live, so changing this later
    # doesn't silently reinterpret already-saved availability windows.
    scheduling_timezone: str = "Asia/Karachi"


settings = Settings()
