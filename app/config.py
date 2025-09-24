# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GOOGLE_SHEET_NAME: str
    WORKSHEET_NAME: str
    GOOGLE_CREDENTIALS_PATH: str

    class Config:
        env_file = ".env"

settings = Settings()