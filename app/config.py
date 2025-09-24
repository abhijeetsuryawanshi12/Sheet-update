# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GOOGLE_SHEET_NAME: str
    WORKSHEET_NAME: str
    GOOGLE_CREDENTIALS_PATH: str
    GOOGLE_API_KEY: str # We'll keep this in case you use other Google AI features later
    
    # --- ADD THESE LINES ---
    HF_API_TOKEN: str
    HF_EMBEDDING_API_URL: str = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2"

    CHROMA_PERSIST_PATH: str = "chroma_db"
    CHROMA_COLLECTION_NAME: str = "companies"

    class Config:
        env_file = ".env"

settings = Settings()
