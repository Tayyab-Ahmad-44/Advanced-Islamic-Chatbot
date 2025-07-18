
from fastapi import FastAPI

from core.config import settings
from core.logging import configure_logging
from services.groq_service import groq_service
from services.open_ai_service import openai_service
from schemas.routes.text_query import TextQuerySchema
from schemas.routes.audio_query import AudioQuerySchema
from services.langgraph_service import LanggraphService


configure_logging()


application = FastAPI()


qdrant_configs = {
    "quran": {
        "url": settings.QURAN_QDRANT_URL,
        "api_key": settings.QURAN_QDRANT_API_KEY,
        "collection": settings.QURAN_COLLECTION_NAME
    },
    "hadith": {
        "url": settings.HADITH_QDRANT_URL,
        "api_key": settings.HADITH_QDRANT_API_KEY,
        "collection": settings.HADITH_COLLECTION_NAME
    },
    "tafseer": {
        "url": settings.TAFSEER_QDRANT_URL,
        "api_key": settings.TAFSEER_QDRANT_API_KEY,
        "collection": settings.TAFSEER_COLLECTION_NAME
    },
    "general_islamic_info": {
        "url": settings.GENERAL_ISLAMIC_INFO_URL,
        "api_key": settings.GENERAL_ISLAMIC_INFO_KEY,
        "collection": settings.ISLAMIC_INFO_COLLECTION_NAME
    }
}

langgraph_service = LanggraphService(qdrant_configs)


@application.get("/")
async def main():
    return {"Version": settings.VERSION}





@application.post('/text_query')
async def process_text_query(request: TextQuerySchema):  
    """Process user text query and return Islamic chatbot response"""

    try:
        translation_response = openai_service.convert_query_to_english(request.query)
        if translation_response["status"] == "error":
            return translation_response


        query = translation_response["message"]


        response = langgraph_service.query(query.text)


        if query.is_russian:
            conversion_response = openai_service.convert_response_to_russian(response)
            if conversion_response["status"] == "error":
                return conversion_response

            response = conversion_response['message']


        return {"status": "success", "message": response}

    except Exception as e:
        return {"status": "error", "message": f"Error processing query: {e}"}





@application.post('/audio_query')
async def process_audio_query(request: AudioQuerySchema):
    """Process user audio query and return Islamic chatbot response"""    

    try:
        file_path = request.file_path

        transcription_response = groq_service.transcribe_auto(file_path)
        if transcription_response["status"] == "error":
            return transcription_response


        translation_response = openai_service.convert_query_to_english(transcription_response["message"])
        if translation_response["status"] == "error":
            return translation_response


        query = translation_response["message"]


        response = langgraph_service.query(query.text)


        if query.is_russian:
            conversion_response = openai_service.convert_response_to_russian(response)
            if conversion_response["status"] == "error":
                return conversion_response

            response = conversion_response['message']


        return {"status": "success", "message": response}

    except Exception as e: 
        return {"status": "error", "message": f"Error processing query: {e}"}
