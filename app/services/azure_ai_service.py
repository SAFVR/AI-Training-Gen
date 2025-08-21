import httpx
import os
import json
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.config import settings

class AzureAIService:
    def __init__(self):
        self.endpoint = settings.AZURE_AI_ENDPOINT
        self.api_key = settings.AZURE_AI_API_KEY
        self.model_id = settings.AZURE_AI_MODEL_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_image(self, prompt: str, output_path: str) -> str:
        """Generate an image using Azure AI"""
        try:
            payload = {
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
                "output_format": "png"
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Azure OpenAI endpoint format
                response = await client.post(
                    f"{self.endpoint}/openai/deployments/{self.model_id}/images/generations?api-version=2025-04-01-preview",
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Handle both URL and base64 response formats
                if "url" in result["data"][0]:
                    # Download the image from URL
                    image_url = result["data"][0]["url"]
                    image_response = await client.get(image_url)
                    image_response.raise_for_status()
                    image_bytes = image_response.content
                elif "b64_json" in result["data"][0]:
                    # Decode base64 image data
                    import base64
                    image_data = result["data"][0]["b64_json"]
                    image_bytes = base64.b64decode(image_data)
                else:
                    raise Exception("No image data found in response")
                
                # Save the image to the output path
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                
                return output_path
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
                
            # Log detailed HTTP error information
            logger.error(f"Azure AI API error: Status {e.response.status_code} - {error_detail}")
            raise Exception(f"Azure AI API error: {e.response.status_code} - {error_detail}") from e
            
        except httpx.RequestError as e:
            # Log detailed connection error information
            error_msg = f"Azure AI connection error: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Connection details - Endpoint: {self.endpoint}, Model: {self.model_id}")
            logger.error(f"Request details - Headers: {self.headers.keys()}, Payload keys: {payload.keys() if 'payload' in locals() else 'N/A'}")
            raise Exception(f"Failed to connect to Azure AI API: {str(e)}") from e
            
        except Exception as e:
            # Log more detailed information about the general exception
            error_msg = f"Error generating image with Azure AI: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Request context - Endpoint: {self.endpoint}, Model: {self.model_id}")
            # Include traceback information for debugging
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise Exception(f"Azure AI image generation failed: {str(e)}") from e

# Create a singleton instance
azure_ai_service = AzureAIService()