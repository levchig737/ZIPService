from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USER: str
    DB_PASS: str
    POSTGRES_PASSWORD: str

    MINIO_NAME: str
    MINIO_PORT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str

    KEYCLOAK_ADMIN: str
    KEYCLOAK_ADMIN_PASSWORD: str
    KC_DB: str
    KC_DB_URL: str
    KC_DB_USERNAME: str
    KC_DB_PASSWORD: str
    KC_HOSTNAME: str
    KC_PORT: str

    KEYCLOAK_CLIENT_SECRET: str
    SECRET: str
