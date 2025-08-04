
from pydantic_settings import BaseSettings

from pathlib import Path

class Settings(BaseSettings):
    VERSION: str = "1.3"
    LOGGING_DIR: str = "logs"
    LLM_MODEL: str = "gpt-4.1-nano" 
    # LLM_MODEL: str = "gpt-4o"
    EMBEDDING_MODEL: str = "text-embedding-3-small"             #new added
    QURAN_COLLECTION_NAME: str = "English_Russain_quran_translation"        #updated
    HADITH_COLLECTION_NAME: str = "hadith_collection"
    TAFSEER_COLLECTION_NAME: str = "tafseer_collection"
    ISLAMIC_INFO_COLLECTION_NAME: str = "general_islamic_info"

    DEEPL_API_KEY: str
    GROQ_API_KEY: str
    TAVILY_API_KEY: str
    OPENAI_API_KEY: str 
    GEMINI_API_KEY: str
    QURAN_QDRANT_URL: str
    HADITH_QDRANT_URL: str
    TAFSEER_QDRANT_URL: str
    QURAN_QDRANT_API_KEY: str
    HADITH_QDRANT_API_KEY: str
    TAFSEER_QDRANT_API_KEY: str
    GENERAL_ISLAMIC_INFO_URL: str
    GENERAL_ISLAMIC_INFO_KEY: str


    class Config:
        env_file = env_file = Path(__file__).resolve().parent.parent / ".env"  # go up to project root



settings = Settings()
print(f'openai api key is {settings.OPENAI_API_KEY}')
print(f'DEEPL api key is {settings.DEEPL_API_KEY}')

import os

key = os.getenv("OPENAI_API_KEY")
print("Key from os.environ:", key)
