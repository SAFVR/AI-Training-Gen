import httpx
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.config import settings
from app.services.s3_service import s3_service

class CreatomateService:
    def __init__(self):
        self.api_key = settings.CREATOMATE_API_KEY
        self.template_id = settings.CREATOMATE_TEMPLATE_ID
        self.api_url = "https://api.creatomate.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def merge_media(self, video_paths: List[str], audio_paths: List[str], subtitles: List[str], output_path: str) -> str:
        """Merge video/image, audio, and subtitles using Creatomate API"""
        try:
            # Prepare source elements for each clip
            sources = []
            for i, (video_path, audio_path, subtitle) in enumerate(zip(video_paths, audio_paths, subtitles)):
                # Upload video/image file
                video_url = await self._upload_file(video_path)
                
                # Upload audio file
                audio_url = await self._upload_file(audio_path)
                
                # Create source element
                source = {
                    "type": "composition",
                    "elements": [
                        {
                            "type": "video",
                            "source": video_url,
                            "fit": "cover"
                        },
                        {
                            "type": "audio",
                            "source": audio_url
                        },
                        {
                            "type": "text",
                            "text": subtitle,
                            "y": "85%",
                            "width": "90%",
                            "height": "auto",
                            "x_alignment": "center",
                            "y_alignment": "center",
                            "fill_color": "#ffffff",
                            "stroke_color": "#000000",
                            "stroke_width": 0.1,
                            "font_family": "Roboto",
                            "font_weight": "bold",
                            "font_size": 36
                        }
                    ]
                }
                sources.append(source)
            
            # Create the final video
            payload = {
                "template_id": self.template_id,
                "output_format": "mp4",
                "width": 1920,
                "height": 1080,
                "framerate": 30,
                "elements": [
                    {
                        "type": "sequence",
                        "elements": sources
                    }
                ]
            }
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_url}/v1/renders",
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Download the final video
                video_url = result["url"]
                video_response = await client.get(video_url)
                video_response.raise_for_status()
                
                # Save the video to the output path
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(video_response.content)
                
                return output_path
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
                
            logger.error(f"Creatomate API error: Status {e.response.status_code} - {error_detail}")
            raise Exception(f"Creatomate API error: {e.response.status_code} - {error_detail}") from e
            
        except httpx.RequestError as e:
            logger.error(f"Creatomate connection error: {str(e)}")
            raise Exception(f"Failed to connect to Creatomate API: {str(e)}") from e
            
        except Exception as e:
            logger.error(f"Error merging media with Creatomate: {str(e)}")
            raise Exception(f"Creatomate media merging failed: {str(e)}") from e
    
    async def _upload_file(self, file_path: str) -> str:
        """Upload a file to S3 and get the URL for Creatomate to use"""
        try:
            logger.info(f"Uploading file to S3: {file_path}")
            
            # Check if S3 service is configured
            if not s3_service.s3_client or not s3_service.bucket_name:
                logger.warning("S3 not configured, falling back to direct Creatomate upload")
                return await self._upload_file_to_creatomate(file_path)
            
            # Upload to S3
            file_url = await s3_service.upload_file(file_path)
            if not file_url:
                logger.warning("S3 upload failed, falling back to direct Creatomate upload")
                return await self._upload_file_to_creatomate(file_path)
            
            logger.info(f"File successfully uploaded to S3: {file_url}")
            return file_url
            
        except Exception as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            logger.warning("S3 upload failed, falling back to direct Creatomate upload")
            return await self._upload_file_to_creatomate(file_path)
    
    async def _upload_file_to_creatomate(self, file_path: str) -> str:
        """Upload a file directly to Creatomate and get the URL (fallback method)"""
        try:
            logger.info(f"Uploading file directly to Creatomate: {file_path}")
            logger.debug(f"Using Creatomate API key: {self.api_key[:10]}...")
            
            # Get file size for logging
            file_size = os.path.getsize(file_path)
            logger.info(f"File size: {file_size / (1024 * 1024):.2f} MB")
            
            # Calculate timeout based on file size (300s base + 1s per MB)
            timeout = 300.0 + (file_size / (1024 * 1024))
            logger.info(f"Setting timeout to {timeout:.2f} seconds")
            
            # Use streaming upload instead of loading entire file into memory
            async with httpx.AsyncClient(timeout=timeout) as client:
                with open(file_path, "rb") as f:
                    response = await client.post(
                        f"{self.api_url}/v1/uploads",  # Use v1 endpoint
                        headers={
                            "Authorization": f"Bearer {self.api_key}"
                        },
                        files={
                            "file": (os.path.basename(file_path), f)
                        }
                    )
                
                response.raise_for_status()
                result = response.json()
                
                if "url" not in result:
                    logger.error(f"No URL in Creatomate upload response: {result}")
                    raise Exception(f"Creatomate upload failed: No URL in response")
                
                logger.info(f"File successfully uploaded to Creatomate")
                return result["url"]
                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
                
            logger.error(f"Creatomate upload API error: Status {e.response.status_code} - {error_detail}")
            raise Exception(f"Creatomate upload API error: {e.response.status_code} - {error_detail}") from e
            
        except httpx.RequestError as e:
            logger.error(f"Creatomate upload connection error: {str(e)}")
            raise Exception(f"Failed to connect to Creatomate upload API: {str(e)}") from e
            
        except Exception as e:
            logger.error(f"Error uploading file to Creatomate: {str(e)}")
            raise Exception(f"Creatomate file upload failed: {str(e)}") from e
            
    async def process_video_with_template(self, video_path, s3_video_url=None):
        """Process a video with a Creatomate template.
        
        Args:
            video_path: Path to the local video file. Can be None if s3_video_url is provided.
            s3_video_url: Optional URL to the video in S3. If provided, this URL will be used instead of uploading the video.
            
        Returns:
            str: URL of the processed video from Creatomate
        """
        try:
            # Use the provided S3 URL if available, otherwise upload the video
            if s3_video_url:
                video_url = s3_video_url
            elif video_path:
                video_url = await self._upload_file(video_path)
            else:
                raise ValueError("Either video_path or s3_video_url must be provided")
                
            logger.info(f"Using video URL for Creatomate: {video_url}")
            
            # Prepare the payload for the template rendering exactly as in the curl example
            payload = {
                "template_id": self.template_id,
                "modifications": {
                    "Video-DHM.source": video_url
                }
            }
            
            logger.info(f"Sending video to Creatomate template: {self.template_id}")
            logger.debug(f"Payload: {json.dumps(payload)}")
            
            # Call the Creatomate API to render the template with the video
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_url}/v2/renders",
                    headers=self.headers,
                    json=payload
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Log the response for debugging
                logger.debug(f"Creatomate API response: {result}")
                
                # Handle different response formats (list or dictionary)
                if isinstance(result, list) and len(result) > 0:
                    # If result is a list, get the first item
                    render_item = result[0]
                    processed_video_url = render_item.get("url") if isinstance(render_item, dict) else None
                elif isinstance(result, dict):
                    # If result is a dictionary
                    processed_video_url = result.get("url")
                else:
                    processed_video_url = None
                    
                if not processed_video_url:
                    logger.warning(f"No URL returned from Creatomate API. Response: {result}")
                    return video_path
                
                # Get the render ID for status checking
                render_id = None
                if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                    render_id = result[0].get('id')
                elif isinstance(result, dict):
                    render_id = result.get('id')
                
                if not render_id:
                    logger.warning(f"No render ID found in response, cannot check status. Response: {result}")
                    return video_path
                
                # Poll for render completion
                max_attempts = 30  # 5 minutes (10 seconds * 30)
                attempts = 0
                render_complete = False
                
                logger.info(f"Polling for render completion, ID: {render_id}")
                
                while attempts < max_attempts and not render_complete:
                    await asyncio.sleep(10)  # Wait 10 seconds between checks
                    
                    # Check render status
                    status_response = await client.get(
                        f"{self.api_url}/v2/renders/{render_id}",
                        headers=self.headers
                    )
                    
                    status_response.raise_for_status()
                    status_result = status_response.json()
                    
                    logger.debug(f"Render status: {status_result}")
                    
                    # Check if render is complete
                    if isinstance(status_result, dict) and (status_result.get('status') == 'completed' or status_result.get('status') == 'succeeded'):
                        render_complete = True
                        processed_video_url = status_result.get('url')
                        logger.info(f"Render completed, URL: {processed_video_url}")
                        # Return immediately when render is complete
                        logger.info(f"Video processed with Creatomate template, URL: {processed_video_url}")
                        return processed_video_url
                    elif isinstance(status_result, dict) and status_result.get('status') == 'failed':
                        error_message = status_result.get('error_message', status_result.get('error', 'Unknown error'))
                        logger.error(f"Render failed: {error_message}")
                        raise Exception(f"Creatomate render failed: {error_message}")
                    else:
                        logger.info(f"Render in progress, status: {status_result.get('status') if isinstance(status_result, dict) else 'unknown'}")
                    
                    attempts += 1
                
                # If we reach here, the render did not complete within the timeout period
                logger.warning("Render did not complete within the timeout period")
                return video_path
                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
                
            logger.error(f"Creatomate API error: Status {e.response.status_code} - {error_detail}")
            raise Exception(f"Creatomate API error: {e.response.status_code} - {error_detail}") from e
            
        except httpx.RequestError as e:
            logger.error(f"Creatomate connection error: {str(e)}")
            raise Exception(f"Failed to connect to Creatomate API: {str(e)}") from e
            
        except Exception as e:
            logger.error(f"Error processing video with Creatomate: {str(e)}")
            raise Exception(f"Creatomate video processing failed: {str(e)}") from e

# Create a singleton instance
creatomate_service = CreatomateService()