import httpx
import os
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.config import settings

class ElevenLabsService:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.api_url = settings.ELEVENLABS_API_URL
        self.voice_id = settings.ELEVENLABS_VOICE_ID
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def generate_audio(self, text: str, output_path: str) -> str:
        """Generate audio narration using ElevenLabs API"""
        try:
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_url}/text-to-speech/{self.voice_id}",
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()
                
                # Save the audio to the output path
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                return output_path
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
                
            logger.error(f"ElevenLabs API error: Status {e.response.status_code} - {error_detail}")
            raise Exception(f"ElevenLabs API error: {e.response.status_code} - {error_detail}") from e
            
        except httpx.RequestError as e:
            logger.error(f"ElevenLabs connection error: {str(e)}")
            raise Exception(f"Failed to connect to ElevenLabs API: {str(e)}") from e
            
        except Exception as e:
            logger.error(f"Error generating audio with ElevenLabs: {str(e)}")
            raise Exception(f"ElevenLabs audio generation failed: {str(e)}") from e

# Create a singleton instance
elevenlabs_service = ElevenLabsService()