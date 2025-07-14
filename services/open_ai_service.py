
import json
from typing import Any

import openai
from pydantic import BaseModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import HumanMessage, SystemMessage

from core.config import settings
from schemas.structured_outputs.query_classification import QueryClassificationSchema
from schemas.structured_outputs.query_translation import TranslateQuerySchema

from services.prompt_templates import (
    QUERY_CLASSIFICATION_PROMPT, FINAL_RESPONSE_PROMPT,
    TRANSLATE_TO_ENGLISH, TRANSLATE_TO_RUSSIAN
)



class OpenAIService:
    """Handles interactions with OpenAI"""

    def __init__(self, openai_model: str, openai_api_key: str):
        openai.api_key = openai_api_key
        self.llm = ChatOpenAI(model=openai_model, api_key=openai_api_key)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=openai_api_key)





    def classify_multi_source_query(self, query):
        """Classify a query to determine which resources are needed."""

        return self._process_request(QUERY_CLASSIFICATION_PROMPT, query, QueryClassificationSchema)





    def generate_response(self, query, context):
        """Generate a comprehensive/final response to a query."""

        prompt = self._replacer(FINAL_RESPONSE_PROMPT, context=context)

        return self._process_request(prompt, query, None)




    def convert_query_to_english(self, query):
        """Translate the Russian query to English if it is."""

        return self._process_request(TRANSLATE_TO_ENGLISH, query, TranslateQuerySchema)





    def convert_response_to_russian(self, query):
        """Translate the english text to Russian"""

        return self._process_request(TRANSLATE_TO_RUSSIAN, query)





    def _replacer(self, prompt: str, **kwargs: Any) -> str:
        """Replaces placeholders in a prompt with actual serialized values."""
        print("Hi")

        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"

            if placeholder not in prompt:
                continue 

            if isinstance(value, str):
                replacement = value

            elif isinstance(value, (dict, list)):
                replacement = json.dumps(value, ensure_ascii=False, indent=2)

            elif isinstance(value, BaseModel):
                replacement = json.dumps(value.model_dump(), ensure_ascii=False, indent=2)

            else:
                try:
                    replacement = json.dumps(value, ensure_ascii=False, indent=2)
                except TypeError:
                    replacement = str(value)

            prompt = prompt.replace(placeholder, replacement)

        return prompt





    def _process_request(
        self, prompt: str, text: str, schema=None
    ):
        """Generic method to handle requests to OpenAI"""

        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=text)
            ]


            # Initialize llm_instance with structured output if schema is provided else use simple llm to invoke.
            llm_instance = self.llm.with_structured_output(schema) if schema else self.llm  
            response = llm_instance.invoke(messages)


            print(response)


            return {"status": "success", "message": response.content if not schema else response}

        except Exception as e:
            return {"status": "error", "message": f"Error processing request: {e}"}



openai_service = OpenAIService(settings.LLM_MODEL, settings.OPENAI_API_KEY)
