
from typing import Literal, List

from pydantic import BaseModel, Field


class QueryClassificationSchema(BaseModel):
    """Structured output for query classification"""
    required_sources: List[Literal['quran', 'hadith', 'tafseer', 'islamic_info']] = Field(
        description="List of required sources from: quran, hadith, tafseer"
    ) 
    reasoning: str = Field(
        description="Brief explanation of why these sources were selected"
    )
