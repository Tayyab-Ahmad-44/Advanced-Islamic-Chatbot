
from fastapi import FastAPI, APIRouter, HTTPException


from core.config import settings
from core.app_logging import configure_logging
from services.groq_service import groq_service
from services.open_ai_service import openai_service
from schemas.routes.text_query import TextQuerySchema
from schemas.routes.audio_query import AudioQuerySchema
from services.langgraph_service import LanggraphService
from services.deepL_service import Deepl_Service


configure_logging()
import logging

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
deepl_services = Deepl_Service()



@application.get("/")
async def main():
    return {"Version": settings.VERSION}





@application.post('/text_query')
async def process_text_query(request: TextQuerySchema):  
    """Process user text query and return Islamic chatbot response"""
    user_input = request.query.strip()
    logging.info(f"Received user query: {user_input}")

    try:
        translation_result = deepl_services.detect_and_translate_query(user_input)
        logging.info(f"Translation result: {translation_result}")
        
        if translation_result.get("status") != "success":
            logging.error("Language detection or translation failed.")
            raise HTTPException(status_code=400, detail="Language detection or translation failed.")
        
        
        processed_query =  translation_result["processed_query"]
        detected_lang =  translation_result["detected_language"]
        
        logging.info(f"Processed query inside Application.py : {processed_query}")
        logging.info(f"Detected language inside application.py : {detected_lang}")
        
        #query to llm
        llm_response = langgraph_service.query(processed_query, detected_lang)
        
        if not llm_response:
            logging.error("LLM response generation failed.")
            raise HTTPException(status_code=500, detail="Failed to generate LLM response.")
        
        return {
            "status": "success",
            "message": llm_response }



    except Exception as e:
    
        return {
            "status": "error",
            "message": f"Error processing query: {str(e)}"
        }





@application.post('/audio_query')
async def process_audio_query(request: AudioQuerySchema):
    """Process user audio query and return Islamic chatbot response"""    

    try:
        file_path = request.file_path

        transcription_response = groq_service.transcribe_auto(file_path)
        if transcription_response["status"] == "error":
            return transcription_response

        query = transcription_response["message"]
        print(f"voice to query : {query}")
        
        translation_result = deepl_services.detect_and_translate_query(query)
        
          
        if translation_result.get("status") != "success":
            raise HTTPException(status_code=400, detail="Language detection or translation failed.")
        
        
        processed_query =  translation_result["processed_query"]
        detected_lang =  translation_result["detected_language"]
        
        
        #query to llm
        llm_response = langgraph_service.query(processed_query, detected_lang)
        
        if not llm_response:
            raise HTTPException(status_code=500, detail="Failed to generate LLM response.")
        
           
        final_response = deepl_services.translate_response(llm_response, detected_lang)

        return {
            "status": "success",
            "message": final_response }



    except Exception as e:
    
        return {
            "status": "error",
            "message": f"Error processing query: {str(e)}"
        }

     




        

    
