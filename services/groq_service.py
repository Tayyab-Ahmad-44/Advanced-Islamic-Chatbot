import os

from groq import Groq
from core.config import settings



class GroqService:
    def __init__(self):

        self.client = Groq(api_key=settings.GROQ_API_KEY)


    def transcribe_auto(
        self,
        file_path: str,
        model: str = "whisper-large-v3"
    ) -> str:
        """
        Transcribe an audio file (English or Russian) using Open Ai's Whisper model.
        """
        try:
            print(file_path)
            with open(file_path, "rb") as f:
                audio_bytes = f.read()
            
            
            response = self.client.audio.transcriptions.create(
                file=(os.path.basename(file_path), audio_bytes),
                response_format="text",
                model=model,
                #language=Language.RU,  # uncomment to force Russian
            )


            return {"status": "success", "message": response}

        except Exception as e:
            return {"status": "error", "message": f"Error transcribing audio: {e}"}


groq_service = GroqService()
