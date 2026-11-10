"""Credentials required only when Auth seeds its initial administrator."""

from pydantic import SecretStr

from src.core.settings import EnvironmentSettings


class AuthBootstrapSettings(EnvironmentSettings):
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: SecretStr
