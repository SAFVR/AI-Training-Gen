import httpx
import asyncio
import json
import sys
import time
from loguru import logger

# Configure logger to output to console with timestamps
logger.remove()
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="INFO")

async def test_caption_generator():
    url = "http://localhost:8000/api/caption_generator"
    
    # Create a sample request payload with a valid S3 URL
    payload = {
        "title": "Test Caption Generator",
        "description": "Testing improved error handling in caption generator endpoint",
        "video_url": "https://your-s3-bucket.s3.amazonaws.com/test-video.mp4"  # Replace with a valid S3 URL
    }
    
    start_time = time.time()
    logger.info("Starting caption generator test")
    
    try:
        logger.info(f"Sending caption generator request to: {url}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        async with httpx.AsyncClient(timeout=900.0) as client:  # 15 minute timeout
            try:
                response = await client.post(url, json=payload)
                logger.info(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Caption generation completed successfully!")
                    logger.info(f"Original Video URL: {result.get('original_video_url')}")
                    logger.info(f"Creatomate Video URL: {result.get('creatomate_video_url')}")
                    logger.info(f"Title: {result.get('title')}")
                    logger.info(f"Description: {result.get('description')}")
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
        logger.error(f"Error in caption generator test: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

# Test with invalid URL to trigger error handling
async def test_caption_generator_with_invalid_url():
    url = "http://localhost:8000/api/caption_generator"
    
    # Create a sample request payload with an invalid URL
    payload = {
        "title": "Test Caption Generator Error Handling",
        "description": "Testing error handling with invalid URL",
        "video_url": "invalid-url"  # Invalid URL to trigger error
    }
    
    logger.info("Starting caption generator test with invalid URL")
    
    try:
        logger.info(f"Sending caption generator request with invalid URL to: {url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:  # Shorter timeout for error case
            try:
                response = await client.post(url, json=payload)
                logger.info(f"Status Code: {response.status_code}")
                
                # We expect an error response
                logger.info(f"Response: {response.text}")
                try:
                    error_json = response.json()
                    logger.info(f"Error details: {json.dumps(error_json, indent=2)}")
                except Exception:
                    logger.error("Could not parse error response as JSON")
            except Exception as e:
                logger.error(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"Error in invalid URL test: {str(e)}")

async def run_tests():
    # Run both tests sequentially
    logger.info("=== Testing with valid URL ===")
    await test_caption_generator()
    
    logger.info("\n=== Testing with invalid URL ===")
    await test_caption_generator_with_invalid_url()

if __name__ == "__main__":
    asyncio.run(run_tests())