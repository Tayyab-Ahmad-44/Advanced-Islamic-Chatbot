import deepl
from core.config import settings
from services.open_ai_service import openai_service

import logging
logger = logging.getLogger(__name__)



class Deepl_Service():
    
    def __init__(self):
        
        self.translator = deepl.Translator(auth_key=settings.DEEPL_API_KEY)
        
        
        
        
    def detect_and_translate_query(self, query: str)-> dict:
        
        try: 
            # First check if already in English
            is_english = openai_service.is_english_with_llm(query)
            logger.info(f"is_english_with_llm result: {is_english}")
            
            if is_english:
                
                logger.info("English query detected successfully")
                return {
                    "status": "success", 
                    "processed_query": query, 
                    "detected_language": "EN",
                    "translation_needed": False
                }
            
            
            logger.info("Non-English query detected, translating...")
            translated_query = self.translator.translate_text(query, target_lang="EN-US")
            detected_lang = translated_query.detected_source_lang
            logger.info(f"Detected language: {detected_lang}")
            
            
            print(f"Detected language: {detected_lang}")
                
                
            if detected_lang.upper() in ["RU", "UK"]:
                logger.info(f"Translated from supported language {detected_lang.upper()}")
                # return {"status": "success", "processed_query": translated_query.text, "detected_language": detected_lang.upper()}
                return {"status": "success", "processed_query": query, "detected_language": detected_lang.upper()}
        
        
            return {
                "status": "success", 
                "processed_query": query,
                "detected_language": detected_lang
            }
                
                
        except deepl.exceptions.AuthorizationException:
            return {
                "status": "error", 
                "message": "DeepL API authentication failed. Please check your API key."
            }
            
            
        except deepl.exceptions.QuotaExceededException:
            return {
                "status": "error", 
                "message": "DeepL API quota exceeded. Please try again later."
            }
            
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to detect and translate input query: {str(e)}"
            }
        
        
        
        
    def translate_response(self, response: str, detected_lang:str)-> str:
        
        logger.debug("Inside translate_response | Detected language: %s", detected_lang)
        
       
        if detected_lang.upper() != "EN":
            try:
                translated = self.translator.translate_text(response, target_lang="RU")
                logger.info("Translated response to RU successfully")
                return translated.text
        

            except Exception as e:
                logger.error("Translation error: %s", e)
                return response

        logger.debug("No translation needed; returning original response.")
        return response
    


