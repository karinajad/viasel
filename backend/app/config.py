from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://viasel:viasel@localhost:5432/viasel"
    API_TOKEN: str = "viasel-dev"  # shared key; set a real one in .env for deploy


settings = Settings()
