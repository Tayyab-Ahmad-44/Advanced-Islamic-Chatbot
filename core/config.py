
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    VERSION: str = "1.3"
    LOGGING_DIR: str = "logs"
    LLM_MODEL: str = "gpt-4.1-nano"

    GROQ_API_KEY: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    QURAN_QDRANT_URL: str
    HADITH_QDRANT_URL: str
    TAFSEER_QDRANT_URL: str
    QURAN_QDRANT_API_KEY: str
    HADITH_QDRANT_API_KEY: str
    TAFSEER_QDRANT_API_KEY: str


    class Config:
        env_file = ".env"



settings = Settings()
