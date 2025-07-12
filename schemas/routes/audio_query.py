
from pydantic import BaseModel


class AudioQuerySchema(BaseModel):
    """Schema for user query data"""
    
    file_path: str
