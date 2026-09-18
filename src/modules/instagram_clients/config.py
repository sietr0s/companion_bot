"""Instagram clients module settings."""

from pydantic_settings import BaseSettings


class InstagramClientsSettings(BaseSettings):
    INSTAGRAM_POLL_INTERVAL_S: float = 20
    INSTAGRAM_SESSION_DIR: str = "sessions/instagram"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


instagram_clients_settings = InstagramClientsSettings()
