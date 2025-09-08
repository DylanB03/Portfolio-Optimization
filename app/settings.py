from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class ConfigSettings(BaseSettings):

    GEMINI_API_KEY: str = Field(...,description="API Key for Gemini LLM Access")

    model_config = SettingsConfigDict(env_file='.env',env_file_encoding="utf-8")

Settings = ConfigSettings()