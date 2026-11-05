"""Instagram clients module settings."""

from src.core.settings import EnvironmentSettings


class InstagramClientsSettings(EnvironmentSettings):
    INSTAGRAM_POLL_INTERVAL_S: float = 20
    INSTAGRAM_SESSION_DIR: str = "sessions/instagram"


instagram_clients_settings = InstagramClientsSettings()
