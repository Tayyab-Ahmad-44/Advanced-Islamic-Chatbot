
from pydantic import BaseModel


class UserQuerySchema(BaseModel):
    """Schema for user query data"""
    
    query: str