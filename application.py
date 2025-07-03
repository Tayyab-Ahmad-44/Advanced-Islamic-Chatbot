
from fastapi import FastAPI

from core.config import settings
from core.logging import configure_logging
from schemas.routes.user_query import UserQuerySchema
from services.langgraph_service import LanggraphService


configure_logging()


application = FastAPI()


qdrant_configs = {
    "quran": {
        "url": settings.QURAN_QDRANT_URL,
        "api_key": settings.QURAN_QDRANT_API_KEY,
        "collection": "quran_collection"
    },
    "hadith": {
        "url": settings.HADITH_QDRANT_URL,
        "api_key": settings.HADITH_QDRANT_API_KEY,
        "collection": "hadith_collection"
    },
    "tafseer": {
        "url": settings.TAFSEER_QDRANT_URL,
        "api_key": settings.TAFSEER_QDRANT_API_KEY,
        "collection": "tafseer_collection"
    }
}

langgraph_service = LanggraphService(qdrant_configs)


@application.get("/")
async def main():
    return {"Version": settings.VERSION}



@application.post('/query')
def process_user_query(request: UserQuerySchema):  
    """Process user query and return Islamic chatbot response"""

    try:
        query = request.query

        response = langgraph_service.query(query)

        return {"status": "success", "response": response} 

    except Exception as e: 
        return {"status": "error", "message": f"Error processing query: {e}"}
