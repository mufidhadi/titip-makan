from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Titip Makan MTN CORE"
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8080
    database_url: str = "sqlite+aiosqlite:///./data/titip_makan.db"
    coordinator_pin: str = "1234"
    waha_base_url: str = "https://waha.masmuf.cloud"
    waha_api_key: str = ""
    default_group_chat_id: str = "120363409564046383@g.us"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
