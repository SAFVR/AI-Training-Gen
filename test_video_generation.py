import httpx
import asyncio
import json
import sys
import time
from loguru import logger

# Configure logger to output to console with timestamps
logger.remove()
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="INFO")

async def test_video_generation():
    url = "http://localhost:8000/api/generate_video"
    
    # Create a sample request payload
    payload = {
        "job_title": "Chemical Plant Operator",
        "job_description": "Operates and monitors chemical processing equipment in an industrial plant. Workers need to understand safety protocols for handling hazardous materials and emergency procedures.",
        "industry": "Chemical Manufacturing",
        "target_audience": "Plant operators and technicians",
        "key_points": [
            "Proper handling of hazardous chemicals", 
            "Emergency shutdown procedures", 
            "Personal protective equipment usage",
            "Spill containment protocols",
            "Safety monitoring systems"
        ],
        "video_type": "image",  # Using IMAGE type as it's faster to generate
        "duration_minutes": 1  # Keep it short for testing
    }
    
    start_time = time.time()
    logger.info("Starting video generation test")
    
    try:
        logger.info(f"Sending video generation request to: {url}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        async with httpx.AsyncClient(timeout=900.0) as client:  # 15 minute timeout for longer processing
            try:
                response = await client.post(url, json=payload)
                logger.info(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Video generation completed successfully!")
                    logger.info(f"Local video URL: {result.get('video_url')}")
                    logger.info(f"S3 video URL: {result.get('s3_video_url')}")
                    logger.info(f"Creatomate video URL: {result.get('creatomate_video_url')}")
                    logger.info(f"Job Title: {result.get('job_title')}")
                    logger.info(f"Course Title: {result.get('course_title')}")
                    logger.info(f"Duration: {result.get('duration')} seconds")
                    logger.info(f"Clip count: {result.get('clip_count')}")
                    logger.info(f"Video Type: {result.get('video_type')}")
                    logger.info(f"Created At: {result.get('created_at')}")
                    logger.info(f"Total processing time: {time.time() - start_time:.2f} seconds")
                else:
                    logger.error(f"Error response: {response.text}")
                    try:
                        error_json = response.json()
                        logger.error(f"Error details: {json.dumps(error_json, indent=2)}")
                    except Exception:
                        logger.error("Could not parse error response as JSON")
            except httpx.TimeoutException:
                logger.error("Request timed out after 15 minutes")
            except httpx.ConnectError:
                logger.error("Connection error - is the server running?")
            except httpx.RequestError as e:
                logger.error(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"Error in video generation test: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_video_generation())