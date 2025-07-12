
from pydantic import BaseModel


class TextQuerySchema(BaseModel):
    """Schema for user query data"""
     
    query: str
