import asyncio
import httpx
from loguru import logger

async def test_caption_generator():
    """Test the caption generator endpoint"""
    # Configure logger
    logger.remove()
    logger.add(lambda msg: print(msg, end=""))
    
    # Test data with an S3 video URL
    test_data = {
        "title": "Test Caption Generation",
        "description": "Testing the caption generator endpoint",
        "video_url": "https://your-s3-bucket.s3.amazonaws.com/your-test-video.mp4"  # Replace with a real S3 URL
    }
    
    logger.info("Testing caption generator endpoint...")
    
    try:
        # Send request to the caption generator endpoint
        async with httpx.AsyncClient(timeout=600.0) as client:  # 10-minute timeout
            response = await client.post(
                "http://localhost:8000/api/caption_generator",
                json=test_data
            )
            
            # Log response status
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                # Parse and log the successful response
                result = response.json()
                logger.info("Caption generation successful!")
                logger.info(f"Original video URL: {result['original_video_url']}")
                logger.info(f"Creatomate video URL: {result['creatomate_video_url']}")
                logger.info(f"Title: {result['title']}")
                logger.info(f"Description: {result['description']}")
                logger.info(f"Created at: {result['created_at']}")
            else:
                # Log error response
                logger.error(f"Error: {response.text}")
    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_caption_generator())