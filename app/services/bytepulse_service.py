import httpx
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.config import settings

class BytePulseService:
    def __init__(self):
        self.api_key = settings.BYTEPULSE_API_KEY
        self.api_url = "https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_video(self, prompt: str, output_path: str) -> str:
        """Generate a video clip using BytePulse API"""
        try:
            # Format the prompt according to BytePulse API requirements
            formatted_prompt = f"{prompt} --resolution 1080p --duration 10 --camerafixed false"
            
            payload = {
                "model": "seedance-1-0-pro-250528",  # Use the model from settings if available
                "content": [
                    {
                        "type": "text",
                        "text": formatted_prompt
                    }
                ]
            }
            
            # Log the request details for debugging
            logger.debug(f"BytePulse API request: {self.api_url}")
            logger.debug(f"BytePulse API payload: {json.dumps(payload)}")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Step 1: Create the generation task
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Log the initial response
                logger.debug(f"BytePulse API initial response: {json.dumps(result)}")
                
                # Extract the task ID from the response
                task_id = result.get("id")
                if not task_id:
                    raise Exception("No task ID returned from BytePulse API")
                
                logger.info(f"BytePulse video generation task created with ID: {task_id}")
                
                # Step 2: Poll the task status until it's complete
                max_retries = 30  # Maximum number of retries (30 * 10 seconds = 5 minutes)
                for attempt in range(max_retries):
                    # Wait for 25 seconds between status checks
                    await asyncio.sleep(25)
                    
                    # Query the task status
                    status_url = f"https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks/{task_id}"
                    status_response = await client.get(
                        status_url,
                        headers=self.headers
                    )
                    
                    status_response.raise_for_status()
                    status_result = status_response.json()
                    
                    logger.debug(f"BytePulse task status (attempt {attempt+1}): {json.dumps(status_result)}")
                    
                    # Check if the task is complete
                    status = status_result.get("status")
                    if status == "succeeded":
                        # Get the video URL from the result
                        video_url = None
                        
                        # Check for video_url in the content field
                        if "content" in status_result and "video_url" in status_result["content"]:
                            video_url = status_result["content"]["video_url"]
                            logger.debug(f"Found video URL in status_result[content][video_url]: {video_url}")
                        
                        # Fallback: check for video URL in different response structures
                        if not video_url:
                            contents = status_result.get("result", {}).get("content", [])
                            for content in contents:
                                if content.get("type") == "video":
                                    video_url = content.get("url")
                                    logger.debug(f"Found video URL in result.content[].url: {video_url}")
                                    break
                        
                        if not video_url and status_result.get("outputs"):
                            for output in status_result.get("outputs", []):
                                if output.get("type") == "video":
                                    video_url = output.get("url")
                                    logger.debug(f"Found video URL in outputs[].url: {video_url}")
                                    break
                        
                        # Log the full response for debugging
                        if not video_url:
                            logger.error(f"Could not find video URL in response: {json.dumps(status_result)}")
                            raise Exception("No video URL found in completed task result")
                        
                        # Download the video
                        video_response = await client.get(video_url)
                        video_response.raise_for_status()
                        
                        # Save the video to the output path
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, "wb") as f:
                            f.write(video_response.content)
                            
                        logger.info(f"BytePulse video downloaded and saved to {output_path}")
                        break
                    elif status == "failed":
                        error_message = status_result.get("error", {}).get("message", "Unknown error")
                        raise Exception(f"BytePulse task failed: {error_message}")
                    
                    # If we've reached the maximum number of retries, raise an exception
                    if attempt == max_retries - 1:
                        raise Exception(f"BytePulse task timed out after {max_retries} attempts")
                
                return output_path
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_json = e.response.json()
                error_detail = json.dumps(error_json, indent=2)
                # Check for specific BytePulse API error format
                if "error" in error_json and "message" in error_json["error"]:
                    error_message = error_json["error"]["message"]
                    error_code = error_json["error"].get("code", "unknown")
                    error_type = error_json["error"].get("type", "unknown")
                    logger.error(f"BytePulse API error: Status {e.response.status_code} - Code: {error_code}, Type: {error_type}, Message: {error_message}")
                    logger.error(f"Full error details: {error_detail}")
                    raise Exception(f"BytePulse API error: {error_message} (Code: {error_code})") from e
            except json.JSONDecodeError:
                error_detail = e.response.text
                
            # If we didn't handle a specific error format above, use the generic format
            logger.error(f"BytePulse API error: Status {e.response.status_code} - {error_detail}")
            logger.error(f"Request URL: {e.request.url}")
            logger.error(f"Request method: {e.request.method}")
            logger.error(f"Request headers: {e.request.headers}")
            raise Exception(f"BytePulse API error: {e.response.status_code} - {error_detail}") from e
            
        except httpx.RequestError as e:
            logger.error(f"BytePulse connection error: {str(e)}")
            raise Exception(f"Failed to connect to BytePulse API: {str(e)}") from e
            
        except Exception as e:
            logger.error(f"Error generating video with BytePulse: {str(e)}")
            raise Exception(f"BytePulse video generation failed: {str(e)}") from e

# Create a singleton instance
bytepulse_service = BytePulseService()