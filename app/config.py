# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GOOGLE_SHEET_NAME: str
    WORKSHEET_NAME: str
    GOOGLE_CREDENTIALS_PATH: str
    GOOGLE_API_KEY: str 
    GEMINI_API_KEY: str
    
    HF_API_TOKEN: str
    HF_EMBEDDING_API_URL: str = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2"

    # --- UPDATE PINECONE SETTINGS ---
    PINECONE_API_KEY: str
    # PINECONE_ENVIRONMENT is no longer needed for Serverless
    PINECONE_INDEX_NAME: str = "companies"

    DATABASE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()