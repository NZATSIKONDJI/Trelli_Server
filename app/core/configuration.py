from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuration(BaseSettings):
    environnement: str = Field(default="development", validation_alias="APP_ENV")
    url_bdd: str = Field(default="sqlite:///./project.db", validation_alias="DATABASE_URL")
    secret_jwt: str = Field(default="development-only-secret-change-me-32-chars", validation_alias="JWT_SECRET")
    origine_client: str = Field(default="http://localhost:8080", validation_alias="CLIENT_ORIGIN")
    cookie_securise: bool = Field(default=False, validation_alias="COOKIE_SECURE")
    duree_jeton_minutes: int = Field(default=30, validation_alias="ACCESS_TOKEN_MINUTES")
    mot_de_passe_demo: str = Field(default="ChangeMe-2026!", validation_alias="DEMO_PASSWORD")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("secret_jwt")
    @classmethod
    def valider_secret(cls, valeur: str) -> str:
        if len(valeur) < 32:
            raise ValueError("JWT_SECRET doit contenir au moins 32 caractères")
        return valeur


@lru_cache
def obtenir_configuration() -> Configuration:
    return Configuration()


configuration = obtenir_configuration()

