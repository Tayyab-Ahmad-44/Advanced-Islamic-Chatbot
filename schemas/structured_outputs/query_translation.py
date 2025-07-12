
from pydantic import BaseModel, Field


class TranslateQuerySchema(BaseModel):
    """Schema for translating text."""

    text: str = Field(description="Text in English")
    is_russian: bool = Field(default=False, description="True if the original query is in Russian, False otherwise")
