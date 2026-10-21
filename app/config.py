"""Application settings, loaded from CARD_* environment variables or .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    # .env is resolved from the project root so the app behaves the same
    # whatever directory uvicorn is started from.
    model_config = SettingsConfigDict(
        env_prefix="CARD_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    translations_json_path: Path = PROJECT_ROOT / "data" / "Translations_with_sources.json"
    fonts_dir: Path = PROJECT_ROOT / "assets" / "fonts"

    # JSON list, e.g. CARD_CORS_ORIGINS='["https://cards.example.org"]'
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # "production" refuses to start with localhost-only CORS (see main.create_app).
    environment: str = "development"
    log_level: str = "INFO"

    # Print sheet geometry.
    page_size: str = "letter"  # "letter" or "a4"
    default_cards_per_page: int = 4
    default_fold_cards_per_page: int = 4
    margin_inches: float = 0.5
    gutter_inches: float = 0.25
    footer_height_inches: float = 0.55

    # Caching: JSON and PDFs only change on redeploy.
    json_cache_seconds: int = 300
    pdf_cache_seconds: int = 3600
    pdf_cache_size: int = 64

    # PDF rendering is CPU-bound: bound concurrency and time, and limit each
    # client (0 disables the limit). Behind a proxy, run uvicorn with
    # --proxy-headers so the limit applies to the real client address.
    render_workers: int = 2
    render_timeout_seconds: float = 30.0
    render_rate_limit_per_minute: int = 20


settings = Settings()
