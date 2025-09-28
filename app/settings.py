from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class ConfigSettings(BaseSettings):

    GEMINI_API_KEY: str = Field(...,description="API Key for Gemini LLM Access")
    
    GEMINI_MODEL: str = Field('gemini-2.5-flash',description="Name of model for Gemini to use")
    
    POLYGON_API_KEY : str = Field(...,description="API key for Polygon API Access")

    model_config = SettingsConfigDict(env_file='.env',env_file_encoding="utf-8")

Settings = ConfigSettings()