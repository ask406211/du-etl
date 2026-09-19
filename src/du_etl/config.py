"""Single source of truth for configuration. Nothing else reads os.environ."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or .env."""

    du_feature_service_url: str
    database_url: str
    target_states: str = "CA"
    http_timeout: float = 30.0
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def states(self) -> list[str]:
        """TARGET_STATES as a normalised list: 'CA,or' -> ['CA', 'OR']."""
        return [s.strip().upper() for s in self.target_states.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    """Load settings once, on first use rather than at import."""
    return Settings()
